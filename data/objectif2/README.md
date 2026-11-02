# Documents des offres pour le RAG (objectif 2)

Base de connaissances du conseiller qui répond aux questions sur un contrat (garanties, exclusions, franchises, obligations) en citant le passage exact. Générée par `src/documents_rag.py` à partir des documents collectés.

- **Documents** : 104 fiches d'information (IPID, format européen), 9 pays, 1 475 pages, langues : de, en, es, fr, it, nl, pt
- **Passages** : 8 456 (environ 800 caractères, coupés aux fins de phrase), chacun avec l'offre et la page
- **Conditions des offres françaises structurées** : 104 exclusions et restrictions

## Fichiers

| Fichier | Contenu |
| --- | --- |
| `documents/` | Les documents originaux (PDF), pour afficher la source |
| `textes/<id_offre>.txt` | Texte complet de chaque document, page par page |
| `passages.parquet` / `passages.csv` | Passages à indexer (embeddings), avec `id_offre`, `assureur`, `produit`, `pays`, `langue`, `page`, `texte`, `url_source` |
| `documents.csv` | Un document par ligne : assureur, produit, pays, langue, nombre de pages et de passages, lien |

## Utilisation (exemple de RAG)

```python
import pandas as pd
passages = pd.read_parquet("passages.parquet")
# 1. calculer un embedding par passage (modèle multilingue, ex. bge-m3 ou multilingual-e5)
# 2. à chaque question : retrouver les 5 passages les plus proches, filtrés sur l'offre du client (id_offre)
# 3. donner ces passages au LLM et lui demander de répondre en citant id_passage et page
```

## Exemples de passages

- **Allianz Österreich, Mein Kfz Paket MAX** (page 1.0) : « Vollkasko
Versichert sind Schäden am versicherten Fahrzeug durch
üBlitzschlag, Felssturz, Steinschlag, Erdrutsch, 
 Muren, Lawinen, Schneedruck, Hagel, Hoch- 
 wasser, Überschwemmungen und Sturm
üBrand, Explosion oder Schmorschäden
üDiebstahl, Raub oder unbefugten Gebrauch
üBerührung des fahrenden F… »
- **Argenta, Assurance moto** (page 1.0) : « Assurance Véhicule 
Document d’information relatif à un produit d’assurance 
Argenta Assurances SA 
 
 
Assurance moto 
Le présent document vous donne un aperçu des couvertures et exclusions principales de cette assurance. Il n’est pas personnalisé en 
fonction de vos besoins individuels. Vous trouv… »

Limite : ce sont des fiches de synthèse (2 à 3 pages) et non les conditions générales complètes. Pour un vrai contrat signé, ajouter ses conditions générales et particulières dans `documents/` et relancer le script.
