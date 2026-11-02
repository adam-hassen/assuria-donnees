# Base de profils d'assurés auto et moto

Profils fictifs mais **réalistes**, organisés comme les formulaires de devis des assureurs français, pour estimer le prix de chaque offre selon le profil (objectif 1). Générés par `src/profils.py` (graine fixe : la base est toujours la même).

- **Profils** : 25 008 (20 008 auto, 5 000 moto)
- **Profils de référence des vrais prix** : 8 (identifiants `REF_…`), reproduits d'après `data/externe/offres_auto_france/auto_prices.csv` pour caler le simulateur
- **Champs** : 56, dans l'ordre d'un formulaire de devis
- **Contrôles de cohérence** : aucun problème

## Organisation

| Bloc du formulaire | Champs |
| --- | --- |
| Conducteur | âge, sexe, situation familiale, enfants, profession, commune, code postal, type de zone, logement |
| Permis | type, ancienneté, date, conduite accompagnée, pays, suspension ou annulation |
| Antécédents | déjà assuré, années assuré, bonus-malus, sinistres responsables et non responsables, bris de glace, résiliation, condamnation |
| Véhicule | marque et modèle réels, catégorie, énergie, puissance, classe de prix, valeur, âge, achat, antivol |
| Usage | usage, kilométrage, stationnement la nuit, conducteur secondaire |
| Couverture souhaitée | formule, franchise, options, budget, paiement |

Le détail de chaque champ (question du formulaire, valeurs possibles) est dans `dictionnaire.csv`.

## Règles de cohérence

- Permis B à partir de 17 ans ; permis moto selon la catégorie (AM 14 ans, A1 16 ans, A2 18 ans, A 20 ans).
- Bonus-malus calculé selon la règle officielle : 1,00 au départ, x 0,95 par année sans sinistre responsable, x 1,25 par sinistre responsable, entre 0,50 et 3,50.
- Pas de sinistre sans avoir été assuré ; pas plus d'années d'assurance que d'années de permis.
- Profession, usage et kilométrage liés (VTC : usage vtc et 60 000 km/an ; retraité : usage privé…).
- Formule souhaitée liée au véhicule (récent, cher ou en location : tous risques).
- Valeur actuelle = prix neuf x 0,85 par année d'âge. Le sexe est gardé pour information mais ne doit pas servir au prix (interdit dans l'UE).

## Couverture (extrait)

| Champ | Valeur | Profils |
| --- | --- | --- |
| tranche_age | 14-17 | 652 |
| tranche_age | 18-20 | 2 119 |
| tranche_age | 21-25 | 3 499 |
| tranche_age | 26-30 | 3 047 |
| tranche_age | 31-40 | 4 294 |
| tranche_age | 41-50 | 3 771 |
| tranche_age | 51-60 | 3 224 |
| tranche_age | 61-70 | 2 343 |
| tranche_age | 71-80 | 1 348 |
| tranche_age | 81+ | 711 |
| annees_permis | 0 | 2 216 |
| annees_permis | 1-2 | 3 122 |
| annees_permis | 11-20 | 4 741 |
| annees_permis | 21+ | 9 282 |
| annees_permis | 3-5 | 2 614 |
| annees_permis | 6-10 | 3 033 |
| coefficient_bonus_malus | 0,50 | 10 596 |
| coefficient_bonus_malus | 0,51-0,70 | 3 491 |
| coefficient_bonus_malus | 0,71-0,95 | 5 560 |
| coefficient_bonus_malus | 0,96-1,00 | 3 592 |
| coefficient_bonus_malus | 1,01-1,50 | 1 325 |
| coefficient_bonus_malus | > 1,50 | 444 |
| type_zone | grande_ville | 7 503 |
| type_zone | urbain | 5 075 |
| type_zone | periurbain | 4 943 |
| type_zone | rural | 4 903 |
| type_zone | metropole | 2 584 |
| categorie_vehicule | citadine | 4 608 |
| categorie_vehicule | suv | 3 628 |
| categorie_vehicule | sportive | 2 697 |
| categorie_vehicule | compacte | 2 185 |
| categorie_vehicule | premium | 2 112 |
| categorie_vehicule | familiale | 1 627 |
| categorie_vehicule | mini | 1 555 |
| categorie_vehicule | utilitaire | 997 |
| categorie_vehicule | trail | 619 |
| categorie_vehicule | roadster_a2 | 614 |
| categorie_vehicule | scooter_125 | 607 |
| categorie_vehicule | berline | 606 |
| categorie_vehicule | scooter_50 | 596 |
| categorie_vehicule | roadster | 591 |
| categorie_vehicule | moto_125 | 584 |
| categorie_vehicule | cabriolet | 541 |
| categorie_vehicule | gt | 282 |
| categorie_vehicule | custom | 281 |
| categorie_vehicule | maxi_scooter | 278 |
| formule_souhaitee | tous_risques | 18 290 |
| formule_souhaitee | tiers | 3 660 |
| formule_souhaitee | tiers_plus | 3 058 |

Toutes les valeurs de tous les champs : `couverture.csv`.

## Utilisation

```python
import pandas as pd
profils = pd.read_parquet("profils.parquet")
jeunes = profils[(profils.annees_permis < 3) & (profils.type_vehicule == "auto")]
```
