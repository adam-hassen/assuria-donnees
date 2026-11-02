"""
Base de sinistres détaillés pour l'objectif 3 (prédire le coût d'un sinistre), auto et moto, 6 pays européens.

Point de départ RÉEL : tous les sinistres des jeux publics collectés (data/clean/sinistres_europe.parquet et les
sinistres individuels de freMTPL2) : France, Belgique, Italie, Espagne, Norvège, Suède. Pour chacun : le vrai coût
et le vrai profil du contrat (âge du conducteur, véhicule, bonus-malus, zone…).

Ce qui est AJOUTÉ (généré, cohérent avec le coût réel) : ce que les données publiques ne donnent pas mais dont
l'objectif 3 a besoin pour tester des LLM : la garantie touchée, les circonstances, le lieu, le moment, la météo,
les blessés, et une déclaration de sinistre en texte libre (comme celle qu'un assuré écrit à son assureur).

Comment c'est cohérent :
  - chaque source dit quelles garanties elle couvre : responsabilité civile seule (freMTPL2, Belgique, Italie),
    toutes garanties (freMPL, Espagne, Norvège) ou dommages, vol et incendie (motos suédoises) ;
  - la garantie est tirée selon la règle de Bayes parmi les garanties de la source, à partir des fréquences et des
    coûts moyens publiés par France Assureurs (data/externe/offres_auto_france/market_auto_guarantee_stats.csv)
    et du coût réel : un sinistre à 300 € est plus souvent un bris de glace, un sinistre à 40 000 € un corporel ;
  - les montants très répétés de freMTPL2 (1 204 €, 1 128,12 €…) sont des forfaits de la convention IRSA ;
  - la gravité décrite dans le texte suit le coût réel, sans jamais écrire le montant.

Sorties (data/objectif3/) : sinistres_detailles.parquet (tout), sinistres_detailles_extrait.csv (50 000 lignes,
tous pays), dictionnaire.csv, README.md
Lancement :  python -m src.sinistres_detailles
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.pays_referentiel import VILLES as VILLES_PAYS

SOURCE = Path("data/externe/fremtpl2")
EUROPE = Path("data/clean/sinistres_europe.parquet")
MARCHE = Path("data/externe/offres_auto_france/market_auto_guarantee_stats.csv")
SORTIE = Path("data/objectif3")
GRAINE = 2026
TAILLE_EXTRAIT = 50000

# garanties couvertes par chaque source (d'après la documentation des jeux de données)
GARANTIES_SOURCE = {
    "fr_fremtpl2": ("responsabilite_civile", ["rc_materiel", "rc_corporel"]),
    "be_bemtpl97": ("responsabilite_civile", ["rc_materiel", "rc_corporel"]),
    "it_eumtpl": ("responsabilite_civile", ["rc_materiel", "rc_corporel"]),
    "fr_frempl": ("toutes_garanties", ["rc_materiel", "rc_corporel", "dommages_vehicule", "bris_de_glace", "vol", "incendie"]),
    "es_portefeuille": ("toutes_garanties", ["rc_materiel", "rc_corporel", "dommages_vehicule", "bris_de_glace", "vol", "incendie"]),
    "no_norauto": ("toutes_garanties", ["rc_materiel", "rc_corporel", "dommages_vehicule", "bris_de_glace", "vol", "incendie"]),
    "se_swmotorcycle": ("dommages_vol_incendie", ["dommages_vehicule", "vol", "incendie"]),
}
CODE_PAYS = {"France": "FR", "Belgique": "BE", "Italie": "IT", "Espagne": "ES", "Norvège": "NO", "Suède": "SE"}
# lien garantie -> ligne du fichier de marché ; écart-type du log du coût (hypothèse)
MARCHE_CLE = {"rc_materiel": ("rc_materiels", 0.9), "rc_corporel": ("rc_corporels", 1.4), "dommages_vehicule": ("dommages", 1.0),
              "bris_de_glace": ("bris_de_glace", 0.6), "vol": ("vol", 1.0), "incendie": ("incendie", 1.0)}

# Circonstances, écrites à la 3e personne (« le conducteur … ») et mises à la 1re personne dans la déclaration
CIRCONSTANCES = {
    "rc_materiel": [
        ("collision_arriere", "a heurté l'arrière du véhicule qui le précédait", 0.24),
        ("refus_priorite", "n'a pas respecté une priorité à un carrefour", 0.16),
        ("changement_file", "a changé de file et accroché un autre véhicule", 0.10),
        ("marche_arriere_stationnement", "a heurté un véhicule en manœuvrant ou en marche arrière", 0.20),
        ("portiere", "a ouvert sa portière sur un véhicule qui passait", 0.04),
        ("perte_controle_bien", "a perdu le contrôle et percuté un mur|a perdu le contrôle et abîmé une clôture|a perdu le contrôle et heurté un abribus", 0.08),
        ("feu_rouge_stop", "n'a pas respecté un feu rouge ou un stop", 0.08),
        ("vehicule_stationne", "a heurté un véhicule en stationnement", 0.10),
    ],
    "rc_corporel": [
        ("pieton", "a renversé un piéton", 0.22),
        ("cycliste_2roues", "a heurté un cycliste|a heurté un scooter|a percuté un motard", 0.28),
        ("collision_arriere", "a heurté l'arrière d'un véhicule, dont un occupant a été blessé", 0.18),
        ("refus_priorite", "a refusé une priorité, l'autre conducteur a été blessé", 0.16),
        ("choc_frontal", "a eu un choc frontal avec un autre véhicule", 0.08),
        ("passager_blesse", "a eu un accident dans lequel un passager a été blessé", 0.08),
    ],
}
# garanties propres au véhicule de l'assuré : déjà à la 1re personne
CIRCONSTANCES_1RE = {
    "dommages_vehicule": [
        ("perte_controle_seul", "j'ai perdu le contrôle et je suis sorti de la route|j'ai glissé et heurté un arbre|j'ai heurté un trottoir et une barrière", 0.30),
        ("collision_responsable", "j'ai percuté un autre véhicule, mon véhicule est abîmé|j'ai heurté l'arrière d'une voiture", 0.30),
        ("degat_stationnement", "j'ai retrouvé mon véhicule abîmé sur le parking, l'auteur est parti", 0.15),
        ("vandalisme", "mon véhicule a été vandalisé pendant la nuit (rayures, rétroviseurs cassés)", 0.10),
        ("animal", "j'ai heurté un animal sauvage (sanglier, chevreuil)", 0.08),
        ("evenement_climatique", "mon véhicule a été abîmé par la grêle|un arbre est tombé sur mon véhicule pendant une tempête", 0.07),
    ],
    "bris_de_glace": [
        ("gravillon", "un gravillon a fissuré mon pare-brise", 0.55),
        ("pare_brise_fendu", "mon pare-brise s'est fendu, il faut le remplacer", 0.20),
        ("vitre_cassee", "une vitre latérale de mon véhicule a été cassée", 0.15),
        ("optique", "un phare de mon véhicule a été cassé", 0.10),
    ],
    "vol": [
        ("vol_vehicule", "on m'a volé mon véhicule, il n'a pas été retrouvé", 0.45),
        ("vol_retrouve_abime", "mon véhicule a été volé puis retrouvé abîmé", 0.25),
        ("tentative_vol", "quelqu'un a essayé de voler mon véhicule (serrure forcée, contact arraché)", 0.20),
        ("vol_accessoires", "on a volé des pièces de mon véhicule (roues, catalyseur, équipements)", 0.10),
    ],
    "incendie": [
        ("incendie_electrique", "mon véhicule a pris feu à cause d'un problème électrique", 0.45),
        ("incendie_criminel", "mon véhicule a été incendié pendant la nuit", 0.35),
        ("incendie_proximite", "le feu d'un véhicule voisin s'est propagé au mien", 0.20),
    ],
}
CIRCONSTANCES_MOTO = {
    "dommages_vehicule": [
        ("chute_seul", "j'ai chuté seul dans un virage|j'ai glissé sur des gravillons et je suis tombé|ma moto a glissé sur une plaque d'huile", 0.50),
        ("collision_responsable", "j'ai percuté une voiture qui freinait devant moi", 0.20),
        ("chute_a_l_arret", "ma moto est tombée à l'arrêt, sur la béquille", 0.15),
        ("vandalisme", "ma moto a été renversée et abîmée pendant la nuit", 0.10),
        ("animal", "j'ai heurté un animal sur la route", 0.05),
    ],
    "vol": [("vol_vehicule", "on m'a volé ma moto, elle n'a pas été retrouvée", 0.6),
            ("vol_retrouve_abime", "ma moto a été volée puis retrouvée abîmée", 0.25),
            ("tentative_vol", "quelqu'un a essayé de voler ma moto (antivol cassé, neiman forcé)", 0.15)],
    "incendie": [("incendie_electrique", "ma moto a pris feu à cause d'un problème électrique", 0.4),
                 ("incendie_criminel", "ma moto a été incendiée pendant la nuit", 0.6)],
}
LIEUX = {"collision_arriere": ["agglomeration", "route", "autoroute"], "refus_priorite": ["agglomeration", "route"],
         "changement_file": ["agglomeration", "autoroute", "voie_rapide"], "marche_arriere_stationnement": ["parking", "agglomeration"],
         "portiere": ["agglomeration"], "perte_controle_bien": ["route", "agglomeration"], "feu_rouge_stop": ["agglomeration"],
         "vehicule_stationne": ["parking", "agglomeration"], "pieton": ["agglomeration", "parking"],
         "cycliste_2roues": ["agglomeration", "route"], "choc_frontal": ["route"], "passager_blesse": ["route", "autoroute", "agglomeration"],
         "perte_controle_seul": ["route"], "collision_responsable": ["agglomeration", "route", "autoroute"],
         "degat_stationnement": ["parking"], "vandalisme": ["domicile", "agglomeration"], "animal": ["route"],
         "evenement_climatique": ["domicile", "parking"], "gravillon": ["autoroute", "route", "voie_rapide"],
         "pare_brise_fendu": ["domicile", "route"], "vitre_cassee": ["parking", "agglomeration"], "optique": ["parking", "agglomeration"],
         "vol_vehicule": ["domicile", "agglomeration", "parking"], "vol_retrouve_abime": ["domicile", "agglomeration"],
         "tentative_vol": ["domicile", "parking"], "vol_accessoires": ["domicile", "parking"],
         "incendie_electrique": ["route", "domicile"], "incendie_criminel": ["domicile", "agglomeration"],
         "incendie_proximite": ["parking", "agglomeration"], "chute_seul": ["route", "agglomeration"],
         "chute_a_l_arret": ["agglomeration", "parking", "domicile"]}
TEXTE_LIEU = {"agglomeration": ["en ville", "dans une rue de {ville}", "en centre-ville de {ville}", "à un carrefour en ville"],
              "route": ["sur une petite route de campagne", "sur une route nationale", "sur une route de montagne près de {ville}"],
              "autoroute": ["sur l'autoroute", "sur l'autoroute, près d'une sortie", "sur l'autoroute près de {ville}"],
              "voie_rapide": ["sur le périphérique de {ville}", "sur une voie rapide"],
              "parking": ["sur un parking de supermarché", "dans un parking souterrain à {ville}", "sur le parking de mon travail"],
              "domicile": ["devant chez moi à {ville}", "dans ma rue", "devant mon immeuble"]}
VILLES_FR = {"Ile-de-France": "Paris", "Rhone-Alpes": "Lyon", "Provence-Alpes-Cotes-D'Azur": "Marseille", "Nord-Pas-de-Calais": "Lille",
             "Aquitaine": "Bordeaux", "Midi-Pyrenees": "Toulouse", "Bretagne": "Rennes", "Pays-de-la-Loire": "Nantes",
             "Languedoc-Roussillon": "Montpellier", "Alsace": "Strasbourg", "Centre": "Tours", "Picardie": "Amiens",
             "Limousin": "Limoges", "Poitou-Charentes": "Poitiers", "Auvergne": "Clermont-Ferrand", "Corse": "Ajaccio",
             "Basse-Normandie": "Caen", "Haute-Normandie": "Rouen", "Bourgogne": "Dijon", "Franche-Comte": "Besançon",
             "Champagne-Ardenne": "Reims"}
VILLES_BE = {"1": "Bruxelles", "2": "Anvers", "3": "Louvain", "4": "Liège", "5": "Namur", "6": "Charleroi", "7": "Mons",
             "8": "Bruges", "9": "Gand"}
VILLES_IT = {"MI": "Milan", "NA": "Naples", "TO": "Turin", "RM": "Rome", "BA": "Bari", "PA": "Palerme", "GE": "Gênes",
             "BO": "Bologne", "FI": "Florence", "CT": "Catane", "VE": "Venise", "VR": "Vérone", "SA": "Salerne", "CA": "Cagliari",
             "BS": "Brescia", "BG": "Bergame", "PD": "Padoue", "TA": "Tarente", "SV": "Savone", "CE": "Caserte"}
METEO_PAYS = {"FR": [.58, .25, .07, .10], "BE": [.5, .32, .08, .10], "IT": [.68, .22, .05, .05], "ES": [.78, .17, .03, .02],
              "NO": [.4, .25, .08, .27], "SE": [.6, .3, .05, .05]}
METEO = ["sec", "pluie", "brouillard", "neige_verglas"]
TEXTE_METEO = {"sec": "", "pluie": " Il pleuvait.", "brouillard": " Il y avait du brouillard.", "neige_verglas": " La route était glissante (verglas)."}


def gravite(cout: float, type_: str) -> str:
    if type_ == "rc_corporel":
        return "blesse_leger" if cout < 5000 else "blesse_hospitalise" if cout < 50000 else "blesse_grave"
    if type_ == "vol":
        return "vol_partiel" if cout < 3000 else "vol_total"
    if type_ == "incendie":
        return "incendie_partiel" if cout < 4000 else "incendie_total"
    if type_ == "bris_de_glace":
        return "reparation_impact" if cout < 250 else "remplacement"
    return "leger" if cout < 600 else "moyen" if cout < 2500 else "important" if cout < 8000 else "tres_important"


DEGATS_TIERS = {
    "leger": ["Juste une rayure et un petit enfoncement sur le pare-choc de l'autre véhicule.", "Dégâts légers : rétroviseur et pare-choc rayés.",
              "Choc léger, quelques rayures sur la carrosserie de l'autre véhicule."],
    "moyen": ["Le pare-choc et une aile de l'autre véhicule sont abîmés, phare cassé.", "La portière et l'aile de l'autre véhicule sont enfoncées.",
              "Dégâts sur l'avant de l'autre véhicule (pare-choc, calandre)."],
    "important": ["L'autre véhicule a l'avant bien enfoncé, il a dû être remorqué.", "Gros dégâts sur l'autre véhicule, airbags déclenchés.",
                  "Le côté de l'autre véhicule est très abîmé, il ne roule plus."],
    "tres_important": ["L'autre véhicule est très endommagé, probablement épave.", "Plusieurs véhicules touchés, gros dégâts.",
                       "Le véhicule de l'autre conducteur n'est plus roulant, dégâts importants sur la structure."],
    "blesse_leger": ["L'autre personne a été légèrement blessée (contusions), vue par un médecin.", "La personne a eu des égratignures et une douleur au poignet."],
    "blesse_hospitalise": ["La personne blessée a été emmenée aux urgences et hospitalisée quelques jours.", "Le blessé a une fracture, il a été hospitalisé."],
    "blesse_grave": ["La victime a été gravement blessée et hospitalisée longtemps.", "Le blessé a des séquelles importantes, hospitalisation de plusieurs semaines."],
}
DEGATS_PROPRES = {
    "leger": ["Mon véhicule a quelques rayures et le pare-choc est marqué.", "Dégâts légers sur mon véhicule (carrosserie rayée)."],
    "moyen": ["Mon véhicule a le pare-choc et une aile abîmés.", "La portière et l'aile de mon véhicule sont enfoncées, il roule encore."],
    "important": ["Mon véhicule ne roule plus, il a été remorqué au garage.", "Gros dégâts sur mon véhicule, les airbags se sont déclenchés."],
    "tres_important": ["Mon véhicule est très endommagé, le garage parle d'une épave.", "La structure de mon véhicule est touchée, sans doute irréparable."],
    "reparation_impact": ["L'impact est petit, il peut être réparé.", "Le garage propose de réparer l'impact."],
    "remplacement": ["Le pare-brise doit être remplacé entièrement.", "La vitre est à remplacer."],
    "vol_partiel": ["Les dégâts concernent surtout la serrure et le contact.", "Il manque quelques équipements."],
    "vol_total": ["Le véhicule n'a pas été retrouvé, j'ai porté plainte.", "Plainte déposée au commissariat, le véhicule est introuvable."],
    "incendie_partiel": ["Le feu a été éteint vite, l'avant est brûlé.", "Une partie du véhicule est brûlée."],
    "incendie_total": ["Le véhicule est entièrement brûlé.", "Il ne reste rien du véhicule, les pompiers sont intervenus."],
}
DEGATS_MOTO = {
    "leger": ["Ma moto a le levier et le rétroviseur cassés.", "Quelques rayures sur le carénage."],
    "moyen": ["Le carénage et le guidon de ma moto sont abîmés.", "La fourche est tordue, le phare est cassé."],
    "important": ["Ma moto ne roule plus, elle a été remorquée.", "Gros dégâts sur ma moto (cadre, fourche, carénage)."],
    "tres_important": ["Ma moto est détruite.", "Le cadre de la moto est tordu, elle est sans doute irréparable."],
}


def un(rng, xs):
    """Un élément au hasard (plus rapide que rng.choice sur une liste)."""
    return xs[rng.integers(len(xs))]


def lognorm_pdf(x, moyenne, sigma):
    mu = np.log(moyenne) - sigma ** 2 / 2
    return np.exp(-(np.log(x) - mu) ** 2 / (2 * sigma ** 2)) / (x * sigma * np.sqrt(2 * np.pi))


def choisir_garantie(rng, cout, possibles, stats, moto):
    """Bayes : P(garantie | coût) proportionnel à fréquence(garantie) x densité(coût | garantie)."""
    if moto:
        possibles = [g for g in possibles if g != "bris_de_glace"]
    poids = np.column_stack([stats[g]["freq"] * lognorm_pdf(cout, stats[g]["cout"], stats[g]["sigma"]) for g in possibles])
    corp = possibles.index("rc_corporel") if "rc_corporel" in possibles else None
    if corp is not None:
        poids[cout < 500, corp] = 0      # un corporel coûte au moins quelques centaines d'euros
    poids = poids / poids.sum(axis=1, keepdims=True)
    u = rng.random(len(cout))[:, None]
    return np.array(possibles)[(u > poids.cumsum(axis=1)).sum(axis=1).clip(0, len(possibles) - 1)]


def ville_de(rng, r) -> str:
    code = CODE_PAYS[r.pays]
    if r.source == "fr_fremtpl2":
        return VILLES_FR.get(r.region, "Paris")
    if code == "BE":
        return VILLES_BE.get(str(r.zone)[:1], "Bruxelles")
    if code == "IT" and str(r.zone) in VILLES_IT:
        return VILLES_IT[str(r.zone)]
    villes = VILLES_PAYS[code] if code != "FR" else [(v, 0, 0, 0) for v in VILLES_FR.values()]
    return villes[rng.integers(len(villes))][0]


def declaration(rng, r) -> str:
    moto = r.type_vehicule == "moto"
    lieu = un(rng, TEXTE_LIEU[r.lieu]).format(ville=r.ville)
    heure = f"vers {r.heure}h" if rng.random() < 0.7 else ("le matin" if 5 <= r.heure < 12 else "l'après-midi" if 12 <= r.heure < 18
                                                           else "le soir" if 18 <= r.heure < 22 else "dans la nuit")
    debut = un(rng, [f"{r.jour_semaine.capitalize()} {heure}, {lieu}, ", f"{lieu[0].upper() + lieu[1:]}, {r.jour_semaine} {heure} : ",
                        f"Bonjour, je déclare un sinistre. {r.jour_semaine.capitalize()} {heure}, {lieu}, "])
    if r.type_sinistre in CIRCONSTANCES:   # responsabilité civile : l'assuré a causé le dommage
        texte = un(rng, dict((c, t) for c, t, _ in CIRCONSTANCES[r.type_sinistre])[r.circonstance].split("|"))
        if rng.random() < 0.75:
            verbe = texte.replace("a heurté", "ai heurté").replace("n'a pas", "n'ai pas").replace("a changé", "ai changé") \
                .replace("a ouvert sa", "ai ouvert ma").replace("a perdu", "ai perdu").replace("a renversé", "ai renversé") \
                .replace("a refusé", "ai refusé").replace("a eu", "ai eu").replace("a percuté", "ai percuté") \
                .replace("qui le précédait", "qui me précédait")
            sujet = "j'" if verbe.startswith("ai") else "je "
        else:
            verbe, sujet = texte, ("le conducteur de ma moto " if moto else "le conducteur de mon véhicule ")
        phrase = debut + sujet + verbe + "."
    else:
        table = CIRCONSTANCES_MOTO if moto and r.type_sinistre in CIRCONSTANCES_MOTO else CIRCONSTANCES_1RE
        texte = un(rng, dict((c, t) for c, t, _ in table[r.type_sinistre])[r.circonstance].split("|"))
        if moto:
            texte = texte.replace("mon véhicule", "ma moto").replace("mon pare-brise", "ma bulle")
        phrase = debut + texte + "."
    phrase += TEXTE_METEO[r.meteo] if r.lieu not in ("domicile", "parking") else ""
    g = r.gravite_decrite
    if r.circonstance == "perte_controle_bien":
        phrase += " " + {"leger": "Quelques dégâts légers sur le bien.", "moyen": "Le bien est abîmé, il faudra le réparer.",
                         "important": "Le bien est fortement endommagé.", "tres_important": "Le bien est détruit, gros travaux à prévoir."}[g]
    elif r.type_sinistre.startswith("rc_"):
        phrase += " " + un(rng, DEGATS_TIERS[g])
    elif moto and g in DEGATS_MOTO:
        phrase += " " + un(rng, DEGATS_MOTO[g])
    elif r.type_sinistre == "vol":
        phrase += " " + {"vol_vehicule": un(rng, ["J'ai porté plainte au commissariat.", "Plainte déposée, toujours aucune nouvelle."]),
                         "vol_retrouve_abime": un(rng, ["Il a été retrouvé quelques jours plus tard, abîmé. J'ai porté plainte.",
                                                        "Retrouvé abîmé (contact arraché, carrosserie rayée). Plainte déposée."]),
                         "tentative_vol": un(rng, ["Les dégâts concernent surtout la serrure et le contact. J'ai porté plainte.",
                                                   "Le véhicule est toujours là, mais il faut réparer la serrure et le contact."]),
                         "vol_accessoires": un(rng, ["Il manque les équipements volés. Plainte déposée.", "J'ai porté plainte."])}[r.circonstance] \
            .replace("Le véhicule", "La moto" if moto else "Le véhicule").replace("le véhicule", "la moto" if moto else "le véhicule")
        return phrase
    elif r.circonstance == "optique":
        phrase += " Le phare est à remplacer."
    else:
        t = un(rng, DEGATS_PROPRES[g])
        phrase += " " + (t.replace("Mon véhicule", "Ma moto").replace("mon véhicule", "ma moto").replace("Le véhicule", "La moto")
                         .replace("du véhicule", "de la moto").replace("pare-brise", "bulle").replace("entièrement brûlé", "entièrement brûlée") if moto else t)
    if r.nb_vehicules > 2:
        phrase += f" {r.nb_vehicules} véhicules impliqués."
    if r.type_sinistre.startswith("rc_") or r.circonstance == "collision_responsable":
        phrase += un(rng, [" Constat amiable rempli avec l'autre conducteur.", " Constat amiable signé sur place.",
                              " Pas de constat, les coordonnées ont été échangées.", " La police est intervenue."]) \
            if r.tiers_identifie else " Pas de constat (bien appartenant à un tiers absent)."
    elif r.type_sinistre == "incendie" or r.circonstance == "vandalisme":
        phrase += un(rng, [" J'ai déposé plainte.", " Une plainte a été déposée.", ""])
    if r.type_sinistre == "rc_materiel" and rng.random() < 0.3:
        phrase += un(rng, [" Mon véhicule a aussi une rayure.", " Aucun blessé.", " Personne n'a été blessé."])
    return phrase


def charger() -> pd.DataFrame:
    """Tous les vrais sinistres, dans un même format."""
    sin = pd.read_parquet(SOURCE / "fremtpl2_claims.parquet")
    pol = pd.read_parquet(SOURCE / "fremtpl2_policies.parquet")
    fr = sin.merge(pol.drop(columns=["claim_amount_total"]), on="id_pol", how="inner")
    fr = fr[fr.claim_amount > 0]
    fr = pd.DataFrame({
        "id_sinistre": "fremtpl2_" + fr.claim_id.astype(str), "id_contrat": "fremtpl2_" + fr.id_pol.astype(str),
        "pays": "France", "type_vehicule": "auto", "source": "fr_fremtpl2", "annee": np.nan,
        "age_conducteur": fr.driv_age.astype(float), "sexe": pd.NA, "age_vehicule": fr.veh_age.astype(float),
        "puissance_vehicule": fr.veh_power.astype(float), "marque_vehicule": fr.veh_brand, "carburant": fr.veh_gas.str.lower()
        .replace({"regular": "essence"}), "zone": fr.area, "densite_population": fr.density.astype(float), "region": fr.region,
        "bonus_malus": fr.bonus_malus.astype(float), "exposition": fr.exposure.astype(float),
        "nb_sinistres_contrat": fr.claim_nb.astype(float), "cout_sinistre_eur": fr.claim_amount.astype(float),
        "nature_cout": "individuel",
    })
    eu = pd.read_parquet(EUROPE)
    eu = eu[eu.source != "fr_fremtpl2"].copy()
    eu["rang"] = eu.groupby("source").cumcount()
    eu = pd.DataFrame({
        "id_sinistre": eu.source + "_" + eu.rang.astype(str), "id_contrat": eu.source + "_" + eu.id_contrat.astype(str),
        "pays": eu.pays, "type_vehicule": eu["type"], "source": eu.source, "annee": eu.annee.astype(float),
        "age_conducteur": eu.age_conducteur.astype(float), "sexe": eu.sexe.astype("string"), "age_vehicule": eu.age_vehicule.astype(float),
        "puissance_vehicule": eu.puissance_ch.astype(float), "marque_vehicule": pd.NA, "carburant": eu.carburant.astype("string"),
        "zone": eu.zone.astype("string"), "densite_population": np.nan, "region": pd.NA,
        "bonus_malus": eu.bonus_malus.astype(float), "exposition": eu.exposition.astype(float),
        "nb_sinistres_contrat": eu.nb_sinistres.astype(float), "cout_sinistre_eur": eu.cout_moyen_eur.astype(float),
        "nature_cout": np.where(eu.nb_sinistres > 1, "moyenne_du_contrat", "individuel"),
    })
    df = pd.concat([fr, eu], ignore_index=True)
    return df[df.cout_sinistre_eur > 0].reset_index(drop=True)


ECHELLE_BM = {"fr_fremtpl2": "coefficient x 100 (50 = bonus maximal, 100 = neutre)", "fr_frempl": "coefficient x 100 (50 = bonus maximal)",
              "be_bemtpl97": "degré belge 0 à 22 (0 = meilleur, 11 = entrée)", "se_swmotorcycle": "classe de bonus suédoise 1 à 7 (7 = meilleure)"}


def main() -> int:
    SORTIE.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(GRAINE)
    df = charger()
    m = pd.read_csv(MARCHE)
    get = lambda g, k: float(m[(m.guarantee == g) & (m.metric == k)].value.iloc[0])
    stats = {}
    for g, (cle, sigma) in MARCHE_CLE.items():
        cout_moyen = 20000.0 if cle == "rc_corporels" else get(cle, "avg_claim_cost")   # coût corporel : hypothèse
        stats[g] = {"freq": get(cle, "claim_frequency"), "cout": cout_moyen, "sigma": sigma}

    cout = df.cout_sinistre_eur.to_numpy()
    df["garanties_source"] = df.source.map(lambda s: GARANTIES_SOURCE[s][0])
    df["type_sinistre"] = ""
    for (src, tv), idx in df.groupby(["source", "type_vehicule"]).groups.items():
        df.loc[idx, "type_sinistre"] = choisir_garantie(rng, cout[idx], GARANTIES_SOURCE[src][1], stats, tv == "moto")
    repetes = df[df.source == "fr_fremtpl2"].cout_sinistre_eur.value_counts().loc[lambda s: s >= 300].index
    df["forfait_convention_irsa"] = (df.source == "fr_fremtpl2") & df.cout_sinistre_eur.isin(repetes)
    df.loc[df.forfait_convention_irsa, "type_sinistre"] = "rc_materiel"

    def circonstance(t, moto):
        if t in CIRCONSTANCES:
            table = [x for x in CIRCONSTANCES[t] if not (moto and x[0] == "portiere")]
        else:
            table = (CIRCONSTANCES_MOTO if moto and t in CIRCONSTANCES_MOTO else CIRCONSTANCES_1RE)[t]
        p = np.array([x[2] for x in table])
        return table[rng.choice(len(table), p=p / p.sum())][0]
    df["gravite_decrite"] = [gravite(c, t) for c, t in zip(cout, df.type_sinistre)]
    df["circonstance"] = [circonstance(t, v == "moto") for t, v in zip(df.type_sinistre, df.type_vehicule)]
    # le vol doit coller au coût : petit montant = tentative ou accessoires, gros montant = véhicule volé
    vol = df.type_sinistre == "vol"
    petit = vol & (df.gravite_decrite == "vol_partiel")
    df.loc[petit, "circonstance"] = rng.choice(["tentative_vol", "vol_accessoires"], petit.sum(), p=[.6, .4])
    df.loc[petit & (df.type_vehicule == "moto"), "circonstance"] = "tentative_vol"
    gros = vol & (df.gravite_decrite == "vol_total")
    df.loc[gros, "circonstance"] = rng.choice(["vol_vehicule", "vol_retrouve_abime"], gros.sum(), p=[.65, .35])
    df.loc[(df.type_sinistre == "bris_de_glace") & (df.circonstance != "gravillon"), "gravite_decrite"] = "remplacement"
    df["lieu"] = [LIEUX[c][rng.integers(len(LIEUX[c]))] for c in df.circonstance]
    rc = df.type_sinistre.str.startswith("rc_")
    df["responsabilite"] = np.where(rc, np.where(rng.random(len(df)) < 0.8, "totale", "partagee"),
                                    np.where(df.circonstance == "collision_responsable", "totale", "sans_objet"))
    df["nb_vehicules"] = np.where(df.circonstance.isin(["perte_controle_bien", "pieton", "passager_blesse"]) |
                                  (~rc & (df.circonstance != "collision_responsable")), 1,
                                  np.where(rc & (cout > 8000) & (rng.random(len(df)) < 0.3), 3, 2))
    df["tiers_identifie"] = rc & (df.circonstance != "perte_controle_bien") | (df.circonstance == "collision_responsable")
    df["nb_blesses"] = np.where(df.type_sinistre == "rc_corporel", np.where(cout > 50000, rng.integers(1, 4, len(df)), 1), 0)
    moto_se = df.source == "se_swmotorcycle"
    df["mois"] = np.where(df.type_vehicule == "moto", rng.choice(np.arange(1, 13), len(df),
                          p=np.array([1, 1, 3, 7, 11, 13, 14, 13, 10, 6, 2, 1]) / 82), rng.integers(1, 13, len(df)))
    df.loc[moto_se, "mois"] = rng.choice(np.arange(4, 11), moto_se.sum())
    df["jour_semaine"] = rng.choice(["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"], len(df),
                                    p=[.15, .15, .15, .15, .17, .13, .10])
    poids = np.array([1, .5, .5, .5, .5, 1, 3, 6, 8, 6, 5, 5, 6, 6, 5, 6, 8, 9, 8, 5, 3, 2, 1.5, 1.5])
    df["heure"] = rng.choice(np.arange(24), len(df), p=poids / poids.sum())
    nuit = df.circonstance.isin(["vandalisme", "incendie_criminel", "vol_vehicule", "tentative_vol", "vol_accessoires"])
    df.loc[nuit, "heure"] = rng.choice([22, 23, 0, 1, 2, 3, 4, 5], nuit.sum())
    df["meteo"] = [METEO[rng.choice(4, p=METEO_PAYS[CODE_PAYS[p]])] for p in df.pays]
    df.loc[df.mois.isin([5, 6, 7, 8, 9]) & (df.meteo == "neige_verglas"), "meteo"] = "sec"
    df["delai_declaration_jours"] = np.clip(rng.geometric(0.45, len(df)) - 1, 0, 30)
    df["ville"] = [ville_de(rng, r) for r in df[["pays", "source", "region", "zone"]].itertuples()]
    df["description_declaration"] = [declaration(rng, r) for r in df.itertuples()]
    df["cout_sinistre_eur"] = df.cout_sinistre_eur.round(2)
    df["log_cout"] = np.log(df.cout_sinistre_eur)
    seuil = df.groupby("source").cout_sinistre_eur.transform(lambda x: x.quantile(0.95))
    df["sinistre_grave"] = df.cout_sinistre_eur > seuil
    df["echelle_bonus_malus"] = df.source.map(ECHELLE_BM)
    # découpage fixe pour le benchmark : 70 % entraînement, 15 % validation, 15 % test (par contrat, sans fuite)
    contrats = np.array(df.id_contrat.unique(), dtype=object)
    rng.shuffle(contrats)
    n = len(contrats)
    jeu = {c: "entrainement" for c in contrats[: int(n * .7)]}
    jeu.update({c: "validation" for c in contrats[int(n * .7): int(n * .85)]})
    jeu.update({c: "test" for c in contrats[int(n * .85):]})
    df["jeu"] = df.id_contrat.map(jeu)

    ordre = ["id_sinistre", "id_contrat", "jeu", "pays", "type_vehicule", "source", "garanties_source", "annee",
             "age_conducteur", "sexe", "bonus_malus", "echelle_bonus_malus", "age_vehicule", "puissance_vehicule", "marque_vehicule",
             "carburant", "zone", "densite_population", "region", "exposition", "nb_sinistres_contrat",
             "type_sinistre", "circonstance", "lieu", "ville", "responsabilite", "nb_vehicules", "tiers_identifie", "nb_blesses",
             "gravite_decrite", "mois", "jour_semaine", "heure", "meteo", "delai_declaration_jours", "description_declaration",
             "forfait_convention_irsa", "nature_cout", "cout_sinistre_eur", "log_cout", "sinistre_grave"]
    df = df[ordre]
    df.to_parquet(SORTIE / "sinistres_detailles.parquet", index=False)
    # extrait CSV (le fichier complet dépasserait la limite de GitHub) : toutes les sources, proportionnellement, au moins 2 000 par source
    part = TAILLE_EXTRAIT / len(df)
    extrait = df.groupby("source", group_keys=False).apply(
        lambda x: x.sample(min(len(x), max(2000, int(len(x) * part))), random_state=GRAINE))
    extrait.to_csv(SORTIE / "sinistres_detailles_extrait.csv", index=False, sep=";", encoding="utf-8-sig")
    ancien = SORTIE / "sinistres_detailles.csv"
    if ancien.exists():
        ancien.unlink()

    dico = [
        ("id_sinistre, id_contrat", "réel", "Identifiants (préfixés par la source)"),
        ("jeu", "découpage", "entrainement (70 %), validation (15 %), test (15 %), par contrat, fixe pour comparer les modèles"),
        ("pays, type_vehicule, source", "réel", "Pays, auto ou moto, jeu de données d'origine"),
        ("garanties_source", "réel", "Garanties couvertes par la source : responsabilite_civile, toutes_garanties, dommages_vol_incendie"),
        ("annee", "réel", "Année du contrat (si connue)"),
        ("age_conducteur", "réel", "Âge du conducteur (vide pour la Norvège)"), ("sexe", "réel", "Information seulement (interdit pour le tarif dans l'UE)"),
        ("bonus_malus, echelle_bonus_malus", "réel", "Bonus-malus dans l'échelle de la source (vide pour Italie, Espagne, Norvège)"),
        ("age_vehicule", "réel", "Âge du véhicule (ans)"), ("puissance_vehicule", "réel", "Puissance : classe 4 à 15 (freMTPL2) ou chevaux"),
        ("marque_vehicule", "réel", "Marque codée (freMTPL2)"), ("carburant", "réel", "essence, diesel ou code de la source"),
        ("zone", "réel", "Zone de la source (A à F en France, code postal en Belgique, province en Italie…)"),
        ("densite_population, region", "réel", "freMTPL2 seulement"), ("exposition", "réel", "Durée du contrat sur l'année"),
        ("nb_sinistres_contrat", "réel", "Nombre de sinistres sur le contrat"),
        ("type_sinistre", "généré", "rc_materiel, rc_corporel, dommages_vehicule, bris_de_glace, vol, incendie (parmi les garanties de la source)"),
        ("circonstance", "généré", "Comment le sinistre s'est produit (collision arrière, piéton, gravillon, vol, chute seul…)"),
        ("lieu, ville", "généré", "agglomeration, route, autoroute, voie_rapide, parking, domicile ; ville réelle du pays (déduite de la zone quand c'est possible)"),
        ("responsabilite", "généré", "totale, partagee (RC) ou sans_objet"), ("nb_vehicules", "généré", "Véhicules impliqués"),
        ("tiers_identifie", "généré", "Un tiers est connu (constat possible)"), ("nb_blesses", "généré", "Nombre de blessés"),
        ("gravite_decrite", "généré", "Gravité décrite dans la déclaration, liée au coût réel"),
        ("mois, jour_semaine, heure", "généré", "Moment du sinistre (motos surtout l'été, vols et incendies la nuit)"),
        ("meteo", "généré", "sec, pluie, brouillard, neige_verglas (fréquences selon le pays)"),
        ("delai_declaration_jours", "généré", "Jours entre le sinistre et la déclaration"),
        ("description_declaration", "généré", "Déclaration de sinistre en français, comme l'écrirait l'assuré (sans le montant)"),
        ("forfait_convention_irsa", "déduit du réel", "Montant forfaitaire de la convention d'indemnisation entre assureurs (freMTPL2)"),
        ("nature_cout", "réel", "individuel, ou moyenne_du_contrat quand la source ne donne que le total de plusieurs sinistres"),
        ("cout_sinistre_eur", "réel", "**Variable à prédire** : coût du sinistre en euros"),
        ("log_cout", "réel", "Logarithme du coût"), ("sinistre_grave", "réel", "Coût au-dessus du 95e centile de sa source"),
    ]
    pd.DataFrame(dico, columns=["colonne", "origine", "sens"]).to_csv(SORTIE / "dictionnaire.csv", index=False, sep=";", encoding="utf-8-sig")
    ecrire_readme(df, dico, len(extrait))
    print(f"[sinistres] {len(df)} sinistres ; {df.pays.value_counts().to_dict()} ; {df.type_sinistre.value_counts().to_dict()}")
    return 0


def ecrire_readme(df, dico, n_extrait):
    n = lambda x: f"{x:,.0f}".replace(",", " ")
    l = ["# Sinistres détaillés (objectif 3)", "",
         "Base pour prédire le **coût d'un sinistre** et comparer des modèles de Machine Learning classiques avec des "
         "architectures intégrant des LLM. Générée par `src/sinistres_detailles.py` (graine fixe).", "",
         f"- **Sinistres** : {n(len(df))} vrais sinistres auto et moto, {df.pays.nunique()} pays, {df.source.nunique()} jeux de données publics",
         f"- **Coût** : réel, médiane {n(df.cout_sinistre_eur.median())} €, moyenne {n(df.cout_sinistre_eur.mean())} €",
         f"- **Découpage** : {n((df.jeu == 'entrainement').sum())} entraînement, {n((df.jeu == 'validation').sum())} validation, {n((df.jeu == 'test').sum())} test",
         f"- **Fichiers** : `sinistres_detailles.parquet` (tout) ; `sinistres_detailles_extrait.csv` ({n(n_extrait)} lignes, toutes les sources, "
         "pour regarder dans Excel : le CSV complet dépasserait la limite de GitHub)", "",
         "## Par pays et par source", "", "| Pays | Véhicule | Source | Garanties couvertes | Sinistres | Coût médian |", "| --- | --- | --- | --- | --- | --- |"]
    for (p, tv, s), x in df.groupby(["pays", "type_vehicule", "source"]):
        l.append(f"| {p} | {tv} | `{s}` | {x.garanties_source.iloc[0].replace('_', ' ')} | {n(len(x))} | {n(x.cout_sinistre_eur.median())} € |")
    l += ["", "## Types de sinistres (générés)", "", "| Type | Sinistres | Coût médian |", "| --- | --- | --- |"]
    for t, x in df.groupby("type_sinistre"):
        l.append(f"| {t} | {n(len(x))} | {n(x.cout_sinistre_eur.median())} € |")
    l += ["", "## Ce qui est réel et ce qui est ajouté", "",
          "| Origine | Colonnes |", "| --- | --- |",
          "| **Réel** | coût du sinistre, pays, auto ou moto, âge du conducteur, bonus-malus, véhicule (âge, puissance, carburant), zone, exposition |",
          "| **Ajouté** (généré, cohérent avec le coût réel et les garanties de la source) | type de sinistre, circonstances, lieu, ville, moment, météo, blessés, véhicules impliqués, délai, **déclaration en texte libre** |", "",
          "Les données publiques ne décrivent jamais comment le sinistre s'est passé. Ces colonnes sont donc générées, selon des règles explicites :",
          "- la garantie touchée est tirée parmi celles que couvre la source (responsabilité civile seule pour freMTPL2, la Belgique et l'Italie ; "
          "toutes garanties pour freMPL, l'Espagne et la Norvège ; dommages, vol et incendie pour les motos suédoises) ;",
          "- le tirage suit la règle de Bayes, avec les fréquences et coûts moyens publiés par France Assureurs (2025) et le coût réel "
          "(coût moyen d'un corporel supposé à 20 000 €, faute de chiffre publié) : les mêmes fréquences servent pour tous les pays (hypothèse) ;",
          "- les montants très répétés de freMTPL2 (1 204 €, 1 128,12 €…) sont des **forfaits de la convention IRSA** : classés en RC matériel ;",
          "- quand une source ne donne que le total de plusieurs sinistres d'un contrat, le coût est la moyenne (`nature_cout`) ;",
          "- la gravité décrite suit le coût réel, mais le texte ne donne jamais le montant ; les déclarations sont en français pour tous les pays.", "",
          "**À dire dans le rapport** : le coût et le profil sont réels ; la description du sinistre est simulée. Les résultats des LLM "
          "sur le texte mesurent leur capacité à extraire l'information d'une déclaration, pas des déclarations réelles. "
          "Les colonnes ne sont pas toutes remplies pour toutes les sources (voir le dictionnaire).", "",
          "## Exemples de déclarations", ""]
    ex = df[~df.forfait_convention_irsa].groupby("type_sinistre").sample(1, random_state=3)
    for _, r in ex.iterrows():
        l.append(f"- *({r.pays}, {r.type_vehicule}, {r.type_sinistre}, coût réel {n(r.cout_sinistre_eur)} €)* « {r.description_declaration} »")
    l += ["", "## Colonnes", "", "| Colonne | Origine | Sens |", "| --- | --- | --- |"]
    l += [f"| `{c}` | {o} | {s} |" for c, o, s in dico]
    l += ["", "## Ce que permet cette base pour l'objectif 3", "",
          "1. **Modèle classique** : prédire `log_cout` à partir des colonnes du contrat et du sinistre (CatBoost, GLM…), par pays ou tous pays.",
          "2. **Petit LLM local** : lire `description_declaration` et en extraire les variables (type, circonstance, gravité, blessés…).",
          "3. **Architecture hybride** : variables extraites par le petit LLM + modèle de prédiction, puis explication par un gros LLM.",
          "4. **Comparaison** sur le jeu `test` : erreur (MAE, RMSE sur le log), calibration, robustesse (entre pays), latence et coût.", "",
          "## Utilisation", "", "```python", "import pandas as pd",
          "df = pd.read_parquet(\"sinistres_detailles.parquet\")",
          "train, test = df[df.jeu == \"entrainement\"], df[df.jeu == \"test\"]",
          "france_rc = df[(df.source == \"fr_fremtpl2\")]", "```", ""]
    (SORTIE / "README.md").write_text("\n".join(l), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
