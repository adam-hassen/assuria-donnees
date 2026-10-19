# AssurIA · Données de sinistres auto et moto (objectif 3)

Collecte automatique, nettoyage et exploration des données européennes de sinistres auto et moto,
utilisées pour comparer des méthodes de prédiction du coût d'un sinistre.

Projet ENSIM 5A · Omar El-Moujahid, Adam Hassen, Ismail Achibat · Encadrant : Meysam Shamsi

## Organisation

```
config/sources.yaml          liste des sources et taux de conversion
src/collecte.py              télécharge les sources et détecte les nouvelles versions
src/nettoyage.py             nettoie, harmonise et fusionne en un seul fichier
dashboard/app.py             dashboard Streamlit (lit les données directement dans ce dépôt)
data/raw/                    données brutes (Parquet) + manifest.json
data/raw/manuel/             fichiers à déposer à la main (Espagne)
data/clean/                  sinistres_europe.parquet (nettoyé), sinistres_bruts.parquet (brut + anomalies), rapports
.github/workflows/           pipeline automatique (chaque lundi, ou à la demande)
```

## Sources

| Pays | Type | Source |
| --- | --- | --- |
| France | Auto | CASdatasets : freMTPL2, freMPL1-10 |
| Italie | Auto | CASdatasets : euMTPL |
| Belgique | Auto | CASdatasets : beMTPL97 |
| Norvège | Auto | CASdatasets : norauto |
| Suède | Moto | CASdatasets : swmotorcycle |
| Espagne | Auto + moto | Mendeley Data : doi.org/10.17632/5cxyb5fp4f.2 |

CASdatasets : https://github.com/dutangc/CASdatasets (licence GPL ≥ 2).

## Automatisation

Le workflow GitHub Actions `pipeline-donnees.yml` tourne chaque lundi, à chaque modification du code,
ou à la demande (onglet **Actions** → **Run workflow**). Il collecte, nettoie, puis enregistre les
données mises à jour dans le dépôt. Rien à télécharger sur son PC.

## Dashboard

En ligne : déployer `dashboard/app.py` sur Streamlit Community Cloud (share.streamlit.io) depuis ce dépôt.

En local (lit quand même les données du dépôt GitHub) :
```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

## Dashboard : 4 onglets

- **Données brutes et anomalies** : rapport des anomalies, où elles se concentrent, valeurs manquantes par pays.
- **Données nettoyées** : chaque graphe répond à une question utile pour la modélisation.
- **Avant / après nettoyage** : lignes retirées par pays et par règle, effet sur la distribution des coûts.
- **Détail du nettoyage** : chaque étape, pour chaque source.

## Fichier final : `data/clean/sinistres_europe.parquet`

| Colonne | Contenu |
| --- | --- |
| pays, type, source | Origine du sinistre |
| age_conducteur, jeune_conducteur, sexe | Assuré |
| age_vehicule, puissance_ch, carburant, usage | Véhicule |
| zone, bonus_malus, exposition | Contrat |
| nb_sinistres, cout_total_eur | Sinistres du contrat |
| **cout_moyen_eur** | **Variable à prédire** : coût moyen par sinistre en euros |
| log_cout, sinistre_extreme | Log du coût, repère des sinistres > 99,5e centile |

Les étapes de nettoyage et le nombre de lignes retirées à chaque étape sont dans
`data/clean/rapport_nettoyage.json` (et dans l'onglet *Nettoyage* du dashboard).
