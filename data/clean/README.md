# Jeu de données : sinistres auto et moto en Europe

Premier jeu de données du projet AssurIA (objectif 3 : prédiction du coût d'un sinistre).
Ce fichier est **généré automatiquement** à chaque mise à jour des données.

- **Mis à jour le** : 21/10/2026 12:00 (UTC)
- **Sinistres** : 251 620 sinistres nettoyés (253 371 lignes brutes)
- **Pays** : Belgique, France, Italie, Norvège, Suède
- **Variable à prédire** : `cout_moyen_eur`, coût moyen par sinistre en euros
- **Format** : Parquet (`pd.read_parquet(...)`)

## Fichiers

| Fichier | Contenu |
| --- | --- |
| `sinistres_europe.parquet` | Données nettoyées, prêtes pour la modélisation |
| `sinistres_bruts.parquet` | Données avant nettoyage, avec une colonne par type d'anomalie (`anom_*`) |
| `rapport_nettoyage.json` | Lignes avant / après chaque étape de nettoyage, par source |

## Sources

| Source | Pays | Type | Sinistres nettoyés | Coût médian | Devise d'origine |
| --- | --- | --- | --- | --- | --- |
| `be_bemtpl97` | Belgique | auto | 18 151 | 545 € | EUR |
| `fr_frempl` | France | auto | 15 875 | 980 € | EUR |
| `fr_fremtpl2` | France | auto | 24 898 | 1 172 € | EUR |
| `it_eumtpl` | Italie | auto | 183 618 | 1 425 € | EUR |
| `no_norauto` | Norvège | auto | 8 416 | 2 004 € | NOK |
| `se_swmotorcycle` | Suède | moto | 662 | 960 € | SEK |

Origine : [CASdatasets](https://github.com/dutangc/CASdatasets) (C. Dutang et A. Charpentier, licence GPL ≥ 2). Portefeuille espagnol : [Mendeley Data](https://doi.org/10.17632/5cxyb5fp4f.2), pas encore intégré.

## Colonnes

| Colonne | Contenu | % renseigné |
| --- | --- | --- |
| `pays` | Pays de la source | 100 % |
| `type` | auto ou moto | 100 % |
| `source` | Jeu de données d'origine | 100 % |
| `id_contrat` | Identifiant du contrat dans la source | 100 % |
| `annee` | Année du contrat, si connue | 14 % |
| `age_conducteur` | Âge du conducteur (ans) | 97 % |
| `jeune_conducteur` | Conducteur de moins de 26 ans | 100 % |
| `sexe` | H, F ou inconnu | 90 % |
| `age_vehicule` | Âge du véhicule (ans) | 19 % |
| `puissance_ch` | Puissance (chevaux) | 80 % |
| `carburant` | essence, diesel, électrique, gpl, ou code d'origine (Italie) | 92 % |
| `usage` | Usage du véhicule | 90 % |
| `zone` | Région, province, code postal ou type de zone selon le pays | 98 % |
| `bonus_malus` | Bonus-malus, dans l'échelle propre à chaque pays | 24 % |
| `exposition` | Durée du contrat sur l'année (1 = année complète) | 100 % |
| `nb_sinistres` | Nombre de sinistres du contrat | 100 % |
| `cout_total_eur` | Coût total des sinistres (€) | 100 % |
| `cout_moyen_eur` | **Variable à prédire** : coût moyen par sinistre (€) | 100 % |
| `log_cout` | Logarithme du coût moyen (cible transformée) | 100 % |
| `sinistre_extreme` | Coût au-delà du 99,5e centile de sa source (gardé, mais repéré) | 100 % |
| `periode_source` | Année relative fournie par la source italienne (7, 8, 9) | 73 % |

## Coût par pays

| Pays | Sinistres | Coût médian | Coût moyen |
| --- | --- | --- | --- |
| Belgique | 18 151 | 545 € | 1 317 € |
| France | 40 773 | 1 136 € | 2 178 € |
| Italie | 183 618 | 1 425 € | 2 460 € |
| Norvège | 8 416 | 2 004 € | 2 840 € |
| Suède | 662 | 960 € | 2 632 € |

## Nettoyage appliqué

1. Seuls les contrats avec au moins un sinistre sont gardés.
2. Les coûts négatifs, nuls ou inférieurs à 10 € sont retirés.
3. Le coût moyen par sinistre est calculé partout (coût total ÷ nombre de sinistres).
4. Les valeurs impossibles (âge < 16 ou > 100 ans, puissance ≤ 0, âge du véhicule > 60 ans) sont mises à vide ; les contrats d'exposition nulle sont retirés.
5. Les sinistres au-delà du 99,5e centile sont gardés mais repérés (`sinistre_extreme`).
6. Les libellés sont harmonisés (carburant, sexe) ; les textes manquants deviennent « inconnu ».
7. Les montants sont convertis en euros ; une colonne `pays` et une colonne `type` sont ajoutées.

Lignes retirées au total : 1 751 (0,69 %).

## Limites connues

- Toutes les variables n'existent pas dans tous les pays (voir « % renseigné ») : les valeurs vides sont laissées vides, sans être inventées.
- Les codes de carburant et d'usage italiens ne sont pas documentés par la source : ils sont gardés tels quels.
- La puissance italienne semble exprimée en chevaux fiscaux : à vérifier avant de la comparer aux autres pays.
- Les taux de conversion des couronnes (Norvège, Suède) sont des ordres de grandeur, à valider.
- Les montants ne sont pas encore ajustés à l'inflation (les données vont de 1997 aux années 2000).
- Les échelles de bonus-malus diffèrent selon les pays.

## Utilisation

```python
import pandas as pd
df = pd.read_parquet("sinistres_europe.parquet")
y = df["log_cout"]   # cible transformée
```
