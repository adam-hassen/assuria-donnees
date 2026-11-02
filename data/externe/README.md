# Données complémentaires (objectifs 1 et 3)

Données préparées par l'équipe à partir de sources publiques, ajoutées le 02/11/2026.
Elles ne sont pas produites par le pipeline automatique : elles se mettent à jour à la main.

## `offres_auto_france/` : offres d'assurance auto françaises structurées (objectif 1)

13 produits réels de 11 assureurs (L'olivier, Luko by Allianz Direct, Macif, MAAF, MAIF, Matmut, BNP Paribas,
Direct Assurance, Suravenir, L'Équité, Pacifica…), extraits de leurs documents officiels (IPID), et des **vrais prix**
relevés sur un comparateur (Selectra) et sur les sites des assureurs, pour des profils décrits.

| Fichier | Contenu | Lignes |
| --- | --- | --- |
| `auto_products.csv` | Les produits : assureur, nom, document source (lien + empreinte sha256), date, franchises, délais de déclaration | 13 |
| `auto_guarantee_types.csv` | Le dictionnaire des garanties (code, libellé, famille) | 25 |
| `auto_product_guarantees.csv` | Les garanties de chaque produit : incluse ou en option, plafond en €, citation du document | 243 |
| `auto_product_conditions.csv` | Les exclusions et restrictions de chaque produit | 104 |
| `auto_offer_levels.csv` | Ce que chaque produit permet en tiers, tiers + et tous risques, et les options à ajouter | 39 |
| `auto_prices.csv` | **Vrais prix** (€/mois) par assureur, formule et profil, avec la description complète du profil, la source et la date | 81 |
| `auto_price_from.csv` | Prix d'entrée (« à partir de ») par assureur et niveau | 20 |
| `market_auto_guarantee_stats.csv` | Statistiques du marché français (France Assureurs) : fréquence et coût moyen des sinistres par garantie, prime moyenne, taux de souscription | 25 |

Les tables se relient par `product_id` (produits) et `code` (types de garanties).

Profils des vrais prix (`profile_key`) : bonus_experienced (50 ans, bonus 0,50, Clio, Nantes), young_driver (22 ans,
permis 2024), malus, low_mileage (6 000 km/an), electric_vehicle (Peugeot e-208), cancelled (résilié), vtc_driver,
age_17, insurer_example (exemple publié par l'assureur).

## `fremtpl2/` : freMTPL2, version complète (objectif 3)

Le jeu français freMTPL2 dans sa version OpenML (678 013 contrats), en complément de la version CASdatasets
utilisée par le pipeline (677 991 contrats, `data/raw/freMTPL2freq.parquet`).

| Fichier | Contenu |
| --- | --- |
| `fremtpl2_policies.parquet` | Un contrat par ligne, avec le nombre de sinistres, le nombre de sinistres ayant un montant et le coût total |
| `fremtpl2_claims.parquet` | Un sinistre par ligne (26 444) avec son montant |
| `fremtpl2_claims_orphans.csv` | 195 sinistres de 6 contrats absents du fichier des contrats (anomalie connue du jeu) |

À noter : 34 060 contrats déclarent au moins un sinistre, mais seuls 24 944 ont un montant.
