"""
Base de sinistres détaillés pour l'objectif 3 (prédire le coût d'un sinistre).

Point de départ RÉEL : les 26 444 sinistres individuels de freMTPL2 (France, assurance responsabilité civile auto),
avec leur vrai coût et le vrai profil du contrat (âge du conducteur, véhicule, bonus-malus, zone, région…).

Ce qui est AJOUTÉ (généré, cohérent avec le coût réel) : ce que les données publiques ne donnent pas mais dont
l'objectif 3 a besoin pour tester des LLM : le type de sinistre, les circonstances de l'accident, le lieu, le moment,
la météo, les blessés, et une déclaration de sinistre en texte libre (comme celle qu'un assuré écrit à son assureur).

Comment c'est cohérent :
  - freMTPL2 ne contient que des sinistres de responsabilité civile (l'assuré a causé un dommage à un tiers) ;
  - le type (matériel ou corporel) est tiré selon la règle de Bayes à partir des fréquences et des coûts moyens
    publiés par France Assureurs (data/externe/offres_auto_france/market_auto_guarantee_stats.csv) et du coût réel ;
  - les montants répétés (1 204 €, 1 128,12 €, 1 172 €…) sont des forfaits de la convention d'indemnisation entre
    assureurs (IRSA) : ils sont repérés comme tels ;
  - la gravité décrite dans le texte (rayure, choc, véhicule non roulant, blessé…) suit le coût réel, sans jamais
    écrire le montant.

Sorties (data/objectif3/) : sinistres_detailles.parquet / .csv, dictionnaire.csv, README.md
Lancement :  python -m src.sinistres_detailles
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SOURCE = Path("data/externe/fremtpl2")
MARCHE = Path("data/externe/offres_auto_france/market_auto_guarantee_stats.csv")
SORTIE = Path("data/objectif3")
GRAINE = 2026

# Circonstances d'un sinistre de responsabilité civile (l'assuré est responsable, au moins en partie)
CIRCONSTANCES = {
    "materiel": [
        ("collision_arriere", "a heurté l'arrière du véhicule qui le précédait", 0.24),
        ("refus_priorite", "n'a pas respecté une priorité à un carrefour", 0.16),
        ("changement_file", "a changé de file et accroché un autre véhicule", 0.10),
        ("marche_arriere_stationnement", "a heurté un véhicule en manœuvrant ou en marche arrière", 0.20),
        ("portiere", "a ouvert sa portière sur un véhicule qui passait", 0.04),
        ("perte_controle_bien", "a perdu le contrôle et percuté un mur|a perdu le contrôle et abîmé une clôture|a perdu le contrôle et heurté un abribus", 0.08),
        ("feu_rouge_stop", "n'a pas respecté un feu rouge ou un stop", 0.08),
        ("vehicule_stationne", "a heurté un véhicule en stationnement", 0.10),
    ],
    "corporel": [
        ("pieton", "a renversé un piéton", 0.22),
        ("cycliste_2roues", "a heurté un cycliste|a heurté un scooter|a percuté un motard", 0.28),
        ("collision_arriere", "a heurté l'arrière d'un véhicule, dont un occupant a été blessé", 0.18),
        ("refus_priorite", "a refusé une priorité, l'autre conducteur a été blessé", 0.16),
        ("choc_frontal", "a eu un choc frontal avec un autre véhicule", 0.08),
        ("passager_blesse", "a eu un accident dans lequel un passager a été blessé", 0.08),
    ],
}
LIEUX = {"collision_arriere": ["agglomeration", "route", "autoroute"], "refus_priorite": ["agglomeration", "route"],
         "changement_file": ["agglomeration", "autoroute", "voie_rapide"], "marche_arriere_stationnement": ["parking", "agglomeration"],
         "portiere": ["agglomeration"], "perte_controle_bien": ["route", "agglomeration"], "feu_rouge_stop": ["agglomeration"],
         "vehicule_stationne": ["parking", "agglomeration"], "pieton": ["agglomeration", "parking"],
         "cycliste_2roues": ["agglomeration", "route"], "choc_frontal": ["route"], "passager_blesse": ["route", "autoroute", "agglomeration"]}
TEXTE_LIEU = {"agglomeration": ["en ville", "dans une rue de {ville}", "en centre-ville", "à un carrefour en ville"],
              "route": ["sur une route départementale", "sur une petite route de campagne", "sur une nationale"],
              "autoroute": ["sur l'autoroute", "sur l'autoroute, près d'une sortie"],
              "voie_rapide": ["sur la rocade", "sur une voie rapide"],
              "parking": ["sur un parking de supermarché", "dans un parking souterrain", "sur le parking de mon travail"]}
VILLES = {"Ile-de-France": "Paris", "Rhone-Alpes": "Lyon", "Provence-Alpes-Cotes-D'Azur": "Marseille", "Nord-Pas-de-Calais": "Lille",
          "Aquitaine": "Bordeaux", "Midi-Pyrenees": "Toulouse", "Bretagne": "Rennes", "Pays-de-la-Loire": "Nantes",
          "Languedoc-Roussillon": "Montpellier", "Alsace": "Strasbourg", "Centre": "Tours", "Picardie": "Amiens",
          "Limousin": "Limoges", "Poitou-Charentes": "Poitiers", "Auvergne": "Clermont-Ferrand", "Corse": "Ajaccio",
          "Basse-Normandie": "Caen", "Haute-Normandie": "Rouen", "Bourgogne": "Dijon", "Franche-Comte": "Besançon",
          "Champagne-Ardenne": "Reims"}
METEO = ["sec", "sec", "sec", "pluie", "pluie", "brouillard", "neige_verglas"]
TEXTE_METEO = {"sec": "", "pluie": " Il pleuvait.", "brouillard": " Il y avait du brouillard.", "neige_verglas": " La route était glissante (verglas)."}


def gravite(cout: float, type_: str) -> str:
    if type_ == "corporel":
        return "blesse_leger" if cout < 5000 else "blesse_hospitalise" if cout < 50000 else "blesse_grave"
    return "leger" if cout < 600 else "moyen" if cout < 2500 else "important" if cout < 8000 else "tres_important"


DEGATS = {
    "leger": ["Juste une rayure et un petit enfoncement sur le pare-choc de l'autre véhicule.", "Dégâts légers : rétroviseur et pare-choc rayés.",
              "Choc léger, quelques rayures sur la carrosserie de l'autre voiture."],
    "moyen": ["Le pare-choc et une aile de l'autre véhicule sont abîmés, phare cassé.", "La portière et l'aile de l'autre voiture sont enfoncées.",
              "Dégâts sur l'avant de l'autre véhicule (pare-choc, calandre)."],
    "important": ["L'autre véhicule a l'avant bien enfoncé, il a dû être remorqué.", "Gros dégâts sur l'autre voiture, airbags déclenchés.",
                  "Le côté de l'autre véhicule est très abîmé, il ne roule plus."],
    "tres_important": ["L'autre véhicule est très endommagé, probablement épave.", "Plusieurs véhicules touchés, gros dégâts.",
                       "Le véhicule de l'autre conducteur n'est plus roulant, dégâts importants sur la structure."],
    "blesse_leger": ["L'autre personne a été légèrement blessée (contusions), vue par un médecin.", "Le cycliste a eu des égratignures et une douleur au poignet."],
    "blesse_hospitalise": ["La personne blessée a été emmenée aux urgences et hospitalisée quelques jours.", "Le blessé a une fracture, il a été hospitalisé."],
    "blesse_grave": ["La victime a été gravement blessée et hospitalisée longtemps.", "Le blessé a des séquelles importantes, hospitalisation de plusieurs semaines."],
}


def lognorm_pdf(x, moyenne, sigma):
    mu = np.log(moyenne) - sigma ** 2 / 2
    return np.exp(-(np.log(x) - mu) ** 2 / (2 * sigma ** 2)) / (x * sigma * np.sqrt(2 * np.pi))


def choisir_type(rng, cout, stats):
    """Bayes : P(type | coût) proportionnel à fréquence(type) x densité(coût | type)."""
    f_mat, f_corp = stats["rc_materiels"]["freq"], stats["rc_corporels"]["freq"]
    p_mat = f_mat * lognorm_pdf(cout, stats["rc_materiels"]["cout"], 0.9)
    p_corp = f_corp * lognorm_pdf(cout, stats["rc_corporels"]["cout"], 1.4)
    corporel = (rng.random(len(cout)) < p_corp / (p_mat + p_corp)) & (cout >= 500)   # un corporel coûte au moins quelques centaines d'euros
    return np.where(corporel, "corporel", "materiel")


def declaration(rng, r) -> str:
    texte_circ = rng.choice(dict((c, t) for c, t, _ in CIRCONSTANCES[r.type_sinistre])[r.circonstance].split("|"))
    lieu = rng.choice(TEXTE_LIEU[r.lieu]).format(ville=VILLES.get(r.region, "ville"))
    heure = f"vers {r.heure}h" if rng.random() < 0.7 else ("matin" if 5 <= r.heure < 12 else "après-midi" if r.heure < 18
                                                           else "soir" if r.heure < 22 else "dans la nuit")
    debut = rng.choice([f"{r.jour_semaine.capitalize()} {heure}, {lieu}, ", f"{lieu[0].upper() + lieu[1:]}, {r.jour_semaine} {heure} : ",
                        f"Bonjour, je déclare un sinistre. {r.jour_semaine.capitalize()} {heure}, {lieu}, "])
    sujet = rng.choice(["j'", "je "]) if rng.random() < 0.75 else "le conducteur de mon véhicule "
    verbe = texte_circ.replace("a heurté", "ai heurté").replace("n'a pas", "n'ai pas").replace("a changé", "ai changé") \
        .replace("a ouvert sa", "ai ouvert ma").replace("a perdu", "ai perdu").replace("a renversé", "ai renversé") \
        .replace("a refusé", "ai refusé").replace("a eu", "ai eu").replace("a été", "a été") if sujet != "le conducteur de mon véhicule " else texte_circ
    if sujet in ("j'", "je "):
        sujet = "j'" if verbe.startswith("ai") else "je "
    if sujet != "le conducteur de mon véhicule ":
        verbe = verbe.replace("qui le précédait", "qui me précédait")
    phrase = debut + sujet + verbe + "."
    phrase += TEXTE_METEO[r.meteo]
    if r.circonstance == "perte_controle_bien":
        phrase += " " + {"leger": "Quelques dégâts légers sur le bien.", "moyen": "Le bien est abîmé, il faudra le réparer.",
                         "important": "Le bien est fortement endommagé.", "tres_important": "Le bien est détruit, gros travaux à prévoir."}[r.gravite_decrite]
    else:
        phrase += " " + rng.choice(DEGATS[r.gravite_decrite])
    if r.nb_vehicules > 2:
        phrase += f" {r.nb_vehicules} véhicules impliqués."
    phrase += rng.choice([" Constat amiable rempli avec l'autre conducteur.", " Constat amiable signé sur place.",
                          " Pas de constat, les coordonnées ont été échangées.", " La police est intervenue."]) \
        if r.tiers_identifie else " Pas de constat (bien appartenant à un tiers absent)."
    if r.type_sinistre == "materiel" and rng.random() < 0.3:
        phrase += rng.choice([" Mon véhicule a aussi une rayure.", " Aucun blessé.", " Personne n'a été blessé."])
    return phrase


def main() -> int:
    SORTIE.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(GRAINE)
    sin = pd.read_parquet(SOURCE / "fremtpl2_claims.parquet")
    pol = pd.read_parquet(SOURCE / "fremtpl2_policies.parquet")
    df = sin.merge(pol.drop(columns=["claim_amount_total"]), on="id_pol", how="inner")
    df = df[df.claim_amount > 0].reset_index(drop=True)

    m = pd.read_csv(MARCHE)
    get = lambda g, k: float(m[(m.guarantee == g) & (m.metric == k)].value.iloc[0])
    stats = {"rc_materiels": {"freq": get("rc_materiels", "claim_frequency"), "cout": get("rc_materiels", "avg_claim_cost")},
             "rc_corporels": {"freq": get("rc_corporels", "claim_frequency"), "cout": 20000.0}}   # coût corporel : hypothèse
    cout = df.claim_amount.to_numpy()
    forfaits = set(df.claim_amount.value_counts().loc[lambda s: s >= 300].index)

    df["forfait_convention_irsa"] = df.claim_amount.isin(forfaits)
    df["type_sinistre"] = choisir_type(rng, cout, stats)
    df.loc[df.forfait_convention_irsa, "type_sinistre"] = "materiel"     # les forfaits IRSA sont des dégâts matériels
    df["circonstance"] = [rng.choice([c for c, _, _ in CIRCONSTANCES[t]], p=[p for _, _, p in CIRCONSTANCES[t]]) for t in df.type_sinistre]
    df["lieu"] = [rng.choice(LIEUX[c]) for c in df.circonstance]
    df["responsabilite"] = np.where(rng.random(len(df)) < 0.8, "totale", "partagee")
    df["nb_vehicules"] = np.where(df.circonstance.isin(["perte_controle_bien", "pieton", "passager_blesse"]), 1,
                                  np.where((df.type_sinistre == "materiel") & (cout > 8000) & (rng.random(len(df)) < 0.3), 3, 2))
    df["tiers_identifie"] = df.circonstance != "perte_controle_bien"
    df["nb_blesses"] = np.where(df.type_sinistre == "corporel", np.where(cout > 50000, rng.integers(1, 4, len(df)), 1), 0)
    df["gravite_decrite"] = [gravite(c, t) for c, t in zip(cout, df.type_sinistre)]
    df["mois"] = rng.integers(1, 13, len(df))
    df["jour_semaine"] = rng.choice(["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"], len(df),
                                    p=[.15, .15, .15, .15, .17, .13, .10])
    poids = np.array([1, .5, .5, .5, .5, 1, 3, 6, 8, 6, 5, 5, 6, 6, 5, 6, 8, 9, 8, 5, 3, 2, 1.5, 1.5])
    df["heure"] = rng.choice(np.arange(24), len(df), p=poids / poids.sum())
    df["meteo"] = rng.choice(METEO, len(df))
    df.loc[df.mois.isin([5, 6, 7, 8]) & (df.meteo == "neige_verglas"), "meteo"] = "sec"
    df["delai_declaration_jours"] = np.clip(rng.geometric(0.45, len(df)) - 1, 0, 30)
    df["description_declaration"] = [declaration(rng, r) for r in df.itertuples()]
    df["cout_sinistre_eur"] = df.claim_amount.round(2)
    df["log_cout"] = np.log(df.cout_sinistre_eur)
    seuil = df.cout_sinistre_eur.quantile(0.95)
    df["sinistre_grave"] = df.cout_sinistre_eur > seuil
    # découpage fixe pour le benchmark : 70 % entraînement, 15 % validation, 15 % test (par contrat, sans fuite)
    contrats = df.id_pol.unique()
    rng.shuffle(contrats)
    n = len(contrats)
    jeu = {c: "entrainement" for c in contrats[: int(n * .7)]}
    jeu.update({c: "validation" for c in contrats[int(n * .7): int(n * .85)]})
    jeu.update({c: "test" for c in contrats[int(n * .85):]})
    df["jeu"] = df.id_pol.map(jeu)

    colonnes = {
        "claim_id": "id_sinistre", "id_pol": "id_contrat", "driv_age": "age_conducteur", "bonus_malus": "bonus_malus",
        "veh_age": "age_vehicule", "veh_power": "puissance_vehicule", "veh_brand": "marque_vehicule", "veh_gas": "carburant",
        "area": "zone", "density": "densite_population", "region": "region", "exposure": "exposition", "claim_nb": "nb_sinistres_contrat",
    }
    df = df.rename(columns=colonnes)
    ordre = ["id_sinistre", "id_contrat", "jeu",
             "age_conducteur", "bonus_malus", "age_vehicule", "puissance_vehicule", "marque_vehicule", "carburant", "zone",
             "densite_population", "region", "exposition", "nb_sinistres_contrat",
             "type_sinistre", "circonstance", "lieu", "responsabilite", "nb_vehicules", "tiers_identifie", "nb_blesses",
             "gravite_decrite", "mois", "jour_semaine", "heure", "meteo", "delai_declaration_jours", "description_declaration",
             "forfait_convention_irsa", "cout_sinistre_eur", "log_cout", "sinistre_grave"]
    df = df[ordre]
    df.to_parquet(SORTIE / "sinistres_detailles.parquet", index=False)
    df.to_csv(SORTIE / "sinistres_detailles.csv", index=False, sep=";", encoding="utf-8-sig")

    dico = [
        ("id_sinistre, id_contrat", "réel", "Identifiants du sinistre et du contrat (freMTPL2)"),
        ("jeu", "découpage", "entrainement (70 %), validation (15 %), test (15 %), par contrat, fixe pour comparer les modèles"),
        ("age_conducteur", "réel", "Âge du conducteur"), ("bonus_malus", "réel", "Bonus-malus x 100 (50 = bonus maximal)"),
        ("age_vehicule", "réel", "Âge du véhicule (ans)"), ("puissance_vehicule", "réel", "Puissance (classe 4 à 15)"),
        ("marque_vehicule", "réel", "Marque (codée B1 à B14)"), ("carburant", "réel", "Regular (essence) ou Diesel"),
        ("zone", "réel", "Type de zone, de A (rural) à F (très dense)"), ("densite_population", "réel", "Habitants par km² de la commune"),
        ("region", "réel", "Région (anciennes régions)"), ("exposition", "réel", "Durée du contrat sur l'année"),
        ("nb_sinistres_contrat", "réel", "Nombre de sinistres déclarés sur le contrat"),
        ("type_sinistre", "généré", "materiel ou corporel (responsabilité civile)"),
        ("circonstance", "généré", "Comment l'accident s'est produit (collision arrière, refus de priorité, piéton…)"),
        ("lieu", "généré", "agglomeration, route, autoroute, voie_rapide, parking"),
        ("responsabilite", "généré", "totale ou partagee"), ("nb_vehicules", "généré", "Véhicules impliqués"),
        ("tiers_identifie", "généré", "Le tiers est connu (constat possible)"), ("nb_blesses", "généré", "Nombre de blessés"),
        ("gravite_decrite", "généré", "Gravité décrite dans la déclaration, liée au coût réel"),
        ("mois, jour_semaine, heure", "généré", "Moment de l'accident"), ("meteo", "généré", "sec, pluie, brouillard, neige_verglas"),
        ("delai_declaration_jours", "généré", "Jours entre l'accident et la déclaration"),
        ("description_declaration", "généré", "Déclaration de sinistre en texte libre, comme l'écrirait l'assuré (sans le montant)"),
        ("forfait_convention_irsa", "déduit du réel", "Montant forfaitaire de la convention d'indemnisation entre assureurs"),
        ("cout_sinistre_eur", "réel", "**Variable à prédire** : coût du sinistre (€)"),
        ("log_cout", "réel", "Logarithme du coût"), ("sinistre_grave", "réel", f"Coût au-dessus du 95e centile ({seuil:,.0f} €)".replace(",", " ")),
    ]
    pd.DataFrame(dico, columns=["colonne", "origine", "sens"]).to_csv(SORTIE / "dictionnaire.csv", index=False, sep=";", encoding="utf-8-sig")
    ecrire_readme(df, dico, seuil)
    print(f"[sinistres] {len(df)} sinistres détaillés ; types : {df.type_sinistre.value_counts().to_dict()}")
    return 0


def ecrire_readme(df, dico, seuil):
    n = lambda x: f"{x:,.0f}".replace(",", " ")
    ex = df[~df.forfait_convention_irsa].groupby("gravite_decrite").head(1).head(4)
    l = ["# Sinistres détaillés (objectif 3)", "",
         "Base pour prédire le **coût d'un sinistre** et comparer des modèles de Machine Learning classiques avec des "
         "architectures intégrant des LLM. Générée par `src/sinistres_detailles.py` (graine fixe).", "",
         f"- **Sinistres** : {n(len(df))} vrais sinistres de responsabilité civile auto (France, freMTPL2)",
         f"- **Coût** : réel, médiane {n(df.cout_sinistre_eur.median())} €, moyenne {n(df.cout_sinistre_eur.mean())} €",
         f"- **Types** : {n((df.type_sinistre == 'materiel').sum())} matériels, {n((df.type_sinistre == 'corporel').sum())} corporels",
         f"- **Découpage** : {n((df.jeu == 'entrainement').sum())} entraînement, {n((df.jeu == 'validation').sum())} validation, {n((df.jeu == 'test').sum())} test", "",
         "## Ce qui est réel et ce qui est ajouté", "",
         "| Origine | Colonnes |", "| --- | --- |",
         "| **Réel** (freMTPL2) | coût du sinistre, âge du conducteur, bonus-malus, véhicule (âge, puissance, marque, carburant), zone, densité, région, exposition |",
         "| **Ajouté** (généré, cohérent avec le coût réel) | type de sinistre, circonstances, lieu, moment, météo, blessés, véhicules impliqués, délai de déclaration, **déclaration en texte libre** |", "",
         "Les données publiques ne décrivent jamais comment l'accident s'est passé. Ces colonnes sont donc générées, selon "
         "des règles explicites :",
         "- freMTPL2 ne contient que des sinistres de **responsabilité civile** (l'assuré a causé un dommage à un tiers) ;",
         "- matériel ou corporel est tiré selon la règle de Bayes, à partir des fréquences et coûts moyens publiés par "
         "France Assureurs (2025 : RC matériels 26,2 ‰ et 2 155 € en moyenne ; RC corporels 2,7 ‰, coût moyen supposé 20 000 €) "
         "et du coût réel du sinistre ;",
         "- les montants très répétés (1 204 €, 1 128,12 €, 1 172 €…) sont des **forfaits de la convention IRSA** entre assureurs : "
         "ils sont repérés (`forfait_convention_irsa`) et classés en dégâts matériels ;",
         "- la gravité décrite dans la déclaration suit le coût réel, mais le texte ne donne jamais le montant.", "",
         "**À dire dans le rapport** : le coût et le profil sont réels ; la description de l'accident est simulée. "
         "Les résultats des LLM sur le texte mesurent donc leur capacité à extraire l'information d'une déclaration, "
         "pas des déclarations réelles.", "",
         "## Exemples de déclarations", ""]
    for _, r in ex.iterrows():
        l.append(f"- *({r.gravite_decrite}, coût réel {n(r.cout_sinistre_eur)} €)* « {r.description_declaration} »")
    l += ["", "## Colonnes", "", "| Colonne | Origine | Sens |", "| --- | --- | --- |"]
    l += [f"| `{c}` | {o} | {s} |" for c, o, s in dico]
    l += ["", "## Ce que permet cette base pour l'objectif 3", "",
          "1. **Modèle classique** : prédire `log_cout` à partir des colonnes du contrat et du sinistre (CatBoost, GLM…).",
          "2. **Petit LLM local** : lire `description_declaration` et en extraire les variables (type, circonstance, gravité, blessés…).",
          "3. **Architecture hybride** : variables extraites par le petit LLM + modèle de prédiction, puis explication par un gros LLM.",
          "4. **Comparaison** sur le jeu `test` : erreur (MAE, RMSE sur le log), calibration, robustesse, latence et coût.", "",
          "## Utilisation", "", "```python", "import pandas as pd",
          "df = pd.read_parquet(\"sinistres_detailles.parquet\")",
          "train, test = df[df.jeu == \"entrainement\"], df[df.jeu == \"test\"]", "```", ""]
    (SORTIE / "README.md").write_text("\n".join(l), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
