"""
Dashboard des données de sinistres auto et moto (projet AssurIA, objectif 3).

Chaque graphe répond à une question précise, utile pour décider du nettoyage ou de la modélisation.
Les données sont lues directement dans le dépôt GitHub (rien à télécharger sur son PC).

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
import plotly.graph_objects as go
import requests
import streamlit as st

# ------------------------------------------------------------------ configuration
DEPOT = os.environ.get("DEPOT_GITHUB", "adam-hassen/assuria-donnees")
BRANCHE = os.environ.get("BRANCHE", "main")
URL_DEPOT = f"https://raw.githubusercontent.com/{DEPOT}/{BRANCHE}/data"
LOCAL = Path(__file__).resolve().parents[1] / "data"
MODE = os.environ.get("SOURCE_DONNEES", "github")

ENCRE, MUET, FOND, ACCENT = "#14213D", "#6B7280", "#F5F7FA", "#0E7C66"
COULEURS_PAYS = {"France": "#2E5EAA", "Italie": "#0E7C66", "Belgique": "#C8963E",
                 "Norvège": "#B5485D", "Suède": "#6B5CA5", "Espagne": "#D9822B"}
ANOMALIES = {
    "anom_cout_negatif": ("Coût négatif", "Remboursement récupéré par l'assureur, pas un coût.", "Ligne retirée"),
    "anom_cout_nul": ("Coût nul", "Sinistre déclaré sans aucun montant.", "Ligne retirée"),
    "anom_cout_minuscule": ("Coût < 10 €", "Montant trop faible pour un vrai sinistre (frais, arrondi).", "Ligne retirée"),
    "anom_age_impossible": ("Âge impossible", "Âge du conducteur < 16 ou > 100 ans.", "Valeur mise à vide"),
    "anom_puissance_impossible": ("Puissance impossible", "Puissance ≤ 0 ou > 1 000 ch.", "Valeur mise à vide"),
    "anom_age_vehicule_impossible": ("Âge véhicule impossible", "Âge du véhicule < 0 ou > 60 ans.", "Valeur mise à vide"),
    "anom_exposition_nulle": ("Exposition nulle", "Contrat d'une durée nulle.", "Ligne retirée"),
    "anom_cout_extreme": ("Coût extrême", "Au-delà du 99,5e centile de sa source.", "Gardé et repéré"),
}
VARIABLES = {"age_conducteur": "Âge conducteur", "sexe": "Sexe", "age_vehicule": "Âge véhicule",
             "puissance_ch": "Puissance (ch)", "carburant": "Carburant", "usage": "Usage",
             "zone": "Zone", "bonus_malus": "Bonus-malus", "exposition": "Exposition"}

st.set_page_config(page_title="AssurIA · Sinistres", page_icon="📊", layout="wide")

st.markdown(f"""
<style>
  .block-container {{padding-top: 3.5rem; max-width: 1400px;}}
  h1, h2, h3 {{color: {ENCRE}; letter-spacing: -0.01em;}}
  .entete {{border-bottom: 2px solid {ENCRE}; padding-bottom: .6rem; margin-bottom: 1.2rem;}}
  .entete .sur {{color: {ACCENT}; font-size: .78rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase;}}
  .entete h1 {{font-size: 2rem; margin: .2rem 0 0;}}
  .kpi {{background: white; border: 1px solid #E3E6EB; border-radius: 10px; padding: 14px 18px;}}
  .kpi .l {{color: {MUET}; font-size: .78rem; text-transform: uppercase; letter-spacing: .06em;}}
  .kpi .v {{color: {ENCRE}; font-size: 1.7rem; font-weight: 700; line-height: 1.2;}}
  .kpi .s {{color: {MUET}; font-size: .8rem;}}
  .carte {{background: white; border: 1px solid #E3E6EB; border-radius: 10px; padding: 16px 18px 4px; margin-bottom: 16px;}}
  .carte .q {{color: {ENCRE}; font-weight: 700; font-size: 1.05rem;}}
  .carte .o {{color: {MUET}; font-size: .85rem; margin: 2px 0 4px;}}
  .retenir {{background: #E7F4F0; border-left: 3px solid {ACCENT}; border-radius: 0 6px 6px 0;
             padding: 8px 12px; font-size: .88rem; color: {ENCRE}; margin: 4px 0 14px;}}
  .alerte {{background: #FDF4E6; border-left: 3px solid #9A5B0B; border-radius: 0 6px 6px 0;
            padding: 8px 12px; font-size: .88rem; color: {ENCRE}; margin: 4px 0 14px;}}
  div[data-testid="stTabs"] button p {{font-size: 1rem; font-weight: 600;}}
</style>""", unsafe_allow_html=True)


# ------------------------------------------------------------------ données
@st.cache_data(ttl=3600, show_spinner="Chargement des données depuis le dépôt…")
def octets(chemin: str) -> bytes:
    if MODE == "local":
        return (LOCAL / chemin).read_bytes()
    r = requests.get(f"{URL_DEPOT}/{chemin}", timeout=120)
    r.raise_for_status()
    return r.content


@st.cache_data(ttl=3600)
def charger():
    propre = pd.read_parquet(io.BytesIO(octets("clean/sinistres_europe.parquet")))
    brut = pd.read_parquet(io.BytesIO(octets("clean/sinistres_bruts.parquet")))
    rapport = json.loads(octets("clean/rapport_nettoyage.json"))
    manifest = json.loads(octets("raw/manifest.json"))
    return propre, brut, rapport, manifest


try:
    propre, brut, rapport, manifest = charger()
except Exception as e:
    st.error(f"Impossible de lire les données ({MODE}) : {e}")
    st.stop()


# ------------------------------------------------------------------ outils d'affichage
def euros(x: float) -> str:
    return f"{x:,.0f} €".replace(",", " ")


def nombre(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


def kpis(valeurs: list[tuple[str, str, str]]) -> None:
    for col, (l, v, s) in zip(st.columns(len(valeurs)), valeurs):
        col.markdown(f'<div class="kpi"><div class="l">{l}</div><div class="v">{v}</div><div class="s">{s}</div></div>',
                     unsafe_allow_html=True)
    st.write("")


def mise_en_forme(fig: go.Figure, hauteur: int = 380) -> go.Figure:
    fig.update_layout(template="simple_white", height=hauteur, margin=dict(l=10, r=10, t=10, b=10),
                      font=dict(family="Inter, sans-serif", color=ENCRE, size=13),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
                      hoverlabel=dict(bgcolor="white"))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#EEF0F3", showgrid=True)
    return fig


def graphe(question: str, objectif: str, fig: go.Figure, retenir: str = "", alerte: bool = False,
           hauteur: int = 380) -> None:
    st.markdown(f'<div class="carte"><div class="q">{question}</div><div class="o">Objectif : {objectif}</div></div>',
                unsafe_allow_html=True)
    st.plotly_chart(mise_en_forme(fig, hauteur), use_container_width=True, config={"displayModeBar": False})
    if retenir:
        st.markdown(f'<div class="{"alerte" if alerte else "retenir"}"><b>À retenir :</b> {retenir}</div>',
                    unsafe_allow_html=True)


def mediane_par_tranche(d: pd.DataFrame, var: str, n: int = 8) -> pd.DataFrame:
    morceaux = []
    for p, g in d[d[var].notna()].groupby("pays"):
        if g[var].nunique() < 3:
            continue
        g = g.assign(tranche=pd.qcut(g[var], q=n, duplicates="drop"))
        m = g.groupby("tranche", observed=True).agg(x=(var, "median"), cout=("cout_moyen_eur", "median"),
                                                     n=("cout_moyen_eur", "size")).reset_index(drop=True)
        morceaux.append(m.assign(pays=p))
    return pd.concat(morceaux) if morceaux else pd.DataFrame(columns=["x", "cout", "n", "pays"])


# ------------------------------------------------------------------ barre latérale
st.sidebar.markdown(f"### AssurIA\n<span style='color:{MUET}'>Objectif 3 · Coût des sinistres</span>",
                    unsafe_allow_html=True)
tous_pays = sorted(brut["pays"].unique())
pays = st.sidebar.multiselect("Pays", tous_pays, default=tous_pays)
types = st.sidebar.multiselect("Type de véhicule", sorted(brut["type"].unique()), default=sorted(brut["type"].unique()))
st.sidebar.divider()
derniere = max((v.get("collecte_le", "") for v in manifest.values()), default="")
st.sidebar.caption(f"Source : {'dépôt ' + DEPOT if MODE == 'github' else 'dossier local'}")
st.sidebar.caption(f"Dernière collecte : {derniere[:16].replace('T', ' ')}")
st.sidebar.caption(f"Nettoyage : {rapport['genere_le'][:16].replace('T', ' ')}")

B = brut[brut["pays"].isin(pays) & brut["type"].isin(types)]
P = propre[propre["pays"].isin(pays) & propre["type"].isin(types)]
couleurs = {p: COULEURS_PAYS.get(p, MUET) for p in tous_pays}

st.markdown('<div class="entete"><div class="sur">Projet AssurIA · Objectif 3</div>'
            '<h1>Sinistres auto et moto en Europe</h1></div>', unsafe_allow_html=True)

onglet_brut, onglet_propre, onglet_avap, onglet_detail = st.tabs(
    ["Données brutes et anomalies", "Données nettoyées", "Avant / après nettoyage", "Détail du nettoyage"])

# ================================================================== 1. DONNÉES BRUTES
with onglet_brut:
    cols_anom = [c for c in ANOMALIES if c in B]
    avec_anom = int((B["nb_anomalies"] > 0).sum())
    naples = int(B.get("faux_manquant_naples", pd.Series(dtype=bool)).fillna(False).sum())
    kpis([("Lignes brutes", nombre(len(B)), "lignes avec un montant de sinistre"),
          ("Lignes avec anomalie", nombre(avec_anom), f"{100 * avec_anom / max(len(B), 1):.1f} % des lignes"),
          ("Types d'anomalies", str(int((B[cols_anom].sum() > 0).sum())), f"sur {len(cols_anom)} contrôlés"),
          ("Faux manquants évités", nombre(naples), "« NA » = Naples, pas une valeur vide")])

    # --- Rapport d'anomalies
    st.subheader("Rapport des anomalies")
    rapport_anom = []
    for c in cols_anom:
        nom, desc, decision = ANOMALIES[c]
        n = int(B[c].sum())
        rapport_anom.append({"Anomalie": nom, "Lignes": n, "% des lignes": round(100 * n / max(len(B), 1), 2),
                             "Pays concernés": ", ".join(B.loc[B[c], "pays"].unique()) or "aucun",
                             "Description": desc, "Décision": decision})
    st.dataframe(pd.DataFrame(rapport_anom).sort_values("Lignes", ascending=False), hide_index=True,
                 use_container_width=True)

    g1, g2 = st.columns(2)
    with g1:
        heat = B.groupby("pays")[cols_anom].mean().mul(100).rename(columns={c: ANOMALIES[c][0] for c in cols_anom})
        cnt = B.groupby("pays")[cols_anom].sum().rename(columns={c: ANOMALIES[c][0] for c in cols_anom})
        fig = px.imshow(heat.T, color_continuous_scale=["#FFFFFF", "#F2C48D", "#B5485D"], aspect="auto",
                        labels=dict(color="% lignes"))
        fig.update_traces(text=cnt.T.values, texttemplate="%{text}", hovertemplate="%{y} · %{x}<br>%{z:.2f} % des lignes")
        pire = cnt.stack().idxmax() if cnt.values.sum() else None
        graphe("Où se concentrent les anomalies ?",
               "repérer, pays par pays, les problèmes à traiter avant de nettoyer.", fig,
               f"l'anomalie la plus fréquente est « {pire[1]} » en {pire[0]} ({nombre(cnt.stack().max())} lignes)."
               if pire else "aucune anomalie avec ces filtres.")
    with g2:
        manq = B.groupby("pays")[list(VARIABLES)].apply(lambda d: d.isna().mean() * 100)
        manq = manq.rename(columns=VARIABLES)
        fig = px.imshow(manq.T.round(0), color_continuous_scale=["#FFFFFF", "#9FB8DA", ENCRE], aspect="auto",
                        text_auto=".0f", labels=dict(color="% manquant"), zmin=0, zmax=100)
        partout = [VARIABLES[v] for v in VARIABLES if B.groupby("pays")[v].apply(lambda s: s.notna().mean()).min() > 0.95]
        graphe("Quelles informations manquent selon le pays ?",
               "savoir quelles variables seront exploitables dans tous les pays.", fig,
               "variables présentes partout : " + (", ".join(partout) if partout else "aucune")
               + ". Les autres n'existent que dans certaines sources.")

    pos = B[B["cout_moyen_eur"] > 0]
    fig = px.histogram(pos, x=np.log10(pos["cout_moyen_eur"]), color="pays", nbins=120, barmode="overlay",
                       opacity=0.6, color_discrete_map=couleurs, labels={"x": "Coût moyen par sinistre (€, échelle log)"})
    fig.add_vline(x=1, line_dash="dash", line_color="#9A5B0B", annotation_text="10 € (seuil minimum)",
                  annotation_position="top left")
    if len(pos):
        p995 = pos["cout_moyen_eur"].quantile(0.995)
        fig.add_vline(x=np.log10(p995), line_dash="dash", line_color="#B5485D",
                      annotation_text=f"{euros(p995)} (extrêmes)", annotation_position="top right")
    fig.update_xaxes(tickvals=[0, 1, 2, 3, 4, 5, 6], ticktext=["1 €", "10 €", "100 €", "1 k€", "10 k€", "100 k€", "1 M€"])
    neg = int((B["cout_total_eur"] <= 0).sum())
    graphe("Les coûts aberrants sont-ils nombreux par rapport à la masse des sinistres ?",
           "situer les coûts minuscules et extrêmes avant de fixer les seuils de nettoyage.", fig,
           f"la grande majorité des sinistres coûte entre 100 € et 10 000 €. {nombre(neg)} lignes ont un coût négatif ou nul "
           "(non visibles sur l'échelle log) et seront retirées.", alerte=neg > 0, hauteur=360)

    with st.expander("Voir des exemples de lignes anormales"):
        choix = st.selectbox("Type d'anomalie", [ANOMALIES[c][0] for c in cols_anom])
        c = next(k for k in cols_anom if ANOMALIES[k][0] == choix)
        st.dataframe(B.loc[B[c], ["pays", "source", "age_conducteur", "age_vehicule", "puissance_ch", "exposition",
                                  "nb_sinistres", "cout_total_eur", "cout_moyen_eur"]].head(200),
                     hide_index=True, use_container_width=True)

# ================================================================== 2. DONNÉES NETTOYÉES
with onglet_propre:
    med = P.groupby("pays")["cout_moyen_eur"].median().sort_values()
    kpis([("Sinistres propres", nombre(len(P)), f"{P['pays'].nunique()} pays"),
          ("Coût médian", euros(P["cout_moyen_eur"].median()), "par sinistre"),
          ("Coût moyen", euros(P["cout_moyen_eur"].mean()), "tiré vers le haut par les gros sinistres"),
          ("Sinistres extrêmes", nombre(P["sinistre_extreme"].sum()), "gardés mais repérés")])

    g1, g2 = st.columns(2)
    with g1:
        fig = px.box(P, x="pays", y="cout_moyen_eur", color="pays", log_y=True, points=False,
                     color_discrete_map=couleurs, category_orders={"pays": list(med.index)},
                     labels={"cout_moyen_eur": "Coût moyen par sinistre (€, log)", "pays": ""})
        fig.update_layout(showlegend=False)
        graphe("Le coût d'un sinistre dépend-il du pays ?",
               "justifier la colonne « pays » et l'harmonisation des montants.", fig,
               f"le coût médian va de {euros(med.iloc[0])} ({med.index[0]}) à {euros(med.iloc[-1])} ({med.index[-1]}) : "
               "le pays doit être une variable du modèle." if len(med) > 1 else "")
    with g2:
        fig = px.histogram(P, x="log_cout", nbins=80, color_discrete_sequence=[ACCENT],
                           labels={"log_cout": "log(coût en €)"})
        fig.add_vline(x=np.log(P["cout_moyen_eur"].median()), line_dash="dash", line_color=ENCRE,
                      annotation_text="médiane")
        graphe("Quelle forme a la variable à prédire ?",
               "choisir la bonne transformation de la cible avant la modélisation.", fig,
               "en échelle log, la distribution devient presque symétrique : on modélisera le log du coût, "
               "pas le coût brut.")

    g1, g2 = st.columns(2)
    with g1:
        m = mediane_par_tranche(P, "age_conducteur")
        fig = px.line(m, x="x", y="cout", color="pays", markers=True, color_discrete_map=couleurs,
                      labels={"x": "Âge du conducteur", "cout": "Coût médian (€)"})
        graphe("Le coût varie-t-il avec l'âge du conducteur ?",
               "vérifier que l'âge est une variable utile pour prédire le coût.", fig,
               "si les courbes descendent avec l'âge, les jeunes conducteurs ont des sinistres plus coûteux.")
    with g2:
        m = mediane_par_tranche(P, "puissance_ch")
        fig = px.line(m, x="x", y="cout", color="pays", markers=True, color_discrete_map=couleurs,
                      labels={"x": "Puissance (ch)", "cout": "Coût médian (€)"})
        graphe("Les véhicules puissants coûtent-ils plus cher en sinistre ?",
               "vérifier que la puissance apporte de l'information au modèle.", fig,
               "disponible seulement pour les pays où la puissance est connue en chevaux.")

    g1, g2 = st.columns(2)
    with g1:
        m = mediane_par_tranche(P, "bonus_malus", n=6)
        fig = px.line(m, x="x", y="cout", color="pays", markers=True, color_discrete_map=couleurs,
                      labels={"x": "Bonus-malus (échelle propre à chaque pays)", "cout": "Coût médian (€)"})
        graphe("Le bonus-malus est-il lié au coût des sinistres ?",
               "décider si le bonus-malus doit être harmonisé entre pays ou gardé par pays.", fig,
               "les échelles diffèrent (France 50-230, Belgique 0-22, Suède 1-7) : on compare les tendances, pas les valeurs.")
    with g2:
        dispo = P.groupby("pays")[list(VARIABLES)].apply(
            lambda d: d.notna().mean() * 100 * (d.astype(str) != "inconnu").mean()).rename(columns=VARIABLES)
        fig = px.imshow(dispo.T.round(0), color_continuous_scale=["#FFFFFF", "#9FD8C7", ACCENT], aspect="auto",
                        text_auto=".0f", zmin=0, zmax=100, labels=dict(color="% renseigné"))
        graphe("Quelles variables pourra-t-on utiliser pour prédire ?",
               "choisir les variables d'entrée du modèle commun à tous les pays.", fig,
               "un modèle commun ne pourra utiliser que les variables renseignées partout ; "
               "les autres serviront aux modèles par pays.")

    # --- Aperçu des données qui serviront à la modélisation
    st.subheader("Aperçu des données utilisées pour la modélisation")
    st.caption("Ce sont exactement les lignes du fichier data/clean/sinistres_europe.parquet, "
               "avec les filtres de la barre latérale.")
    DICO = {
        "pays": "Pays de la source", "type": "auto ou moto", "source": "Jeu de données d'origine",
        "age_conducteur": "Âge du conducteur (ans)", "jeune_conducteur": "Moins de 26 ans",
        "sexe": "H / F / inconnu", "age_vehicule": "Âge du véhicule (ans)", "puissance_ch": "Puissance (chevaux)",
        "carburant": "essence, diesel, ou code d'origine", "usage": "Usage du véhicule",
        "zone": "Région, province, code postal ou zone", "bonus_malus": "Bonus-malus (échelle du pays)",
        "exposition": "Durée du contrat sur l'année", "nb_sinistres": "Nombre de sinistres du contrat",
        "cout_total_eur": "Coût total des sinistres (€)", "cout_moyen_eur": "VARIABLE À PRÉDIRE : coût moyen par sinistre (€)",
        "log_cout": "Logarithme du coût moyen (cible transformée)", "sinistre_extreme": "Coût au-delà du 99,5e centile",
    }
    c1, c2, c3 = st.columns([1, 1, 2])
    nb_lignes = c1.selectbox("Nombre de lignes", [20, 50, 100, 500], index=1)
    ordre = c2.selectbox("Ordre", ["Échantillon aléatoire", "Coût décroissant", "Coût croissant"])
    colonnes = c3.multiselect("Colonnes affichées", list(DICO), default=[
        "pays", "type", "age_conducteur", "sexe", "age_vehicule", "puissance_ch", "carburant",
        "zone", "bonus_malus", "nb_sinistres", "cout_moyen_eur"])
    if ordre == "Échantillon aléatoire":
        apercu = P.sample(min(nb_lignes, len(P)), random_state=42) if len(P) else P
    else:
        apercu = P.sort_values("cout_moyen_eur", ascending=(ordre == "Coût croissant")).head(nb_lignes)
    st.dataframe(apercu[colonnes or list(DICO)], hide_index=True, use_container_width=True,
                 column_config={"cout_moyen_eur": st.column_config.NumberColumn("cout_moyen_eur", format="%.0f €"),
                                "cout_total_eur": st.column_config.NumberColumn("cout_total_eur", format="%.0f €"),
                                "puissance_ch": st.column_config.NumberColumn("puissance_ch", format="%.0f")})
    with st.expander("Signification des colonnes"):
        st.dataframe(pd.DataFrame({"Colonne": list(DICO), "Contenu": list(DICO.values()),
                                   "% renseigné": [round(100 * P[c].notna().mean() *
                                                         (P[c].astype(str) != "inconnu").mean(), 1) if len(P) else 0
                                                   for c in DICO]}),
                     hide_index=True, use_container_width=True)

# ================================================================== 3. AVANT / APRÈS
with onglet_avap:
    nb_b, nb_p = B.groupby("pays").size(), P.groupby("pays").size()
    comp = pd.DataFrame({"Avant": nb_b, "Après": nb_p}).fillna(0)
    comp["% retiré"] = (100 * (1 - comp["Après"] / comp["Avant"])).round(2)
    kpis([("Avant nettoyage", nombre(comp["Avant"].sum()), "lignes"),
          ("Après nettoyage", nombre(comp["Après"].sum()), "sinistres"),
          ("Lignes retirées", nombre(comp["Avant"].sum() - comp["Après"].sum()),
           f"{100 * (1 - comp['Après'].sum() / max(comp['Avant'].sum(), 1)):.2f} % du total"),
          ("Médiane avant → après", f"{euros(B.loc[B['cout_moyen_eur'] > 0, 'cout_moyen_eur'].median())} → "
                                    f"{euros(P['cout_moyen_eur'].median())}", "le centre ne bouge presque pas")])

    g1, g2 = st.columns(2)
    with g1:
        long = comp[["Avant", "Après"]].reset_index(names="pays").melt("pays", var_name="état", value_name="lignes")
        fig = px.bar(long, x="pays", y="lignes", color="état", barmode="group",
                     color_discrete_map={"Avant": "#C9CED6", "Après": ACCENT}, log_y=True,
                     labels={"lignes": "Lignes (échelle log)", "pays": ""})
        top = comp["% retiré"].idxmax() if len(comp) else ""
        graphe("Combien de lignes le nettoyage retire-t-il dans chaque pays ?",
               "vérifier que le nettoyage ne vide pas un pays de ses données.", fig,
               f"c'est en {top} que le nettoyage retire le plus ({comp['% retiré'].max():.1f} % des lignes)." if top else "")
    with g2:
        etapes = pd.DataFrame([e for src, es in rapport["sources"].items() for e in es])
        # On ne compte que les règles de nettoyage (pas la sélection des contrats avec sinistre ni la jointure)
        par_etape = (etapes[(etapes["retirees"] > 0) & (~etapes["etape"].isin([0, 1, 4]))]
                     .groupby("nom")["retirees"].sum().sort_values().reset_index())
        fig = px.bar(par_etape, x="retirees", y="nom", orientation="h", color_discrete_sequence=["#B5485D"],
                     labels={"retirees": "Lignes retirées", "nom": ""})
        graphe("Quelle règle de nettoyage a le plus d'impact ?",
               "justifier chaque règle dans le rapport par son effet réel.", fig,
               (f"la règle « {par_etape.iloc[-1]['nom']} » retire le plus de lignes "
                f"({nombre(par_etape.iloc[-1]['retirees'])})." if len(par_etape) else ""))

    av = B[B["cout_moyen_eur"] > 0].assign(état="Avant")[["cout_moyen_eur", "état"]]
    ap = P.assign(état="Après")[["cout_moyen_eur", "état"]]
    both = pd.concat([av, ap])
    fig = px.histogram(both, x=np.log10(both["cout_moyen_eur"]), color="état", nbins=120, barmode="overlay",
                       opacity=0.6, histnorm="percent", color_discrete_map={"Avant": "#9AA3AF", "Après": ACCENT},
                       labels={"x": "Coût moyen par sinistre (€, échelle log)"})
    fig.update_xaxes(tickvals=[0, 1, 2, 3, 4, 5, 6], ticktext=["1 €", "10 €", "100 €", "1 k€", "10 k€", "100 k€", "1 M€"])
    graphe("Le nettoyage déforme-t-il la distribution des coûts ?",
           "s'assurer qu'on retire les anomalies sans changer la nature des données.", fig,
           "les deux courbes se superposent sauf sous 10 € : seules les anomalies ont été retirées.", hauteur=340)

    st.dataframe(comp.assign(**{"Médiane avant (€)": B[B["cout_moyen_eur"] > 0].groupby("pays")["cout_moyen_eur"].median().round(0),
                                "Médiane après (€)": P.groupby("pays")["cout_moyen_eur"].median().round(0)}),
                 use_container_width=True)

# ================================================================== 4. DÉTAIL DU NETTOYAGE
with onglet_detail:
    st.caption("Chaque étape, pour chaque source : nombre de lignes avant, après, et raison.")
    for src, es in rapport["sources"].items():
        e = pd.DataFrame(es).sort_values("etape")
        debut, fin = e["lignes_avant"].iloc[0], e["lignes_apres"].iloc[-1]
        with st.expander(f"{src} · {nombre(debut)} → {nombre(fin)} lignes"):
            st.dataframe(e[["etape", "nom", "lignes_avant", "lignes_apres", "retirees", "detail"]]
                         .rename(columns={"etape": "Étape", "nom": "Règle", "lignes_avant": "Avant",
                                          "lignes_apres": "Après", "retirees": "Retirées", "detail": "Détail"}),
                         hide_index=True, use_container_width=True)
    st.download_button("Télécharger les données nettoyées (CSV)", P.to_csv(index=False).encode("utf-8"),
                       file_name="sinistres_nettoyes.csv", mime="text/csv")
