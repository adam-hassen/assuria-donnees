# Base de profils d'assurés auto et moto (Europe, permis du monde entier)

Profils fictifs mais **réalistes**, organisés comme les formulaires de devis des assureurs, pour estimer le prix de chaque offre selon le profil (objectif 1). Générés par `src/profils.py` (graine fixe : la base est toujours la même).

- **Profils** : 100 008 (80 008 auto, 20 000 moto)
- **Profils de référence des vrais prix** : 8 (identifiants `REF_…`), reproduits d'après `data/externe/offres_auto_france/auto_prices.csv` pour caler le simulateur
- **Pays de résidence** : 20 (France 26 946, Allemagne 11 554, Italie 9 450, Espagne 8 331, Royaume-Uni 6 266, Belgique 4 338, Pays-Bas 4 331, Pologne 4 194, Portugal 3 262, Autriche 2 802, Suisse 2 795, Roumanie 2 293, Grèce 2 223, Irlande 2 207, Suède 2 154, Norvège 1 686, Tchéquie 1 672, Danemark 1 628, Finlande 1 184, Luxembourg 692)
- **Villes réelles** : 174
- **Pays d'obtention du permis** : 62 (86 010 dans le pays, 4 958 UE/EEE, 9 040 hors UE)
- **Champs** : 68, dans l'ordre d'un formulaire de devis
- **Contrôles de cohérence** : aucun problème

## Organisation

| Bloc du formulaire | Champs |
| --- | --- |
| Conducteur | âge, sexe, situation familiale, enfants, profession, pays, ville, code postal, région, type de zone, devise, logement |
| Permis | type, ancienneté, date, conduite accompagnée, pays d'obtention, statut (même pays, UE, hors UE), échange, suspension |
| Antécédents | déjà assuré, années assuré, bonus-malus (équivalent français et système du pays), années sans sinistre, sinistres, bris de glace, résiliation, condamnation |
| Véhicule | marque et modèle réels, catégorie, énergie, puissance, classe de prix, valeur, âge, achat, antivol |
| Usage | usage, kilométrage, stationnement la nuit, conducteur secondaire |
| Couverture souhaitée | formule, franchise, options, budget, paiement |

Le détail de chaque champ (question du formulaire, valeurs possibles) est dans `dictionnaire.csv`.

## Règles de cohérence

- Permis B à l'âge minimal du pays d'obtention (16 aux États-Unis, 17 en France, Allemagne, Royaume-Uni…, 18 ailleurs) ; permis moto selon la catégorie (AM selon le pays, A1 16 ans, A2 18 ans, A 20 ans) ; 125 cm3 avec permis B selon la règle du pays.
- Bonus-malus : coefficient selon la règle française pour tous (1,00 au départ, x 0,95 par an sans sinistre, x 1,25 par sinistre, 0,50 à 3,50), pour comparer, et niveau dans le système du pays (classe di merito, SF-Klasse, degré belge, Stufe, trede…, règles simplifiées).
- Permis hors UE : souvent sans relevé d'assurance dans le nouveau pays (jamais assuré ici), permis pas toujours échangé.
- Taux de change approximatifs (2026) : montants donnés en euros et en devise locale.
- Pas de sinistre sans avoir été assuré ; pas plus d'années d'assurance que d'années de permis.
- Profession, usage et kilométrage liés (VTC : usage vtc et 60 000 km/an ; retraité : usage privé…).
- Formule souhaitée liée au véhicule (récent, cher ou en location : tous risques).
- Valeur actuelle = prix neuf x 0,85 par année d'âge. Le sexe est gardé pour information mais ne doit pas servir au prix (interdit dans l'UE).

## Couverture (extrait)

| Champ | Valeur | Profils |
| --- | --- | --- |
| tranche_age | 14-17 | 1 864 |
| tranche_age | 18-20 | 8 510 |
| tranche_age | 21-25 | 13 906 |
| tranche_age | 26-30 | 12 207 |
| tranche_age | 31-40 | 17 196 |
| tranche_age | 41-50 | 15 127 |
| tranche_age | 51-60 | 12 842 |
| tranche_age | 61-70 | 9 685 |
| tranche_age | 71-80 | 5 801 |
| tranche_age | 81+ | 2 870 |
| annees_permis | 0 | 9 381 |
| annees_permis | 1-2 | 11 962 |
| annees_permis | 11-20 | 18 923 |
| annees_permis | 21+ | 37 425 |
| annees_permis | 3-5 | 10 340 |
| annees_permis | 6-10 | 11 977 |
| coefficient_bonus_malus | 0,50 | 40 541 |
| coefficient_bonus_malus | 0,51-0,70 | 13 214 |
| coefficient_bonus_malus | 0,71-0,95 | 21 222 |
| coefficient_bonus_malus | 0,96-1,00 | 18 089 |
| coefficient_bonus_malus | 1,01-1,50 | 5 248 |
| coefficient_bonus_malus | > 1,50 | 1 694 |
| pays_residence | France | 26 946 |
| pays_residence | Allemagne | 11 554 |
| pays_residence | Italie | 9 450 |
| pays_residence | Espagne | 8 331 |
| pays_residence | Royaume-Uni | 6 266 |
| pays_residence | Belgique | 4 338 |
| pays_residence | Pays-Bas | 4 331 |
| pays_residence | Pologne | 4 194 |
| pays_residence | Portugal | 3 262 |
| pays_residence | Autriche | 2 802 |
| pays_residence | Suisse | 2 795 |
| pays_residence | Roumanie | 2 293 |
| pays_residence | Grèce | 2 223 |
| pays_residence | Irlande | 2 207 |
| pays_residence | Suède | 2 154 |
| pays_residence | Norvège | 1 686 |
| pays_residence | Tchéquie | 1 672 |
| pays_residence | Danemark | 1 628 |
| pays_residence | Finlande | 1 184 |
| pays_residence | Luxembourg | 692 |
| statut_permis | meme_pays | 86 010 |
| statut_permis | hors_UE | 9 040 |
| statut_permis | UE_EEE | 4 958 |
| type_zone | grande_ville | 25 687 |
| type_zone | urbain | 22 965 |
| type_zone | rural | 17 931 |
| type_zone | periurbain | 16 786 |
| type_zone | metropole | 16 639 |
| categorie_vehicule | citadine | 19 106 |
| categorie_vehicule | suv | 14 926 |
| categorie_vehicule | compacte | 11 119 |
| categorie_vehicule | mini | 8 252 |
| categorie_vehicule | premium | 8 138 |
| categorie_vehicule | sportive | 7 034 |
| categorie_vehicule | familiale | 5 519 |
| categorie_vehicule | utilitaire | 4 302 |
| categorie_vehicule | roadster | 3 711 |
| categorie_vehicule | scooter_125 | 2 945 |
| categorie_vehicule | maxi_scooter | 2 284 |
| categorie_vehicule | roadster_a2 | 2 238 |
| categorie_vehicule | scooter_50 | 2 177 |
| categorie_vehicule | trail | 2 130 |
| categorie_vehicule | berline | 1 594 |
| categorie_vehicule | cabriolet | 1 537 |
| categorie_vehicule | moto_125 | 1 471 |
| categorie_vehicule | custom | 774 |
| categorie_vehicule | gt | 751 |
| formule_souhaitee | tous_risques | 72 260 |
| formule_souhaitee | tiers | 15 106 |
| formule_souhaitee | tiers_plus | 12 642 |

Toutes les valeurs de tous les champs : `couverture.csv`.

## Utilisation

```python
import pandas as pd
profils = pd.read_parquet("profils.parquet")
jeunes = profils[(profils.annees_permis < 3) & (profils.type_vehicule == "auto")]
```
