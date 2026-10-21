# Jeu de données : offres d'assurance auto et moto en Europe

Deuxième jeu de données du projet AssurIA (objectif 1 : personnaliser les offres d'assurance).
Ce fichier est **généré automatiquement** à chaque collecte.

- **Dernière nouvelle version d'un document** : 2026-10-21
- **Offres** : 102 offres collectées sur 158 suivies
- **Pays** : Allemagne, Autriche, Belgique, Espagne, France, Irlande, Italie, Pays-Bas, Portugal
- **Format** : Parquet (`offres_europe.parquet`) et JSON lisible (`offres_europe.json`)

## D'où viennent les données

Chaque assureur européen doit publier, pour chaque produit, un **document d'information normalisé** (IPID, « Document d'information sur le produit d'assurance »), imposé par la directive européenne sur la distribution d'assurances ([règlement 2017/1469](https://eur-lex.europa.eu/eli/reg_impl/2017/1469/oj)). Il a le même plan dans tous les pays et toutes les langues, ce qui permet de comparer les offres entre elles.

La liste des documents suivis est dans `config/offres.yaml` du dépôt [assuria-donnees](https://github.com/adam-hassen/assuria-donnees). Pour ajouter une offre, il suffit d'y ajouter son lien. Un robot parcourt aussi les pages « documents » de certains assureurs (`pages_a_explorer`) pour trouver tout seul les nouveaux documents. Un garde-fou ne garde que les documents qui ont le plan IPID et parlent d'un véhicule.

## Offres par pays

| Pays | Auto | Moto | Total |
| --- | --- | --- | --- |
| Allemagne | 6 | 1 | 7 |
| Autriche | 1 | 0 | 1 |
| Belgique | 14 | 10 | 24 |
| Espagne | 8 | 1 | 9 |
| France | 21 | 10 | 31 |
| Irlande | 4 | 0 | 4 |
| Italie | 9 | 8 | 17 |
| Pays-Bas | 1 | 0 | 1 |
| Portugal | 5 | 3 | 8 |

## Garanties citées

| Garantie | Offres qui la citent |
| --- | --- |
| responsabilite civile | 95 % |
| vol | 75 % |
| incendie | 74 % |
| bris de glace | 47 % |
| dommages vehicule | 70 % |
| catastrophes naturelles | 57 % |
| assistance | 69 % |
| protection conducteur | 65 % |
| protection juridique | 66 % |
| equipements | 21 % |
| vehicule remplacement | 30 % |

## Liste des offres

| Pays | Type | Assureur | Produit | Rubriques trouvées |
| --- | --- | --- | --- | --- |
| Allemagne | auto | [ARCD](https://www.arcd.de/fileadmin/Dokumente/Versicherungen/Kfz-Versicherung/produktinformationsblatt-kfz.pdf) | Kfz-Versicherung | 7/9 |
| Allemagne | auto | [Allianz](https://goa-eportale.allianz.de/IPI/D-2/IPID-2006Z0.pdf.open.pdf) | Kfz-Versicherung 2006 | 9/9 |
| Allemagne | auto | [Allianz](https://goa-eportale.allianz.de/IPI/D-2/IPID-2008Z0.pdf.open.pdf) | Kfz-Versicherung 2008 | 9/9 |
| Allemagne | auto | [Allianz](https://goa-eportale.allianz.de/IPI/D-2/IPID-2002Z0.pdf.open.pdf) | Kfz-Versicherung | 9/9 |
| Allemagne | auto | [Allianz](https://goa-eportale.allianz.de/IPI/D-2/IPID-2001Z0.pdf.open.pdf) | Kfz-Versicherung Smart | 9/9 |
| Allemagne | auto | [WGV](https://www.wgv.de/docs/vertragsunterlagen/kfz.pdf) | Kfz-Versicherung | 9/9 |
| Allemagne | moto | [Allianz](https://goa-eportale.allianz.de/IPI/D-2/IPID-2009Z0.pdf.open.pdf) | Mopedversicherung | 9/9 |
| Autriche | auto | [Allianz Österreich](https://www.allianz.at/content/dam/onemarketing/cee/azat/privat_pdf/Mein-Kfz-Paket-MAX.pdf) | Mein Kfz Paket MAX | 9/9 |
| Belgique | auto | [AXA Belgium](https://cdn.website.axa.be/nl-be/-/media/axa-documents/library-public/ipid/3/8/c/d/a/Comfort%20Auto%20(Personenwagen,%20Mobilhome,%20Minibus)%20-%20IPID%20Fiches.pdf?rev=39a27ef263c344f98695978d4af045eb) | Comfort Auto | 9/9 |
| Belgique | auto | [AXA Belgium](https://distributorportal.axa.be/fr-be/-/media/axa-documents/library-public/ipid/3/8/c/d/a/Confort%20Auto%20-%20Fiches%20IPID.pdf?rev=e72a16bb015743978fd0a703857733fe) | Confort Auto | 9/9 |
| Belgique | auto | [Argenta](https://www.argenta.be/content/dam/argenta/documenten/verzekeringen/ipid/IPID%20Autoverzekering.pdf) | Autoverzekering | 9/9 |
| Belgique | auto | [Arval](https://www.arval.be/sites/default/files/inline-files/IPID%20BA.pdf) | Autoverzekering | 8/9 |
| Belgique | auto | [Baloise](https://www.baloise.be/dam/baloise-be/prive/documents/nl/IPID/B9000.MOT.02.26.Fiche-ipid-Mobility_Safe_1_Personenwagens-en-Lichte-vrachtwagens_NL.pdf) | Mobility Safe 1 | 9/9 |
| Belgique | auto | [Hyundai Insurance](https://www.hyundai.com/content/dam/hyundai/downloads/be/lu/pdf/FR_Hy_IPID_Insurance.pdf) | Assurance auto | 6/9 |
| Belgique | auto | [Hyundai Insurance](https://www.hyundai.com/content/dam/hyundai/downloads/be/nl/pdf/NL_Hy_IPID_Insurance.pdf) | Autoverzekering | 9/9 |
| Belgique | auto | [P&V](https://www.pv.be/documents/2579080/0/IPID_495_PV+Auto_FR_0101294_201811.pdf/fea71854-173a-c58d-def1-20006281cb2b) | Document d’information Assurance véhicule automoteur - P&V Auto - 010/1294 - nov | 9/9 |
| Belgique | auto | [P&V](https://www.pv.be/documents/2579080/0/IPID_495_PV+Oldtimer_FR_DEFweb.pdf/05d27820-016a-bf96-5ae3-8945de9f12f2) | Document d’information Assurance véhicule automoteur - P&V Auto - Oldtimer - 010 | 9/9 |
| Belgique | auto | [P&V](https://www.pv.be/documents/2579080/0/IPID_495_PV+Auto_FR_DEFweb.pdf/2b84f6f9-5aec-989a-3084-20350cfc497a) | P&V Auto | 9/9 |
| Belgique | auto | [Vivium](https://www.vivium.be/documents/1091840/1198871/IPID_495_VIV+Auto_FR_DEFweb.pdf/131a7864-14f3-5f23-918b-1d1cbb74097a?t=1741252135635) | Document d’information Assurance véhicule automoteur - VIVIUM Auto - 8.933F - se | 9/9 |
| Belgique | auto | [Vivium](https://www.vivium.be/documents/1091840/1198851/IPID_495_VIV+Oldtimer_FR_DEFweb.pdf/64ebca30-4312-bb00-4cb0-dde9db82fe1f?t=1741252155937) | Document d’information Assurance véhicule automoteur - VIVIUM Auto - Oldtimer -  | 9/9 |
| Belgique | auto | [Vivium](https://www.vivium.be/documents/1091840/0/IPID_495_VIV+Oldtimer_8932F_2025.pdf/5e81ad48-5ca7-30b9-9b57-f57358cc9f12?t=1741171338427) | Document d’information Assurance véhicule automoteur - VIVIUM Auto - Oldtimer -  | 9/9 |
| Belgique | auto | [Vivium](https://www.vivium.be/documents/1091840/0/IPID_495_VIV+Auto_8933F_2025.pdf/de2042a0-8fc0-1c6f-bf9a-2059c1806081?t=1740652956203) | Document d’information Assurance véhicule automoteur - VIVIUM Auto - 8.933F - ja | 9/9 |
| Belgique | moto | [Argenta](https://www.argenta.be/content/dam/argenta/documents/assurer/ipid/IPID%20Assurance%20moto.pdf) | Assurance moto | 9/9 |
| Belgique | moto | [ING Belgique](https://assets.ing.com/m/445285b944971a8d/original/ING-motorbike-and-moped-insurance-IPID-NL.pdf) | Motor- en bromfietsverzekering | 9/9 |
| Belgique | moto | [ING Belgique](https://assets.ing.com/m/531a38da1f7d4826/original/ING-motorbike-and-moped-insurance-IPID-FR.pdf) | Assurance moto et cyclomoteur | 8/9 |
| Belgique | moto | [P&V](https://www.pv.be/documents/2579080/0/IPID_495_PV+Moto_FR_DEFweb.pdf/553317d9-8010-8c82-3d1e-8c89cae73844) | Document d’information Assurance véhicule automoteur - P&V Auto - Moto - 010/129 | 9/9 |
| Belgique | moto | [Vivium](https://www.vivium.be/documents/1091840/1198851/_IPID_495_VIV+Andere+tweewielers_FR_2020.pdf/6060525b-9ad5-5e93-7f79-c3b14299a514?t=1741252155935) | Document d’information Assurance véhicule automoteur - VIVIUM Auto - Autres 2 ro | 9/9 |
| Belgique | moto | [Vivium](https://www.vivium.be/documents/1091840/0/IPID_495_VIV+Moto_8931F_2025.pdf/8bc98d9f-86aa-2874-93db-90ccf29664d5?t=1741171153793) | Document d’information Assurance véhicule automoteur - VIVIUM Auto - Moto - 8.93 | 9/9 |
| Belgique | moto | [Vivium](https://www.vivium.be/documents/1091840/1198851/IPID_495_VIV+Moto_FR_2019.pdf/00d8adbd-1460-2086-7176-01aed26e0769?t=1741252155937) | Document d’information Assurance véhicule automoteur - VIVIUM Auto - Moto - 8.93 | 9/9 |
| Belgique | moto | [Vivium](https://www.vivium.be/documents/1091840/0/IPID_495_VIV+Andere+tweewielers_8974F_2025.pdf/2f7fc3d1-dc9b-d1d0-a42a-35d1e98479e3?t=1741171745228) | Document d’information Assurance véhicule automoteur - VIVIUM Auto - Autres 2 ro | 9/9 |
| Belgique | moto | [Vivium](https://www.vivium.be/documents/1091840/1198851/_IPID_495_VIV+Moto+Oldtimer_FR_2020.pdf/2ca3e480-b0b0-d0a4-c3fe-50add710f66c?t=1741252155936) | Document d’information Assurance véhicule automoteur - VIVIUM Auto - Moto oldtim | 9/9 |
| Belgique | moto | [Vivium](https://www.vivium.be/documents/1091840/0/IPID_495_VIV+Moto+Oldtimer_8976F_2025.pdf/6e463abe-d772-c731-3ba1-9ca0be4eb100?t=1741171913020) | Document d’information Assurance véhicule automoteur - VIVIUM Auto - Moto oldtim | 9/9 |
| Espagne | auto | [AXA España](https://calcular-seguro.axa.es/documents/776357/19370091/Documento_informacion_producto_MotorElige_8972.pdf/a64cddaf-81e9-195e-d252-a2230ef983e9?t=1669128995936) | MotorElige | 9/9 |
| Espagne | auto | [AXA España](https://servicios.axa.es/documents/776357/53007345/Documento_de_informaci%C3%B3n_sobre_el_producto_Coche+360_castellano.pdf/a5c3418a-4ff5-512f-d70f-2e83ce26f69b?t=1766059561113) | Coche 360 | 9/9 |
| Espagne | auto | [Allianz Direct](https://www.allianzdirect.es/dam/documents/IPID-seguro-de-coche.pdf) | Seguro de coche | 9/9 |
| Espagne | auto | [Allianz España](https://www.allianz.es/content/dam/onemarketing/iberolatam/allianz-es/legal/pdf/productos/seguros-auto/auto-plus-terceros.pdf) | Auto Plus terceros | 9/9 |
| Espagne | auto | [Generali España](https://www.generalion.es/documents/13959/21879141/IPID+AUTO/4551add2-0622-057d-799b-3c6d9e38d028) | Seguro autos | 9/9 |
| Espagne | auto | [LAM Seguros](https://lam-seguros.com/wp-content/uploads/2025/09/seguro-de-coche-a-todo-riesgo.pdf) | Todo riesgo | 9/9 |
| Espagne | auto | [Mutua Madrileña](https://www.mutua.es/digital/webcontent/1459158692600PID_Autos_Terceros+BC3A1sico_TCB.pdf) | Terceros básico | 9/9 |
| Espagne | auto | [Santander Mapfre](https://www.santandermapfreseguros.es/obtener-documento?entidad=015&sector=200&producto=43&subtipo=5&timestamp=1728604800046) | Seguro de autos | 8/9 |
| Espagne | moto | [Allianz España](https://www.allianz.es/content/dam/onemarketing/iberolatam/allianz-es/legal/pdf/productos/seguros-moto/ipid-moto-seguro-franquicia.pdf) | Moto con franquicia | 9/9 |
| France | auto | [ADEP](https://www.adep.com/cms/Paragraphes/an103431/ADEP%20Assurance%20IPID%20ADEP%20Auto.pdf) | ADEP Auto | 8/9 |
| France | auto | [AXA France](https://media.axa.fr/content/dam/axa-fr/image/particuliers/auto/documents-informations/auto/pdf-mon-auto-dipa.pdf) | Mon Auto | 9/9 |
| France | auto | [AXA France](https://www.axa.fr/content/dam/axa-fr-convergence/auto/ipid/972723-1121-Dipa-NDA.pdf) | Assurance automobile | 9/9 |
| France | auto | [AXA France](https://www.tea-cerede.com/wp-content/uploads/2023/03/IPID-Prestige-AXA.pdf) | Auto Prestige | 9/9 |
| France | auto | [Allianz France](https://www.best-assurances.com/app/uploads/IPAC_IPID_ALLIANZ_MALUS.pdf) | Auto malussé | 9/9 |
| France | auto | [Allianz France](https://espaceclient.allianz.fr/pdf/tarification/DG/auto/AUTO-MA/COM21405-V0721.pdf) | Assurance automobile | 7/9 |
| France | auto | [Assu 2000](https://www.assu2000.fr/sites/default/files/documents-legaux/A2_IPID_AUTO.pdf) | Assurance auto | 9/9 |
| France | auto | [Caisse d'Epargne](https://www.img.caisse-epargne.fr/app/uploads/sites/3/2021/10/08170442/2021-03-ipid-auto-part.pdf) | Assurance automobile | 9/9 |
| France | auto | [Club Auto MMA](https://www.clubauto-mma.com/libs/pdf/ipid.pdf) | Assurance véhicule | 9/9 |
| France | auto | [Crédit Mutuel](https://www.creditmutuel.fr/fr/guides-et-informations-reglementaires/IPID.html?refipid=AA1AFRFR001) | Assurance automobile | 9/9 |
| France | auto | [Direct Assurance](https://directassurance.cdn.prismic.io/directassurance/aYnxBN0YXLCxVnsa_fiche-ipid-auto-022026.pdf) | Assurance automobile | 9/9 |
| France | auto | [L'olivier Assurance](https://www.lolivier.fr/medias/uploads/2025/07/ipid-loa-tous-risques.pdf) | Auto tous risques (LOA) | 8/9 |
| France | auto | [Luko (Allianz Direct)](https://www.fr.luko.eu/dam/documents/motor/dfcar202606/IPID.pdf) | Assurance automobile | 9/9 |
| France | auto | [MAAF](https://www.maaf.fr/fr/files/live/sites/maaf/files/TECH/Ipids/AUT11001.PDF) | Assurance véhicule | 7/9 |
| France | auto | [MAIF](https://www.maif.fr/files/live/sites/maif-fr/files/pdf/documentation-contractuelle/mobilite/document-information-assurance-auto-vam.pdf) | Auto VAM | 9/9 |
| France | auto | [Macif](https://www.macif.fr/files/live/sites/maciffr/files/dipa/DIPA_auto_pro.pdf) | Auto professionnel | 7/9 |
| France | auto | [Matmut](https://www.matmut.fr/services-en-ligne/doc/IPID/ipidauto4d.pdf) | Assurance automobile | 9/9 |
| France | auto | [PRO BTP](https://www.probtp.com/files/live/sites/probtp/files/media/pdf/ipid/ipid-assurance-auto.pdf) | Assurance auto | 7/9 |
| France | auto | [SG (Sogessur)](https://particuliers.sg.fr/static/Particuliers/Home/Assurances/nos-offres/assurance-vehicule/assurance-auto/Ipid_assurance_automobile.pdf) | Assurance automobile | 9/9 |
| France | auto | [Wakam](https://www.best-assurances.com/app/uploads/wakam-ipid-auto.pdf) | Auto DOM | 9/9 |
| France | auto | [Wakam (Solly Azar)](https://www.sollyazar.com/sites/particulier/files/media_fichier/dg-ipid-wakam-auto-moto.pdf) | Auto | 9/9 |
| France | moto | [AMV](https://www.amv.fr/docs/Docs/IPID_AMV_MOTO_EQ.pdf) | Assurance moto (équipement) | 9/9 |
| France | moto | [AMV](https://www.amv.fr/docs/Docs/IPID_AMV_MOTO_GB.pdf) | Assurance moto | 9/9 |
| France | moto | [MAIF](https://www.maif.fr/files/live/sites/maif-fr/files/pdf/documentation-contractuelle/mobilite/document-information-assurance-moto-loisir.pdf) | Assurance moto (contrat 4+2) | 9/9 |
| France | moto | [Macif](https://www.macif.fr/files/live/sites/maciffr/files/dipa/DIPA_deux_roues.pdf) | Deux-roues | 9/9 |
| France | moto | [Macif](https://www.macif.fr/files/live/sites/maciffr/files/dipa/DIPA_Moto_Pro.pdf) | Moto professionnel | 7/9 |
| France | moto | [Matmut](https://www.matmut.fr/services-en-ligne/doc/IPID/IPID2R.pdf) | Assurance deux-roues | 9/9 |
| France | moto | [Solly Azar](https://www.sollyazar.com/sites/particulier/files/media_fichier/dg-ipid-gbike-moto125quad.pdf) | Moto 125 et quad | 9/9 |
| France | moto | [Solly Azar](https://www.sollyazar.com/sites/particulier/files/media_fichier/DG_IPID_CYCLO_ET_SCOOTER_50.pdf) | Cyclo et scooter 50 | 9/9 |
| France | moto | [Solly Azar (Wakam)](https://www.sollyazar.com/sites/particulier/files/2023-07/moto_motopass_ipid_wakam.pdf) | Motopass | 9/9 |
| France | moto | [Wakam (Solly Azar)](https://www.sollyazar.com/sites/particulier/files/media_fichier/dg-ipid-wakam-cyclo.pdf) | Cyclo | 9/9 |
| Irlande | auto | [AIG Ireland](https://www.aig.ie/content/dam/aig/emea/ireland/documents/ipids/post-brexit-ipids/ie-direct-motor-ipid-12-2018-min.pdf) | Direct motor | 9/9 |
| Irlande | auto | [Allianz Ireland](https://www.allianz.ie/content/dam/onemarketing/azie/allianz-ireland/en_us/documents/documents---car-insurance/DMR-Full-IPID-Pre-July-2025.pdf) | Car insurance | 9/9 |
| Irlande | auto | [Aviva Ireland](https://static.aviva.io/content/dam/aviva-public/ie/pdfs/motorcare-ipid.pdf) | Motorcare | 9/9 |
| Irlande | auto | [Outsurance](https://www.outsurance.ie/globalassets/documents/outsurance-dac/outsurance-car-ipid_202403.pdf) | Car insurance | 9/9 |
| Italie | auto | [Allianz Italia](https://www.allianz.it/content/dam/onemarketing/azit/allianz-it/le-soluzioni-per-te/mobilita/set_informativi/01_SI_BM_ed_RCA_01_07_2024_e_ARD_01_02_2024.pdf) | RC auto bonus malus | 9/9 |
| Italie | auto | [Quixa](https://www.quixa.it/wp-content/documents/SetInformativi/ed.25.05.2022_Auto_QP.pdf) | Assicurazione auto | 9/9 |
| Italie | auto | [Quixa](https://www.quixa.it/wp-content/documents/SetInformativi/ed.19.12.24_Sicurauto.pdf) | Sicurauto | 9/9 |
| Italie | auto | [Quixa](https://www.quixa.it/wp-content/documents/SetInformativi/ed.14.11.2023_Auto_QP.pdf) | Auto | 9/9 |
| Italie | auto | [UnipolSai](https://www.unipol.it/api/pub/ueba/download/doc/v1/fascicoli/345a4c27-b163-491c-b3b9-bdfb511ba345) | RCA autovetture | 9/9 |
| Italie | auto | [UnipolSai](https://www.unipol.it/api/pub/ueba/download/doc/v1/fascicoli/a599b493-f541-4aa9-88f2-1745285d89f4) | Contratto base RCA autovetture | 9/9 |
| Italie | auto | [UnipolSai](https://www.unipol.it/api/pub/ueba/download/doc/v1/fascicoli/ddae4130-7d3b-453b-bc75-419f18e04bee) | Auto | 9/9 |
| Italie | auto | [UnipolSai](https://www.unipol.it/api/pub/ueba/download/doc/v1/fascicoli/981646c6-9a11-422a-a2e4-0daa88ab0086) | Km&Servizi | 9/9 |
| Italie | auto | [Verti](https://www.santanderconsumer.it/sites/default/files/2022-08/SET%20INFORMATIVO_SANTANDER%20RCauto_Verti%20ed.2022.pdf) | RC auto | 9/9 |
| Italie | moto | [Allianz Italia](https://www.allianz.it/content/dam/onemarketing/azit/allianz-it/le-soluzioni-per-te/mobilita/set_informativi/03_moto_ciclo_ed_RCA_01_06_2025_e_ARD_01_12_2024.pdf) | Moto e ciclomotori | 9/9 |
| Italie | moto | [Crédit Agricole Assicurazioni](https://www.ca-assicurazioni.it/media/filer_public/ad/0f/ad0f0423-1f71-4134-8ae3-77ddf53707ce/202601_honda_safe_20_moto.pdf) | Honda Safe 2.0 moto | 9/9 |
| Italie | moto | [Linear](https://www.linear.it/extra/pdf/set_informativo_moto_06-2026.pdf) | Moto | 9/9 |
| Italie | moto | [Linear Next](https://www.linearnext.it/extra/pdf/set_informativo_linearnext_moto_05-2026.pdf) | Moto | 9/9 |
| Italie | moto | [Quixa](https://www.quixa.it/wp-content/documents/SetInformativi/ed.16.07.2026_Moto.pdf) | Assicurazione moto | 9/9 |
| Italie | moto | [Quixa](https://www.quixa.it/wp-content/documents/SetInformativi/ed.25.06.2025_Moto_ContrattoBase.pdf) | Contratto base moto | 4/9 |
| Italie | moto | [Quixa](https://quixa.it/wp-content/documents/SetInformativi/ed.01.04.2025_Moto_Protetta.pdf) | Moto Protetta | 9/9 |
| Italie | moto | [Verti](https://www.verti.it/media/SET-INFORMATIVO-MOTOCICLO-E-CICLOMOTORE-05-07-2025.pdf) | Motociclo e ciclomotore | 9/9 |
| Pays-Bas | auto | [Interpolis](https://verzekeringskaarten.nl/interpolis/Interpolis-Autoverzekering-WA-AIEP-20) | Autoverzekering WA | 9/9 |
| Portugal | auto | [CTT Seguros](https://www.ctt.pt/application/themes/pdfs/particulares/dinheiro-e-seguros/ipc-dds-automovel.pdf) | Seguro automóvel | 8/9 |
| Portugal | auto | [CTT Seguros](https://www.ctt.pt/application/themes/pdfs/IPID_+AUTO_Plano%203.pdf) | Auto Plano 3 | 8/9 |
| Portugal | auto | [Cofidis](https://campanhas-cofidis.pt/seguros/seguro-automovel/A1827_IPID_Protec_jun22.pdf) | Auto Protec | 8/9 |
| Portugal | auto | [Novo Banco](https://www.novobanco.pt/content/dam/novobancopublicsites/docs/pdfs/seguros/seguro-auto/Documento%20de%20Informacao%20sobre%20o%20Produto%20Seguro%20Auto.pdf.coredownload.inline.pdf) | Seguro auto | 8/9 |
| Portugal | auto | [Victoria Seguros](https://www.victoria-seguros.pt/cdu-services/IPID_REALRC_AUTO_MKT) | Auto RC | 8/9 |
| Portugal | moto | [Allianz Portugal](https://www.allianz.pt/content/dam/onemarketing/iberolatam/allianz-pt/seguros-/moto/docs/DISPS_Moto_2022.pdf) | Moto | 8/9 |
| Portugal | moto | [Generali Tranquilidade](https://generalitranquilidade.pt/-/media/files/moto-bicicleta-trotinete/ficha-produto-dds-auto-2-rodas.pdf) | Auto 2 rodas | 8/9 |
| Portugal | moto | [Mapfre Portugal](https://www.mapfre.pt/media/DIPS_410_MAPFREAuto_Moto_16062026.pdf) | MAPFRE Auto Moto | 8/9 |

## Documents non retenus

Liens morts, doublons, ou documents qui ne sont pas des offres auto/moto (écartés automatiquement).

- `be_ethias_auto_80ae6a` (Ethias) : lien en erreur (HTTPError)
- `be_mini_carplan_auto_fc3337` (MINI CarPlan) : lien en erreur (ReadTimeout)
- `be_polisa_auto_046a93` (Polisa) : lien en erreur (HTTPError)
- `be_toyota_insurance_auto_f3858f` (Toyota Insurance) : lien en erreur (HTTPError)
- `be_vivium_auto_e1e0c5` (Vivium) : doublon de be_vivium_auto_1fa4e5
- `de_devk_auto_4d9d31` (DEVK) : PDF illisible (DependencyError)
- `de_devk_auto_c61eb9` (DEVK) : PDF illisible (DependencyError)
- `de_gothaer_auto_96a53b` (Gothaer) : écarté : pas un document d'offre auto/moto
- `de_herzenssache_auto_f96060` (Herzenssache) : lien en erreur (HTTPError)
- `es_bbva_allianz_auto_505d45` (BBVA Allianz) : lien en erreur (HTTPError)
- `fr_april_moto_moto_062108` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_088fad` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_14ba7c` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_19242c` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_1e3666` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_1f6345` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_1fb69d` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_2e0baa` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_3cea98` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_3e6d97` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_5015d1` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_53f339` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_5c395c` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_6e8a2a` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_754896` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_772c19` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_7e901a` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_834352` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_86dade` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_97401f` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_9a67e8` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_a1d098` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_a48011` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_a6e7f6` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_b52afd` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_b68f14` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_b7282a` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_b794a0` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_b8fc61` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_ba6184` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_c2a8d0` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_c44513` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_c90825` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_cd19f5` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_d2d643` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_d64830` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_e4f593` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_ecf993` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_ed48df` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_april_moto_moto_ee1f34` (APRIL Moto) : écarté : pas un document d'offre auto/moto
- `fr_bnp_paribas_auto_94c14d` (BNP Paribas) : lien en erreur (HTTPError)
- `fr_bnp_paribas_moto_5385c9` (BNP Paribas) : lien en erreur (HTTPError)
- `fr_club_auto_macsf_auto_ff01ac` (Club Auto MACSF) : doublon de fr_club_auto_mma_auto_2d9ab9
- `fr_credit_mutuel_auto_79a9b0` (Crédit Mutuel) : écarté : pas un document d'offre auto/moto
- `fr_mutuelle_des_motards_moto_78df94` (Mutuelle des Motards) : PDF illisible (DependencyError)
- `nl_a_s_r_moto_a95f2f` (a.s.r.) : lien en erreur (ConnectionError)

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
| `url_source, fichier_source` | Lien d'origine et copie du document dans le dépôt (PDF, ou texte si l'IPID est une page web) |
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
