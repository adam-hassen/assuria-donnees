"""
Nettoyage et harmonisation des données de sinistres auto et moto.

Lit les fichiers Parquet de data/raw/ (produits par src/collecte.py) et produit :
  - data/clean/sinistres_europe.parquet : un seul fichier, mêmes colonnes pour toutes les sources
  - data/clean/rapport_nettoyage.json  : lignes avant / après chaque étape, par source
  - data/clean/qualite_brute.json      : profil de qualité des données brutes (pour le dashboard)

Lancement : python -m src.nettoyage
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RACINE = Path(__file__).resolve().parents[1]
RAW = RACINE / "data" / "raw"
CLEAN = RACINE / "data" / "clean"
CONFIG = yaml.safe_load((RACINE / "config" / "sources.yaml").read_text(encoding="utf-8"))
TAUX = CONFIG["taux_euro"]

# Colonnes du fichier final, dans l'ordre
COLONNES = [
    "pays", "type", "source", "id_contrat", "annee",
    "age_conducteur", "jeune_conducteur", "sexe",
    "age_vehicule", "puissance_ch", "carburant", "usage",
    "zone", "bonus_malus", "exposition",
    "nb_sinistres", "cout_total_eur", "cout_moyen_eur", "log_cout", "sinistre_extreme",
]

CARBURANT = {
    "regular": "essence", "gasoline": "essence", "petrol": "essence", "p": "essence",
    "diesel": "diesel", "d": "diesel", "gpl": "gpl", "eletric": "électrique", "electric": "électrique",
}
SEXE = {"male": "H", "m": "H", "1": "H", "female": "F", "f": "F", "0": "F"}


def log(msg: str) -> None:
    print(f"[nettoyage] {msg}", flush=True)


def lire(nom: str) -> pd.DataFrame | None:
    chemin = RAW / f"{nom}.parquet"
    return pd.read_parquet(chemin) if chemin.exists() else None


class Rapport:
    """Garde la trace de chaque étape : combien de lignes avant, après, et pourquoi."""

    def __init__(self) -> None:
        self.sources: dict[str, list[dict]] = {}

    def etape(self, source: str, num: int, nom: str, avant: int, apres: int, detail: str = "") -> None:
        self.sources.setdefault(source, []).append(
            {"etape": num, "nom": nom, "lignes_avant": int(avant), "lignes_apres": int(apres),
             "retirees": int(avant - apres), "detail": detail})

    def sauver(self, chemin: Path) -> None:
        chemin.write_text(json.dumps(
            {"genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sources": self.sources},
            indent=2, ensure_ascii=False), encoding="utf-8")


R = Rapport()


# ------------------------------------------------------------------ étapes communes
BRUTS: dict[str, pd.DataFrame] = {}  # données brutes harmonisées, avec les anomalies repérées
COUT_MIN = float(CONFIG.get("cout_minimum_eur", 10))


def harmoniser_libelles(df: pd.DataFrame) -> pd.DataFrame:
    """Étape 10 : libellés communs (carburant, sexe). Appliquée aussi aux données brutes pour les comparer."""
    df = df.copy()
    if "carburant" in df:
        df["carburant"] = df["carburant"].astype("string").map(
            lambda v: CARBURANT.get(str(v).lower(), v) if pd.notna(v) else v)
    if "sexe" in df:
        df["sexe"] = df["sexe"].astype("string").str.lower().map(lambda v: SEXE.get(v, v) if pd.notna(v) else v)
    if "age_conducteur" in df and "jeune_conducteur" not in df:
        df["jeune_conducteur"] = df["age_conducteur"] < 26
    return df


def reperer_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute une colonne booléenne par type d'anomalie (sans rien supprimer)."""
    col = lambda c: df[c] if c in df else pd.Series(np.nan, index=df.index)
    a = pd.DataFrame(index=df.index)
    a["anom_cout_negatif"] = col("cout_total_eur") < 0
    a["anom_cout_nul"] = col("cout_total_eur") == 0
    a["anom_cout_minuscule"] = (col("cout_moyen_eur") > 0) & (col("cout_moyen_eur") < COUT_MIN)
    a["anom_age_impossible"] = (col("age_conducteur") < 16) | (col("age_conducteur") > 100)
    a["anom_puissance_impossible"] = (col("puissance_ch") <= 0) | (col("puissance_ch") > 1000)
    a["anom_age_vehicule_impossible"] = (col("age_vehicule") < 0) | (col("age_vehicule") > 60)
    a["anom_exposition_nulle"] = col("exposition").notna() & (col("exposition") <= 0)
    pos = col("cout_moyen_eur")[col("cout_moyen_eur") > 0]
    seuil = pos.quantile(0.995) if len(pos) else np.inf
    a["anom_cout_extreme"] = col("cout_moyen_eur") > seuil
    out = pd.concat([df, a], axis=1)
    out["nb_anomalies"] = a.sum(axis=1)
    return out


def etapes_communes(df: pd.DataFrame, src: str, devise: str) -> pd.DataFrame:
    """Conversion, coût moyen, repérage des anomalies (copie brute gardée), puis nettoyage."""
    # 12. Conversion en euros (avant tout, pour comparer brut et nettoyé dans la même unité)
    taux = TAUX.get(devise, 1.0)
    df = df.assign(cout_total_eur=df["cout_total_eur"] * taux)
    R.etape(src, 12, f"Conversion {devise} -> EUR (taux {taux})", len(df), len(df))

    # 3. Coût moyen par sinistre (variable à prédire)
    nb = df["nb_sinistres"].where(df["nb_sinistres"] > 0)
    df = df.assign(cout_moyen_eur=df["cout_total_eur"] / nb)
    R.etape(src, 3, "Coût moyen par sinistre calculé", len(df), len(df))

    # Copie BRUTE avec anomalies repérées (pour le dashboard)
    BRUTS[src] = harmoniser_libelles(reperer_anomalies(df))

    # 2. Coûts négatifs, nuls ou minuscules
    n = len(df)
    nb_neg = int((df["cout_total_eur"] < 0).sum())
    nb_min = int(((df["cout_moyen_eur"] > 0) & (df["cout_moyen_eur"] < COUT_MIN)).sum())
    df = df[(df["cout_total_eur"] > 0) & (df["nb_sinistres"] > 0) & (df["cout_moyen_eur"] >= COUT_MIN)]
    R.etape(src, 2, f"Coûts négatifs, nuls ou inférieurs à {COUT_MIN:.0f} € retirés", n, len(df),
            f"{nb_neg} négatifs ; {nb_min} coûts inférieurs à {COUT_MIN:.0f} €")

    # 7. Valeurs impossibles : mises à vide (âge, puissance) ou lignes retirées (exposition nulle)
    n = len(df)
    df = df.copy()
    imposs = 0
    if "age_conducteur" in df:
        m = (df["age_conducteur"] < 16) | (df["age_conducteur"] > 100)
        imposs += int(m.sum()); df.loc[m, "age_conducteur"] = np.nan
    if "puissance_ch" in df:
        m = (df["puissance_ch"] <= 0) | (df["puissance_ch"] > 1000)
        imposs += int(m.sum()); df.loc[m, "puissance_ch"] = np.nan
    if "age_vehicule" in df:
        m = (df["age_vehicule"] < 0) | (df["age_vehicule"] > 60)
        imposs += int(m.sum()); df.loc[m, "age_vehicule"] = np.nan
    if "exposition" in df:
        df = df[~(df["exposition"].notna() & (df["exposition"] <= 0))]
    R.etape(src, 7, "Valeurs impossibles", n, len(df),
            f"{imposs} valeurs mises à vide (âge, puissance, âge véhicule) ; expositions nulles retirées")

    # 8. Sinistres extrêmes : gardés mais repérés ; log du coût pour la modélisation
    seuil = df["cout_moyen_eur"].quantile(0.995)
    df = df.assign(sinistre_extreme=df["cout_moyen_eur"] > seuil, log_cout=np.log(df["cout_moyen_eur"]))
    R.etape(src, 8, "Sinistres extrêmes repérés (> 99,5e centile)", len(df), len(df),
            f"seuil = {seuil:,.0f} EUR ; {int(df['sinistre_extreme'].sum())} sinistres repérés")

    # 10. Libellés communs
    df = harmoniser_libelles(df)
    R.etape(src, 10, "Libellés harmonisés (carburant, sexe)", len(df), len(df))
    return df


def garder_sinistres(df: pd.DataFrame, src: str, masque: pd.Series, total: int) -> pd.DataFrame:
    """Étape 1 : ne garder que les contrats avec au moins un sinistre."""
    out = df[masque]
    R.etape(src, 1, "Contrats sans sinistre retirés", total, len(out))
    return out


# ------------------------------------------------------------------ une fonction par source
def france_fremtpl2() -> pd.DataFrame | None:
    src = "fr_fremtpl2"
    freq, sev = lire("freMTPL2freq"), lire("freMTPL2sev")
    if freq is None or sev is None:
        return None
    sev = sev.assign(IDpol=sev["IDpol"].astype(str))
    freq = freq.assign(IDpol=freq["IDpol"].astype(str))
    # 4. Lien entre fichiers : un contrat peut avoir plusieurs sinistres -> on regroupe par contrat
    agg = sev.groupby("IDpol").agg(cout_total_eur=("ClaimAmount", "sum"), nb_sinistres=("ClaimAmount", "size")).reset_index()
    df = agg.merge(freq, on="IDpol", how="inner")
    R.etape(src, 1, "Contrats sans sinistre retirés", len(freq), len(df),
            f"{len(sev)} sinistres regroupés en {len(agg)} contrats")
    R.etape(src, 4, "Lien coûts / contrats (IDpol)", len(agg), len(df),
            f"{len(agg) - len(df)} contrats sans caractéristiques retirés")
    out = pd.DataFrame({
        "id_contrat": df["IDpol"], "annee": np.nan,
        "age_conducteur": df["DrivAge"].astype(float), "sexe": pd.NA,
        "age_vehicule": df["VehAge"].astype(float), "puissance_ch": np.nan,
        "carburant": df["VehGas"], "usage": pd.NA, "zone": df["Region"],
        "bonus_malus": df["BonusMalus"].astype(float), "exposition": df["Exposure"].astype(float),
        "nb_sinistres": df["nb_sinistres"].astype(float), "cout_total_eur": df["cout_total_eur"].astype(float),
    })
    return etapes_communes(out, src, "EUR")


def france_frempl() -> pd.DataFrame | None:
    src = "fr_frempl"
    morceaux = []
    for i in range(1, 11):
        d = lire(f"freMPL{i}")
        if d is None:
            continue
        # Les colonnes ClaimNb* de freMPL5-10 sont des historiques de sinistres, pas le nombre lié à ce montant :
        # un montant non nul correspond ici à un sinistre déclaré sur la période.
        nb = pd.Series(1.0, index=d.index)
        annee = pd.to_datetime(d["RecordBeg"], unit="D", errors="coerce").dt.year if "RecordBeg" in d else np.nan
        age_veh = (d["VehAge"].astype("string").str.extract(r"(\d+)")[0].astype(float)
                   if "VehAge" in d else pd.Series(np.nan, index=d.index))
        col = lambda c: d[c] if c in d else pd.Series(pd.NA, index=d.index)
        morceaux.append(pd.DataFrame({
            "id_contrat": f"freMPL{i}_" + d.index.astype(str), "annee": annee,
            "age_conducteur": d["DrivAge"].astype(float), "sexe": d["Gender"],
            "age_vehicule": age_veh, "puissance_ch": np.nan, "carburant": col("VehEnergy"),
            "usage": col("VehUsage"), "zone": col("RiskArea").astype("string"),
            "bonus_malus": d["BonusMalus"].astype(float), "exposition": d["Exposure"].astype(float),
            "nb_sinistres": nb.astype(float), "cout_total_eur": d["ClaimAmount"].astype(float),
        }))
    if not morceaux:
        return None
    df = pd.concat(morceaux, ignore_index=True)
    df = garder_sinistres(df, src, df["cout_total_eur"] != 0, len(df))
    return etapes_communes(df, src, "EUR")


def italie_eumtpl() -> pd.DataFrame | None:
    src = "it_eumtpl"
    d = lire("euMTPL")
    if d is None:
        return None
    types = ["nc", "cg", "fcg", "cd"]
    cout = sum(d[f"cost_{t}"].astype(float) for t in types)
    nb = sum(d[f"num_{t}"].astype(float) for t in types)
    df = pd.DataFrame({
        "id_contrat": d["policy_id"].astype(str), "annee": np.nan,
        "age_conducteur": d["age"].astype(float), "sexe": d["gender"],
        "age_vehicule": np.nan, "puissance_ch": d["horsepower"].astype(float),
        "carburant": "code " + d["fuel_type"].astype("string"),  # codes non documentés par la source
        "usage": "code " + d["vehicle_use"].astype("string"),
        "zone": d["province"],  # "NA" = Naples, conservé grâce à la lecture depuis R
        "bonus_malus": np.nan, "exposition": d["exposure"].astype(float),
        "nb_sinistres": nb, "cout_total_eur": cout,
    })
    df["periode_source"] = d["year"].astype(float)  # année relative (7, 8, 9), utile pour la simulation
    df = garder_sinistres(df, src, df["nb_sinistres"] > 0, len(df))
    return etapes_communes(df, src, "EUR")


def belgique_bemtpl97() -> pd.DataFrame | None:
    src = "be_bemtpl97"
    d = lire("beMTPL97")
    if d is None:
        return None
    df = pd.DataFrame({
        "id_contrat": d["id"].astype(str), "annee": 1997.0,
        "age_conducteur": d["ageph"].astype(float), "sexe": d["sex"],
        "age_vehicule": d["agec"].astype(float),
        "puissance_ch": d["power"].astype(float) * 1.36,  # 9. kW -> chevaux
        "carburant": d["fuel"], "usage": d["use"], "zone": d["postcode"].astype("string"),
        "bonus_malus": d["bm"].astype(float), "exposition": d["expo"].astype(float),
        "nb_sinistres": d["nclaims"].astype(float), "cout_total_eur": d["amount"].astype(float),
    })
    R.etape(src, 9, "Puissance convertie de kW en chevaux", len(df), len(df))
    df = garder_sinistres(df, src, df["nb_sinistres"] > 0, len(df))
    return etapes_communes(df, src, "EUR")


def norvege_norauto() -> pd.DataFrame | None:
    src = "no_norauto"
    d = lire("norauto")
    if d is None:
        return None
    nb = d["NbClaim"].astype(float)
    df = pd.DataFrame({
        "id_contrat": d.index.astype(str), "annee": np.nan,
        "age_conducteur": np.nan, "jeune_conducteur": d["Young"].astype(float) == 1,
        "sexe": d["Male"].astype("string"), "age_vehicule": np.nan, "puissance_ch": np.nan,
        "carburant": pd.NA, "usage": "limite " + d["DistLimit"].astype("string"),
        "zone": d["GeoRegion"], "bonus_malus": np.nan, "exposition": d["Expo"].astype(float),
        "nb_sinistres": nb,
        "cout_total_eur": d["ClaimAmount"].astype(float) * nb,  # la source donne déjà un coût moyen
    })
    df = garder_sinistres(df, src, df["nb_sinistres"] > 0, len(df))
    return etapes_communes(df, src, "NOK")


def suede_swmotorcycle() -> pd.DataFrame | None:
    src = "se_swmotorcycle"
    d = lire("swmotorcycle")
    if d is None:
        return None
    df = pd.DataFrame({
        "id_contrat": d.index.astype(str), "annee": np.nan,
        "age_conducteur": d["OwnerAge"].astype(float), "sexe": d["Gender"],
        "age_vehicule": d["VehAge"].astype(float), "puissance_ch": np.nan,
        "carburant": pd.NA, "usage": d["RiskClass"], "zone": d["Area"],
        "bonus_malus": d["BonusClass"].astype("string").str.extract(r"(\d+)")[0].astype(float),
        "exposition": d["Exposure"].astype(float),
        "nb_sinistres": d["ClaimNb"].astype(float), "cout_total_eur": d["ClaimAmount"].astype(float),
    })
    df = garder_sinistres(df, src, df["nb_sinistres"] > 0, len(df))
    return etapes_communes(df, src, "SEK")


def espagne() -> pd.DataFrame | None:
    """Portefeuille espagnol 2015-2018. Noms de colonnes d'après l'article (European Actuarial Journal, 2024)."""
    src = "es_portefeuille"
    d = lire("espagne")
    if d is None:
        log("Espagne absente : à ajouter dans data/raw/manuel/espagne.csv")
        return None
    attendues = {"Type_risk", "Cost_claims_year", "N_claims_year", "Date_birth", "Date_last_renewal"}
    manquantes = attendues - set(d.columns)
    if manquantes:
        log(f"Espagne : colonnes attendues absentes {sorted(manquantes)}, source ignorée")
        return None
    date = lambda c: pd.to_datetime(d[c], dayfirst=True, errors="coerce")
    renouv = date("Date_last_renewal")
    n = len(d)
    type_risque = pd.to_numeric(d["Type_risk"], errors="coerce")
    garder = type_risque.isin([1, 3])  # 1 = moto, 3 = voiture ; utilitaires (2) et agricoles (4) écartés
    R.etape(src, 0, "Utilitaires et véhicules agricoles écartés", n, int(garder.sum()))
    d, renouv, type_risque = d[garder], renouv[garder], type_risque[garder]
    df = pd.DataFrame({
        "type": np.where(type_risque == 1, "moto", "auto"),
        "id_contrat": d["ID"].astype(str) if "ID" in d else d.index.astype(str),
        "annee": renouv.dt.year.astype(float),
        "age_conducteur": ((renouv - date("Date_birth")[garder]).dt.days / 365.25).round(),
        "sexe": pd.NA,
        "age_vehicule": renouv.dt.year - pd.to_numeric(d.get("Year_matriculation"), errors="coerce"),
        "puissance_ch": pd.to_numeric(d.get("Power"), errors="coerce"),
        "carburant": d.get("Type_fuel"), "usage": pd.NA,
        "zone": d.get("Area").astype("string") if "Area" in d else pd.NA,
        "bonus_malus": np.nan, "exposition": np.nan,
        "nb_sinistres": pd.to_numeric(d["N_claims_year"], errors="coerce"),
        "cout_total_eur": pd.to_numeric(d["Cost_claims_year"].astype("string").str.replace(",", "."), errors="coerce"),
    })
    df = garder_sinistres(df, src, df["nb_sinistres"] > 0, len(df))
    return etapes_communes(df, src, "EUR")


# ------------------------------------------------------------------ qualité des données brutes
def profil_qualite() -> dict:
    """Profil simple de chaque fichier brut : manques, valeurs distinctes, min / max, exemples."""
    profil = {}
    for chemin in sorted(RAW.glob("*.parquet")):
        d = pd.read_parquet(chemin)
        cols = {}
        for c in d.columns:
            s = d[c]
            info = {"type": str(s.dtype), "manquants": int(s.isna().sum()),
                    "pct_manquants": round(100 * s.isna().mean(), 2), "distinctes": int(s.nunique())}
            if pd.api.types.is_numeric_dtype(s):
                info.update(min=None if s.dropna().empty else float(s.min()),
                            max=None if s.dropna().empty else float(s.max()),
                            negatifs=int((s < 0).sum()), zeros=int((s == 0).sum()))
            info["exemples"] = [str(v) for v in s.dropna().value_counts().head(6).index]
            cols[str(c)] = info
        profil[chemin.stem] = {"lignes": int(len(d)), "colonnes": len(d.columns),
                               "doublons": int(d.duplicated().sum()), "detail": cols}
    return profil


# ------------------------------------------------------------------ fiche descriptive du jeu de données
DESCRIPTION_COLONNES = [
    ("pays", "Pays de la source"), ("type", "auto ou moto"), ("source", "Jeu de données d'origine"),
    ("id_contrat", "Identifiant du contrat dans la source"), ("annee", "Année du contrat, si connue"),
    ("age_conducteur", "Âge du conducteur (ans)"), ("jeune_conducteur", "Conducteur de moins de 26 ans"),
    ("sexe", "H, F ou inconnu"), ("age_vehicule", "Âge du véhicule (ans)"), ("puissance_ch", "Puissance (chevaux)"),
    ("carburant", "essence, diesel, électrique, gpl, ou code d'origine (Italie)"), ("usage", "Usage du véhicule"),
    ("zone", "Région, province, code postal ou type de zone selon le pays"),
    ("bonus_malus", "Bonus-malus, dans l'échelle propre à chaque pays"),
    ("exposition", "Durée du contrat sur l'année (1 = année complète)"),
    ("nb_sinistres", "Nombre de sinistres du contrat"), ("cout_total_eur", "Coût total des sinistres (€)"),
    ("cout_moyen_eur", "**Variable à prédire** : coût moyen par sinistre (€)"),
    ("log_cout", "Logarithme du coût moyen (cible transformée)"),
    ("sinistre_extreme", "Coût au-delà du 99,5e centile de sa source (gardé, mais repéré)"),
    ("periode_source", "Année relative fournie par la source italienne (7, 8, 9)"),
]


def ecrire_fiche(final: pd.DataFrame, brut: pd.DataFrame) -> None:
    """Écrit data/clean/README.md : description du jeu de données, avec les chiffres à jour."""
    infos = {s["id"]: s for s in CONFIG["sources"]}
    n = lambda x: f"{int(x):,}".replace(",", " ")
    e = lambda x: f"{x:,.0f} €".replace(",", " ")
    l = []
    l += ["# Jeu de données : sinistres auto et moto en Europe", "",
          "Premier jeu de données du projet AssurIA (objectif 3 : prédiction du coût d'un sinistre).",
          "Ce fichier est **généré automatiquement** à chaque mise à jour des données.", "",
          f"- **Mis à jour le** : {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} (UTC)",
          f"- **Sinistres** : {n(len(final))} sinistres nettoyés ({n(len(brut))} lignes brutes)",
          f"- **Pays** : {', '.join(sorted(final['pays'].unique()))}",
          f"- **Variable à prédire** : `cout_moyen_eur`, coût moyen par sinistre en euros",
          "- **Format** : Parquet (`pd.read_parquet(...)`)", ""]
    l += ["## Fichiers", "",
          "| Fichier | Contenu |", "| --- | --- |",
          "| `sinistres_europe.parquet` | Données nettoyées, prêtes pour la modélisation |",
          "| `sinistres_bruts.parquet` | Données avant nettoyage, avec une colonne par type d'anomalie (`anom_*`) |",
          "| `rapport_nettoyage.json` | Lignes avant / après chaque étape de nettoyage, par source |", ""]
    l += ["## Sources", "",
          "| Source | Pays | Type | Sinistres nettoyés | Coût médian | Devise d'origine |",
          "| --- | --- | --- | --- | --- | --- |"]
    for sid, g in final.groupby("source"):
        s = infos.get(sid, {})
        l.append(f"| `{sid}` | {s.get('pays', '')} | {', '.join(sorted(g['type'].unique()))} | {n(len(g))} | "
                 f"{e(g['cout_moyen_eur'].median())} | {s.get('devise', '')} |")
    l += ["", "Origine : [CASdatasets](https://github.com/dutangc/CASdatasets) (C. Dutang et A. Charpentier, licence GPL ≥ 2). "
          "Portefeuille espagnol : [Mendeley Data](https://doi.org/10.17632/5cxyb5fp4f.2), "
          + ("intégré." if "es_portefeuille" in set(final["source"]) else "pas encore intégré."), ""]
    l += ["## Colonnes", "", "| Colonne | Contenu | % renseigné |", "| --- | --- | --- |"]
    for c, d in DESCRIPTION_COLONNES:
        if c in final:
            s = final[c]
            pct = 100 * s.notna().mean() * (s.astype(str) != "inconnu").mean()
            l.append(f"| `{c}` | {d} | {pct:.0f} % |")
    l += ["", "## Coût par pays", "", "| Pays | Sinistres | Coût médian | Coût moyen |", "| --- | --- | --- | --- |"]
    for p, g in final.groupby("pays"):
        l.append(f"| {p} | {n(len(g))} | {e(g['cout_moyen_eur'].median())} | {e(g['cout_moyen_eur'].mean())} |")
    l += ["", "## Nettoyage appliqué", "",
          "1. Seuls les contrats avec au moins un sinistre sont gardés.",
          f"2. Les coûts négatifs, nuls ou inférieurs à {COUT_MIN:.0f} € sont retirés.",
          "3. Le coût moyen par sinistre est calculé partout (coût total ÷ nombre de sinistres).",
          "4. Les valeurs impossibles (âge < 16 ou > 100 ans, puissance ≤ 0, âge du véhicule > 60 ans) sont mises à vide ; "
          "les contrats d'exposition nulle sont retirés.",
          "5. Les sinistres au-delà du 99,5e centile sont gardés mais repérés (`sinistre_extreme`).",
          "6. Les libellés sont harmonisés (carburant, sexe) ; les textes manquants deviennent « inconnu ».",
          "7. Les montants sont convertis en euros ; une colonne `pays` et une colonne `type` sont ajoutées.", "",
          f"Lignes retirées au total : {n(len(brut) - len(final))} ({100 * (1 - len(final) / max(len(brut), 1)):.2f} %)".replace(".", ",") + f".", ""]
    l += ["## Limites connues", "",
          "- Toutes les variables n'existent pas dans tous les pays (voir « % renseigné ») : les valeurs vides sont "
          "laissées vides, sans être inventées.",
          "- Les codes de carburant et d'usage italiens ne sont pas documentés par la source : ils sont gardés tels quels.",
          "- La puissance italienne semble exprimée en chevaux fiscaux : à vérifier avant de la comparer aux autres pays.",
          "- Les taux de conversion des couronnes (Norvège, Suède) sont des ordres de grandeur, à valider.",
          "- Les montants ne sont pas encore ajustés à l'inflation (les données vont de 1997 aux années 2000).",
          "- Les échelles de bonus-malus diffèrent selon les pays.", ""]
    l += ["## Utilisation", "", "```python", "import pandas as pd",
          "df = pd.read_parquet(\"sinistres_europe.parquet\")", "y = df[\"log_cout\"]   # cible transformée", "```", ""]
    (CLEAN / "README.md").write_text("\n".join(l), encoding="utf-8")


def main() -> int:
    CLEAN.mkdir(parents=True, exist_ok=True)
    infos = {s["id"]: s for s in CONFIG["sources"]}
    fonctions = [("fr_fremtpl2", france_fremtpl2), ("fr_frempl", france_frempl), ("it_eumtpl", italie_eumtpl),
                 ("be_bemtpl97", belgique_bemtpl97), ("no_norauto", norvege_norauto),
                 ("se_swmotorcycle", suede_swmotorcycle), ("es_portefeuille", espagne)]
    morceaux = []
    for sid, f in fonctions:
        df = f()
        if df is None or df.empty:
            continue
        df["source"] = sid
        df["pays"] = infos[sid]["pays"]
        if "type" not in df or df["type"].isna().all():
            df["type"] = infos[sid]["type"]
        # 5. Valeurs manquantes des colonnes texte -> "inconnu" (les numériques restent vides)
        remplis = 0
        for c in ["sexe", "carburant", "usage", "zone"]:
            if c in df:
                remplis += int(df[c].isna().sum())
                df[c] = df[c].astype("string").fillna("inconnu")
        R.etape(sid, 5, "Valeurs manquantes (texte) remplacées par « inconnu »", len(df), len(df),
                f"{remplis} valeurs remplacées ; les colonnes numériques manquantes restent vides")
        morceaux.append(df)
        log(f"{sid} : {len(df):,} sinistres propres")

    final = pd.concat(morceaux, ignore_index=True)
    extra = [c for c in final.columns if c not in COLONNES]
    final = final[COLONNES + extra]
    final.to_parquet(CLEAN / "sinistres_europe.parquet", index=False)

    # Données brutes harmonisées (lignes avec un montant de sinistre, AVANT nettoyage), anomalies repérées
    bruts = []
    for sid, b in BRUTS.items():
        b = b.copy()
        b["source"], b["pays"] = sid, infos[sid]["pays"]
        if "type" not in b or b["type"].isna().all():
            b["type"] = infos[sid]["type"]
        if sid == "it_eumtpl":  # « NA » = Naples : faux manquant que l'on a évité
            b["faux_manquant_naples"] = b["zone"].astype("string") == "NA"
        bruts.append(b)
    brut = pd.concat(bruts, ignore_index=True)
    for c in ["sexe", "carburant", "usage", "zone"]:
        if c in brut:
            brut[c] = brut[c].astype("string")
    brut.to_parquet(CLEAN / "sinistres_bruts.parquet", index=False)
    ecrire_fiche(final, brut)
    log(f"Fichier brut : {len(brut):,} lignes, {int((brut['nb_anomalies'] > 0).sum()):,} avec au moins une anomalie")
    R.sauver(CLEAN / "rapport_nettoyage.json")
    (CLEAN / "qualite_brute.json").write_text(json.dumps(profil_qualite(), indent=1, ensure_ascii=False), encoding="utf-8")
    log(f"Fichier final : {len(final):,} sinistres, {final['pays'].nunique()} pays -> data/clean/sinistres_europe.parquet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
