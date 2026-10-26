# Simulation des prix des offres d'assurance (objectif 1)

Fichiers **générés automatiquement** par `src/simulateur.py` à chaque mise à jour des offres.

- **Mis à jour le** : 26/10/2026
- **Offres réelles avec un prix de base** : 104 offres, 268 couples offre x formule
- **Profils générés** : 2 049 (dont 25 cas typiques nommés)
- **Prix simulés** : 37 445 devis, dont 31 777 acceptés et 5 668 refusés

## Le principe

Comme un assureur : **prix = prix de base de l'offre x coefficients du profil**.

1. **Prix de base** (`prix_base.parquet`) : le prix de l'offre pour le profil de référence (le « à partir de » affiché par les assureurs : 50 ans, bonus 0,50, citadine récente, ville moyenne). Vrai prix d'entrée publié quand il existe, sinon référence de marché du pays (`config/prix_base.yaml`, chaque chiffre a sa source).
2. **Coefficients appris sur des sinistres réels** (`coefficients.json`) : modèles GLM fréquence x coût, comme les assureurs. Auto : freMTPL2 (677 991 contrats). Moto : swmotorcycle (62 436 contrats).
3. **Règles du marché** : bonus-malus, surprime jeune conducteur, usage, kilométrage, stationnement, franchise, valeur du véhicule (pour la partie dommages), refus des profils hors cible.
4. **Prix final** = partie responsabilité civile x coefficients du profil + partie dommages x coefficients du profil x coefficient du véhicule.

## Fichiers

| Fichier | Contenu |
| --- | --- |
| `prix_base.parquet` | Prix de base par offre réelle et par formule, avec sa source |
| `coefficients.json` | Coefficients appris (âge, puissance, âge du véhicule, zone, énergie) et règles |
| `profils.parquet` | Profils générés : conducteur, permis, véhicule, zone, usage, besoins |
| `devis_simules.parquet` | Un prix simulé par profil x offre x formule, avec le détail des coefficients |
| **`offres_prix_profils.csv` / `.parquet`** | **Le fichier unique** : une ligne = un profil simulé x une offre réelle x une formule. Caractéristiques du profil (`profil_*`), offre et garanties (`offre_*`), prix de base, prix simulé, détail des coefficients, lien de l'offre. Le CSV s'ouvre dans Excel (séparateur « ; ») |

## Les profils couvrent

- 9 pays, auto et moto ; chaque tranche d'âge (18 à 85 ans) croisée avec chaque catégorie de véhicule
- Auto : citadine, compacte, SUV, familiale, premium, sportive, électrique (20 modèles)
- Moto : scooter 50, 125, A2, roadster, trail, sportive, GT, maxi-scooter (11 modèles)
- Permis récent ou ancien, conduite accompagnée, permis national / UE / hors UE, 0 à 3 sinistres
- Zone (rural à métropole), usage (privé, trajet travail, pro), kilométrage, stationnement, franchise

## Contrôle : moyennes simulées et moyennes publiées

| Cas (France) | Moyenne simulée | Moyenne publiée (LeLynx 2026) |
| --- | --- | --- |
| Auto, tous profils | 1 588 €/an | 663 €/an |
| Auto, tiers | 552 €/an | 526 €/an |
| Auto, tous risques | 1 791 €/an | 784 €/an |
| Auto, moins de 3 ans de permis | 2 849 €/an | 1 231 €/an |
| Auto, 65 à 69 ans | 1 181 €/an | 434 €/an |
| Auto, conducteur expérimenté (10 ans de permis ou plus) | 868 €/an | 645 €/an |
| Moto, tous profils | 899 €/an | 634 €/an |

Les profils sont générés pour couvrir tous les cas, pas pour reproduire la population réelle : les moyennes ne doivent être que du même ordre de grandeur. Les moyennes simulées sont plus hautes car les profils risqués (jeunes, voitures puissantes, malus, tous risques sur véhicule cher) y sont volontairement aussi nombreux que les autres.

## Sources des prix de base

| Pays | Méthode | Source |
| --- | --- | --- |
| France | Prix d'entrée médians des assureurs pour un conducteur expérimenté bonussé à 50 % | [lien](https://www.avis-assurances.com/assurances/auto) |
| Belgique | Bas des fourchettes publiées (profil favorable) : RC, mini-omnium, full omnium | [lien](https://callmepower.be/fr/assurance/auto/prix) |
| Pays-Bas | Médiane des 5 primes les moins chères (60 ans, 19 ans sans sinistre, Citroën C1), octobre 2026 | [lien](https://www.overstappen.nl/nieuws/dit-zijn-de-vijf-goedkoopste-autopremies-in-oktober-2026/) |
| Italie | Prix moyen RC auto IVASS 422 € (T2 2026) x 0,485 ; cohérent avec les prix d'entrée publiés (131 à 161 €/an) | [lien](https://www.teleborsa.it/DettaglioNews/239_2026-09-24_TLB/RC-Auto-prezzo-medio-scende-a-422-euro-le-province-che-pagano-di-pi.html) |
| Espagne | Prime moyenne 390 € (mai 2026) x 0,385 ; cohérent avec les prix d'entrée publiés (153 à 171 €/an) | [lien](https://seguros.check24.es/wp-content/uploads/2026/06/NdP_La-prima-media-del-seguro-de-coche-baja-en-mayo-hasta-los-390-euros-un-53-menos-que-hace-un-ano.pdf) |
| Portugal | Prime moyenne 344 €/an (2026) x 0,385 | [lien](https://www.e-konomista.pt/seguro-automovel-mais-caro-em-2026/) |
| Irlande | Prime moyenne 655 € (Banque centrale d'Irlande, S1 2025) x 0,385 | [lien](https://rte.ie/news/business/2026/0331/1566059-average-cost-of-motor-insurance-was-655-last-year/) |
| Allemagne | Haftpflicht moyenne 300 € x 0,485 ; Vollkasko moyenne 550 € x (450 / 784) | [lien](https://versicherungsvergleiche.de/fragen/was-kostet-eine-kfz-versicherung-im-durchschnitt/) |
| Autriche | Prime moyenne 1 004 € x 0,385 (donnée ancienne, durchblicker.at 2015 : à mettre à jour) | [lien](https://www.trend.at/mobilitaet/autoversicherung-vergleich) |

## Limites

- **Ce sont des prix estimés**, pas des devis : les offres sont réelles, mais seul l'assureur donne le prix exact. Toujours afficher le lien vers le devis officiel (`url_offre`).
- Les coefficients viennent de données françaises (auto) et suédoises (moto) : ils sont appliqués à tous les pays.
- Le bonus-malus est le système français, utilisé comme équivalent pour les autres pays.
- La plupart des offres n'ont pas de prix d'entrée publié : elles reçoivent la référence de marché de leur pays.
- Pas de coefficient selon le sexe : interdit dans l'Union européenne depuis 2012.

## Utilisation

```python
import pandas as pd
devis = pd.read_parquet("devis_simules.parquet")
profils = pd.read_parquet("profils.parquet")
# les 5 offres les moins chères pour un profil, dans la formule qu'il souhaite
devis[(devis.id_profil == "P00000") & devis.formule_souhaitee].nsmallest(5, "prix_annuel_estime")
```
