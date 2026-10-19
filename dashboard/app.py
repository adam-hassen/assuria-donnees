"""
Dashboard d'exploration des données de sinistres auto et moto (objectif 3).

Les données sont lues DIRECTEMENT depuis le dépôt GitHub (rien à télécharger sur son PC).
Lancement local :  streamlit run dashboard/app.py
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ------------------------------------------------------------------ source des données
DEPOT = os.environ.get("DEPOT_GITHUB", "adam-hassen/assuria-donnees")  # propriétaire/nom du dépôt
BRANCHE = os.environ.get("BRANCHE", "main")
URL_DEPOT = f"https://raw.githubusercontent.com/{DEPOT}/{BRANCHE}/data"
LOCAL = Path(__file__).resolve().parents[1] / "data"
MODE = os.environ.get("SOURCE_DONNEES", "github")  # "github" ou "local"

st.set_page_config(page_title="AssurIA · Données sinistres", layout="wide")


@st.cache_data(ttl=3600, show_spinner="Chargement des données depuis le dépôt…")
def lire_octets(chemin: str) -> bytes:
    if MODE == "local":
        return (LOCAL / chemin).read_bytes()
    r = requests.get(f"{URL_DEPOT}/{chemin}", timeout=120)
    r.raise_for_status()
    return r.content


@st.cache_data(ttl=3600)
def charger():
    df = pd.read_parquet(io.BytesIO(lire_octets("clean/sinistres_europe.parquet")))
    rapport = json.loads(lire_octets("clean/rapport_nettoyage.json"))
    qualite = json.loads(lire_octets("clean/qualite_brute.json"))
    manifest = json.loads(lire_octets("raw/manifest.json"))
    return df, rapport, qualite, manifest


try:
    df, rapport, qualite, manifest = charger()
except Exception as e:
    st.error(f"Impossible de lire les données ({MODE}) : {e}")
    st.stop()

# ------------------------------------------------------------------ filtres
st.sidebar.title("AssurIA")
st.sidebar.caption("Objectif 3 · Coût des sinistres")
pays = st.sidebar.multiselect("Pays", sorted(df["pays"].unique()), default=sorted(df["pays"].unique()))
types = st.sidebar.multiselect("Type", sorted(df["type"].unique()), default=sorted(df["type"].unique()))
sans_extremes = st.sidebar.toggle("Exclure les sinistres extrêmes", value=False)
st.sidebar.divider()
st.sidebar.caption(f"Données : {'dépôt ' + DEPOT if MODE == 'github' else 'dossier local'}")
derniere = max((v.get("collecte_le", "") for v in manifest.values()), default="?")
st.sidebar.caption(f"Dernière collecte : {derniere[:16].replace('T', ' ')}")

f = df[df["pays"].isin(pays) & df["type"].isin(types)]
if sans_extremes:
    f = f[~f["sinistre_extreme"]]

st.title("Données de sinistres auto et moto en Europe")
onglets = st.tabs(["Vue d'ensemble", "Qualité des données brutes", "Coûts", "Explorer une variable",
                   "Nettoyage", "Données"])

# ------------------------------------------------------------------ 1. vue d'ensemble
with onglets[0]:
    c = st.columns(4)
    c[0].metric("Sinistres", f"{len(f):,}".replace(",", " "))
    c[1].metric("Pays", f["pays"].nunique())
    c[2].metric("Coût médian", f"{f['cout_moyen_eur'].median():,.0f} €".replace(",", " "))
    c[3].metric("Coût moyen", f"{f['cout_moyen_eur'].mean():,.0f} €".replace(",", " "))

    g1, g2 = st.columns(2)
    par_pays = f.groupby(["pays", "type"]).size().reset_index(name="sinistres")
    g1.plotly_chart(px.bar(par_pays, x="pays", y="sinistres", color="type", title="Nombre de sinistres par pays"),
                    use_container_width=True)
    med = f.groupby("pays")["cout_moyen_eur"].median().sort_values().reset_index()
    g2.plotly_chart(px.bar(med, x="cout_moyen_eur", y="pays", orientation="h",
                           title="Coût médian d'un sinistre (€)", labels={"cout_moyen_eur": "€"}),
                    use_container_width=True)

    st.subheader("Fichiers collectés")
    st.dataframe(pd.DataFrame([{"fichier": k, "pays": v.get("pays"), "lignes": v.get("lignes"),
                                "colonnes": len(v.get("colonnes", [])), "collecté le": v.get("collecte_le", "")[:16]}
                               for k, v in manifest.items()]), hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ 2. qualité brute
with onglets[1]:
    st.caption("Profil des fichiers bruts, avant nettoyage : à utiliser pour décider quoi nettoyer.")
    fichier = st.selectbox("Fichier brut", list(qualite.keys()))
    q = qualite[fichier]
    c = st.columns(3)
    c[0].metric("Lignes", f"{q['lignes']:,}".replace(",", " "))
    c[1].metric("Colonnes", q["colonnes"])
    c[2].metric("Lignes en double", q["doublons"])
    tab = pd.DataFrame([{"colonne": k, **{x: v.get(x) for x in
                        ["type", "pct_manquants", "distinctes", "min", "max", "negatifs", "zeros"]},
                         "exemples": ", ".join(v.get("exemples", []))} for k, v in q["detail"].items()])
    alertes = tab[(tab["pct_manquants"] > 0) | (tab["negatifs"].fillna(0) > 0)]
    if len(alertes):
        st.warning(f"{len(alertes)} colonne(s) avec des valeurs manquantes ou négatives : "
                   + ", ".join(alertes["colonne"]))
    st.dataframe(tab, hide_index=True, use_container_width=True)
    if tab["pct_manquants"].sum() > 0:
        st.plotly_chart(px.bar(tab[tab["pct_manquants"] > 0], x="colonne", y="pct_manquants",
                               title="% de valeurs manquantes par colonne"), use_container_width=True)

# ------------------------------------------------------------------ 3. coûts
with onglets[2]:
    st.caption("Le coût est très asymétrique : l'axe est en échelle logarithmique.")
    g1, g2 = st.columns(2)
    g1.plotly_chart(px.histogram(f, x="log_cout", color="pays", nbins=80, barmode="overlay", opacity=0.55,
                                 title="Distribution du log du coût moyen par sinistre",
                                 labels={"log_cout": "log(coût en €)"}), use_container_width=True)
    g2.plotly_chart(px.box(f, x="pays", y="cout_moyen_eur", log_y=True, points=False,
                           title="Coût par pays (échelle log)", labels={"cout_moyen_eur": "€"}),
                    use_container_width=True)
    quant = f.groupby("pays")["cout_moyen_eur"].describe(percentiles=[.25, .5, .75, .99]).round(0)
    st.dataframe(quant, use_container_width=True)
    st.subheader("Sinistres les plus coûteux")
    st.dataframe(f.nlargest(20, "cout_moyen_eur")[["pays", "source", "age_conducteur", "puissance_ch",
                                                   "zone", "nb_sinistres", "cout_moyen_eur"]],
                 hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ 4. explorer une variable
with onglets[3]:
    variables = ["age_conducteur", "age_vehicule", "puissance_ch", "bonus_malus", "exposition",
                 "sexe", "carburant", "usage", "zone", "jeune_conducteur"]
    v = st.selectbox("Variable", variables)
    sous = f[f[v].notna()]
    if sous.empty:
        st.info("Aucune donnée pour cette variable avec les filtres choisis.")
    elif pd.api.types.is_numeric_dtype(sous[v]) and sous[v].nunique() > 15:
        sous = sous.assign(tranche=pd.qcut(sous[v], q=10, duplicates="drop").astype(str))
        g1, g2 = st.columns(2)
        g1.plotly_chart(px.histogram(sous, x=v, color="pays", barmode="overlay", opacity=0.55,
                                     title=f"Répartition de {v}"), use_container_width=True)
        m = sous.groupby(["pays", "tranche"], observed=True)["cout_moyen_eur"].median().reset_index()
        g2.plotly_chart(px.line(m, x="tranche", y="cout_moyen_eur", color="pays", markers=True,
                                title=f"Coût médian selon {v}", labels={"cout_moyen_eur": "€"}),
                        use_container_width=True)
    else:
        top = sous[v].astype(str).value_counts().head(25).index
        sous = sous[sous[v].astype(str).isin(top)].assign(valeur=lambda d: d[v].astype(str))
        g1, g2 = st.columns(2)
        g1.plotly_chart(px.histogram(sous, x="valeur", color="pays", title=f"Valeurs de {v}"),
                        use_container_width=True)
        m = sous.groupby(["pays", "valeur"])["cout_moyen_eur"].median().reset_index()
        g2.plotly_chart(px.bar(m, x="valeur", y="cout_moyen_eur", color="pays", barmode="group",
                               title=f"Coût médian selon {v}", labels={"cout_moyen_eur": "€"}),
                        use_container_width=True)
    dispo = f.groupby("pays")[variables].apply(lambda d: d.notna().mean().round(2) * 100)
    st.subheader("Disponibilité des variables par pays (%)")
    st.dataframe(dispo, use_container_width=True)

# ------------------------------------------------------------------ 5. nettoyage
with onglets[4]:
    st.caption(f"Rapport généré le {rapport['genere_le'][:16].replace('T', ' ')}")
    for src, etapes in rapport["sources"].items():
        e = pd.DataFrame(etapes).sort_values("etape")
        debut, fin = e["lignes_avant"].iloc[0], e["lignes_apres"].iloc[-1]
        with st.expander(f"{src} : {debut:,} → {fin:,} lignes".replace(",", " ")):
            st.dataframe(e[["etape", "nom", "lignes_avant", "lignes_apres", "retirees", "detail"]],
                         hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ 6. données
with onglets[5]:
    st.dataframe(f.head(1000), hide_index=True, use_container_width=True)
    st.download_button("Télécharger la sélection (CSV)", f.to_csv(index=False).encode("utf-8"),
                       file_name="sinistres_selection.csv", mime="text/csv")
