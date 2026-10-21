# Jeu de données : offres d'assurance auto et moto en Europe

Deuxième jeu de données du projet AssurIA (objectif 1 : personnaliser les offres d'assurance).
Ce fichier est **généré automatiquement** à chaque collecte.

- **Dernière nouvelle version d'un document** : 2026-10-21
- **Offres** : 31 offres collectées sur 31 suivies
- **Pays** : Allemagne, Belgique, Espagne, France, Italie
- **Format** : Parquet (`offres_europe.parquet`) et JSON lisible (`offres_europe.json`)

## D'où viennent les données

Chaque assureur européen doit publier, pour chaque produit, un **document d'information normalisé** (IPID, « Document d'information sur le produit d'assurance »), imposé par la directive européenne sur la distribution d'assurances ([règlement 2017/1469](https://eur-lex.europa.eu/eli/reg_impl/2017/1469/oj)). Il a le même plan dans tous les pays et toutes les langues, ce qui permet de comparer les offres entre elles.

La liste des documents suivis est dans `config/offres.yaml` du dépôt [assuria-donnees](https://github.com/adam-hassen/assuria-donnees). Pour ajouter une offre, il suffit d'y ajouter son lien.

## Offres par pays

| Pays | Auto | Moto | Total |
| --- | --- | --- | --- |
| Allemagne | 3 | 1 | 4 |
| Belgique | 3 | 2 | 5 |
| Espagne | 3 | 0 | 3 |
| France | 8 | 7 | 15 |
| Italie | 2 | 2 | 4 |

## Garanties citées

| Garantie | Offres qui la citent |
| --- | --- |
| responsabilite civile | 100 % |
| vol | 81 % |
| incendie | 71 % |
| bris de glace | 55 % |
| dommages vehicule | 68 % |
| catastrophes naturelles | 61 % |
| assistance | 81 % |
| protection conducteur | 52 % |
| protection juridique | 65 % |
| equipements | 29 % |
| vehicule remplacement | 42 % |

## Liste des offres

| Pays | Type | Assureur | Produit | Rubriques trouvées |
| --- | --- | --- | --- | --- |
| Allemagne | auto | [ARCD](https://www.arcd.de/fileadmin/Dokumente/Versicherungen/Kfz-Versicherung/produktinformationsblatt-kfz.pdf) | Kfz-Versicherung | 7/9 |
| Allemagne | auto | [Allianz](https://goa-eportale.allianz.de/IPI/D-2/IPID-2001Z0.pdf.open.pdf) | Kfz-Versicherung Smart | 9/9 |
| Allemagne | auto | [Allianz](https://goa-eportale.allianz.de/IPI/D-2/IPID-2002Z0.pdf.open.pdf) | Kfz-Versicherung | 9/9 |
| Allemagne | moto | [Allianz](https://goa-eportale.allianz.de/IPI/D-2/IPID-2009Z0.pdf.open.pdf) | Mopedversicherung | 9/9 |
| Belgique | auto | [AXA Belgium](https://distributorportal.axa.be/fr-be/-/media/axa-documents/library-public/ipid/3/8/c/d/a/Confort%20Auto%20-%20Fiches%20IPID.pdf?rev=e72a16bb015743978fd0a703857733fe) | Confort Auto | 9/9 |
| Belgique | auto | [Hyundai Insurance](https://www.hyundai.com/content/dam/hyundai/downloads/be/lu/pdf/FR_Hy_IPID_Insurance.pdf) | Assurance auto | 6/9 |
| Belgique | auto | [P&V](https://www.pv.be/documents/2579080/0/IPID_495_PV+Auto_FR_DEFweb.pdf/2b84f6f9-5aec-989a-3084-20350cfc497a) | P&V Auto | 9/9 |
| Belgique | moto | [Argenta](https://www.argenta.be/content/dam/argenta/documents/assurer/ipid/IPID%20Assurance%20moto.pdf) | Assurance moto | 9/9 |
| Belgique | moto | [ING Belgique](https://assets.ing.com/m/531a38da1f7d4826/original/ING-motorbike-and-moped-insurance-IPID-FR.pdf) | Assurance moto et cyclomoteur | 8/9 |
| Espagne | auto | [LAM Seguros](https://lam-seguros.com/wp-content/uploads/2025/09/seguro-de-coche-a-todo-riesgo.pdf) | Todo riesgo | 9/9 |
| Espagne | auto | [Mutua Madrileña](https://www.mutua.es/digital/webcontent/1459158692600PID_Autos_Terceros+BC3A1sico_TCB.pdf) | Terceros básico | 9/9 |
| Espagne | auto | [Santander Mapfre](https://www.santandermapfreseguros.es/obtener-documento?entidad=015&sector=200&producto=43&subtipo=5&timestamp=1728604800046) | Seguro de autos | 8/9 |
| France | auto | [ADEP](https://www.adep.com/cms/Paragraphes/an103431/ADEP%20Assurance%20IPID%20ADEP%20Auto.pdf) | ADEP Auto | 8/9 |
| France | auto | [Assu 2000](https://www.assu2000.fr/sites/default/files/documents-legaux/A2_IPID_AUTO.pdf) | Assurance auto | 9/9 |
| France | auto | [Caisse d'Epargne](https://www.img.caisse-epargne.fr/app/uploads/sites/3/2021/10/08170442/2021-03-ipid-auto-part.pdf) | Assurance automobile | 9/9 |
| France | auto | [Direct Assurance](https://directassurance.cdn.axa-contento-118412.eu/directassurance/aed9dfb5-3d46-4669-82ac-273c5d8372af_fiche-ipid-auto-032025.pdf) | Assurance automobile | 9/9 |
| France | auto | [L'olivier Assurance](https://www.lolivier.fr/medias/uploads/2025/07/ipid-loa-tous-risques.pdf) | Auto tous risques (LOA) | 8/9 |
| France | auto | [Matmut](https://www.matmut.fr/services-en-ligne/doc/IPID/ipidauto4d.pdf) | Assurance automobile | 9/9 |
| France | auto | [PRO BTP](https://www.probtp.com/files/live/sites/probtp/files/media/pdf/ipid/ipid-assurance-auto.pdf) | Assurance auto | 7/9 |
| France | auto | [SG (Sogessur)](https://particuliers.sg.fr/static/Particuliers/Home/Assurances/nos-offres/assurance-vehicule/assurance-auto/Ipid_assurance_automobile.pdf) | Assurance automobile | 9/9 |
| France | moto | [AMV](https://www.amv.fr/docs/Docs/IPID_AMV_MOTO_EQ.pdf) | Assurance moto (équipement) | 9/9 |
| France | moto | [AMV](https://www.amv.fr/docs/Docs/IPID_AMV_MOTO_GB.pdf) | Assurance moto | 9/9 |
| France | moto | [MAIF](https://www.maif.fr/files/live/sites/maif-fr/files/pdf/documentation-contractuelle/mobilite/document-information-assurance-moto-loisir.pdf) | Assurance moto (contrat 4+2) | 9/9 |
| France | moto | [Matmut](https://www.matmut.fr/services-en-ligne/doc/IPID/IPID2R.pdf) | Assurance deux-roues | 9/9 |
| France | moto | [Solly Azar](https://www.sollyazar.com/sites/particulier/files/media_fichier/dg-ipid-gbike-moto125quad.pdf) | Moto 125 et quad | 9/9 |
| France | moto | [Solly Azar](https://www.sollyazar.com/sites/particulier/files/media_fichier/DG_IPID_CYCLO_ET_SCOOTER_50.pdf) | Cyclo et scooter 50 | 9/9 |
| France | moto | [Solly Azar (Wakam)](https://www.sollyazar.com/sites/particulier/files/2023-07/moto_motopass_ipid_wakam.pdf) | Motopass | 9/9 |
| Italie | auto | [Quixa](https://www.quixa.it/wp-content/documents/SetInformativi/ed.25.05.2022_Auto_QP.pdf) | Assicurazione auto | 9/9 |
| Italie | auto | [Verti](https://www.santanderconsumer.it/sites/default/files/2022-08/SET%20INFORMATIVO_SANTANDER%20RCauto_Verti%20ed.2022.pdf) | RC auto | 9/9 |
| Italie | moto | [Crédit Agricole Assicurazioni](https://www.ca-assicurazioni.it/media/filer_public/ad/0f/ad0f0423-1f71-4134-8ae3-77ddf53707ce/202601_honda_safe_20_moto.pdf) | Honda Safe 2.0 moto | 9/9 |
| Italie | moto | [Quixa](https://www.quixa.it/wp-content/documents/SetInformativi/ed.15.01.2026_Moto.pdf) | Assicurazione moto | 9/9 |

## Colonnes

| Colonne | Contenu |
| --- | --- |
| `id_offre` | Identifiant de l'offre |
| `pays` | Pays où l'offre est vendue |
| `type` | auto ou moto |
| `assureur` | Compagnie ou distributeur |
| `produit` | Nom du produit |
| `langue` | Langue du document |
| `g_*` | Garantie citée dans « ce qui est assuré » (incluse ou en option) : oui / non |
| `franchise_mentionnee` | Le document parle d'une franchise |
| `franchise_min_eur, franchise_max_eur` | Plus petit et plus grand montant de franchise trouvés (€) |
| `paiement_mensuel` | Paiement mensuel ou fractionné possible |
| `description` | Rubrique « De quel type d'assurance s'agit-il ? » |
| `garanties` | Rubrique « Qu'est-ce qui est assuré ? » |
| `non_assure` | Rubrique « Qu'est-ce qui n'est pas assuré ? » |
| `restrictions` | Rubrique « Y a-t-il des restrictions ? » (franchises, plafonds, exclusions) |
| `zone` | Rubrique « Où suis-je couvert ? » |
| `obligations` | Rubrique « Quelles sont mes obligations ? » |
| `paiement` | Rubrique « Quand et comment payer ? » |
| `duree` | Rubrique « Quand commence et finit la couverture ? » |
| `resiliation` | Rubrique « Comment résilier ? » |
| `rubriques_trouvees` | Nombre de rubriques retrouvées sur 9 (qualité de l'extraction) |
| `prix` | Vide pour l'instant : le prix n'est pas publié, il dépend d'un devis |
| `url_source, fichier_pdf` | Lien d'origine et copie du PDF dans le dépôt (traçabilité) |
| `collecte_le, statut_lien` | Date de la version collectée et état du lien au dernier passage |

## Limites connues

- **Pas de prix** : l'IPID décrit les garanties, pas le tarif, qui dépend d'un devis (âge, véhicule, lieu…).
- Les colonnes `g_*` sont repérées par mots-clés : une garantie citée peut être incluse ou en option.
- Les montants de franchise sont repérés automatiquement près du mot « franchise » : à vérifier pour une offre précise.
- Certains documents sont anciens (date dans le lien) : l'offre actuelle peut avoir changé.
- Les PDF de plus de 4 Mo ne sont gardés que pour leurs 12 premières pages (là où se trouve l'IPID).

## Utilisation

```python
import pandas as pd
offres = pd.read_parquet("offres_europe.parquet")
offres[(offres.pays == "France") & (offres.type == "moto") & offres.g_vol]
```
