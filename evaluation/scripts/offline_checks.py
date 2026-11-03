"""Contrôles d'évaluation 100 % hors ligne (aucun appel d'API, coût nul).

Reproduit le découpage de server/modules/load_vectorstore.py:index_pdf (pypdf, filtrage
des pages vides, RecursiveCharacterTextSplitter(500, 100), IDs sha1(nom)[:16]#i) puis :
  1. statistiques de chunks par PDF ;
  2. pour chaque question du golden set : dans quels chunks se trouvent les preuves
     (plafond théorique du retrieval avec k=3) ;
  3. doublons de chunks (définitions répétées) ;
  4. part des chunks de bibliographie ;
  5. mots coupés par l'extraction pypdf (heuristique).

Usage (depuis la racine du repo) :
    .venv/bin/python prep-entretien/evaluation/scripts/offline_checks.py
"""
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVAL_DIR = ROOT / "prep-entretien" / "evaluation"
sys.path.insert(0, str(ROOT / "server"))

from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402
from modules.load_vectorstore import doc_id_prefix, load_pdf  # noqa: E402  (aucun appel réseau à l'import)

# Doit rester identique à load_vectorstore.py:104
CHUNK_SIZE, CHUNK_OVERLAP = 500, 100
PDFS = ["articles_falc.pdf", "document.pdf"]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def chunk_pdf(path: Path):
    docs = [d for d in load_pdf(path) if d.page_content.strip()]
    chunks = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP).split_documents(docs)
    prefix = doc_id_prefix(path.name)
    return docs, [(f"{prefix}{i}", c) for i, c in enumerate(chunks)]


def main():
    out = {"chunking": {}, "golden": [], "duplicates": {}, "references": {}, "broken_words": {}}
    all_chunks = []
    for name in PDFS:
        path = ROOT / "server" / "uploaded_docs" / name
        docs, chunks = chunk_pdf(path)
        all_chunks += [(cid, name, c) for cid, c in chunks]
        lengths = [len(c.page_content) for _, c in chunks]
        out["chunking"][name] = {
            "pages_with_text": len(docs),
            "chars": sum(len(d.page_content) for d in docs),
            "chunks": len(chunks),
            "len_min": min(lengths), "len_median": statistics.median(lengths),
            "len_mean": round(statistics.mean(lengths), 1), "len_max": max(lengths),
            "chunks_lt_200_chars": sum(n < 200 for n in lengths),
        }
        raw = "\n".join(d.page_content for d in docs)
        # Heuristique : fragment de 1-4 lettres en fin de ligne suivi d'une suite en minuscules ("Pre\nmier").
        out["broken_words"][name] = len(re.findall(r"(?m)(?:^|\s)[A-Za-zÀ-ÿ]{1,4}\n[a-zà-ÿ]{2,}", raw))

        # Doublons exacts (après normalisation des espaces)
        seen = defaultdict(list)
        for cid, c in chunks:
            seen[norm(c.page_content)].append((cid, c.metadata["page"]))
        dups = [v for v in seen.values() if len(v) > 1]
        out["duplicates"][name] = {"groups": len(dups), "chunks_in_groups": sum(len(v) for v in dups),
                                   "examples": [[f"{cid} (p.{p})" for cid, p in v] for v in dups[:5]]}

    # Bibliographie de document.pdf : à partir du chunk contenant "REFERENCES"
    doc_chunks = [(cid, c) for cid, n, c in all_chunks if n == "document.pdf"]
    start = next(i for i, (_, c) in enumerate(doc_chunks) if "REFERENCES" in c.page_content)
    out["references"]["document.pdf"] = {"first_ref_chunk": doc_chunks[start][0], "ref_chunks": len(doc_chunks) - start,
                                         "share": round((len(doc_chunks) - start) / len(doc_chunks), 3)}

    # Couverture des preuves du golden set
    golden = [json.loads(line) for line in (EVAL_DIR / "golden_set.jsonl").read_text().splitlines() if line.strip()]
    for q in golden:
        hits = {}
        for ev in q["evidence"]:
            hits[ev] = [f"{cid} ({n} p.{c.metadata['page']})" for cid, n, c in all_chunks if norm(ev) in norm(c.page_content)]
        needed = {h[0] if h else None for h in hits.values()}
        out["golden"].append({
            "id": q["id"], "category": q["category"], "answerable": q["answerable"],
            "evidence_found": all(hits.values()) if hits else None,
            "min_chunks_needed": None if not hits else (len(needed) if None not in needed else "introuvable"),
            "hits": hits,
        })

    (EVAL_DIR / "results" / "offline").mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / "results" / "offline" / "offline_checks.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))

    # Résumé lisible
    print("== Chunking"); [print(" ", k, v) for k, v in out["chunking"].items()]
    print("== Doublons"); [print(" ", k, {x: y for x, y in v.items() if x != 'examples'}, v["examples"][:3]) for k, v in out["duplicates"].items()]
    print("== Bibliographie", out["references"])
    print("== Mots coupés (heuristique)", out["broken_words"])
    print("== Golden set : preuves")
    for g in out["golden"]:
        if g["evidence_found"] is None:
            continue
        n_hits = {ev[:35]: len(h) for ev, h in g["hits"].items()}
        print(f"  {g['id']:4} {g['category']:22} found={g['evidence_found']!s:5} chunks_min={g['min_chunks_needed']!s:11} hits={n_hits}")


if __name__ == "__main__":
    main()
