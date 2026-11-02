"""
Base de profils d'assurés auto et moto dans 20 pays européens, avec des permis obtenus partout dans le monde,
organisée comme les formulaires de devis des assureurs (conducteur, permis, antécédents, véhicule, usage,
stationnement, couverture souhaitée).

Les profils sont générés pour couvrir presque tous les cas possibles, avec des règles de cohérence
(âge et permis, bonus-malus calculé selon la règle officielle, véhicule et permis moto, usage VTC…).
Les profils de référence des vrais prix relevés (data/externe/offres_auto_france/auto_prices.csv) sont inclus
tels quels, pour caler et vérifier le simulateur de prix.

Sorties (data/profils/) :
  profils.parquet / profils.csv   un profil par ligne
  dictionnaire.csv                chaque champ : question du formulaire, type, valeurs possibles
  couverture.csv                  combien de profils pour chaque valeur de chaque champ
  README.md

Lancement :  python -m src.profils        (NB_AUTO=80000 NB_MOTO=20000 par défaut)
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from src.pays_referentiel import AUTOS_EUROPE, MOTOS_EUROPE, PAYS, PAYS_PERMIS_MONDE, VILLES

SORTIE = Path("data/profils")
GRAINE = 2026
AUJOURDHUI = date(2026, 11, 1)
NB_AUTO = int(os.environ.get("NB_AUTO", "80000"))
NB_MOTO = int(os.environ.get("NB_MOTO", "20000"))

# ------------------------------------------------------------------ référentiels
# modèle, catégorie, énergie, puissance ch, puissance fiscale CV, prix neuf €, groupe SRA (classe de prix, A à Z simplifié)
AUTOS = [
    ("Renault Clio 5", "citadine", "essence", 90, 5, 19500, "E"), ("Renault Clio 4", "citadine", "essence", 90, 5, 16500, "D"),
    ("Peugeot 208", "citadine", "essence", 100, 5, 21000, "E"), ("Peugeot e-208", "citadine", "electrique", 136, 1, 34000, "H"),
    ("Citroën C3", "citadine", "essence", 83, 4, 18500, "D"), ("Toyota Yaris", "citadine", "hybride", 116, 4, 24000, "F"),
    ("Dacia Sandero", "citadine", "essence", 90, 5, 13500, "C"), ("Renault Twingo", "mini", "essence", 65, 4, 13000, "C"),
    ("Fiat 500", "mini", "essence", 70, 4, 17000, "D"), ("Smart Fortwo", "mini", "essence", 71, 4, 15000, "D"),
    ("Volkswagen Polo", "citadine", "essence", 95, 5, 21500, "E"), ("Renault Zoé", "citadine", "electrique", 135, 1, 33000, "H"),
    ("Peugeot 308", "compacte", "diesel", 130, 7, 31000, "H"), ("Volkswagen Golf", "compacte", "essence", 130, 7, 30000, "H"),
    ("Renault Mégane", "compacte", "diesel", 115, 6, 28000, "G"), ("Toyota Corolla", "compacte", "hybride", 140, 6, 32000, "H"),
    ("Peugeot 3008", "suv", "diesel", 130, 7, 36000, "I"), ("Renault Captur", "suv", "essence", 140, 7, 27000, "G"),
    ("Dacia Duster", "suv", "essence", 115, 6, 20000, "E"), ("Volkswagen Tiguan", "suv", "diesel", 150, 8, 40000, "J"),
    ("Tesla Model Y", "suv", "electrique", 299, 3, 45000, "M"), ("Peugeot 2008", "suv", "essence", 130, 7, 27500, "G"),
    ("Skoda Octavia Break", "familiale", "diesel", 150, 8, 33000, "I"), ("Peugeot 5008", "familiale", "diesel", 130, 7, 40000, "J"),
    ("Renault Espace", "familiale", "hybride", 200, 9, 45000, "K"), ("Citroën Berlingo", "utilitaire", "diesel", 100, 5, 25000, "F"),
    ("Renault Kangoo", "utilitaire", "diesel", 95, 5, 26000, "F"), ("Peugeot 508", "berline", "essence", 130, 7, 38000, "J"),
    ("BMW Série 3", "premium", "diesel", 190, 10, 48000, "N"), ("Audi A4", "premium", "essence", 204, 11, 50000, "N"),
    ("Mercedes Classe C", "premium", "hybride", 204, 11, 52000, "O"), ("Tesla Model 3", "premium", "electrique", 283, 3, 42000, "M"),
    ("Volkswagen Golf GTI", "sportive", "essence", 245, 14, 45000, "P"), ("Renault Mégane RS", "sportive", "essence", 300, 17, 42000, "P"),
    ("BMW M3", "sportive", "essence", 510, 37, 95000, "U"), ("Porsche 911", "sportive", "essence", 385, 29, 125000, "W"),
    ("Mazda MX-5", "cabriolet", "essence", 132, 8, 32000, "J"), ("Toyota RAV4", "suv", "hybride", 218, 8, 42000, "K"),
] + AUTOS_EUROPE
MOTOS = [  # modèle, catégorie, permis minimal, kW, cylindrée cm3, prix neuf €
    ("Peugeot Kisbee 50", "scooter_50", "AM", 2.5, 50, 1900), ("Yamaha Neo's 50", "scooter_50", "AM", 2.5, 50, 2300),
    ("Yamaha NMAX 125", "scooter_125", "B+formation", 9, 125, 3800), ("Honda PCX 125", "scooter_125", "B+formation", 9, 125, 3600),
    ("Honda CB125R", "moto_125", "A1", 11, 125, 4800), ("KTM 125 Duke", "moto_125", "A1", 11, 125, 5000),
    ("Yamaha MT-07 (A2)", "roadster_a2", "A2", 35, 689, 8000), ("Kawasaki Z650 (A2)", "roadster_a2", "A2", 35, 649, 7500),
    ("Yamaha MT-07", "roadster", "A", 54, 689, 8000), ("Yamaha MT-09", "roadster", "A", 87, 890, 10500),
    ("BMW R 1250 GS", "trail", "A", 100, 1254, 21000), ("Honda Africa Twin", "trail", "A", 75, 1084, 15500),
    ("Honda CBR1000RR-R", "sportive", "A", 160, 1000, 25000), ("Yamaha R1", "sportive", "A", 147, 998, 21000),
    ("BMW R 1250 RT", "gt", "A", 100, 1254, 24000), ("Yamaha TMAX 560", "maxi_scooter", "A2", 35, 562, 13000),
    ("Harley-Davidson Sportster S", "custom", "A", 89, 1252, 17000),
] + MOTOS_EUROPE
# commune, code postal, département, région, type de zone
COMMUNES = [
    ("Paris 15e", "75015", "75", "Île-de-France", "metropole"), ("Marseille", "13001", "13", "Provence-Alpes-Côte d'Azur", "metropole"),
    ("Lyon", "69003", "69", "Auvergne-Rhône-Alpes", "metropole"), ("Toulouse", "31000", "31", "Occitanie", "grande_ville"),
    ("Nice", "06000", "06", "Provence-Alpes-Côte d'Azur", "grande_ville"), ("Nantes", "44000", "44", "Pays de la Loire", "grande_ville"),
    ("Lille", "59000", "59", "Hauts-de-France", "grande_ville"), ("Bordeaux", "33000", "33", "Nouvelle-Aquitaine", "grande_ville"),
    ("Strasbourg", "67000", "67", "Grand Est", "grande_ville"), ("Rennes", "35000", "35", "Bretagne", "grande_ville"),
    ("Montpellier", "34000", "34", "Occitanie", "grande_ville"), ("Saint-Denis", "93200", "93", "Île-de-France", "grande_ville"),
    ("Le Mans", "72000", "72", "Pays de la Loire", "urbain"), ("Dijon", "21000", "21", "Bourgogne-Franche-Comté", "urbain"),
    ("Angers", "49000", "49", "Pays de la Loire", "urbain"), ("Clermont-Ferrand", "63000", "63", "Auvergne-Rhône-Alpes", "urbain"),
    ("Limoges", "87000", "87", "Nouvelle-Aquitaine", "urbain"), ("Ajaccio", "20000", "2A", "Corse", "urbain"),
    ("Versailles", "78000", "78", "Île-de-France", "periurbain"), ("Allonnes", "72700", "72", "Pays de la Loire", "periurbain"),
    ("Mérignac", "33700", "33", "Nouvelle-Aquitaine", "periurbain"), ("Villeurbanne", "69100", "69", "Auvergne-Rhône-Alpes", "periurbain"),
    ("Aubagne", "13400", "13", "Provence-Alpes-Côte d'Azur", "periurbain"), ("Saint-Herblain", "44800", "44", "Pays de la Loire", "periurbain"),
    ("Sillé-le-Guillaume", "72140", "72", "Pays de la Loire", "rural"), ("Mogneneins", "01140", "01", "Auvergne-Rhône-Alpes", "rural"),
    ("Quedillac", "35290", "35", "Bretagne", "rural"), ("Meslan", "56320", "56", "Bretagne", "rural"),
    ("Bastide-de-Besplas", "09350", "09", "Occitanie", "rural"), ("Gérardmer", "88400", "88", "Grand Est", "rural"),
]
PROFESSIONS = ["salarie", "fonctionnaire", "independant", "etudiant", "retraite", "sans_emploi", "commercial_itinerant",
               "chauffeur_vtc", "agriculteur", "profession_liberale"]
TRANCHES = [(17, 17), (18, 20), (21, 25), (26, 30), (31, 40), (41, 50), (51, 60), (61, 70), (71, 80), (81, 90)]


# ------------------------------------------------------------------ règles officielles
def coefficient_bonus_malus(annees_assure: int, sinistres_resp: int, a_ete_assure: bool) -> float:
    """Règle française : 1,00 au départ, x 0,95 par année sans sinistre responsable, x 1,25 par sinistre responsable,
    borné entre 0,50 et 3,50 (simplifié : les sinistres sont supposés dans les 3 dernières années)."""
    if not a_ete_assure:
        return 1.0
    crm = 1.0
    for _ in range(max(0, annees_assure - min(sinistres_resp, 3))):
        crm *= 0.95
    for _ in range(sinistres_resp):
        crm *= 1.25
    return round(float(np.clip(crm, 0.50, 3.50)), 2)


# ------------------------------------------------------------------ pays
CODES = list(PAYS)
POIDS_PAYS = np.array([PAYS[c][1] for c in CODES]); POIDS_PAYS = POIDS_PAYS / POIDS_PAYS.sum()
POIDS_PERMIS = np.array([x[3] for x in PAYS_PERMIS_MONDE], float); POIDS_PERMIS /= POIDS_PERMIS.sum()
LIEUX = {"FR": [(c[0], c[1], c[3], c[4], c[2]) for c in COMMUNES]}
LIEUX.update({k: [(v[0], v[1], v[2], v[3], None) for v in vs] for k, vs in VILLES.items()})
ZONES = ["rural", "periurbain", "urbain", "grande_ville", "metropole"]


def tirer_pays(rng):
    return CODES[rng.choice(len(CODES), p=POIDS_PAYS)]


def lieu(rng, code, zone=None):
    choix = [x for x in LIEUX[code] if zone is None or x[3] == zone] or LIEUX[code]
    v = choix[rng.integers(len(choix))]
    nom, devise, taux = PAYS[code][0], PAYS[code][2], PAYS[code][3]
    return {"pays_residence": nom, "code_pays": code, "commune": v[0], "code_postal": v[1], "departement": v[4],
            "region": v[2], "type_zone": v[3], "devise_locale": devise, "taux_eur_devise": taux}


def permis_origine(rng, code, part_etranger=0.15):
    """Pays où le permis a été obtenu : le pays de résidence le plus souvent, sinon un pays d'Europe ou du monde."""
    if rng.random() >= part_etranger:
        return PAYS[code][0], "meme_pays", PAYS[code][4]
    while True:
        nom, statut, age_min, _ = PAYS_PERMIS_MONDE[rng.choice(len(PAYS_PERMIS_MONDE), p=POIDS_PERMIS)]
        if nom != PAYS[code][0]:
            # pour un résident britannique ou suisse, un permis UE reste « UE_EEE » ; un permis britannique est hors UE
            return nom, statut, age_min


def bonus_malus_national(code, annees_sans_sinistre, sinistres, deja_assure, crm):
    """Niveau dans le système national de bonus-malus (règles simplifiées, documentées dans le dictionnaire)."""
    systeme = PAYS[code][7]
    a, s = annees_sans_sinistre, sinistres
    if not deja_assure:
        a = 0
    if systeme == "crm_france":
        return systeme, f"CRM {crm:.2f}"
    if systeme == "classe_merito":       # Italie : entrée en classe 14, -1 par an sans sinistre, +2 par sinistre, 1 à 18
        return systeme, f"classe {int(np.clip(14 - a + 2 * s, 1, 18))}"
    if systeme == "degre_bonus_malus":   # Belgique : entrée au degré 11, -1 par an, +5 par sinistre, 0 à 22
        return systeme, f"degré {int(np.clip(11 - a + 5 * s, 0, 22))}"
    if systeme == "stufe_autriche":      # Autriche : entrée Stufe 9, -1 par an, +3 par sinistre, 0 à 17
        return systeme, f"Stufe {int(np.clip(9 - a + 3 * s, 0, 17))}"
    if systeme == "sf_klasse":           # Allemagne : SF = années sans sinistre, un sinistre fait reculer d'environ 4 classes
        sf = a - 4 * s
        return systeme, "SF 0" if sf == 0 else ("M (malus)" if sf < 0 else f"SF {min(sf, 50)}")
    if systeme == "trede":               # Pays-Bas : entrée trede 5, +1 par an, -5 par sinistre, 1 à 20
        return systeme, f"trede {int(np.clip(5 + a - 5 * s, 1, 20))}"
    if systeme == "bonus_malus_roumanie":  # Roumanie : B0 à l'entrée, B1..B8 en bonus, M1..M8 en malus
        n = a - 2 * s
        return systeme, "B0" if n == 0 else (f"B{min(n, 8)}" if n > 0 else f"M{min(-n, 8)}")
    if systeme in ("bonus_norvege", "bonus_finlande"):  # réduction en % (Norvège jusqu'à 75 %, Finlande jusqu'à 80 %)
        plafond = 75 if systeme == "bonus_norvege" else 80
        return systeme, f"bonus {int(np.clip(20 + 10 * a - 30 * s, -50, plafond))} %"
    if systeme == "no_claims_bonus":     # Royaume-Uni, Irlande : années de bonus sans sinistre
        n = max(0, a - 2 * s)
        return systeme, f"{n} an{'s' if n > 1 else ''} de no claims bonus"
    n = max(0, a - 2 * s)
    return systeme, f"{n} an{'s' if n > 1 else ''} sans sinistre"


# ------------------------------------------------------------------ génération
def tirer_age(rng, tranche):
    a, b = tranche
    return int(rng.integers(a, b + 1))


def profil_auto(rng, i, age=None, vehicule=None, commune=None, pays=None, zone=None, **force):
    code = pays or tirer_pays(rng)
    loc = lieu(rng, code, zone)
    if commune is not None:
        loc = {**lieu(rng, "FR"), "commune": commune[0], "code_postal": commune[1], "departement": commune[2],
               "region": commune[3], "type_zone": commune[4]}
        code = "FR"
    pays_permis, statut_permis, age_permis_min = permis_origine(rng, code)
    if "pays_permis" in force:
        pays_permis, statut_permis, age_permis_min = force.pop("pays_permis"), "meme_pays", PAYS[code][4]
    tranches_possibles = [t for t in TRANCHES if t[1] >= age_permis_min]
    p = np.array([.02, .08, .14, .12, .17, .15, .13, .1, .06, .03])[[TRANCHES.index(t) for t in tranches_possibles]]
    age = age or tirer_age(rng, tranches_possibles[rng.choice(len(tranches_possibles), p=p / p.sum())])
    age = max(age, age_permis_min)
    aac = bool(force.get("conduite_accompagnee", age <= 22 and statut_permis == "meme_pays" and rng.random() < 0.4))
    max_permis = max(0, age - age_permis_min)
    annees_permis = int(force.get("annees_permis", min(max_permis, max(0, int(rng.normal(max_permis * 0.85, 2))))))
    if age <= 25 and "annees_permis" not in force:
        annees_permis = int(rng.integers(0, max_permis + 1))
    jamais_assure = annees_permis == 0 or rng.random() < (0.25 if annees_permis <= 2 else 0.02)
    jamais_assure = bool(force.get("jamais_assure", jamais_assure))
    conducteur_secondaire_avant = bool(not jamais_assure and annees_permis <= 3 and rng.random() < 0.5)
    annees_assure = 0 if jamais_assure else int(min(annees_permis, rng.integers(max(1, annees_permis - 3), annees_permis + 1)))
    sinistres_resp = int(force.get("sinistres_responsables_36_mois", rng.choice([0] * 14 + [1] * 4 + [2] * 1 + [3] * 1)))
    if annees_assure == 0:
        sinistres_resp = 0
    sinistres_non_resp = int(rng.choice([0] * 8 + [1] * 2 + [2]))
    bris_glace = int(rng.choice([0] * 7 + [1] * 2 + [2]))
    resiliation = force.get("resiliation_assureur", rng.choice(["non"] * 40 + ["non_paiement", "sinistres", "fausse_declaration"]))
    if jamais_assure:
        resiliation = "non"
    crm = force.get("coefficient_bonus_malus", coefficient_bonus_malus(annees_assure, sinistres_resp, not jamais_assure))
    if conducteur_secondaire_avant and "coefficient_bonus_malus" not in force:
        crm = round(max(0.5, 1.0 * 0.95 ** min(annees_assure, 3)), 2)

    profession = force.get("profession", "etudiant" if age <= 22 and rng.random() < 0.6 else
                           "retraite" if age >= 64 and rng.random() < 0.9 else
                           rng.choice(PROFESSIONS[:3] + PROFESSIONS[5:7] + PROFESSIONS[8:], p=[.48, .2, .1, .08, .05, .03, .06]))
    usage = force.get("usage", "professionnel" if profession in ("commercial_itinerant", "chauffeur_vtc") else
                      "prive" if profession in ("retraite", "sans_emploi") else
                      rng.choice(["prive", "prive_trajet_travail", "prive_trajet_travail", "professionnel"]))
    if profession == "chauffeur_vtc":
        usage = "vtc"
    km = int(force.get("kilometrage_annuel", 60000 if usage == "vtc" else
                       rng.choice([4000, 6000, 8000, 10000, 12000, 15000, 20000, 25000, 35000],
                                  p=[.08, .12, .12, .16, .18, .14, .1, .06, .04])))

    v = vehicule or AUTOS[rng.integers(len(AUTOS))]
    age_vehicule = int(force.get("age_vehicule", rng.choice([0, 1, 2, 3, 4, 5, 7, 9, 11, 14, 17, 20],
                                                             p=[.1, .08, .08, .1, .08, .1, .1, .1, .08, .08, .06, .04])))
    valeur = int(v[5] * 0.85 ** age_vehicule)
    acquisition = force.get("mode_acquisition", "LOA_LLD" if age_vehicule <= 3 and rng.random() < 0.45 else
                            rng.choice(["comptant", "comptant", "credit"]))
    stationnement = force.get("stationnement_nuit", rng.choice(["garage_ferme", "parking_prive", "voie_publique"],
                                                               p=[.35, .3, .35] if loc["type_zone"] != "metropole" else [.15, .35, .5]))
    if statut_permis == "hors_UE" and "jamais_assure" not in force and rng.random() < 0.5:
        # beaucoup de conducteurs au permis étranger n'ont pas de relevé d'information dans leur nouveau pays
        jamais_assure, annees_assure, sinistres_resp, crm, conducteur_secondaire_avant = True, 0, 0, 1.0, False
    annees_sans = max(0, annees_assure - min(sinistres_resp, 3))
    systeme, niveau = bonus_malus_national(code, annees_sans, sinistres_resp, not jamais_assure, crm)
    budget = int(rng.choice([20, 30, 40, 50, 60, 80, 100, 150, 200]))
    formule = force.get("formule_souhaitee", "tous_risques" if (age_vehicule <= 4 or acquisition != "comptant" or v[5] > 40000)
                        else rng.choice(["tiers", "tiers_plus", "tous_risques"], p=[.45, .4, .15]))
    conducteur_sec = force.get("conducteur_secondaire", rng.choice(["aucun"] * 6 + ["conjoint", "enfant_jeune_conducteur", "parent"]))
    return {
        "id_profil": f"A{i:06d}", "type_vehicule": "auto", "profil_reference": force.get("profil_reference"),
        # conducteur principal
        "age": age, "sexe": rng.choice(["homme", "femme"]), "situation_familiale": force.get("situation_familiale",
            rng.choice(["celibataire", "en_couple", "marie_pacse", "veuf_divorce"]) if age >= 22 else "celibataire"),
        "enfants_a_charge": int(rng.choice([0, 0, 1, 2, 3]) if 25 <= age <= 60 else 0),
        "profession": profession, **loc,
        "logement": rng.choice(["maison", "appartement"], p=[.7, .3] if loc["type_zone"] in ("rural", "periurbain") else [.25, .75]),
        # permis
        "type_permis": "B", "annees_permis": annees_permis, "date_permis": f"{AUJOURDHUI.year - annees_permis}-{rng.integers(1, 13):02d}",
        "conduite_accompagnee": aac, "pays_permis": pays_permis, "statut_permis": statut_permis,
        "age_minimal_permis": age_permis_min,
        "permis_echange_ou_reconnu": True if statut_permis != "hors_UE" else bool(rng.random() < 0.7),
        "suspension_ou_annulation_5_ans": bool(force.get("suspension_ou_annulation_5_ans", rng.random() < 0.02)),
        # antécédents d'assurance
        "deja_assure": not jamais_assure, "assure_conducteur_secondaire_avant": conducteur_secondaire_avant,
        "annees_assure_36_derniers_mois": min(annees_assure, 3), "annees_assure_total": annees_assure,
        "coefficient_bonus_malus": crm, "systeme_bonus_malus_national": systeme, "niveau_bonus_malus_national": niveau,
        "annees_sans_sinistre": annees_sans if not jamais_assure else 0, "sinistres_responsables_36_mois": sinistres_resp,
        "sinistres_non_responsables_36_mois": sinistres_non_resp, "bris_de_glace_36_mois": bris_glace,
        "resiliation_assureur": resiliation, "condamnation_alcool_stupefiants": bool(rng.random() < 0.01),
        # véhicule
        "marque_modele": v[0], "categorie_vehicule": v[1], "energie": v[2], "puissance_ch": v[3], "puissance_fiscale_cv": v[4],
        "cylindree_cm3": None, "groupe_sra": v[6], "prix_neuf_eur": v[5], "age_vehicule": age_vehicule,
        "annee_mise_en_circulation": AUJOURDHUI.year - age_vehicule, "valeur_actuelle_eur": valeur,
        "achete_neuf": age_vehicule == 0 or rng.random() < 0.3, "mode_acquisition": acquisition,
        "dispositif_antivol": rng.choice(["aucun", "aucun", "alarme", "traceur_gps"]),
        # usage et stationnement
        "usage": usage, "kilometrage_annuel": km, "stationnement_nuit": stationnement, "conducteur_secondaire": conducteur_sec,
        # couverture souhaitée
        "formule_souhaitee": formule, "franchise_souhaitee": force.get("franchise_souhaitee", rng.choice(["basse", "standard", "standard", "haute"])),
        "option_assistance_0km": bool(rng.random() < 0.5), "option_vehicule_remplacement": bool(rng.random() < 0.35),
        "option_conducteur_renforcee": bool(rng.random() < 0.3),
        "budget_mensuel_max_eur": budget,
        "budget_mensuel_max_devise_locale": round(budget / loc["taux_eur_devise"]),
        "valeur_actuelle_devise_locale": round(valeur / loc["taux_eur_devise"]),
        "paiement": rng.choice(["mensuel", "mensuel", "annuel"]),
    }


def profil_moto(rng, i, age=None, moto=None, commune=None, pays=None, **force):
    code = pays or tirer_pays(rng)
    loc = lieu(rng, code)
    m = moto or MOTOS[rng.integers(len(MOTOS))]
    permis_min = m[2]
    if permis_min == "B+formation":  # 125 cm3 : règle propre à chaque pays
        permis_min = PAYS[code][6]
    age_b = PAYS[code][4] if PAYS[code][4] >= 18 else 18
    age_min = {"AM": PAYS[code][5], "A1": 16, "A2": 18, "A": 20, "B": age_b}.get(permis_min, age_b)
    age = max(age or tirer_age(rng, TRANCHES[1 + rng.choice(9, p=[.1, .14, .14, .2, .16, .12, .08, .04, .02])]), age_min)
    if permis_min == "AM":
        age = age if rng.random() < 0.5 else int(rng.integers(age_min, 18))
    annees_permis_moto = int(min(max(0, age - age_min), rng.choice([0, 1, 2, 3, 5, 8, 12, 20, 30])))
    if permis_min == "A" and annees_permis_moto < 2 and rng.random() < 0.5:
        permis_min_affiche = "A2 (moins de 2 ans) : moto non autorisée"
    else:
        permis_min_affiche = permis_min
    sinistres_resp = int(rng.choice([0] * 14 + [1] * 4 + [2, 3]))
    deja = annees_permis_moto > 0 and rng.random() > 0.1
    annees_assure = annees_permis_moto if deja else 0
    pays_permis, statut_permis, _ = permis_origine(rng, code, 0.10)
    annees_sans = max(0, annees_assure - min(sinistres_resp, 3)) if deja else 0
    crm = coefficient_bonus_malus(annees_assure, sinistres_resp if deja else 0, deja)
    systeme, niveau = bonus_malus_national(code, annees_sans, sinistres_resp if deja else 0, deja, crm)
    age_vehicule = int(rng.choice([0, 1, 2, 3, 5, 7, 10, 15]))
    valeur = int(m[5] * 0.85 ** age_vehicule)
    budget = int(rng.choice([10, 15, 20, 30, 40, 60, 80, 120]))
    return {
        "id_profil": f"M{i:06d}", "type_vehicule": "moto", "profil_reference": None,
        "age": age, "sexe": rng.choice(["homme", "homme", "homme", "femme"]),
        "situation_familiale": rng.choice(["celibataire", "en_couple", "marie_pacse"]) if age >= 22 else "celibataire",
        "enfants_a_charge": int(rng.choice([0, 0, 1, 2]) if 25 <= age <= 60 else 0),
        "profession": "etudiant" if age <= 22 else "retraite" if age >= 64 else rng.choice(["salarie", "fonctionnaire", "independant", "sans_emploi"]),
        **loc, "logement": rng.choice(["maison", "appartement"]),
        "type_permis": permis_min_affiche, "annees_permis": annees_permis_moto,
        "date_permis": f"{AUJOURDHUI.year - annees_permis_moto}-{rng.integers(1, 13):02d}",
        "conduite_accompagnee": False, "pays_permis": pays_permis, "statut_permis": statut_permis, "age_minimal_permis": age_min,
        "permis_echange_ou_reconnu": True if statut_permis != "hors_UE" else bool(rng.random() < 0.7),
        "suspension_ou_annulation_5_ans": bool(rng.random() < 0.02),
        "deja_assure": deja, "assure_conducteur_secondaire_avant": False,
        "annees_assure_36_derniers_mois": min(annees_assure, 3), "annees_assure_total": annees_assure,
        "coefficient_bonus_malus": crm, "systeme_bonus_malus_national": systeme, "niveau_bonus_malus_national": niveau,
        "annees_sans_sinistre": annees_sans,
        "sinistres_responsables_36_mois": sinistres_resp if deja else 0,
        "sinistres_non_responsables_36_mois": int(rng.choice([0] * 8 + [1, 2])), "bris_de_glace_36_mois": 0,
        "resiliation_assureur": rng.choice(["non"] * 40 + ["non_paiement", "sinistres"]),
        "condamnation_alcool_stupefiants": bool(rng.random() < 0.01),
        "marque_modele": m[0], "categorie_vehicule": m[1], "energie": "electrique" if m[4] == 0 else "essence", "puissance_ch": int(round(m[3] * 1.36)),
        "puissance_fiscale_cv": None, "cylindree_cm3": m[4] or None, "groupe_sra": None, "prix_neuf_eur": m[5], "age_vehicule": age_vehicule,
        "annee_mise_en_circulation": AUJOURDHUI.year - age_vehicule, "valeur_actuelle_eur": valeur,
        "achete_neuf": age_vehicule == 0, "mode_acquisition": rng.choice(["comptant", "comptant", "credit"]),
        "dispositif_antivol": rng.choice(["aucun", "antivol_u_ou_bloque_disque", "alarme", "traceur_gps"]),
        "usage": rng.choice(["loisirs", "prive_trajet_travail", "prive_trajet_travail", "professionnel"]),
        "kilometrage_annuel": int(rng.choice([2000, 4000, 6000, 8000, 12000, 18000])),
        "stationnement_nuit": rng.choice(["garage_ferme", "parking_prive", "voie_publique"]),
        "conducteur_secondaire": "aucun",
        "formule_souhaitee": "tous_risques" if age_vehicule <= 3 else rng.choice(["tiers", "tiers_plus", "tous_risques"], p=[.5, .35, .15]),
        "franchise_souhaitee": rng.choice(["basse", "standard", "haute"]),
        "option_assistance_0km": bool(rng.random() < 0.5), "option_vehicule_remplacement": False,
        "option_conducteur_renforcee": bool(rng.random() < 0.4),
        "option_equipement_casque": bool(rng.random() < 0.5),
        "budget_mensuel_max_eur": budget,
        "budget_mensuel_max_devise_locale": round(budget / loc["taux_eur_devise"]),
        "valeur_actuelle_devise_locale": round(valeur / loc["taux_eur_devise"]),
        "paiement": rng.choice(["mensuel", "annuel"]),
    }


def profils_reference() -> list[dict]:
    """Les profils des vrais prix relevés (Selectra et sites des assureurs), reproduits champ par champ."""
    rng = np.random.default_rng(1)
    clio = next(v for v in AUTOS if v[0] == "Renault Clio 4")
    e208 = next(v for v in AUTOS if v[0] == "Peugeot e-208")
    p508 = ("Peugeot 508 1.2 PureTech", "berline", "essence", 130, 7, 38000, "J")
    nantes = next(c for c in COMMUNES if c[0] == "Nantes")
    commun = dict(vehicule=clio, commune=nantes, age_vehicule=11, kilometrage_annuel=12000, stationnement_nuit="parking_prive",
                  usage="prive_trajet_travail", pays_permis="France", conducteur_secondaire="aucun", mode_acquisition="comptant",
                  suspension_ou_annulation_5_ans=False, resiliation_assureur="non")
    refs = [
        ("bonus_experienced", 50, dict(annees_permis=30, coefficient_bonus_malus=0.5, sinistres_responsables_36_mois=0, profession="salarie")),
        ("malus", 50, dict(annees_permis=30, coefficient_bonus_malus=1.09, sinistres_responsables_36_mois=2, profession="salarie")),
        ("young_driver", 22, dict(annees_permis=2, coefficient_bonus_malus=0.9, sinistres_responsables_36_mois=0, profession="etudiant",
                                  age_vehicule=11, mode_acquisition="comptant")),
        ("low_mileage", 50, dict(annees_permis=30, coefficient_bonus_malus=0.5, sinistres_responsables_36_mois=0, profession="salarie",
                                 kilometrage_annuel=6000, usage="prive")),
        ("electric_vehicle", 50, dict(annees_permis=30, coefficient_bonus_malus=0.5, sinistres_responsables_36_mois=0, profession="salarie",
                                      vehicule=e208, age_vehicule=5)),
        ("cancelled", 50, dict(annees_permis=30, coefficient_bonus_malus=0.5, sinistres_responsables_36_mois=0, profession="salarie",
                               resiliation_assureur="non_paiement")),
        ("vtc_driver", 50, dict(annees_permis=30, coefficient_bonus_malus=0.5, sinistres_responsables_36_mois=0, profession="chauffeur_vtc",
                                vehicule=p508, age_vehicule=2, kilometrage_annuel=60000, usage="vtc")),
        ("age_17", 17, dict(annees_permis=0, coefficient_bonus_malus=1.0, sinistres_responsables_36_mois=0, profession="etudiant",
                            jamais_assure=True)),
    ]
    sortie = []
    for k, (cle, age, f) in enumerate(refs):
        params = {**commun, **f}
        p = profil_auto(rng, 900000 + k, age=age, vehicule=params.pop("vehicule"), commune=params.pop("commune"),
                        profil_reference=cle, **params)
        p["id_profil"] = f"REF_{cle}"
        p["sexe"] = "homme"
        sortie.append(p)
    return sortie


def verifier(df: pd.DataFrame) -> list[str]:
    """Règles de cohérence : renvoie la liste des problèmes trouvés (doit être vide)."""
    pb = []
    auto = df[df.type_vehicule == "auto"]
    if (auto.annees_permis > auto.age - auto.age_minimal_permis).any():
        pb.append("permis auto obtenu avant l'âge minimal du pays d'obtention")
    if (df.age < df.age_minimal_permis).any():
        pb.append("conducteur plus jeune que l'âge minimal du permis")
    if df.code_pays.isna().any() or df.commune.isna().any():
        pb.append("pays ou ville manquant")
    if (df.annees_sans_sinistre > df.annees_assure_total).any():
        pb.append("plus d'années sans sinistre que d'années d'assurance")
    if (df.coefficient_bonus_malus < 0.5).any() or (df.coefficient_bonus_malus > 3.5).any():
        pb.append("bonus-malus hors de 0,50 à 3,50")
    if ((~df.deja_assure) & (df.sinistres_responsables_36_mois > 0)).any():
        pb.append("sinistres responsables sans avoir été assuré")
    if (df.annees_assure_total > df.annees_permis).any():
        pb.append("assuré plus longtemps que la durée du permis")
    if ((df.usage == "vtc") & (df.kilometrage_annuel < 20000)).any():
        pb.append("VTC avec un faible kilométrage")
    return pb


def dictionnaire() -> pd.DataFrame:
    d = [
        ("id_profil", "Identifiant", "texte", "A000001 (auto), M000001 (moto), REF_… (profil d'un vrai prix relevé)"),
        ("type_vehicule", "Quel véhicule souhaitez-vous assurer ?", "choix", "auto, moto"),
        ("profil_reference", "Profil de référence d'un vrai prix", "choix", "vide, bonus_experienced, malus, young_driver, low_mileage, electric_vehicle, cancelled, vtc_driver, age_17"),
        ("age", "Quelle est votre date de naissance ? (âge)", "entier", "14 à 90"),
        ("sexe", "Civilité (information seulement : interdit pour le tarif dans l'UE)", "choix", "homme, femme"),
        ("situation_familiale", "Situation familiale", "choix", "celibataire, en_couple, marie_pacse, veuf_divorce"),
        ("enfants_a_charge", "Nombre d'enfants à charge", "entier", "0 à 3"),
        ("profession", "Profession", "choix", ", ".join(PROFESSIONS)),
        ("pays_residence, code_pays", "Dans quel pays habitez-vous ?", "choix", ", ".join(f"{v[0]} ({k})" for k, v in PAYS.items())),
        ("commune, code_postal, region", "Où habitez-vous ?", "texte", f"{sum(len(v) for v in LIEUX.values())} villes réelles, de la capitale au village"),
        ("departement", "Département (France seulement)", "texte", "vide hors France"),
        ("devise_locale, taux_eur_devise", "Devise du pays et valeur d'une unité en euros", "texte / décimal", "EUR, GBP, CHF, PLN, SEK, NOK, DKK, CZK, RON ; taux approximatifs 2026"),
        ("type_zone", "Type de zone (déduit de la commune)", "choix", "rural, periurbain, urbain, grande_ville, metropole"),
        ("logement", "Type de logement", "choix", "maison, appartement"),
        ("type_permis", "Type de permis", "choix", "B (auto) ; AM, B+formation, A1, A2, A (moto)"),
        ("annees_permis, date_permis", "Date d'obtention du permis", "entier / AAAA-MM", "0 à 73 ans"),
        ("conduite_accompagnee", "Avez-vous suivi la conduite accompagnée ?", "oui/non", ""),
        ("pays_permis", "Pays d'obtention du permis", "choix", f"pays de résidence ou l'un de {len(PAYS_PERMIS_MONDE)} pays d'Europe, d'Afrique, d'Asie, d'Amérique et d'Océanie"),
        ("statut_permis", "Statut du permis", "choix", "meme_pays, UE_EEE (reconnu tel quel), hors_UE"),
        ("age_minimal_permis", "Âge minimal du permis dans le pays d'obtention", "entier", "14 à 20 selon pays et catégorie"),
        ("permis_echange_ou_reconnu", "Votre permis est-il échangé ou reconnu dans le pays ?", "oui/non", "toujours oui pour un permis UE"),
        ("suspension_ou_annulation_5_ans", "Suspension ou annulation de permis ces 5 dernières années ?", "oui/non", ""),
        ("deja_assure", "Avez-vous déjà été assuré en tant que conducteur principal ?", "oui/non", ""),
        ("assure_conducteur_secondaire_avant", "Avez-vous été conducteur secondaire ?", "oui/non", ""),
        ("annees_assure_36_derniers_mois", "Combien de mois assuré sur les 36 derniers mois ? (en années)", "entier", "0 à 3"),
        ("annees_assure_total", "Depuis combien d'années êtes-vous assuré ?", "entier", ""),
        ("coefficient_bonus_malus", "Coefficient bonus-malus, équivalent de la règle française (pour comparer tous les pays)", "décimal", "0,50 à 3,50"),
        ("systeme_bonus_malus_national", "Système de bonus-malus du pays", "choix", "crm_france, sf_klasse (DE), classe_merito (IT), degre_bonus_malus (BE), stufe_autriche (AT), trede (NL), bonus_malus_roumanie (RO), bonus_norvege, bonus_finlande, no_claims_bonus (GB, IE), annees_sans_sinistre (autres)"),
        ("niveau_bonus_malus_national", "Niveau dans le système du pays (tel qu'écrit sur le relevé)", "texte", "ex. CRM 0.68, classe 9, degré 6, SF 12, Stufe 4, trede 14, B3, bonus 60 %, 5 ans de no claims bonus ; règles simplifiées"),
        ("annees_sans_sinistre", "Années d'assurance sans sinistre responsable", "entier", "commun à tous les pays"),
        ("sinistres_responsables_36_mois", "Sinistres responsables ces 36 derniers mois", "entier", "0 à 3"),
        ("sinistres_non_responsables_36_mois", "Sinistres non responsables ces 36 derniers mois", "entier", "0 à 2"),
        ("bris_de_glace_36_mois", "Bris de glace ces 36 derniers mois", "entier", "0 à 2"),
        ("resiliation_assureur", "Avez-vous été résilié par un assureur ?", "choix", "non, non_paiement, sinistres, fausse_declaration"),
        ("condamnation_alcool_stupefiants", "Condamnation pour alcool ou stupéfiants ?", "oui/non", ""),
        ("marque_modele, categorie_vehicule", "Marque et modèle du véhicule", "texte", f"{len(AUTOS)} voitures et {len(MOTOS)} motos réelles"),
        ("energie", "Énergie", "choix", "essence, diesel, hybride, electrique"),
        ("puissance_ch, puissance_fiscale_cv, cylindree_cm3", "Puissance (carte grise)", "entier", ""),
        ("groupe_sra", "Classe de prix SRA du véhicule (approximation)", "lettre", "C à W"),
        ("prix_neuf_eur, valeur_actuelle_eur", "Valeur du véhicule", "€", "valeur actuelle = prix neuf x 0,85 ^ âge"),
        ("age_vehicule, annee_mise_en_circulation", "Date de première mise en circulation", "entier", "0 à 20 ans"),
        ("achete_neuf", "Véhicule acheté neuf ?", "oui/non", ""),
        ("mode_acquisition", "Mode d'achat", "choix", "comptant, credit, LOA_LLD"),
        ("dispositif_antivol", "Dispositif antivol", "choix", "aucun, alarme, traceur_gps, antivol_u_ou_bloque_disque"),
        ("usage", "Usage du véhicule", "choix", "prive, prive_trajet_travail, professionnel, vtc (auto) ; loisirs (moto)"),
        ("kilometrage_annuel", "Kilométrage annuel", "entier", "2 000 à 60 000 km"),
        ("stationnement_nuit", "Où stationne le véhicule la nuit ?", "choix", "garage_ferme, parking_prive, voie_publique"),
        ("conducteur_secondaire", "Conducteur secondaire", "choix", "aucun, conjoint, enfant_jeune_conducteur, parent"),
        ("formule_souhaitee", "Formule souhaitée", "choix", "tiers, tiers_plus, tous_risques"),
        ("franchise_souhaitee", "Niveau de franchise", "choix", "basse, standard, haute"),
        ("option_assistance_0km, option_vehicule_remplacement, option_conducteur_renforcee, option_equipement_casque", "Options souhaitées", "oui/non", ""),
        ("budget_mensuel_max_eur, budget_mensuel_max_devise_locale", "Budget mensuel maximum", "€ / devise", "10 à 200 €"),
        ("valeur_actuelle_devise_locale", "Valeur du véhicule en devise locale", "devise", ""),
        ("paiement", "Fréquence de paiement", "choix", "mensuel, annuel"),
    ]
    return pd.DataFrame(d, columns=["champ", "question_du_formulaire", "type", "valeurs_possibles"])


def couverture(df: pd.DataFrame) -> pd.DataFrame:
    champs = ["type_vehicule", "pays_residence", "statut_permis", "pays_permis", "systeme_bonus_malus_national", "devise_locale", "type_zone", "profession", "resiliation_assureur", "categorie_vehicule", "energie",
              "usage", "stationnement_nuit", "formule_souhaitee", "franchise_souhaitee", "conducteur_secondaire", "mode_acquisition"]
    lignes = []
    tr = pd.cut(df.age, [13, 17, 20, 25, 30, 40, 50, 60, 70, 80, 95], labels=["14-17", "18-20", "21-25", "26-30", "31-40",
                "41-50", "51-60", "61-70", "71-80", "81+"]).astype(str)
    for v, n in tr.value_counts().sort_index().items():
        lignes.append(("tranche_age", v, n))
    ap = pd.cut(df.annees_permis, [-1, 0, 2, 5, 10, 20, 80], labels=["0", "1-2", "3-5", "6-10", "11-20", "21+"]).astype(str)
    for v, n in ap.value_counts().sort_index().items():
        lignes.append(("annees_permis", v, n))
    bm = pd.cut(df.coefficient_bonus_malus, [0, .5, .7, .95, 1.0, 1.5, 3.5], labels=["0,50", "0,51-0,70", "0,71-0,95",
                "0,96-1,00", "1,01-1,50", "> 1,50"]).astype(str)
    for v, n in bm.value_counts().sort_index().items():
        lignes.append(("coefficient_bonus_malus", v, n))
    for c in ["sinistres_responsables_36_mois"] + champs:
        for v, n in df[c].astype(str).value_counts().items():
            lignes.append((c, v, n))
    return pd.DataFrame(lignes, columns=["champ", "valeur", "nb_profils"])


def ecrire_readme(df, couv, problemes):
    n = lambda x: f"{x:,}".replace(",", " ")
    l = ["# Base de profils d'assurés auto et moto (Europe, permis du monde entier)", "",
         "Profils fictifs mais **réalistes**, organisés comme les formulaires de devis des assureurs, pour estimer "
         "le prix de chaque offre selon le profil (objectif 1). Générés par `src/profils.py` (graine fixe : la base est "
         "toujours la même).", "",
         f"- **Profils** : {n(len(df))} ({n((df.type_vehicule == 'auto').sum())} auto, {n((df.type_vehicule == 'moto').sum())} moto)",
         f"- **Profils de référence des vrais prix** : {df.profil_reference.notna().sum()} (identifiants `REF_…`), reproduits "
         "d'après `data/externe/offres_auto_france/auto_prices.csv` pour caler le simulateur",
         f"- **Pays de résidence** : {df.code_pays.nunique()} ({', '.join(f'{k} {n(v)}' for k, v in df.pays_residence.value_counts().items())})",
         f"- **Villes réelles** : {df.commune.nunique()}",
         f"- **Pays d'obtention du permis** : {df.pays_permis.nunique()} ({n((df.statut_permis == 'meme_pays').sum())} dans le pays, "
         f"{n((df.statut_permis == 'UE_EEE').sum())} UE/EEE, {n((df.statut_permis == 'hors_UE').sum())} hors UE)",
         f"- **Champs** : {df.shape[1]}, dans l'ordre d'un formulaire de devis",
         f"- **Contrôles de cohérence** : {'aucun problème' if not problemes else ', '.join(problemes)}", "",
         "## Organisation", "", "| Bloc du formulaire | Champs |", "| --- | --- |",
         "| Conducteur | âge, sexe, situation familiale, enfants, profession, pays, ville, code postal, région, type de zone, devise, logement |",
         "| Permis | type, ancienneté, date, conduite accompagnée, pays d'obtention, statut (même pays, UE, hors UE), échange, suspension |",
         "| Antécédents | déjà assuré, années assuré, bonus-malus (équivalent français et système du pays), années sans sinistre, sinistres, bris de glace, résiliation, condamnation |",
         "| Véhicule | marque et modèle réels, catégorie, énergie, puissance, classe de prix, valeur, âge, achat, antivol |",
         "| Usage | usage, kilométrage, stationnement la nuit, conducteur secondaire |",
         "| Couverture souhaitée | formule, franchise, options, budget, paiement |", "",
         "Le détail de chaque champ (question du formulaire, valeurs possibles) est dans `dictionnaire.csv`.", "",
         "## Règles de cohérence", "",
         "- Permis B à l'âge minimal du pays d'obtention (16 aux États-Unis, 17 en France, Allemagne, Royaume-Uni…, 18 ailleurs) ; "
         "permis moto selon la catégorie (AM selon le pays, A1 16 ans, A2 18 ans, A 20 ans) ; 125 cm3 avec permis B selon la règle du pays.",
         "- Bonus-malus : coefficient selon la règle française pour tous (1,00 au départ, x 0,95 par an sans sinistre, x 1,25 par sinistre, "
         "0,50 à 3,50), pour comparer, et niveau dans le système du pays (classe di merito, SF-Klasse, degré belge, Stufe, trede…, règles simplifiées).",
         "- Permis hors UE : souvent sans relevé d'assurance dans le nouveau pays (jamais assuré ici), permis pas toujours échangé.",
         "- Taux de change approximatifs (2026) : montants donnés en euros et en devise locale.",
         "- Pas de sinistre sans avoir été assuré ; pas plus d'années d'assurance que d'années de permis.",
         "- Profession, usage et kilométrage liés (VTC : usage vtc et 60 000 km/an ; retraité : usage privé…).",
         "- Formule souhaitée liée au véhicule (récent, cher ou en location : tous risques).",
         "- Valeur actuelle = prix neuf x 0,85 par année d'âge. Le sexe est gardé pour information mais ne doit pas servir au prix (interdit dans l'UE).", "",
         "## Couverture (extrait)", "", "| Champ | Valeur | Profils |", "| --- | --- | --- |"]
    for _, r in couv[couv.champ.isin(["pays_residence", "statut_permis", "tranche_age", "annees_permis", "coefficient_bonus_malus", "type_zone",
                                      "categorie_vehicule", "formule_souhaitee"])].iterrows():
        l.append(f"| {r.champ} | {r.valeur} | {n(int(r.nb_profils))} |")
    l += ["", "Toutes les valeurs de tous les champs : `couverture.csv`.", "",
          "## Utilisation", "", "```python", "import pandas as pd", "profils = pd.read_parquet(\"profils.parquet\")",
          "jeunes = profils[(profils.annees_permis < 3) & (profils.type_vehicule == \"auto\")]", "```", ""]
    (SORTIE / "README.md").write_text("\n".join(l), encoding="utf-8")


def main() -> int:
    SORTIE.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(GRAINE)
    profils = profils_reference()
    # 1) couverture garantie : chaque pays x chaque tranche d'âge x chaque catégorie de véhicule (zone tournante)
    cats_auto = sorted({v[1] for v in AUTOS})
    i = 0
    for code in CODES:
        for tr in TRANCHES[1:]:
            for k, cat in enumerate(cats_auto):
                v = [x for x in AUTOS if x[1] == cat]
                profils.append(profil_auto(rng, i, age=tirer_age(rng, tr), vehicule=v[rng.integers(len(v))], pays=code,
                                           zone=ZONES[(k + i) % len(ZONES)]))
                i += 1
        # chaque pays x chaque type de zone
        for z in ZONES:
            for _ in range(5):
                profils.append(profil_auto(rng, i, pays=code, zone=z))
                i += 1
    # 2) le reste au hasard, avec le poids réel de chaque pays
    while i < NB_AUTO:
        profils.append(profil_auto(rng, i))
        i += 1
    # motos : chaque pays x chaque modèle, puis au hasard
    j = 0
    for code in CODES:
        for m in MOTOS:
            profils.append(profil_moto(rng, j, moto=m, pays=code))
            j += 1
    while j < NB_MOTO:
        profils.append(profil_moto(rng, j))
        j += 1
    df = pd.DataFrame(profils)
    df.insert(1, "type_vehicule", df.pop("type_vehicule"))
    problemes = verifier(df)
    df.to_parquet(SORTIE / "profils.parquet", index=False)
    df.to_csv(SORTIE / "profils.csv", index=False, sep=";", encoding="utf-8-sig")
    dictionnaire().to_csv(SORTIE / "dictionnaire.csv", index=False, sep=";", encoding="utf-8-sig")
    couv = couverture(df)
    couv.to_csv(SORTIE / "couverture.csv", index=False, sep=";", encoding="utf-8-sig")
    ecrire_readme(df, couv, problemes)
    print(f"[profils] {len(df)} profils, {df.shape[1]} champs ; cohérence : {problemes or 'OK'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
