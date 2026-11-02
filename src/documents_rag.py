"""
Documents des offres prêts pour le RAG (objectif 2 : conseiller qui répond aux questions sur un contrat).

Pour chaque document d'offre collecté (data/raw/offres, fiches IPID d'assureurs européens) :
  - le texte complet, page par page ;
  - des passages courts (environ 800 caractères, découpés aux fins de phrase), chacun avec sa page,
    pour retrouver la clause et la citer dans la réponse ;
  - les conditions (exclusions, restrictions) des 13 offres françaises structurées (data/externe/offres_auto_france).

Sorties (data/objectif2/) : documents.csv, passages.parquet / passages.csv, textes/<id_offre>.txt, README.md
Lancement :  python -m src.documents_rag
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

RAW = Path("data/raw/offres")
OFFRES = Path("data/clean/offres/offres_europe.parquet")
CONDITIONS = Path("data/externe/offres_auto_france")
SORTIE = Path("data/objectif2")
TAILLE = 800


def pages(chemin: Path) -> list[str]:
    if chemin.suffix == ".pdf":
        sortie = []
        for p in PdfReader(chemin).pages:
            try:
                sortie.append(p.extract_text() or "")
            except Exception:  # page abîmée : on essaie sans les images
                try:
                    sortie.append(p.extract_text(extraction_mode="layout") or "")
                except Exception:
                    sortie.append("")
        return sortie
    return [chemin.read_text(encoding="utf-8")]


def nettoyer(t: str) -> str:
    t = re.sub(r"-\n(\w)", r"\1", t)          # mots coupés en fin de ligne
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def decouper(texte: str) -> list[str]:
    phrases = re.split(r"(?<=[.;:!?])\s+|\n(?=[•\-–▪■●✓✔○])", texte)
    morceaux, courant = [], ""
    for ph in phrases:
        ph = ph.strip()
        if not ph:
            continue
        if len(courant) + len(ph) > TAILLE and courant:
            morceaux.append(courant.strip())
            courant = ""
        courant += " " + ph
    if courant.strip():
        morceaux.append(courant.strip())
    return [m for m in morceaux if len(m) > 40]


def main() -> int:
    (SORTIE / "textes").mkdir(parents=True, exist_ok=True)
    offres = pd.read_parquet(OFFRES)
    docs, passages = [], []
    for o in offres.itertuples():
        chemin = next((RAW / f"{o.id_offre}{e}" for e in (".pdf", ".txt") if (RAW / f"{o.id_offre}{e}").exists()), None)
        if chemin is None:
            continue
        pp = [nettoyer(p) for p in pages(chemin)]
        (SORTIE / "textes" / f"{o.id_offre}.txt").write_text(
            "\n\n".join(f"===== page {i} =====\n{p}" for i, p in enumerate(pp, 1)), encoding="utf-8")
        k = 0
        for num, p in enumerate(pp, 1):
            for m in decouper(p):
                k += 1
                passages.append({"id_passage": f"{o.id_offre}_p{num}_{k:03d}", "id_offre": o.id_offre, "pays": o.pays,
                                 "type": o.type, "assureur": o.assureur, "produit": o.produit, "langue": o.langue,
                                 "page": num, "texte": m, "source": "fiche IPID", "url_source": o.url_source})
        docs.append({"id_offre": o.id_offre, "pays": o.pays, "type": o.type, "assureur": o.assureur, "produit": o.produit,
                     "langue": o.langue, "fichier_document": f"documents/{chemin.name}", "fichier_texte": f"textes/{o.id_offre}.txt",
                     "nb_pages": len(pp), "nb_caracteres": sum(len(p) for p in pp), "nb_passages": k, "url_source": o.url_source})
    # conditions des offres françaises structurées (exclusions et restrictions relevées sur les documents des assureurs)
    if (CONDITIONS / "auto_product_conditions.csv").exists():
        prod = pd.read_csv(CONDITIONS / "auto_products.csv")
        cond = pd.read_csv(CONDITIONS / "auto_product_conditions.csv").merge(prod, on="product_id", how="left")
        nom = lambda r, c: r[c] if c in r and pd.notna(r[c]) else ""
        for k, r in enumerate(cond.to_dict("records"), 1):
            passages.append({"id_passage": f"fr_struct_{r['product_id']}_{k:03d}", "id_offre": f"fr_struct_{r['product_id']}",
                             "pays": "France", "type": "auto", "assureur": nom(r, "insurer") or nom(r, "insurer_name"),
                             "produit": nom(r, "product_name") or r["product_id"], "langue": "fr", "page": None,
                             "texte": f"{'Exclusion' if r['kind'] == 'exclusion' else 'Restriction'} : {r['text']}",
                             "source": "offres françaises structurées", "url_source": nom(r, "source_url")})
    docs, passages = pd.DataFrame(docs), pd.DataFrame(passages)
    docs.to_csv(SORTIE / "documents.csv", index=False, sep=";", encoding="utf-8-sig")
    passages.to_parquet(SORTIE / "passages.parquet", index=False)
    passages.to_csv(SORTIE / "passages.csv", index=False, sep=";", encoding="utf-8-sig")
    ecrire_readme(docs, passages)
    print(f"[rag] {len(docs)} documents, {len(passages)} passages")
    return 0


def ecrire_readme(docs, passages):
    n = lambda x: f"{x:,.0f}".replace(",", " ")
    ex = passages[passages.texte.str.contains("exclu|non assuré|not insured|nicht versichert", case=False)].head(2)
    l = ["# Documents des offres pour le RAG (objectif 2)", "",
         "Base de connaissances du conseiller qui répond aux questions sur un contrat (garanties, exclusions, franchises, "
         "obligations) en citant le passage exact. Générée par `src/documents_rag.py` à partir des documents collectés.", "",
         f"- **Documents** : {n(len(docs))} fiches d'information (IPID, format européen), {docs.pays.nunique()} pays, "
         f"{n(docs.nb_pages.sum())} pages, langues : {', '.join(sorted(docs.langue.unique()))}",
         f"- **Passages** : {n(len(passages))} (environ {TAILLE} caractères, coupés aux fins de phrase), chacun avec l'offre et la page",
         f"- **Conditions des offres françaises structurées** : {n((passages.source == 'offres françaises structurées').sum())} exclusions et restrictions", "",
         "## Fichiers", "", "| Fichier | Contenu |", "| --- | --- |",
         "| `documents/` | Les documents originaux (PDF), pour afficher la source |",
         "| `textes/<id_offre>.txt` | Texte complet de chaque document, page par page |",
         "| `passages.parquet` / `passages.csv` | Passages à indexer (embeddings), avec `id_offre`, `assureur`, `produit`, `pays`, `langue`, `page`, `texte`, `url_source` |",
         "| `documents.csv` | Un document par ligne : assureur, produit, pays, langue, nombre de pages et de passages, lien |", "",
         "## Utilisation (exemple de RAG)", "", "```python", "import pandas as pd",
         "passages = pd.read_parquet(\"passages.parquet\")",
         "# 1. calculer un embedding par passage (modèle multilingue, ex. bge-m3 ou multilingual-e5)",
         "# 2. à chaque question : retrouver les 5 passages les plus proches, filtrés sur l'offre du client (id_offre)",
         "# 3. donner ces passages au LLM et lui demander de répondre en citant id_passage et page", "```", "",
         "## Exemples de passages", ""]
    for _, r in ex.iterrows():
        l.append(f"- **{r.assureur}, {r.produit}** (page {r.page}) : « {r.texte[:300]}… »")
    l += ["", "Limite : ce sont des fiches de synthèse (2 à 3 pages) et non les conditions générales complètes. "
          "Pour un vrai contrat signé, ajouter ses conditions générales et particulières dans `documents/` et relancer le script.", ""]
    (SORTIE / "README.md").write_text("\n".join(l), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
