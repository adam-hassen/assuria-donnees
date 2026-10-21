"""
Simulateur de prix d'assurance auto et moto (objectif 1).

Il fonctionne comme le tarif d'un assureur :
    prix = prix de base de l'offre (profil de référence) x coefficients du profil

  1. Prix de base : pour chaque offre réelle et chaque formule (tiers, intermédiaire, tous risques),
     à partir des prix d'entrée publiés par l'assureur, sinon de la référence de marché du pays (config/prix_base.yaml).
  2. Coefficients appris sur des sinistres réels (comme les assureurs, avec des modèles GLM) :
       auto : freMTPL2 (France, 678 000 contrats) ; moto : swmotorcycle (Suède, 64 000 contrats).
       Fréquence des sinistres (Poisson) x coût moyen (Gamma) = prime pure, ramenée à 1 pour le profil de référence.
  3. Règles du marché : bonus-malus (coefficient 0,50 à 3,50), surprime jeune conducteur (+100 %, +50 %, +25 %),
     pas de tarif selon le sexe (interdit dans l'UE depuis 2012), refus des profils hors cible.
  4. Profils : générés pour couvrir tous les cas (âge, permis, véhicule, zone, usage, sinistres, pays, auto/moto).

Sorties (data/clean/simulation/) :
  prix_base.parquet, coefficients.json, profils.parquet, devis_simules.parquet, README.md

Lancement :  python -m src.simulateur
"""
from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
import yaml

warnings.filterwarnings("ignore")
RACINE = Path(__file__).resolve().parents[1]
RAW = RACINE / "data" / "raw"
OFFRES = RACINE / "data" / "clean" / "offres" / "offres_europe.parquet"
SORTIE = RACINE / "data" / "clean" / "simulation"
CONFIG = RACINE / "config" / "prix_base.yaml"
GRAINE = 2026
FORMULES = ["tiers", "intermediaire", "tous_risques"]


def log(msg: str) -> None:
    print(f"[simulateur] {msg}", flush=True)


# ====================================================================== 1. prix de base
def formules_disponibles(o: pd.Series) -> list[str]:
    """Formules proposées par une offre, d'après les garanties de son document (IPID)."""
    f = ["tiers"]
    if o.g_vol or o.g_incendie or o.g_bris_de_glace:
        f.append("intermediaire")
    if o.g_dommages_vehicule:
        f.append("tous_risques")
    return f


def reference_pays(cfg: dict, pays: str, type_: str) -> dict[str, float]:
    r, ref = cfg["ratios_marche"], cfg["references_pays"][pays]
    base = {"tiers": ref["tiers"],
            "intermediaire": ref.get("intermediaire", ref["tiers"] * r["intermediaire_sur_tiers"]),
            "tous_risques": ref.get("tous_risques", ref["tiers"] * r["tous_risques_sur_tiers"])}
    if type_ == "moto":
        base = {f: v * r["moto_sur_auto"][f] for f, v in base.items()}
    return base


def construire_prix_base(offres: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    connus = {(p["pays"], p["type"], p["assureur"]): p for p in cfg["prix_assureurs"]}
    lignes = []
    for _, o in offres.iterrows():
        if o.pays not in cfg["references_pays"]:
            continue
        ref = reference_pays(cfg, o.pays, o.type)
        publie = connus.get((o.pays, o.type, o.assureur), {})
        # positionnement de l'assureur par rapport au marché (moyenne sur les formules dont le prix est publié)
        ecarts = [publie[f] / ref[f] for f in FORMULES if f in publie]
        facteur = float(np.mean(ecarts)) if ecarts else 1.0
        formules = formules_disponibles(o)
        formules += [f for f in FORMULES if f in publie and f not in formules]
        for f in FORMULES:
            if f not in formules:
                continue
            if f in publie:
                prix, source = publie[f], "prix d'entrée publié par l'assureur"
            elif ecarts:
                prix, source = ref[f] * facteur, "déduit du prix d'entrée publié par l'assureur (autre formule)"
            else:
                prix, source = ref[f], "référence de marché du pays"
            lignes.append({"id_offre": o.id_offre, "pays": o.pays, "type": o.type, "assureur": o.assureur,
                           "produit": o.produit, "formule": f, "prix_base_annuel": round(float(prix), 2),
                           "source_prix_base": source, "lien_source_prix": publie.get("source", cfg["references_pays"][o.pays]["source"]),
                           "url_offre": o.url_source})
    df = pd.DataFrame(lignes)
    # cohérence : tiers <= intermédiaire <= tous risques pour une même offre
    for oid, g in df.groupby("id_offre"):
        prix = g.set_index("formule")["prix_base_annuel"]
        for a, b in [("tiers", "intermediaire"), ("intermediaire", "tous_risques"), ("tiers", "tous_risques")]:
            if a in prix and b in prix and prix[b] < prix[a] * 1.03:
                df.loc[(df.id_offre == oid) & (df.formule == b), "prix_base_annuel"] = round(prix[a] * 1.03, 2)
                prix[b] = prix[a] * 1.03
    return df


# ====================================================================== 2. coefficients (GLM)
TRANCHES_AGE = [17, 20, 25, 30, 40, 50, 60, 70, 120]
NOMS_AGE = ["18-20", "21-25", "26-30", "31-40", "41-50", "51-60", "61-70", "71+"]


def tranche(x, bornes, noms):
    return pd.cut(x, bornes, labels=noms, right=True).astype(str)


def relativites(modele, variables: dict[str, str]) -> dict[str, dict[str, float]]:
    """exp(coefficients) du GLM, ramenés à 1 pour la modalité de référence de chaque variable."""
    out = {}
    for var, ref in variables.items():
        niveaux = {}
        for nom, coef in modele.params.items():
            if nom.startswith(f"C({var}[T."):
                niveaux[nom.split("[T.")[1].rstrip("]")] = float(np.exp(coef))
        niveaux[ref] = 1.0
        out[var] = niveaux
    return out


def combiner(freq: dict, sev: dict) -> dict:
    out = {}
    for var in freq:
        out[var] = {k: round(freq[var][k] * sev.get(var, {}).get(k, 1.0), 4) for k in freq[var]}
    return out


def coefficients_auto() -> dict:
    f = pd.read_parquet(RAW / "freMTPL2freq.parquet")
    s = pd.read_parquet(RAW / "freMTPL2sev.parquet")
    f = f.astype({"ClaimNb": float, "Exposure": float, "VehPower": int, "VehAge": int, "DrivAge": int}).copy()
    f["IDpol"] = f["IDpol"].astype(float).astype(int)
    f["Exposure"] = f["Exposure"].clip(0.01, 1)
    f["ClaimNb"] = f["ClaimNb"].clip(upper=4)
    f["age"] = tranche(f.DrivAge, TRANCHES_AGE, NOMS_AGE)
    f["puissance"] = pd.cut(f.VehPower, [0, 4, 5, 6, 7, 8, 10, 99], labels=["4", "5", "6", "7", "8", "9-10", "11+"]).astype(str)
    f["age_vehicule"] = pd.cut(f.VehAge, [-1, 0, 2, 5, 10, 15, 200], labels=["0", "1-2", "3-5", "6-10", "11-15", "16+"]).astype(str)
    f["zone"] = f["Area"].astype(str)
    f["carburant"] = f["VehGas"].astype(str)
    refs = {"age": "51-60", "puissance": "5", "age_vehicule": "3-5", "zone": "C", "carburant": "Regular"}
    formule = "ClaimNb ~ " + " + ".join(f"C({v}, Treatment('{r}'))" for v, r in refs.items())
    freq = smf.glm(formule, data=f, family=sm.families.Poisson(), offset=np.log(f.Exposure)).fit()
    s["IDpol"] = s["IDpol"].astype(float).astype(int)
    s["ClaimAmount"] = s["ClaimAmount"].astype(float)
    s = s[s.ClaimAmount > 0]
    s["ClaimAmount"] = s.ClaimAmount.clip(upper=s.ClaimAmount.quantile(0.995))   # gros sinistres écrêtés
    sev_df = s.groupby("IDpol").ClaimAmount.mean().rename("cout").reset_index().merge(f, on="IDpol")
    sev = smf.glm(formule.replace("ClaimNb", "cout"), data=sev_df,
                  family=sm.families.Gamma(sm.families.links.Log())).fit()
    coefs = combiner(relativites(_renommer(freq, refs), refs), relativites(_renommer(sev, refs), refs))
    return {"variables": coefs, "references": refs, "contrats": int(len(f)), "sinistres": int(len(sev_df))}


def _renommer(modele, refs):
    """statsmodels nomme 'C(age, Treatment('51-60'))[T.18-20]' -> on garde 'C(age[T.18-20]'."""
    class M:
        pass
    m = M()
    m.params = pd.Series({k.replace(f", Treatment('{refs[k.split(',')[0][2:]]}'))", "") if k.startswith("C(") else k: v
                          for k, v in modele.params.items()})
    return m


def coefficients_moto() -> dict:
    d = pd.read_parquet(RAW / "swmotorcycle.parquet")
    d = d.astype({"OwnerAge": int, "VehAge": int, "Exposure": float, "ClaimNb": float, "ClaimAmount": float})
    d = d[(d.OwnerAge >= 16) & (d.Exposure > 0)].copy()
    d["Exposure"] = d.Exposure.clip(0.01, 3)
    d["age"] = tranche(d.OwnerAge, TRANCHES_AGE, NOMS_AGE).replace({"nan": "18-20"})
    d["classe_puissance"] = d.RiskClass.astype(str).str.replace("EV ratio ", "")
    d["age_vehicule"] = pd.cut(d.VehAge, [-1, 2, 5, 10, 15, 200], labels=["0-2", "3-5", "6-10", "11-15", "16+"]).astype(str)
    zones = {"Central parts of Sweden's three largest cities": "grande_ville", "Suburbs; middle-sized cities": "urbain",
             "Lesser towns except Gotland; Northern towns": "periurbain", "Northern towns": "periurbain"}
    d["zone"] = d.Area.astype(str).map(zones).fillna("rural")
    refs = {"age": "51-60", "classe_puissance": "9-12", "age_vehicule": "3-5", "zone": "urbain"}
    formule = "ClaimNb ~ " + " + ".join(f"C({v}, Treatment('{r}'))" for v, r in refs.items())
    freq = smf.glm(formule, data=d, family=sm.families.Poisson(), offset=np.log(d.Exposure)).fit()
    sv = d[d.ClaimAmount > 0].copy()
    sv["cout"] = (sv.ClaimAmount / sv.ClaimNb.clip(lower=1)).clip(upper=sv.ClaimAmount.quantile(0.99))
    sev = smf.glm("cout ~ C(classe_puissance, Treatment('9-12'))", data=sv,
                  family=sm.families.Gamma(sm.families.links.Log())).fit()
    coefs = combiner(relativites(_renommer(freq, refs), refs),
                     relativites(_renommer(sev, {"classe_puissance": "9-12"}), {"classe_puissance": "9-12"}))
    # peu de sinistres moto (moins de 700) : coefficients rapprochés de 1 (crédibilité, racine carrée) puis bornés
    coefs = {v: {k: round(float(np.clip(x ** 0.5, 0.5, 2.5)), 4) for k, x in niv.items()} for v, niv in coefs.items()}
    return {"variables": coefs, "references": refs, "contrats": int(len(d)), "sinistres": int(len(sv))}


# Règles et hypothèses de marché (documentées dans le README)
REGLES = {
    "bonus_malus": "coefficient = 0,95 par année sans sinistre, x 1,25 par sinistre responsable (3 ans), borné de 0,50 à 3,50 ; "
                   "prix x coefficient / 0,50 (le profil de référence est à 0,50)",
    "jeune_conducteur": {"0": 2.0, "1": 1.5, "2": 1.25, "conduite_accompagnee": {"0": 1.5, "1": 1.25, "2": 1.0}},
    "permis_hors_ue": 1.10,
    "usage": {"prive": 1.0, "domicile_travail": 1.05, "professionnel": 1.20},
    "kilometrage": [[5000, 0.85], [10000, 0.93], [15000, 1.0], [20000, 1.07], [30000, 1.15], [10 ** 9, 1.25]],
    "stationnement": {"garage": 0.93, "parking": 1.0, "rue": 1.08},
    "franchise": {"basse": 1.10, "standard": 1.0, "haute": 0.88},
    "valeur_vehicule": "partie dommages x (valeur actuelle / 12 000 €) ^ 0,5 ; valeur actuelle = valeur neuve x 0,85 ^ âge",
    "jeunes_age": "pour les moins de 26 ans, on garde le coefficient des 26-30 ans : le bonus-malus (1,00 au départ) "
                  "et la surprime jeune conducteur comptent déjà le manque d'expérience",
    "moto": "peu de sinistres dans les données moto : coefficients rapprochés de 1 (racine carrée) et bornés entre 0,5 et 2,5",
}


# ====================================================================== 3. profils
VEHICULES_AUTO = [  # modèle, catégorie, puissance ch, énergie, valeur neuve €
    ("Renault Clio", "citadine", 90, "essence", 19000), ("Peugeot 208", "citadine", 100, "essence", 21000),
    ("Citroën C1", "citadine", 72, "essence", 13000), ("Toyota Yaris", "citadine", 116, "hybride", 24000),
    ("Volkswagen Golf", "compacte", 130, "essence", 30000), ("Peugeot 308", "compacte", 130, "diesel", 31000),
    ("Renault Mégane", "compacte", 115, "diesel", 28000), ("Peugeot 3008", "suv", 130, "diesel", 36000),
    ("Volkswagen Tiguan", "suv", 150, "diesel", 40000), ("Dacia Duster", "suv", 115, "essence", 20000),
    ("Skoda Octavia Break", "familiale", 150, "diesel", 33000), ("BMW Série 3", "premium", 184, "diesel", 48000),
    ("Audi A4", "premium", 204, "essence", 50000), ("Mercedes Classe C", "premium", 204, "hybride", 52000),
    ("Volkswagen Golf GTI", "sportive", 245, "essence", 45000), ("BMW M3", "sportive", 510, "essence", 95000),
    ("Porsche 911", "sportive", 385, "essence", 125000), ("Renault Zoé", "electrique", 135, "electrique", 33000),
    ("Tesla Model 3", "electrique", 283, "electrique", 42000), ("Fiat 500", "citadine", 70, "essence", 17000),
]
VEHICULES_MOTO = [  # modèle, catégorie, kW, poids kg, valeur neuve €
    ("Peugeot Kisbee 50", "scooter_50", 2.5, 85, 1900), ("Yamaha NMAX 125", "125", 9, 131, 3800),
    ("Honda CB125R", "125", 11, 130, 4800), ("Yamaha MT-07 (bridée A2)", "a2", 35, 184, 8000),
    ("Kawasaki Z650 (bridée A2)", "a2", 35, 188, 7500), ("Yamaha MT-07", "roadster", 54, 184, 8000),
    ("Yamaha MT-09", "roadster", 87, 193, 10500), ("BMW R 1250 GS", "trail", 100, 249, 21000),
    ("Honda CBR1000RR-R", "sportive", 160, 201, 25000), ("BMW R 1250 RT", "gt", 100, 279, 24000),
    ("Yamaha TMAX 560", "maxi_scooter", 35, 220, 13000),
]
VILLES = {
    "France": {"rural": "Sillé-le-Guillaume", "periurbain": "Allonnes", "urbain": "Le Mans", "grande_ville": "Lyon", "metropole": "Paris"},
    "Belgique": {"rural": "Bastogne", "periurbain": "Wavre", "urbain": "Namur", "grande_ville": "Liège", "metropole": "Bruxelles"},
    "Italie": {"rural": "Aosta", "periurbain": "Monza", "urbain": "Bologna", "grande_ville": "Roma", "metropole": "Napoli"},
    "Allemagne": {"rural": "Lüneburg", "periurbain": "Potsdam", "urbain": "Leipzig", "grande_ville": "München", "metropole": "Berlin"},
    "Autriche": {"rural": "Zell am See", "periurbain": "Mödling", "urbain": "Linz", "grande_ville": "Graz", "metropole": "Wien"},
    "Espagne": {"rural": "Teruel", "periurbain": "Alcalá de Henares", "urbain": "Zaragoza", "grande_ville": "Barcelona", "metropole": "Madrid"},
    "Portugal": {"rural": "Bragança", "periurbain": "Sintra", "urbain": "Braga", "grande_ville": "Porto", "metropole": "Lisboa"},
    "Irlande": {"rural": "Westport", "periurbain": "Naas", "urbain": "Galway", "grande_ville": "Cork", "metropole": "Dublin"},
    "Pays-Bas": {"rural": "Assen", "periurbain": "Amersfoort", "urbain": "Groningen", "grande_ville": "Utrecht", "metropole": "Amsterdam"},
}
ZONE_AUTO = {"rural": "A", "periurbain": "B", "urbain": "C", "grande_ville": "D", "metropole": "E"}
ZONE_MOTO = {"rural": "rural", "periurbain": "periurbain", "urbain": "urbain", "grande_ville": "grande_ville", "metropole": "grande_ville"}
TRANCHES_PROFIL = [(18, 20), (21, 25), (26, 30), (31, 40), (41, 50), (51, 60), (61, 70), (71, 85)]

PERSONAS = [  # cas typiques nommés, faciles à présenter
    dict(persona="Lucas, jeune permis, voiture puissante", pays="France", type="auto", age=19, annees_permis=1, vehicule="Volkswagen Golf GTI", zone="grande_ville"),
    dict(persona="Inès, jeune permis avec conduite accompagnée", pays="France", type="auto", age=18, annees_permis=0, conduite_accompagnee=True, vehicule="Renault Clio", zone="urbain"),
    dict(persona="Karim, 22 ans, citadine à Lyon", formule="intermediaire", pays="France", type="auto", age=22, annees_permis=2, vehicule="Peugeot 208", zone="grande_ville"),
    dict(persona="Sophie, famille, SUV en périphérie", pays="France", type="auto", age=38, annees_permis=20, vehicule="Peugeot 3008", zone="periurbain"),
    dict(persona="Jean, 50 ans, profil de référence", pays="France", type="auto", age=50, annees_permis=32, vehicule="Renault Clio", zone="urbain"),
    dict(persona="Marc, cadre, berline premium à Paris", pays="France", type="auto", age=45, annees_permis=27, vehicule="BMW Série 3", zone="metropole", usage="domicile_travail"),
    dict(persona="Paul, retraité rural, petit rouleur", formule="intermediaire", pays="France", type="auto", age=72, annees_permis=50, vehicule="Dacia Duster", zone="rural", km_an=4000),
    dict(persona="Nadia, permis étranger hors UE", formule="intermediaire", pays="France", type="auto", age=30, annees_permis=8, pays_permis="hors_UE", vehicule="Toyota Yaris", zone="urbain"),
    dict(persona="Thomas, malussé (2 sinistres)", formule="intermediaire", pays="France", type="auto", age=35, annees_permis=15, sinistres=2, vehicule="Volkswagen Golf", zone="urbain"),
    dict(persona="Éric, commercial, gros rouleur", pays="France", type="auto", age=42, annees_permis=22, vehicule="Skoda Octavia Break", zone="periurbain", usage="professionnel", km_an=40000),
    dict(persona="Léa, voiture électrique", pays="France", type="auto", age=33, annees_permis=14, vehicule="Tesla Model 3", zone="grande_ville"),
    dict(persona="Hugo, 25 ans, Porsche 911", pays="France", type="auto", age=25, annees_permis=6, vehicule="Porsche 911", zone="grande_ville"),
    dict(persona="Yanis, 16 ans, scooter 50", formule="tiers", pays="France", type="moto", age=16, annees_permis=0, vehicule="Peugeot Kisbee 50", zone="urbain"),
    dict(persona="Camille, 125 pour aller au travail", formule="intermediaire", pays="France", type="moto", age=30, annees_permis=1, vehicule="Yamaha NMAX 125", zone="metropole", usage="domicile_travail"),
    dict(persona="Mehdi, permis A2 récent", formule="intermediaire", pays="France", type="moto", age=20, annees_permis=1, vehicule="Yamaha MT-07 (bridée A2)", zone="urbain"),
    dict(persona="Julien, A2 sur une moto trop puissante", pays="France", type="moto", age=21, annees_permis=1, vehicule="Yamaha MT-09", zone="urbain"),
    dict(persona="Patrick, motard expérimenté, GT", pays="France", type="moto", age=55, annees_permis=30, vehicule="BMW R 1250 RT", zone="rural"),
    dict(persona="Antoine, sportive en ville", pays="France", type="moto", age=28, annees_permis=6, vehicule="Honda CBR1000RR-R", zone="grande_ville"),
    dict(persona="Giulia, Rome, citadine", formule="tiers", pays="Italie", type="auto", age=27, annees_permis=9, vehicule="Fiat 500", zone="grande_ville"),
    dict(persona="Marco, Naples, scooter 125", formule="tiers", pays="Italie", type="moto", age=24, annees_permis=4, vehicule="Yamaha NMAX 125", zone="metropole"),
    dict(persona="Lucía, Madrid, compacte", pays="Espagne", type="auto", age=37, annees_permis=19, vehicule="Volkswagen Golf", zone="metropole"),
    dict(persona="Pieter, Bruxelles, SUV", pays="Belgique", type="auto", age=44, annees_permis=25, vehicule="Volkswagen Tiguan", zone="metropole"),
    dict(persona="Lena, Berlin, jeune conductrice", pays="Allemagne", type="auto", age=19, annees_permis=1, vehicule="Volkswagen Golf", zone="metropole"),
    dict(persona="João, Lisbonne, moto A2", pays="Portugal", type="moto", age=23, annees_permis=2, vehicule="Kawasaki Z650 (bridée A2)", zone="metropole"),
    dict(persona="Seán, Dublin, citadine", pays="Irlande", type="auto", age=29, annees_permis=10, vehicule="Toyota Yaris", zone="metropole"),
]


def nouveau_profil(rng, pays: str, type_: str, age: int, vehicule: tuple, **fixe) -> dict:
    age_min = 16 if type_ == "moto" and vehicule[1] in ("scooter_50", "125") else 18
    age = max(age, age_min if type_ == "moto" else 18)
    max_permis = age - age_min
    annees_permis = fixe.get("annees_permis", int(min(max_permis, rng.choice(
        [0, 1, 2, 3, 5, 8, 12, 20, 30, 40], p=[.08, .08, .08, .08, .12, .12, .12, .12, .1, .1]))))
    sinistres = fixe.get("sinistres", int(rng.choice([0, 0, 0, 0, 0, 0, 1, 1, 2, 3])))
    annees_sans = max(0, annees_permis - (2 * sinistres))
    valeur = vehicule[-1]
    p = {
        "pays": pays, "type": type_, "age": int(age), "annees_permis": int(annees_permis),
        "conduite_accompagnee": bool(fixe.get("conduite_accompagnee", annees_permis < 3 and age < 22 and rng.random() < 0.35)),
        "pays_permis": fixe.get("pays_permis", rng.choice(["national", "national", "national", "national", "UE", "hors_UE"])),
        "annees_sans_sinistre": int(annees_sans), "sinistres_responsables_3ans": int(sinistres),
        "vehicule": vehicule[0], "categorie_vehicule": vehicule[1],
        "puissance_ch": int(vehicule[2]) if type_ == "auto" else int(round(vehicule[2] * 1.36)),
        "puissance_kw": round(vehicule[2] / 1.36, 1) if type_ == "auto" else float(vehicule[2]),
        "poids_kg": int(vehicule[3]) if type_ == "moto" else None,
        "energie": vehicule[3] if type_ == "auto" else "essence",
        "valeur_neuve_eur": int(valeur), "age_vehicule": int(fixe.get("age_vehicule", rng.choice([0, 1, 2, 3, 5, 8, 12, 16]))),
        "zone": fixe.get("zone", rng.choice(list(ZONE_AUTO))), "usage": fixe.get("usage", rng.choice(
            ["prive", "domicile_travail", "domicile_travail", "professionnel"], p=[.45, .25, .2, .1])),
        "km_an": int(fixe.get("km_an", rng.choice([3000, 6000, 10000, 12000, 15000, 20000, 30000]) if type_ == "auto"
                              else rng.choice([2000, 4000, 6000, 8000, 12000]))),
        "stationnement": fixe.get("stationnement", rng.choice(["garage", "parking", "rue"])),
        "franchise": fixe.get("franchise", rng.choice(["basse", "standard", "standard", "haute"])),
        "persona": fixe.get("persona"),
    }
    p["ville"] = VILLES[pays][p["zone"]]
    neuf_ou_cher = p["age_vehicule"] <= 4 or valeur >= 30000
    p["formule_souhaitee"] = fixe.get("formule", "tous_risques" if neuf_ou_cher else rng.choice(["tiers", "intermediaire"]))
    return p


def generer_profils(pays_types: list[tuple[str, str]]) -> pd.DataFrame:
    rng = np.random.default_rng(GRAINE)
    profils = []
    for pays, type_ in pays_types:
        catalogue = VEHICULES_AUTO if type_ == "auto" else VEHICULES_MOTO
        categories = sorted({v[1] for v in catalogue})
        repetitions = 3 if pays == "France" else 2
        for a, b in TRANCHES_PROFIL:          # chaque tranche d'âge x chaque catégorie de véhicule
            for cat in categories:
                modeles = [v for v in catalogue if v[1] == cat]
                for _ in range(repetitions):
                    v = modeles[rng.integers(len(modeles))]
                    profils.append(nouveau_profil(rng, pays, type_, int(rng.integers(a, b + 1)), v))
    for fixe in PERSONAS:
        cat = VEHICULES_AUTO if fixe["type"] == "auto" else VEHICULES_MOTO
        v = next(x for x in cat if x[0] == fixe["vehicule"])
        reste = {k: x for k, x in fixe.items() if k not in ("pays", "type", "age", "vehicule")}
        profils.append(nouveau_profil(rng, fixe["pays"], fixe["type"], fixe["age"], v, age_vehicule=3,
                                      pays_permis=fixe.get("pays_permis", "national"), stationnement="parking",
                                      franchise="standard", **{k: x for k, x in reste.items() if k not in ("pays_permis",)}))
    df = pd.DataFrame(profils)
    df.insert(0, "id_profil", [f"P{i:05d}" for i in range(len(df))])
    return df


# ====================================================================== 4. calcul du prix
def coef_bonus_malus(p) -> float:
    if p["pays_permis"] == "hors_UE":
        crm = 1.0                                    # historique non reconnu : on repart de 1,00
    else:
        crm = 1.0 * 0.95 ** min(p["annees_sans_sinistre"], 14) * 1.25 ** p["sinistres_responsables_3ans"]
    return float(np.clip(crm, 0.50, 3.50))


def coef_jeune(p) -> float:
    if p["annees_permis"] >= 3:
        return 1.0
    table = REGLES["jeune_conducteur"]["conduite_accompagnee"] if p["conduite_accompagnee"] else REGLES["jeune_conducteur"]
    return float(table[str(p["annees_permis"])])


def coef_km(km: int) -> float:
    return next(c for seuil, c in REGLES["kilometrage"] if km <= seuil)


def classe_fiscale(ch: int) -> str:
    for seuil, c in [(75, "4"), (100, "5"), (130, "6"), (160, "7"), (200, "8"), (260, "9-10")]:
        if ch < seuil:
            return c
    return "11+"


def classe_moto(kw: float, poids: int) -> str:
    r = kw / poids * 100
    for seuil, c in [(5, "<5"), (8, "6-8"), (12, "9-12"), (15, "13-15"), (19, "16-19"), (24, "20-24")]:
        if r <= seuil:
            return c
    return ">25"


def age_tranche(age: int) -> str:
    for (a, b), n in zip(TRANCHES_PROFIL, NOMS_AGE):
        if a <= age <= b:
            return n
    return "18-20" if age < 18 else "71+"


def refus(p) -> str | None:
    if p["sinistres_responsables_3ans"] >= 3:
        return "refusé : 3 sinistres responsables ou plus en 3 ans (assureur spécialisé risques aggravés)"
    if p["type"] == "moto" and p["categorie_vehicule"] not in ("scooter_50", "125", "a2") and p["puissance_kw"] > 35 \
            and p["annees_permis"] < 2:
        return "refusé : moto de plus de 35 kW interdite avec un permis A2 de moins de 2 ans"
    if p["type"] == "auto" and p["age"] < 23 and p["annees_permis"] < 3 and p["puissance_ch"] >= 250:
        return "refusé : véhicule de plus de 250 ch pour un jeune conducteur"
    return None


def coefficients_profil(p, coefs: dict) -> dict[str, float]:
    if p["type"] == "auto":
        v = coefs["auto"]["variables"]
        tr = age_tranche(p["age"])
        c_age = v["age"].get(tr, 1.0)
        c_puiss = v["puissance"].get(classe_fiscale(p["puissance_ch"]), 1.0)
        av = p["age_vehicule"]
        c_vage = v["age_vehicule"].get("0" if av == 0 else "1-2" if av <= 2 else "3-5" if av <= 5 else
                                       "6-10" if av <= 10 else "11-15" if av <= 15 else "16+", 1.0)
        c_zone = v["zone"].get(ZONE_AUTO[p["zone"]], 1.0)
        c_carb = v["carburant"].get("Diesel" if p["energie"] == "diesel" else "Regular", 1.0)
        if p["energie"] == "electrique":
            c_carb *= 1.05                       # réparations plus chères (baromètre LeLynx : +18 % en tous risques)
    else:
        v = coefs["moto"]["variables"]
        tr = age_tranche(p["age"])
        c_age = v["age"].get(tr, 1.0)
        c_puiss = v["classe_puissance"].get(classe_moto(p["puissance_kw"], p["poids_kg"]), 1.0)
        av = p["age_vehicule"]
        c_vage = v["age_vehicule"].get("0-2" if av <= 2 else "3-5" if av <= 5 else "6-10" if av <= 10 else
                                       "11-15" if av <= 15 else "16+", 1.0)
        c_zone = v["zone"].get(ZONE_MOTO[p["zone"]], 1.0)
        c_carb = 1.0
    if p["age"] < 26:                            # éviter le double comptage avec bonus-malus et surprime jeune
        c_age = v["age"].get("26-30", 1.0)
    return {
        "coef_age": c_age, "coef_puissance": c_puiss, "coef_age_vehicule": c_vage, "coef_zone": c_zone,
        "coef_energie": c_carb, "coef_bonus_malus": coef_bonus_malus(p) / 0.5, "coef_jeune_conducteur": coef_jeune(p),
        "coef_permis_etranger": REGLES["permis_hors_ue"] if p["pays_permis"] == "hors_UE" else 1.0,
        "coef_usage": REGLES["usage"][p["usage"]], "coef_kilometrage": coef_km(p["km_an"]),
        "coef_stationnement": REGLES["stationnement"][p["stationnement"]],
    }


def simuler(profils: pd.DataFrame, prix_base: pd.DataFrame, coefs: dict) -> pd.DataFrame:
    lignes = []
    base_par_offre = {oid: g.set_index("formule")["prix_base_annuel"].to_dict() for oid, g in prix_base.groupby("id_offre")}
    for _, p in profils.iterrows():
        offres = prix_base[(prix_base.pays == p.pays) & (prix_base.type == p.type)]
        motif_refus = refus(p)
        c = coefficients_profil(p, coefs)
        R = float(np.prod(list(c.values())))
        valeur_actuelle = p.valeur_neuve_eur * 0.85 ** p.age_vehicule
        D = (valeur_actuelle / 12000) ** 0.5 * REGLES["franchise"][p.franchise]
        for _, o in offres.iterrows():
            bases = base_par_offre[o.id_offre]
            b_tiers = bases.get("tiers", min(bases.values()))
            prix = None
            if motif_refus is None:
                partie_rc = b_tiers * R
                partie_dommages = max(o.prix_base_annuel - b_tiers, 0) * R * D
                prix = round(partie_rc + partie_dommages, 2)
            lignes.append({"id_profil": p.id_profil, "id_offre": o.id_offre, "pays": p.pays, "type": p.type,
                           "assureur": o.assureur, "produit": o.produit, "formule": o.formule,
                           "formule_souhaitee": p.formule_souhaitee == o.formule,
                           "prix_base_annuel": o.prix_base_annuel, "source_prix_base": o.source_prix_base,
                           "coef_total_profil": round(R, 4), "coef_vehicule_dommages": round(D, 4) if o.formule != "tiers" else None,
                           **{k: round(x, 4) for k, x in c.items()},
                           "prix_annuel_estime": prix, "prix_mensuel_estime": round(prix / 12, 2) if prix else None,
                           "statut": "ok" if motif_refus is None else motif_refus, "url_offre": o.url_offre})
    return pd.DataFrame(lignes)


# ====================================================================== 5. contrôle et README
def controle(profils, devis) -> list[str]:
    """Compare quelques moyennes simulées (France) aux moyennes publiées par LeLynx en 2026."""
    d = devis[(devis.pays == "France") & devis.prix_annuel_estime.notna() & devis.formule_souhaitee]
    d = d.merge(profils[["id_profil", "annees_permis", "age"]], on="id_profil")
    lignes = ["| Cas (France) | Moyenne simulée | Moyenne publiée (LeLynx 2026) |", "| --- | --- | --- |"]
    def m(x):
        return f"{x.mean():,.0f} €/an".replace(",", " ") if len(x) else "-"
    auto, moto = d[d.type == "auto"], d[d.type == "moto"]
    lignes += [
        f"| Auto, tous profils | {m(auto.prix_annuel_estime)} | 663 €/an |",
        f"| Auto, tiers | {m(auto[auto.formule == 'tiers'].prix_annuel_estime)} | 526 €/an |",
        f"| Auto, tous risques | {m(auto[auto.formule == 'tous_risques'].prix_annuel_estime)} | 784 €/an |",
        f"| Auto, moins de 3 ans de permis | {m(auto[auto.annees_permis < 3].prix_annuel_estime)} | 1 231 €/an |",
        f"| Auto, 65 à 69 ans | {m(auto[auto.age.between(65, 69)].prix_annuel_estime)} | 434 €/an |",
        f"| Auto, conducteur expérimenté (10 ans de permis ou plus) | {m(auto[auto.annees_permis >= 10].prix_annuel_estime)} | 645 €/an |",
        f"| Moto, tous profils | {m(moto.prix_annuel_estime)} | 634 €/an |",
    ]
    return lignes


def ecrire_readme(prix_base, coefs, profils, devis, cfg):
    n = lambda x: f"{int(x):,}".replace(",", " ")
    ok = devis[devis.statut == "ok"]
    l = ["# Simulation des prix des offres d'assurance (objectif 1)", "",
         "Fichiers **générés automatiquement** par `src/simulateur.py` à chaque mise à jour des offres.", "",
         f"- **Mis à jour le** : {datetime.now(timezone.utc).strftime('%d/%m/%Y')}",
         f"- **Offres réelles avec un prix de base** : {prix_base.id_offre.nunique()} offres, {len(prix_base)} couples offre x formule",
         f"- **Profils générés** : {n(len(profils))} (dont {profils.persona.notna().sum()} cas typiques nommés)",
         f"- **Prix simulés** : {n(len(devis))} devis, dont {n(len(ok))} acceptés et {n(len(devis) - len(ok))} refusés", "",
         "## Le principe", "",
         "Comme un assureur : **prix = prix de base de l'offre x coefficients du profil**.", "",
         "1. **Prix de base** (`prix_base.parquet`) : le prix de l'offre pour le profil de référence (le « à partir de » "
         "affiché par les assureurs : 50 ans, bonus 0,50, citadine récente, ville moyenne). Vrai prix d'entrée publié "
         "quand il existe, sinon référence de marché du pays (`config/prix_base.yaml`, chaque chiffre a sa source).",
         f"2. **Coefficients appris sur des sinistres réels** (`coefficients.json`) : modèles GLM fréquence x coût, "
         f"comme les assureurs. Auto : freMTPL2 ({n(coefs['auto']['contrats'])} contrats). Moto : swmotorcycle "
         f"({n(coefs['moto']['contrats'])} contrats).",
         "3. **Règles du marché** : bonus-malus, surprime jeune conducteur, usage, kilométrage, stationnement, "
         "franchise, valeur du véhicule (pour la partie dommages), refus des profils hors cible.",
         "4. **Prix final** = partie responsabilité civile x coefficients du profil + partie dommages x coefficients "
         "du profil x coefficient du véhicule.", "",
         "## Fichiers", "", "| Fichier | Contenu |", "| --- | --- |",
         "| `prix_base.parquet` | Prix de base par offre réelle et par formule, avec sa source |",
         "| `coefficients.json` | Coefficients appris (âge, puissance, âge du véhicule, zone, énergie) et règles |",
         "| `profils.parquet` | Profils générés : conducteur, permis, véhicule, zone, usage, besoins |",
         "| `devis_simules.parquet` | Un prix simulé par profil x offre x formule, avec le détail des coefficients |",
         "| **`offres_prix_profils.csv` / `.parquet`** | **Le fichier unique** : une ligne = un profil simulé x une offre réelle x une formule. "
         "Caractéristiques du profil (`profil_*`), offre et garanties (`offre_*`), prix de base, prix simulé, détail des coefficients, lien de l'offre. "
         "Le CSV s'ouvre dans Excel (séparateur « ; ») |", "",
         "## Les profils couvrent", "",
         "- 9 pays, auto et moto ; chaque tranche d'âge (18 à 85 ans) croisée avec chaque catégorie de véhicule",
         "- Auto : citadine, compacte, SUV, familiale, premium, sportive, électrique (20 modèles)",
         "- Moto : scooter 50, 125, A2, roadster, trail, sportive, GT, maxi-scooter (11 modèles)",
         "- Permis récent ou ancien, conduite accompagnée, permis national / UE / hors UE, 0 à 3 sinistres",
         "- Zone (rural à métropole), usage (privé, trajet travail, pro), kilométrage, stationnement, franchise", "",
         "## Contrôle : moyennes simulées et moyennes publiées", ""]
    l += controle(profils, devis)
    l += ["", "Les profils sont générés pour couvrir tous les cas, pas pour reproduire la population réelle : "
          "les moyennes ne doivent être que du même ordre de grandeur. Les moyennes simulées sont plus hautes car les profils "
          "risqués (jeunes, voitures puissantes, malus, tous risques sur véhicule cher) y sont volontairement aussi nombreux que les autres.", "",
          "## Sources des prix de base", "", "| Pays | Méthode | Source |", "| --- | --- | --- |"]
    for pays, r in cfg["references_pays"].items():
        l.append(f"| {pays} | {r['methode']} | [lien]({r['source'].split(' ; ')[0]}) |")
    l += ["", "## Limites", "",
          "- **Ce sont des prix estimés**, pas des devis : les offres sont réelles, mais seul l'assureur donne le prix exact. "
          "Toujours afficher le lien vers le devis officiel (`url_offre`).",
          "- Les coefficients viennent de données françaises (auto) et suédoises (moto) : ils sont appliqués à tous les pays.",
          "- Le bonus-malus est le système français, utilisé comme équivalent pour les autres pays.",
          "- La plupart des offres n'ont pas de prix d'entrée publié : elles reçoivent la référence de marché de leur pays.",
          "- Pas de coefficient selon le sexe : interdit dans l'Union européenne depuis 2012.", "",
          "## Utilisation", "", "```python", "import pandas as pd",
          "devis = pd.read_parquet(\"devis_simules.parquet\")",
          "profils = pd.read_parquet(\"profils.parquet\")",
          "# les 5 offres les moins chères pour un profil, dans la formule qu'il souhaite",
          "devis[(devis.id_profil == \"P00000\") & devis.formule_souhaitee].nsmallest(5, \"prix_annuel_estime\")", "```", ""]
    (SORTIE / "README.md").write_text("\n".join(l), encoding="utf-8")


def fichier_unique(offres: pd.DataFrame, profils: pd.DataFrame, devis: pd.DataFrame) -> pd.DataFrame:
    """Un seul fichier : une ligne = un profil simulé x une offre réelle x une formule, avec tout le détail."""
    p = profils.rename(columns={c: f"profil_{c}" for c in profils.columns if c not in ("id_profil", "pays", "type")})
    g = [c for c in offres.columns if c.startswith("g_")]
    o = offres[["id_offre", "produit", *g, "franchise_min_eur", "franchise_max_eur", "paiement_mensuel"]].rename(
        columns={c: f"offre_{c}" for c in [*g, "franchise_min_eur", "franchise_max_eur", "paiement_mensuel"]})
    d = devis.drop(columns=["produit"]).merge(p.drop(columns=["pays", "type"]), on="id_profil").merge(o, on="id_offre")
    colonnes_profil = [c for c in d.columns if c.startswith("profil_")]
    colonnes_offre = [c for c in d.columns if c.startswith("offre_")]
    coefs = [c for c in d.columns if c.startswith("coef_")]
    ordre = ["id_profil", "pays", "type", *colonnes_profil,
             "id_offre", "assureur", "produit", "formule", "formule_souhaitee", *colonnes_offre,
             "prix_base_annuel", "source_prix_base", "prix_annuel_estime", "prix_mensuel_estime", "statut",
             *coefs, "url_offre"]
    return d[ordre].sort_values(["id_profil", "formule", "prix_annuel_estime"]).reset_index(drop=True)


def main() -> int:
    SORTIE.mkdir(parents=True, exist_ok=True)
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    offres = pd.read_parquet(OFFRES)
    prix_base = construire_prix_base(offres, cfg)
    log(f"Prix de base : {prix_base.id_offre.nunique()} offres, {len(prix_base)} couples offre x formule")

    coefs = {"auto": coefficients_auto(), "moto": coefficients_moto(), "regles": REGLES}
    log("Coefficients appris (auto : freMTPL2, moto : swmotorcycle)")

    pays_types = sorted(set(zip(prix_base.pays, prix_base.type)))
    profils = generer_profils(pays_types)
    devis = simuler(profils, prix_base, coefs)
    log(f"Profils : {len(profils)} ; devis simulés : {len(devis)}")

    prix_base.to_parquet(SORTIE / "prix_base.parquet", index=False)
    (SORTIE / "coefficients.json").write_text(json.dumps(coefs, indent=2, ensure_ascii=False), encoding="utf-8")
    profils.to_parquet(SORTIE / "profils.parquet", index=False)
    devis.to_parquet(SORTIE / "devis_simules.parquet", index=False)
    tout = fichier_unique(offres, profils, devis)
    tout.to_parquet(SORTIE / "offres_prix_profils.parquet", index=False)
    tout.to_csv(SORTIE / "offres_prix_profils.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")
    log(f"Fichier unique : {len(tout)} lignes, {tout.shape[1]} colonnes")
    ecrire_readme(prix_base, coefs, profils, devis, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
