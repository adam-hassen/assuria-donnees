# Sinistres détaillés (objectif 3)

Base pour prédire le **coût d'un sinistre** et comparer des modèles de Machine Learning classiques avec des architectures intégrant des LLM. Générée par `src/sinistres_detailles.py` (graine fixe).

- **Sinistres** : 26 444 vrais sinistres de responsabilité civile auto (France, freMTPL2)
- **Coût** : réel, médiane 1 172 €, moyenne 2 266 €
- **Types** : 25 521 matériels, 923 corporels
- **Découpage** : 18 524 entraînement, 3 982 validation, 3 938 test

## Ce qui est réel et ce qui est ajouté

| Origine | Colonnes |
| --- | --- |
| **Réel** (freMTPL2) | coût du sinistre, âge du conducteur, bonus-malus, véhicule (âge, puissance, marque, carburant), zone, densité, région, exposition |
| **Ajouté** (généré, cohérent avec le coût réel) | type de sinistre, circonstances, lieu, moment, météo, blessés, véhicules impliqués, délai de déclaration, **déclaration en texte libre** |

Les données publiques ne décrivent jamais comment l'accident s'est passé. Ces colonnes sont donc générées, selon des règles explicites :
- freMTPL2 ne contient que des sinistres de **responsabilité civile** (l'assuré a causé un dommage à un tiers) ;
- matériel ou corporel est tiré selon la règle de Bayes, à partir des fréquences et coûts moyens publiés par France Assureurs (2025 : RC matériels 26,2 ‰ et 2 155 € en moyenne ; RC corporels 2,7 ‰, coût moyen supposé 20 000 €) et du coût réel du sinistre ;
- les montants très répétés (1 204 €, 1 128,12 €, 1 172 €…) sont des **forfaits de la convention IRSA** entre assureurs : ils sont repérés (`forfait_convention_irsa`) et classés en dégâts matériels ;
- la gravité décrite dans la déclaration suit le coût réel, mais le texte ne donne jamais le montant.

**À dire dans le rapport** : le coût et le profil sont réels ; la description de l'accident est simulée. Les résultats des LLM sur le texte mesurent donc leur capacité à extraire l'information d'une déclaration, pas des déclarations réelles.

## Exemples de déclarations

- *(moyen, coût réel 995 €)* « Bonjour, je déclare un sinistre. Lundi vers 14h, dans une rue de Amiens, je n'ai pas respecté une priorité à un carrefour. Dégâts sur l'avant de l'autre véhicule (pare-choc, calandre). Constat amiable signé sur place. »
- *(blesse_grave, coût réel 54 943 €)* « Sur une route départementale, dimanche vers 7h : j'ai refusé une priorité, l'autre conducteur a été blessé. Le blessé a des séquelles importantes, hospitalisation de plusieurs semaines. Constat amiable rempli avec l'autre conducteur. »
- *(important, coût réel 7 620 €)* « Mardi matin, sur l'autoroute, près d'une sortie, j'ai heurté l'arrière du véhicule qui me précédait. La route était glissante (verglas). Gros dégâts sur l'autre voiture, airbags déclenchés. La police est intervenue. Aucun blessé. »
- *(leger, coût réel 77 €)* « Bonjour, je déclare un sinistre. Vendredi après-midi, sur l'autoroute, j'ai changé de file et accroché un autre véhicule. Il pleuvait. Choc léger, quelques rayures sur la carrosserie de l'autre voiture. Pas de constat, les coordonnées ont été échangées. »

## Colonnes

| Colonne | Origine | Sens |
| --- | --- | --- |
| `id_sinistre, id_contrat` | réel | Identifiants du sinistre et du contrat (freMTPL2) |
| `jeu` | découpage | entrainement (70 %), validation (15 %), test (15 %), par contrat, fixe pour comparer les modèles |
| `age_conducteur` | réel | Âge du conducteur |
| `bonus_malus` | réel | Bonus-malus x 100 (50 = bonus maximal) |
| `age_vehicule` | réel | Âge du véhicule (ans) |
| `puissance_vehicule` | réel | Puissance (classe 4 à 15) |
| `marque_vehicule` | réel | Marque (codée B1 à B14) |
| `carburant` | réel | Regular (essence) ou Diesel |
| `zone` | réel | Type de zone, de A (rural) à F (très dense) |
| `densite_population` | réel | Habitants par km² de la commune |
| `region` | réel | Région (anciennes régions) |
| `exposition` | réel | Durée du contrat sur l'année |
| `nb_sinistres_contrat` | réel | Nombre de sinistres déclarés sur le contrat |
| `type_sinistre` | généré | materiel ou corporel (responsabilité civile) |
| `circonstance` | généré | Comment l'accident s'est produit (collision arrière, refus de priorité, piéton…) |
| `lieu` | généré | agglomeration, route, autoroute, voie_rapide, parking |
| `responsabilite` | généré | totale ou partagee |
| `nb_vehicules` | généré | Véhicules impliqués |
| `tiers_identifie` | généré | Le tiers est connu (constat possible) |
| `nb_blesses` | généré | Nombre de blessés |
| `gravite_decrite` | généré | Gravité décrite dans la déclaration, liée au coût réel |
| `mois, jour_semaine, heure` | généré | Moment de l'accident |
| `meteo` | généré | sec, pluie, brouillard, neige_verglas |
| `delai_declaration_jours` | généré | Jours entre l'accident et la déclaration |
| `description_declaration` | généré | Déclaration de sinistre en texte libre, comme l'écrirait l'assuré (sans le montant) |
| `forfait_convention_irsa` | déduit du réel | Montant forfaitaire de la convention d'indemnisation entre assureurs |
| `cout_sinistre_eur` | réel | **Variable à prédire** : coût du sinistre (€) |
| `log_cout` | réel | Logarithme du coût |
| `sinistre_grave` | réel | Coût au-dessus du 95e centile (4 765 €) |

## Ce que permet cette base pour l'objectif 3

1. **Modèle classique** : prédire `log_cout` à partir des colonnes du contrat et du sinistre (CatBoost, GLM…).
2. **Petit LLM local** : lire `description_declaration` et en extraire les variables (type, circonstance, gravité, blessés…).
3. **Architecture hybride** : variables extraites par le petit LLM + modèle de prédiction, puis explication par un gros LLM.
4. **Comparaison** sur le jeu `test` : erreur (MAE, RMSE sur le log), calibration, robustesse, latence et coût.

## Utilisation

```python
import pandas as pd
df = pd.read_parquet("sinistres_detailles.parquet")
train, test = df[df.jeu == "entrainement"], df[df.jeu == "test"]
```
