# AssurIA · Données du projet

Collecte automatique des deux jeux de données européens du projet, auto et moto :

- **Sinistres** (objectif 3) : pour prédire le coût d'un sinistre ;
- **Offres d'assurance** (objectif 1) : pour proposer à l'assuré les offres qui lui correspondent. Description : [`data/clean/offres/README.md`](data/clean/offres/README.md).

Projet ENSIM 5A · Omar El-Moujahid, Adam Hassen, Ismail Achibat · Encadrant : Meysam Shamsi

## Organisation

```
config/sources.yaml          liste des sources et taux de conversion
config/offres.yaml           liste des offres d'assurance suivies (liens vers les documents IPID)
src/offres.py                collecte les documents d'offres et construit le fichier des offres
src/collecte.py              télécharge les sources et détecte les nouvelles versions
src/nettoyage.py             nettoie, harmonise et fusionne en un seul fichier
dashboard/app.py             dashboard Streamlit (lit les données directement dans ce dépôt)
data/raw/                    données brutes (Parquet) + manifest.json
data/raw/manuel/             fichiers à déposer à la main (Espagne)
data/raw/offres/              documents d'offres (PDF) + manifest.json
data/clean/offres/           offres_europe.parquet / .json + README
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

Le workflow `pipeline-offres.yml` fait de même pour les offres d'assurance (chaque lundi, ou dès que
`config/offres.yaml` change). Pour suivre une nouvelle offre, il suffit d'ajouter son lien dans ce fichier.

Les deux jeux sont recopiés automatiquement dans le dépôt global du projet
[assuria-projet](https://github.com/adam-hassen/assuria-projet), dossier `data/`.

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
