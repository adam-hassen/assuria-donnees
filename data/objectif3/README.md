# Sinistres détaillés (objectif 3)

Base pour prédire le **coût d'un sinistre** et comparer des modèles de Machine Learning classiques avec des architectures intégrant des LLM. Générée par `src/sinistres_detailles.py` (graine fixe).

- **Sinistres** : 269 730 vrais sinistres auto et moto, 6 pays, 7 jeux de données publics
- **Coût** : réel, médiane 1 373 €, moyenne 2 234 €
- **Découpage** : 188 838 entraînement, 40 474 validation, 40 418 test
- **Fichiers** : `sinistres_detailles.parquet` (tout) ; `sinistres_detailles_extrait.csv` (50 976 lignes, toutes les sources, pour regarder dans Excel : le CSV complet dépasserait la limite de GitHub)

## Par pays et par source

| Pays | Véhicule | Source | Garanties couvertes | Sinistres | Coût médian |
| --- | --- | --- | --- | --- | --- |
| Belgique | auto | `be_bemtpl97` | responsabilite civile | 18 151 | 545 € |
| Espagne | auto | `es_portefeuille` | toutes garanties | 15 927 | 163 € |
| Espagne | moto | `es_portefeuille` | toutes garanties | 637 | 85 € |
| France | auto | `fr_frempl` | toutes garanties | 15 875 | 980 € |
| France | auto | `fr_fremtpl2` | responsabilite civile | 26 444 | 1 172 € |
| Italie | auto | `it_eumtpl` | responsabilite civile | 183 618 | 1 425 € |
| Norvège | auto | `no_norauto` | toutes garanties | 8 416 | 2 004 € |
| Suède | moto | `se_swmotorcycle` | dommages vol incendie | 662 | 960 € |

## Types de sinistres (générés)

| Type | Sinistres | Coût médian |
| --- | --- | --- |
| bris_de_glace | 11 577 | 469 € |
| dommages_vehicule | 22 830 | 572 € |
| incendie | 212 | 3 758 € |
| rc_corporel | 12 722 | 3 999 € |
| rc_materiel | 221 619 | 1 373 € |
| vol | 770 | 2 725 € |

## Ce qui est réel et ce qui est ajouté

| Origine | Colonnes |
| --- | --- |
| **Réel** | coût du sinistre, pays, auto ou moto, âge du conducteur, bonus-malus, véhicule (âge, puissance, carburant), zone, exposition |
| **Ajouté** (généré, cohérent avec le coût réel et les garanties de la source) | type de sinistre, circonstances, lieu, ville, moment, météo, blessés, véhicules impliqués, délai, **déclaration en texte libre** |

Les données publiques ne décrivent jamais comment le sinistre s'est passé. Ces colonnes sont donc générées, selon des règles explicites :
- la garantie touchée est tirée parmi celles que couvre la source (responsabilité civile seule pour freMTPL2, la Belgique et l'Italie ; toutes garanties pour freMPL, l'Espagne et la Norvège ; dommages, vol et incendie pour les motos suédoises) ;
- le tirage suit la règle de Bayes, avec les fréquences et coûts moyens publiés par France Assureurs (2025) et le coût réel (coût moyen d'un corporel supposé à 20 000 €, faute de chiffre publié) : les mêmes fréquences servent pour tous les pays (hypothèse) ;
- les montants très répétés de freMTPL2 (1 204 €, 1 128,12 €…) sont des **forfaits de la convention IRSA** : classés en RC matériel ;
- quand une source ne donne que le total de plusieurs sinistres d'un contrat, le coût est la moyenne (`nature_cout`) ;
- la gravité décrite suit le coût réel, mais le texte ne donne jamais le montant ; les déclarations sont en français pour tous les pays.

**À dire dans le rapport** : le coût et le profil sont réels ; la description du sinistre est simulée. Les résultats des LLM sur le texte mesurent leur capacité à extraire l'information d'une déclaration, pas des déclarations réelles. Les colonnes ne sont pas toutes remplies pour toutes les sources (voir le dictionnaire).

## Exemples de déclarations

- *(Espagne, auto, bris_de_glace, coût réel 403 €)* « Bonjour, je déclare un sinistre. Jeudi vers 18h, sur une voie rapide, un gravillon a fissuré mon pare-brise. Il pleuvait. La vitre est à remplacer. »
- *(France, auto, dommages_vehicule, coût réel 398 €)* « Samedi vers 6h, dans une rue de Dijon, j'ai heurté l'arrière d'une voiture. Dégâts légers sur mon véhicule (carrosserie rayée). Constat amiable signé sur place. »
- *(Suède, moto, incendie, coût réel 15 730 €)* « Dans une rue de Malmö, jeudi vers 5h : ma moto a été incendiée pendant la nuit. Il ne reste rien de la moto, les pompiers sont intervenus. J'ai déposé plainte. »
- *(Italie, auto, rc_corporel, coût réel 1 478 €)* « Samedi le matin, à un carrefour en ville, j'ai heurté un cycliste. Il pleuvait. L'autre personne a été légèrement blessée (contusions), vue par un médecin. Pas de constat, les coordonnées ont été échangées. »
- *(Italie, auto, rc_materiel, coût réel 2 150 €)* « Bonjour, je déclare un sinistre. Dimanche le matin, dans une rue de Bologna, le conducteur de mon véhicule n'a pas respecté un feu rouge ou un stop. Le pare-choc et une aile de l'autre véhicule sont abîmés, phare cassé. Pas de constat, les coordonnées ont été échangées. Mon véhicule a aussi une rayure. »
- *(France, auto, vol, coût réel 126 €)* « Bonjour, je déclare un sinistre. Jeudi dans la nuit, sur le parking de mon travail, on a volé des pièces de mon véhicule (roues, catalyseur, équipements). J'ai porté plainte. »

## Colonnes

| Colonne | Origine | Sens |
| --- | --- | --- |
| `id_sinistre, id_contrat` | réel | Identifiants (préfixés par la source) |
| `jeu` | découpage | entrainement (70 %), validation (15 %), test (15 %), par contrat, fixe pour comparer les modèles |
| `pays, type_vehicule, source` | réel | Pays, auto ou moto, jeu de données d'origine |
| `garanties_source` | réel | Garanties couvertes par la source : responsabilite_civile, toutes_garanties, dommages_vol_incendie |
| `annee` | réel | Année du contrat (si connue) |
| `age_conducteur` | réel | Âge du conducteur (vide pour la Norvège) |
| `sexe` | réel | Information seulement (interdit pour le tarif dans l'UE) |
| `bonus_malus, echelle_bonus_malus` | réel | Bonus-malus dans l'échelle de la source (vide pour Italie, Espagne, Norvège) |
| `age_vehicule` | réel | Âge du véhicule (ans) |
| `puissance_vehicule` | réel | Puissance : classe 4 à 15 (freMTPL2) ou chevaux |
| `marque_vehicule` | réel | Marque codée (freMTPL2) |
| `carburant` | réel | essence, diesel ou code de la source |
| `zone` | réel | Zone de la source (A à F en France, code postal en Belgique, province en Italie…) |
| `densite_population, region` | réel | freMTPL2 seulement |
| `exposition` | réel | Durée du contrat sur l'année |
| `nb_sinistres_contrat` | réel | Nombre de sinistres sur le contrat |
| `type_sinistre` | généré | rc_materiel, rc_corporel, dommages_vehicule, bris_de_glace, vol, incendie (parmi les garanties de la source) |
| `circonstance` | généré | Comment le sinistre s'est produit (collision arrière, piéton, gravillon, vol, chute seul…) |
| `lieu, ville` | généré | agglomeration, route, autoroute, voie_rapide, parking, domicile ; ville réelle du pays (déduite de la zone quand c'est possible) |
| `responsabilite` | généré | totale, partagee (RC) ou sans_objet |
| `nb_vehicules` | généré | Véhicules impliqués |
| `tiers_identifie` | généré | Un tiers est connu (constat possible) |
| `nb_blesses` | généré | Nombre de blessés |
| `gravite_decrite` | généré | Gravité décrite dans la déclaration, liée au coût réel |
| `mois, jour_semaine, heure` | généré | Moment du sinistre (motos surtout l'été, vols et incendies la nuit) |
| `meteo` | généré | sec, pluie, brouillard, neige_verglas (fréquences selon le pays) |
| `delai_declaration_jours` | généré | Jours entre le sinistre et la déclaration |
| `description_declaration` | généré | Déclaration de sinistre en français, comme l'écrirait l'assuré (sans le montant) |
| `forfait_convention_irsa` | déduit du réel | Montant forfaitaire de la convention d'indemnisation entre assureurs (freMTPL2) |
| `nature_cout` | réel | individuel, ou moyenne_du_contrat quand la source ne donne que le total de plusieurs sinistres |
| `cout_sinistre_eur` | réel | **Variable à prédire** : coût du sinistre en euros |
| `log_cout` | réel | Logarithme du coût |
| `sinistre_grave` | réel | Coût au-dessus du 95e centile de sa source |

## Ce que permet cette base pour l'objectif 3

1. **Modèle classique** : prédire `log_cout` à partir des colonnes du contrat et du sinistre (CatBoost, GLM…), par pays ou tous pays.
2. **Petit LLM local** : lire `description_declaration` et en extraire les variables (type, circonstance, gravité, blessés…).
3. **Architecture hybride** : variables extraites par le petit LLM + modèle de prédiction, puis explication par un gros LLM.
4. **Comparaison** sur le jeu `test` : erreur (MAE, RMSE sur le log), calibration, robustesse (entre pays), latence et coût.

## Utilisation

```python
import pandas as pd
df = pd.read_parquet("sinistres_detailles.parquet")
train, test = df[df.jeu == "entrainement"], df[df.jeu == "test"]
france_rc = df[(df.source == "fr_fremtpl2")]
```
