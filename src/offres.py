"""
Collecte automatique des offres d'assurance auto et moto en Europe (objectif 1).

Pour chaque offre de config/offres.yaml :
  1. télécharge le document d'information produit (IPID, PDF) ;
  2. garde le PDF dans data/raw/offres/ et note son empreinte (sha256) pour repérer les nouvelles versions ;
  3. découpe le texte selon les 9 rubriques fixées par le modèle européen (même plan dans toutes les langues) ;
  4. repère les garanties proposées, les franchises et le paiement mensuel ;
  5. écrit un seul fichier : data/clean/offres/offres_europe.parquet (+ .json lisible et un README).

Lancement :  python -m src.offres
"""
from __future__ import annotations

import hashlib
import html
import io
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
import yaml
from pypdf import PdfReader, PdfWriter

RACINE = Path(__file__).resolve().parents[1]
CONFIG = RACINE / "config" / "offres.yaml"
RAW = RACINE / "data" / "raw" / "offres"
CLEAN = RACINE / "data" / "clean" / "offres"
MANIFEST = RAW / "manifest.json"

PAGES_MAX = 12            # l'IPID tient en 2-3 pages ; les « set informativi » italiens sont bien plus longs
TAILLE_MAX_PDF = 4_000_000
TAILLE_MAX_RUBRIQUE = 6000
NAVIGATEUR = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/126.0 Safari/537.36", "Accept": "application/pdf,*/*"}


def log(msg: str) -> None:
    print(f"[offres] {msg}", flush=True)


# ------------------------------------------------------------------ texte
def normaliser(texte: str) -> str:
    """Minuscules sans accents, caractère par caractère (les positions restent celles du texte d'origine)."""
    sortie = []
    for c in texte:
        n = "".join(x for x in unicodedata.normalize("NFKD", c) if not unicodedata.combining(x)).lower()
        sortie.append(n[0] if n else " ")
    return "".join(sortie)


def motif(phrase: str) -> str:
    """'qu'est-ce qui est assuré' -> regex tolérante à la ponctuation, aux espaces et aux retours à la ligne."""
    mots = re.findall(r"[a-z0-9]+", normaliser(phrase))
    # " ?" entre les lettres : certains PDF espacent les lettres (« Q u'est-ce qui est assuré »)
    return r"[^a-z0-9]{0,4}".join(" ?".join(re.escape(c) for c in m) for m in mots)


# Les 9 rubriques du modèle européen d'IPID, dans l'ordre, pour chaque langue
RUBRIQUES = {
    "description": ["de quel type d'assurance s'agit-il", "che tipo di assicurazione", "um welche art der versicherung",
                    "um welche art von versicherung", "en que consiste este tipo de seguro", "what is this type of insurance",
                    "welk soort verzekering is dit", "om welk type verzekering gaat het", "qual e o tipo de seguro",
                    "que tipo de seguro e este"],
    "garanties": ["qu'est-ce qui est assure", "qu est ce qui est assure", "che cosa e assicurato", "was ist versichert",
                  "que se asegura", "what is insured", "wat is verzekerd", "o que esta seguro",
                  "que riscos sao segurados", "o que e que esta seguro"],
    "non_assure": ["qu'est-ce qui n'est pas assure", "qu est ce qui n est pas assure", "che cosa non e assicurato",
                   "was ist nicht versichert", "que no esta asegurado", "what is not insured", "wat is niet verzekerd",
                   "o que nao esta seguro", "que riscos nao sao segurados"],
    "restrictions": ["y a t il des exclusions", "y a t il des restrictions", "ya t il des exclusions", "ya t il des restrictions",
                     "ci sono limiti di copertura", "gibt es deckungsbeschrankungen", "gibt es deckungseinschrankungen",
                     "existen restricciones", "are there any restrictions", "zijn er dekkingsbeperkingen",
                     "zijn er beperkingen", "ha exclusoes", "existem restricoes", "ha restricoes"],
    "zone": ["ou suis-je couvert", "dove vale la copertura", "wo bin ich versichert", "donde estoy cubierto",
             "where am i covered", "waar ben ik gedekt", "waar ben ik verzekerd", "onde estou coberto"],
    "obligations": ["quelles sont mes obligations", "che obblighi ho", "welche verpflichtungen habe ich",
                    "cuales son mis obligaciones", "what are my obligations", "wat zijn mijn verplichtingen",
                    "quais sao as minhas obrigacoes"],
    "paiement": ["quand et comment effectuer", "quand et comment dois-je", "quand et comment payer", "quand et comment regler",
                 "quando e come devo pagare", "wann und wie zahle ich", "cuando y como tengo que efectuar",
                 "when and how do i pay", "wanneer en hoe betaal ik", "wanneer en hoe moet ik betalen",
                 "quando e como devo pagar", "quando e como devo efetuar"],
    "duree": ["quand commence la couverture", "quando comincia la copertura", "wann beginnt und endet",
              "cuando comienza y finaliza", "when does the cover start", "wanneer begint en eindigt",
              "quando comeca e acaba", "quando comeca e termina"],
    "resiliation": ["comment puis-je resilier", "comment resilier", "come posso disdire", "wie kann ich den vertrag kundigen",
                    "wie kann ich meinen vertrag kundigen", "como puedo rescindir", "how do i cancel", "hoe zeg ik", "hoe kan ik mijn",
                    "como posso rescindir", "como posso resolver", "como posso cancelar"],
}
RUBRIQUES_RE = {k: re.compile("|".join(motif(p) for p in v)) for k, v in RUBRIQUES.items()}

# Garanties repérées dans la rubrique « ce qui est assuré » (incluses ou en option)
GARANTIES = {
    "responsabilite_civile": ["responsabilite civile", r"\brc\b", "causes a un tiers", "causes aux tiers", "cause a un tiers",
                              "dommages aux tiers", "a autrui", "responsabilita civile", "danni a terzi", "r.c. auto",
                              "haftpflicht", "responsabilidad civil", r"\bterceros\b", "aansprakelijkheid", r"\bwa\b",
                              "responsabilidade civil", "third party", "liability"],
    "vol": [r"\bvol\b", "furto", "diebstahl", "entwendung", r"\brobo\b", "diefstal", "roubo", "theft"],
    "incendie": ["incendie", "incendio", r"\bbrand\b", r"\bfire\b"],
    "bris_de_glace": ["bris de glace", "glaces", "cristalli", "glasbruch", "lunas", "cristales", "glasbreuk", "ruitbreuk", "quebra de vidros",
                      "windscreen", "windshield"],
    "dommages_vehicule": ["tous accidents", "tous risques", "dommages collision", "dommages au vehicule", "dommages du vehicule",
                          "kasko", "collisione", "todo riesgo", "danos propios", "omnium", "allrisk", "all risk",
                          "danos proprios", "choque", "comprehensive", "accidental damage", "own damage"],
    "catastrophes_naturelles": ["catastrophe", "evenements climatiques", "tempete", "eventi naturali", "eventi atmosferici",
                                "naturgefahren", "elementar", "fenomenos", "consorcio", "natuurrampen", "storm",
                                "fenomenos da natureza", "natural", "flood"],
    "assistance": ["assistance", "assistenza", "schutzbrief", "pannenhilfe", "asistencia", "bijstand", "pechhulp",
                   "assistencia", "breakdown", "roadside"],
    "protection_conducteur": ["corporels du conducteur", "garantie du conducteur", "protection du conducteur",
                              "securite du conducteur", "individuelle conducteur", "infortuni", "insassenunfall",
                              "fahrerschutz", "accidentes del conductor", "accidentes personales", "bestuurder",
                              "ocupantes", "condutor", "personal accident"],
    "protection_juridique": ["protection juridique", "defense juridique", "defense et recours", "defense recours",
                             "tutela legale", "rechtsschutz", "defensa juridica", "reclamacion de danos",
                             "rechtsbijstand", "protecao juridica", "legal expenses", "legal protection"],
    "equipements": ["equipement", "casque", "abbigliamento", r"\bcasco\b", r"\bhelm\b", "bekleidung", "equipamiento", "kleding", "capacete", "helmet"],
    "vehicule_remplacement": ["vehicule de remplacement", "vehicule de pret", "auto sostitutiva", "veicolo sostitutivo",
                              "ersatzfahrzeug", "mietwagen", "vehiculo de sustitucion", "vervangwagen",
                              "vervangend vervoer", "veiculo de substituicao", "courtesy car", "replacement vehicle",
                              "replacement car"],
}
GARANTIES_RE = {k: re.compile("|".join(v)) for k, v in GARANTIES.items()}


def compact(texte: str) -> str:
    return re.sub(r"[^a-z]", "", texte)


def cite(garantie: str, norm: str, norm_compact: str) -> bool:
    """Garantie citée ? Mots simples cherchés aussi sans espaces (PDF aux lettres espacées)."""
    for mot in GARANTIES[garantie]:
        if "\\b" in mot:
            if re.search(mot, norm):
                return True
        elif mot in norm or (len(compact(mot)) >= 6 and compact(mot) in norm_compact):
            return True
    return False
FRANCHISE_RE = re.compile(r"franchise|franchigia|scoperto|selbstbeteiligung|selbstbehalt|franquicia|eigen risico|vrijstelling|"
                          r"franquia|excess")
MONTANT_RE = re.compile(r"(?:(\d{1,3}(?:[ .  ]\d{3})*|\d+)(?:,\d{1,2})?\s?(?:€|eur\b|euro))|(?:€\s?(\d{1,3}(?:[ .]\d{3})*|\d+))")
MENSUEL_RE = re.compile(r"mensuel|mensualit|mensile|monatlich|mensual|fraccionad|rateizz|maandelijks|mensal|monthly|instal")
VEHICULE_RE = re.compile(r"vehicule|automobile|\bauto|voiture|moto|scooter|cyclo|deux.roues|veicolo|autovettur|ciclomotor|kfz|"
                         r"fahrzeug|kraftrad|motorrad|moped|vehiculo|coche|automovel|veiculo|voertuig|motorrijtuig|bromfiets|"
                         r"\bcar\b|motor|motorcycle|motorbike")
HORS_SUJET_RE = re.compile(r"camion|remorque|caravane|mobilhome|mobil.home|camping.car|tracteur|agricole|autocarr|"
                          r"construction|corporate|entreprise|flotte|fleet|lkw|anhanger|wohnmobil|vrachtwagen|aanhangwagen")
MOTO_RE = re.compile(r"moto|scooter|cyclo|deux.roues|2.roues|2r\b|ciclomot|kraftrad|motorrad|moped|bromfiets|motorbike|"
                     r"motorcycle|2.rodas|duas rodas")


def nettoyer(texte: str) -> str:
    texte = re.sub(r"[-✓✔✗✘•■□▪●❖➢►]", " ", texte)
    return re.sub(r"\s+", " ", texte).strip(" :?-–")


def decouper(texte: str) -> dict[str, str | None]:
    """Découpe le texte en rubriques : première apparition de chaque titre, puis tri par position
    (les PDF en deux colonnes ne donnent pas toujours les rubriques dans l'ordre du modèle)."""
    norm = normaliser(texte)
    trouves = []
    for cle, rx in RUBRIQUES_RE.items():
        m = rx.search(norm)
        if m:
            trouves.append((cle, m.start(), m.end()))
    trouves.sort(key=lambda x: x[1])
    rubriques = {cle: None for cle in RUBRIQUES}
    for i, (cle, _, fin) in enumerate(trouves):
        suite = trouves[i + 1][1] if i + 1 < len(trouves) else min(len(texte), fin + 2500)
        q = texte.find("?", fin, min(fin + 80, suite))   # fin du titre (« ... à la couverture ? »)
        debut = q + 1 if q != -1 else fin
        rubriques[cle] = nettoyer(texte[debut:suite])[:TAILLE_MAX_RUBRIQUE] or None
    return rubriques


def montants_franchise(texte: str) -> list[float]:
    norm = normaliser(texte)
    vus = []
    for f in FRANCHISE_RE.finditer(norm):
        zone = norm[max(0, f.start() - 60): f.end() + 160]
        for m in MONTANT_RE.finditer(zone):
            brut = (m.group(1) or m.group(2) or "").replace(" ", "").replace(".", "").replace(" ", "").replace(" ", "")
            if brut.isdigit() and 10 <= int(brut) <= 20000:
                vus.append(float(brut))
    return sorted(set(vus))


# ------------------------------------------------------------------ collecte
def telecharger(url: str) -> bytes:
    r = requests.get(url, headers=NAVIGATEUR, timeout=90, allow_redirects=True)
    r.raise_for_status()
    if not r.content.lstrip()[:5].startswith(b"%PDF"):
        raise ValueError("la réponse n'est pas un PDF")
    return r.content


def lire_pdf(contenu: bytes) -> tuple[str, int, PdfReader]:
    lecteur = PdfReader(io.BytesIO(contenu))
    pages = lecteur.pages[:PAGES_MAX]
    return "\n".join((p.extract_text() or "") for p in pages), len(lecteur.pages), lecteur


def sauver_pdf(contenu: bytes, lecteur: PdfReader, chemin: Path) -> None:
    """Garde le PDF ; s'il est très gros (set informativo complet), ne garde que les premières pages (l'IPID)."""
    if len(contenu) <= TAILLE_MAX_PDF:
        chemin.write_bytes(contenu)
        return
    w = PdfWriter()
    for p in lecteur.pages[:PAGES_MAX]:
        w.add_page(p)
    with open(chemin, "wb") as f:
        w.write(f)


CODES_PAYS = {"France": "fr", "Belgique": "be", "Italie": "it", "Allemagne": "de", "Autriche": "at", "Espagne": "es",
              "Portugal": "pt", "Irlande": "ie", "Pays-Bas": "nl", "Finlande": "fi", "Luxembourg": "lu"}


def identifiant(o: dict) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normaliser(o["assureur"])).strip("_")[:25]
    return f"{CODES_PAYS.get(o['pays'], 'xx')}_{slug}_{o['type']}_{hashlib.sha1(o['url'].encode()).hexdigest()[:6]}"


PAGES_OK: set[str] = set()


def decouvrir(page: dict) -> list[dict]:
    """Parcourt une page d'assureur et renvoie les liens vers des documents auto ou moto (PDF / IPID)."""
    try:
        r = requests.get(page["url"], headers=NAVIGATEUR, timeout=60)
        r.raise_for_status()
    except Exception as e:
        log(f"page {page['url']} : inaccessible ({e.__class__.__name__})")
        return []
    PAGES_OK.add(page["url"])
    trouves = {}
    for lien, texte in re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", r.text, flags=re.S | re.I):
        url = urljoin(r.url, lien.strip())
        texte = html.unescape(re.sub(r"<[^>]+>|\s+", " ", texte)).strip()
        cle = normaliser(url + " " + texte)
        if not re.search(r"\.pdf|ipid|dipa|\bdip\b|informatie|informacion|informacao", cle):
            continue
        if not VEHICULE_RE.search(cle) or HORS_SUJET_RE.search(cle) or url in trouves:
            continue
        nom = texte or Path(urlparse(url).path).stem
        trouves[url] = {"pays": page["pays"], "assureur": page["assureur"], "langue": page["langue"], "url": url,
                        "type": "moto" if MOTO_RE.search(cle) else "auto", "produit": nom[:80], "decouvert_sur": page["url"]}
    log(f"page {page['url']} : {len(trouves)} document(s) auto/moto trouvé(s)")
    return list(trouves.values())[:40]


def est_une_offre(texte: str) -> bool:
    """Garde-fou : le document doit avoir le plan IPID et parler d'un véhicule."""
    rubriques = sum(v is not None for v in decouper(texte).values())
    return rubriques >= 4 and bool(VEHICULE_RE.search(normaliser(texte[:6000])))


def collecter(offre: dict, manifest: dict, empreintes: dict) -> bool:
    oid, chemin = offre["id"], RAW / f"{offre['id']}.pdf"
    ancien = manifest.get(oid, {})
    meta = {k: offre[k] for k in ("pays", "type", "assureur", "produit", "langue", "url", "decouvert_sur") if k in offre}
    try:
        contenu = telecharger(offre["url"])
    except Exception as e:
        statut = f"lien en erreur ({e.__class__.__name__})"
        if chemin.exists():
            statut += ", dernière version gardée"
        log(f"{oid} : {statut}")
        manifest[oid] = {**ancien, "offre": meta, "statut": statut}
        return False
    empreinte = hashlib.sha256(contenu).hexdigest()
    if empreinte in empreintes and empreintes[empreinte] != oid:
        manifest[oid] = {"offre": meta, "statut": f"doublon de {empreintes[empreinte]}"}
        chemin.unlink(missing_ok=True)
        return False
    empreintes[empreinte] = oid
    if ancien.get("sha256") == empreinte and chemin.exists():
        manifest[oid] = {**ancien, "offre": meta, "statut": "ok"}
        return False
    try:
        texte, nb_pages, lecteur = lire_pdf(contenu)
    except Exception as e:
        manifest[oid] = {"offre": meta, "statut": f"PDF illisible ({e.__class__.__name__})"}
        return False
    if not est_une_offre(texte):
        manifest[oid] = {"offre": meta, "statut": "écarté : pas un document d'offre auto/moto"}
        chemin.unlink(missing_ok=True)
        log(f"{oid} : écarté")
        return False
    sauver_pdf(contenu, lecteur, chemin)
    manifest[oid] = {"offre": meta, "sha256": empreinte, "pages": nb_pages, "statut": "ok", "collecte_le": maintenant()}
    log(f"{oid} : NOUVELLE VERSION ({nb_pages} pages)")
    return True


def maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ table finale
def construire_table(manifest: dict) -> pd.DataFrame:
    lignes = []
    for oid, m in sorted(manifest.items()):
        chemin = RAW / f"{oid}.pdf"
        if not chemin.exists() or "offre" not in m:
            continue
        o = {**m["offre"], "id": oid}
        texte, _, _ = lire_pdf(chemin.read_bytes())
        r = decouper(texte)
        # Si la rubrique est vide (titres empilés en haut de page), on cherche dans tout le document sauf les exclusions
        if r["garanties"] and len(r["garanties"]) >= 40:
            assure = normaliser(r["garanties"])
        else:
            assure = normaliser(texte.replace(r["non_assure"] or "\x00", " "))
        tout = " ".join(v for v in r.values() if v)
        franchises = montants_franchise(tout)
        ligne = {
            "id_offre": o["id"], "pays": o["pays"], "type": o["type"], "assureur": o["assureur"], "produit": o["produit"],
            "langue": o["langue"],
            **{f"g_{g}": cite(g, assure, compact(assure)) for g in GARANTIES},
            "franchise_mentionnee": bool(FRANCHISE_RE.search(normaliser(tout))),
            "franchise_min_eur": min(franchises) if franchises else None,
            "franchise_max_eur": max(franchises) if franchises else None,
            "paiement_mensuel": bool(MENSUEL_RE.search(normaliser(r["paiement"] or ""))),
            **r,
            "rubriques_trouvees": sum(v is not None for v in r.values()),
            "prix": None,  # pas publié dans l'IPID : dépend d'un devis personnalisé
            "url_source": o["url"], "fichier_pdf": f"data/raw/offres/{oid}.pdf",
            "collecte_le": m.get("collecte_le"), "statut_lien": m.get("statut"),
        }
        lignes.append(ligne)
    return pd.DataFrame(lignes)


DESCRIPTION_COLONNES = [
    ("id_offre", "Identifiant de l'offre"), ("pays", "Pays où l'offre est vendue"), ("type", "auto ou moto"),
    ("assureur", "Compagnie ou distributeur"), ("produit", "Nom du produit"), ("langue", "Langue du document"),
    ("g_*", "Garantie citée dans « ce qui est assuré » (incluse ou en option) : oui / non"),
    ("franchise_mentionnee", "Le document parle d'une franchise"),
    ("franchise_min_eur, franchise_max_eur", "Plus petit et plus grand montant de franchise trouvés (€)"),
    ("paiement_mensuel", "Paiement mensuel ou fractionné possible"),
    ("description", "Rubrique « De quel type d'assurance s'agit-il ? »"),
    ("garanties", "Rubrique « Qu'est-ce qui est assuré ? »"),
    ("non_assure", "Rubrique « Qu'est-ce qui n'est pas assuré ? »"),
    ("restrictions", "Rubrique « Y a-t-il des restrictions ? » (franchises, plafonds, exclusions)"),
    ("zone", "Rubrique « Où suis-je couvert ? »"), ("obligations", "Rubrique « Quelles sont mes obligations ? »"),
    ("paiement", "Rubrique « Quand et comment payer ? »"), ("duree", "Rubrique « Quand commence et finit la couverture ? »"),
    ("resiliation", "Rubrique « Comment résilier ? »"),
    ("rubriques_trouvees", "Nombre de rubriques retrouvées sur 9 (qualité de l'extraction)"),
    ("prix", "Vide pour l'instant : le prix n'est pas publié, il dépend d'un devis"),
    ("url_source, fichier_pdf", "Lien d'origine et copie du PDF dans le dépôt (traçabilité)"),
    ("collecte_le, statut_lien", "Date de la version collectée et état du lien au dernier passage"),
]


def ecrire_readme(df: pd.DataFrame, offres: list[dict], manifest: dict) -> None:
    dates = [m.get("collecte_le") for m in manifest.values() if m.get("collecte_le")]
    maj = max(dates)[:10] if dates else "-"
    l = ["# Jeu de données : offres d'assurance auto et moto en Europe", "",
         "Deuxième jeu de données du projet AssurIA (objectif 1 : personnaliser les offres d'assurance).",
         "Ce fichier est **généré automatiquement** à chaque collecte.", "",
         f"- **Dernière nouvelle version d'un document** : {maj}",
         f"- **Offres** : {len(df)} offres collectées sur {len(offres)} suivies",
         f"- **Pays** : {', '.join(sorted(df['pays'].unique())) if len(df) else '-'}",
         "- **Format** : Parquet (`offres_europe.parquet`) et JSON lisible (`offres_europe.json`)", "",
         "## D'où viennent les données", "",
         "Chaque assureur européen doit publier, pour chaque produit, un **document d'information normalisé** (IPID, "
         "« Document d'information sur le produit d'assurance »), imposé par la directive européenne sur la distribution "
         "d'assurances ([règlement 2017/1469](https://eur-lex.europa.eu/eli/reg_impl/2017/1469/oj)). "
         "Il a le même plan dans tous les pays et toutes les langues, ce qui permet de comparer les offres entre elles.", "",
         "La liste des documents suivis est dans `config/offres.yaml` du dépôt "
         "[assuria-donnees](https://github.com/adam-hassen/assuria-donnees). Pour ajouter une offre, il suffit d'y ajouter son lien. "
         "Un robot parcourt aussi les pages « documents » de certains assureurs (`pages_a_explorer`) pour trouver tout seul "
         "les nouveaux documents. Un garde-fou ne garde que les documents qui ont le plan IPID et parlent d'un véhicule.", ""]
    if len(df):
        l += ["## Offres par pays", "", "| Pays | Auto | Moto | Total |", "| --- | --- | --- | --- |"]
        for p, g in df.groupby("pays"):
            l.append(f"| {p} | {(g['type'] == 'auto').sum()} | {(g['type'] == 'moto').sum()} | {len(g)} |")
        l += ["", "## Garanties citées", "", "| Garantie | Offres qui la citent |", "| --- | --- |"]
        for g in GARANTIES:
            l.append(f"| {g.replace('_', ' ')} | {df[f'g_{g}'].mean() * 100:.0f} % |")
        l += ["", "## Liste des offres", "", "| Pays | Type | Assureur | Produit | Rubriques trouvées |",
              "| --- | --- | --- | --- | --- |"]
        for _, r in df.sort_values(["pays", "type", "assureur"]).iterrows():
            l.append(f"| {r['pays']} | {r['type']} | [{r['assureur']}]({r['url_source']}) | {r['produit']} | {r['rubriques_trouvees']}/9 |")
    erreurs = [(k, v) for k, v in sorted(manifest.items()) if v.get("statut", "ok") != "ok"]
    if erreurs:
        l += ["", "## Documents non retenus", "",
              "Liens morts, doublons, ou documents qui ne sont pas des offres auto/moto (écartés automatiquement).", ""]
        l += [f"- `{k}` ({v.get('offre', {}).get('assureur', '')}) : {v['statut']}" for k, v in erreurs]
    l += ["", "## Colonnes", "", "| Colonne | Contenu |", "| --- | --- |"]
    l += [f"| `{c}` | {d} |" for c, d in DESCRIPTION_COLONNES]
    l += ["", "## Limites connues", "",
          "- **Pas de prix** : l'IPID décrit les garanties, pas le tarif, qui dépend d'un devis (âge, véhicule, lieu…).",
          "- Les colonnes `g_*` sont repérées par mots-clés : une garantie citée peut être incluse ou en option.",
          "- Les montants de franchise sont repérés automatiquement près du mot « franchise » : à vérifier pour une offre précise.",
          "- Certains documents sont anciens (date dans le lien) : l'offre actuelle peut avoir changé.",
          "- Les PDF de plus de 4 Mo ne sont gardés que pour leurs 12 premières pages (là où se trouve l'IPID).", "",
          "## Utilisation", "", "```python", "import pandas as pd",
          "offres = pd.read_parquet(\"offres_europe.parquet\")",
          "offres[(offres.pays == \"France\") & (offres.type == \"moto\") & offres.g_vol]", "```", ""]
    (CLEAN / "README.md").write_text("\n".join(l), encoding="utf-8")


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    CLEAN.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    offres = config["offres"]
    for page in config.get("pages_a_explorer", []):        # liens trouvés automatiquement
        offres += decouvrir(page)
    vus = set()
    offres = [o for o in offres if not (o["url"] in vus or vus.add(o["url"]))]
    for o in offres:
        o.setdefault("id", identifiant(o))

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    ids = {o["id"] for o in offres}
    # on garde les offres déjà découvertes même si leur page n'a pas répondu cette fois-ci
    pages_en_panne = {p["url"] for p in config.get("pages_a_explorer", [])} - PAGES_OK
    manifest = {k: v for k, v in manifest.items()
                if k in ids or v.get("offre", {}).get("decouvert_sur") in pages_en_panne}
    empreintes = {v["sha256"]: k for k, v in manifest.items() if v.get("sha256") and v.get("statut", "").startswith(("ok", "lien"))}
    nouveautes = sum(collecter(o, manifest, empreintes) for o in offres)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    for pdf in RAW.glob("*.pdf"):                        # PDF d'offres retirées de la liste
        if pdf.stem not in manifest:
            pdf.unlink()

    df = construire_table(manifest)
    df.to_parquet(CLEAN / "offres_europe.parquet", index=False)
    df.to_json(CLEAN / "offres_europe.json", orient="records", force_ascii=False, indent=2)
    ecrire_readme(df, offres, manifest)
    log(f"Terminé : {len(df)} offres dans le fichier final sur {len(offres)} documents suivis, "
        f"{nouveautes} nouvelle(s) version(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
