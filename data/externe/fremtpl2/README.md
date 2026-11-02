# freMTPL2, version complète (objectif 3)


Le jeu français freMTPL2 dans sa version OpenML (678 013 contrats), en complément de la version CASdatasets
utilisée par le pipeline (677 991 contrats, `data/raw/freMTPL2freq.parquet`).

| Fichier | Contenu |
| --- | --- |
| `fremtpl2_policies.parquet` | Un contrat par ligne, avec le nombre de sinistres, le nombre de sinistres ayant un montant et le coût total |
| `fremtpl2_claims.parquet` | Un sinistre par ligne (26 444) avec son montant |
| `fremtpl2_claims_orphans.csv` | 195 sinistres de 6 contrats absents du fichier des contrats (anomalie connue du jeu) |

À noter : 34 060 contrats déclarent au moins un sinistre, mais seuls 24 944 ont un montant.
