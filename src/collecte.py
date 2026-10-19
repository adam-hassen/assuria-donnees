"""
Collecte automatique des données de sinistres auto et moto.

Pour chaque source déclarée dans config/sources.yaml :
  1. télécharge les fichiers d'origine ;
  2. calcule une empreinte (sha256) pour savoir si la source a changé ;
  3. si elle a changé (ou n'a jamais été collectée), convertit les fichiers en Parquet
     dans data/raw/ et met à jour data/raw/manifest.json.

Lancement :  python -m src.collecte
Option    :  CASDATASETS_LOCAL=/chemin/vers/CASdatasets/data  (utilise une copie locale)
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import yaml

RACINE = Path(__file__).resolve().parents[1]
CONFIG = RACINE / "config" / "sources.yaml"
DOSSIER_RAW = RACINE / "data" / "raw"
MANIFEST = DOSSIER_RAW / "manifest.json"


def log(msg: str) -> None:
    print(f"[collecte] {msg}", flush=True)


def sha256(contenu: bytes) -> str:
    return hashlib.sha256(contenu).hexdigest()


def charger_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def sauver_manifest(manifest: dict) -> None:
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def normaliser_types(df: pd.DataFrame) -> pd.DataFrame:
    """Rend un DataFrame issu de R compatible Parquet (catégories et chaînes -> texte simple)."""
    df = df.reset_index(drop=True).copy()
    for col in df.columns:
        s = df[col]
        if isinstance(s.dtype, pd.CategoricalDtype) or pd.api.types.is_string_dtype(s) or s.dtype == object:
            df[col] = s.astype("string")
    return df


# ---------------------------------------------------------------- CASdatasets
def telecharger_rda(nom: str, url_base: str) -> bytes:
    local = os.environ.get("CASDATASETS_LOCAL")
    if local:
        return (Path(local) / f"{nom}.rda").read_bytes()
    r = requests.get(f"{url_base}/{nom}.rda", timeout=120)
    r.raise_for_status()
    return r.content


def lire_rda(contenu: bytes) -> dict[str, pd.DataFrame]:
    import rdata  # import local : seulement utile pour les fichiers R

    with tempfile.NamedTemporaryFile(suffix=".rda", delete=False) as tmp:
        tmp.write(contenu)
        chemin = tmp.name
    try:
        # Important : rdata garde la chaîne "NA" (ex. province de Naples) au lieu d'en faire une valeur manquante
        return rdata.read_rda(chemin)
    finally:
        os.unlink(chemin)


def collecter_casdatasets(source: dict, url_base: str, manifest: dict) -> bool:
    change = False
    for nom in source["fichiers"]:
        contenu = telecharger_rda(nom, url_base)
        empreinte = sha256(contenu)
        sortie = DOSSIER_RAW / f"{nom}.parquet"
        ancien = manifest.get(nom, {})
        if ancien.get("sha256") == empreinte and sortie.exists():
            log(f"{nom} : inchangé")
            continue
        for objet, df in lire_rda(contenu).items():
            df = normaliser_types(df)
            df.to_parquet(sortie, index=False)
            manifest[nom] = {
                "source": source["id"],
                "pays": source["pays"],
                "sha256": empreinte,
                "lignes": int(len(df)),
                "colonnes": list(map(str, df.columns)),
                "collecte_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            log(f"{nom} : NOUVELLE VERSION -> {sortie.name} ({len(df):,} lignes)")
            change = True
    return change


# ---------------------------------------------------------------- Mendeley (Espagne)
def telecharger_mendeley(source: dict) -> bytes | None:
    """Tente le téléchargement via l'API publique de Mendeley Data. Renvoie None si impossible."""
    api = f"https://data.mendeley.com/public-api/datasets/{source['mendeley_id']}/files"
    try:
        r = requests.get(api, params={"folder_id": "root", "version": source["mendeley_version"]}, timeout=60)
        r.raise_for_status()
        fichiers = r.json()
        csv = [f for f in fichiers if str(f.get("filename", "")).lower().endswith(".csv")
               and "sample" not in str(f.get("filename", "")).lower()]
        if not csv:
            log("Espagne : aucun CSV trouvé via l'API Mendeley")
            return None
        url = csv[0]["content_details"]["download_url"]
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        return r.content
    except Exception as e:  # réseau bloqué, API modifiée...
        log(f"Espagne : téléchargement automatique impossible ({e.__class__.__name__})")
        return None


def collecter_mendeley(source: dict, manifest: dict) -> bool:
    contenu = telecharger_mendeley(source)
    manuel = RACINE / source["fichier_manuel"]
    if contenu is None and manuel.exists():
        log(f"Espagne : utilisation du fichier déposé manuellement ({manuel.relative_to(RACINE)})")
        contenu = manuel.read_bytes()
    if contenu is None:
        log(f"Espagne : IGNORÉE. Déposer le CSV dans {source['fichier_manuel']} pour l'inclure.")
        return False
    empreinte = sha256(contenu)
    sortie = DOSSIER_RAW / "espagne.parquet"
    if manifest.get("espagne", {}).get("sha256") == empreinte and sortie.exists():
        log("Espagne : inchangé")
        return False
    sep = ";" if contenu[:2000].count(b";") > contenu[:2000].count(b",") else ","
    df = normaliser_types(pd.read_csv(io.BytesIO(contenu), sep=sep, keep_default_na=False, na_values=[""]))
    df.to_parquet(sortie, index=False)
    manifest["espagne"] = {
        "source": source["id"], "pays": source["pays"], "sha256": empreinte,
        "lignes": int(len(df)), "colonnes": list(map(str, df.columns)),
        "collecte_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    log(f"Espagne : NOUVELLE VERSION -> {sortie.name} ({len(df):,} lignes)")
    return True


def main() -> int:
    DOSSIER_RAW.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    manifest = charger_manifest()
    nouveautes = False
    for source in config["sources"]:
        log(f"--- {source['id']} ({source['pays']}, {source['type']})")
        if source["origine"] == "casdatasets":
            nouveautes |= collecter_casdatasets(source, config["casdatasets"]["url_base"], manifest)
        elif source["origine"] == "mendeley":
            nouveautes |= collecter_mendeley(source, manifest)
    sauver_manifest(manifest)
    log("Terminé : " + ("nouvelles données collectées" if nouveautes else "aucune nouveauté"))
    # Dans GitHub Actions : indique au workflow s'il faut relancer le nettoyage
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"nouveautes={'true' if nouveautes else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
