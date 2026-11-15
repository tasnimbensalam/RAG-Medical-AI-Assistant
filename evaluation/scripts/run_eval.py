"""Évaluation de bout en bout du RAG, sur le VRAI chemin de production.

Ce que fait un run, pour chaque question du golden set :
  1. exécute le graphe de production : routes/ask_question.py reproduit à l'identique
     (get_vectorstore().as_retriever(k=K) -> get_llm_chain -> build_graph -> invoke) ;
  2. relance une recherche de diagnostic top-DK avec les scores (similarity_search_with_score) ;
  3. calcule des métriques déterministes : routage, refus, hit@K, evidence_recall@K, MRR@DK
     (K = --k, DK = --diag-k, toujours >= K) ;
  4.  demande à un LLM juge : correctness (0, 0.5 ou 1) et faithfulness (0 à 1).

Les résultats sont écrits dans results/runs_k{K}/ : un dossier par valeur de k.

Configurations :
  prod : paramètres du code actuel (température par défaut de ChatGroq = 0.7, sans seed)
  det  : ChatGroq patché en mémoire avec temperature=0 et seed=42

Sans --confirm, le script s'arrête avant tout appel d'API (dry-run).
"""
import argparse
import functools
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]
ROOT = EVAL_DIR.parent
sys.path.insert(0, str(ROOT / "server" if (ROOT / "server").exists() else ROOT))
REFUSAL = "désolé, je n'ai pas trouvé"
GEN_MODEL = "openai/gpt-oss-120b"
DEFAULT_K = int(os.getenv("RETRIEVER_K", "10"))

JUDGE_PROMPT = """Tu es un évaluateur strict d'un système RAG. Réponds UNIQUEMENT par un objet JSON.

Question : {question}

Réponse de référence (écrite à la main) : {expected}

Passages fournis au système :
{contexts}

Réponse du système : {answer}

Évalue :
- "correctness" : 1 si la réponse du système contient l'information essentielle de la référence, 0.5 si elle est partielle, 0 si elle est fausse, absente ou si le système refuse alors qu'une réponse existe. Si la référence commence par REFUS, 1 si le système refuse ou dit ne pas savoir, 0 sinon.
- "faithfulness" : proportion (0 à 1) des affirmations factuelles de la réponse du système qui sont justifiées par les passages fournis. Une réponse qui refuse ou ne contient aucune affirmation factuelle vaut 1.
- "unsupported_claims" : liste des affirmations non justifiées par les passages.
- "rationale" : une phrase.

JSON : {{"correctness": ..., "faithfulness": ..., "unsupported_claims": [...], "rationale": "..."}}"""


# remplace l'apostrophe typographique, réduit les espaces, met en minuscules
def norm(s: str) -> str:
    s = s.replace("’", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


# lit le golden set (jsonl), éventuellement filtré par IDs
def load_golden(only):
    rows = [json.loads(line) for line in (EVAL_DIR / "golden_set.jsonl").read_text().splitlines() if line.strip()]
    return [r for r in rows if not only or r["id"] in only]


def evidence_hits(q, docs):
    """Pour chaque preuve attendue : est-elle présente dans au moins un des documents ?"""
    texts = [norm(d.page_content) for d in docs]
    return {ev: any(norm(ev) in t for t in texts) for ev in q["evidence"]}


def first_rank(q, docs):
    for rank, d in enumerate(docs, 1):
        if any(norm(ev) in norm(d.page_content) for ev in q["evidence"]):
            return rank
    return None


def build_production_graph(config, k):
    from langchain_groq import ChatGroq
    import modules.graph as graph_mod
    import modules.llm as llm_mod
    from modules.load_vectorstore import get_vectorstore

    if config == "det":
        patched = functools.partial(ChatGroq, temperature=0, model_kwargs={"seed": 42})
        llm_mod.ChatGroq = patched
        graph_mod.ChatGroq = patched
    retriever = get_vectorstore().as_retriever(search_kwargs={"k": k})
    chain = llm_mod.get_llm_chain(retriever)
    return graph_mod.build_graph(retriever, chain), get_vectorstore()


def judge(q, answer, contexts, judge_model):
    from langchain_groq import ChatGroq
    llm = ChatGroq(model=judge_model, temperature=0, model_kwargs={"seed": 42})
    ctx = "\n\n".join(f"[{i}] {d.page_content}" for i, d in enumerate(contexts, 1)) or "(aucun passage)"
    try:
        raw = llm.invoke(JUDGE_PROMPT.format(question=q["question"], expected=q["expected_answer"],
                                             contexts=ctx, answer=answer)).content
    except Exception as e:  # quota, modèle indisponible... : on garde la ligne, sans score
        return {"correctness": None, "faithfulness": None, "judge_error": f"{type(e).__name__}: {e}"}
    visible = re.sub(r"<think>.*?</think>", "", raw, flags=re.S)
    m = re.search(r"\{.*\}", visible, re.S)
    try:
        return json.loads(m.group(0))
    except Exception:  # le juge n'a pas renvoyé de JSON valide : on le note sans inventer de score
        return {"correctness": None, "faithfulness": None, "judge_error": "JSON invalide"}


def run_one(q, graph, vectorstore, args):
    K, DK = args.k, args.diag_k
    rec = {"id": q["id"], "category": q["category"], "question": q["question"], "answerable": q["answerable"]}
    t0 = time.perf_counter()
    try:
        state = graph.invoke({"question": q["question"]})
        rec["error"] = None
    except Exception as e:  # on garde l'erreur dans les résultats (scénario « erreurs intermittentes »)
        state, rec["error"] = {}, f"{type(e).__name__}: {e}"
    rec["latency_s"] = round(time.perf_counter() - t0, 3)

    contexts = state.get("context", []) or []
    rec.update(intent=state.get("intent"), answer=state.get("answer", ""),
               contexts=[{"id": d.id, "source": d.metadata.get("source"), "page": d.metadata.get("page"),
                          "text": d.page_content} for d in contexts])
    rec["refused"] = REFUSAL in norm(rec["answer"])
    if "expected_intent" in q:
        rec["routing_ok"] = rec["intent"] == q["expected_intent"]
    if q["answerable"]:
        rec["refusal_ok"] = not rec["refused"]
    elif q.get("expected_intent") != "smalltalk":
        rec["refusal_ok"] = rec["refused"]

    if q["evidence"] and rec["intent"] == "question":
        # hit@K / evidence_recall@K : sur les K contextes réellement fournis au générateur
        hits = evidence_hits(q, contexts)
        rec[f"hit@{K}"] = any(hits.values())
        rec[f"evidence_recall@{K}"] = round(sum(hits.values()) / len(hits), 3)
        # hit@DK / mrr@DK : diagnostic sur un top-DK plus large, avec les scores
        diag = vectorstore.similarity_search_with_score(q["question"], k=DK)
        docs_diag = [d for d, _ in diag]
        rank = first_rank(q, docs_diag)
        rec[f"hit@{DK}"] = rank is not None
        rec[f"mrr@{DK}"] = round(1 / rank, 3) if rank else 0.0
        rec["diag_top"] = [{"id": d.id, "page": d.metadata.get("page"), "source": d.metadata.get("source"),
                            "score": round(s, 4)} for d, s in diag]

    if args.judge and rec["intent"] == "question" and not rec["error"]:
        rec["judge"] = judge(q, rec["answer"], contexts, args.judge_model)
    return rec


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", choices=["prod", "det"], default="prod")
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--k", type=int, default=DEFAULT_K,
                   help="top-k du retriever (défaut : RETRIEVER_K ou 10, comme ask_question.py)")
    p.add_argument("--diag-k", type=int, default=10, help="top-k du diagnostic (forcé à >= k)")
    p.add_argument("--judge", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--judge-model", default="qwen/qwen3.8-27b",
                   help="modèle juge DIFFÉRENT du générateur pour limiter l'auto-complaisance (à confirmer)")
    p.add_argument("--only", nargs="*", help="IDs de questions (ex : F02 D01)")
    p.add_argument("--sleep", type=float, default=1.0, help="pause entre questions (quotas gratuits)")
    p.add_argument("--confirm", action="store_true", help="autorise les appels d'API (sinon dry-run)")
    args = p.parse_args()
    args.diag_k = max(args.diag_k, args.k)  # le diagnostic doit couvrir au moins les k de production

    golden = load_golden(args.only)
    print(f"Golden set : {len(golden)} questions | config={args.config} | runs={args.runs} | k={args.k} "
          f"| diag_k={args.diag_k} | juge={args.judge_model if args.judge else 'non'}")
    if not args.confirm:
        print("\nDry-run : aucun appel effectué. Ajoutez --confirm pour lancer.")
        return

    graph, vectorstore = build_production_graph(args.config, args.k)
    out_dir = EVAL_DIR / "results" / f"runs_k{args.k}" 
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    meta = {
        "stamp": stamp, "config": args.config, "runs": args.runs, "k": args.k, "diag_k": args.diag_k,
        "gen_model": GEN_MODEL, "judge_model": args.judge_model if args.judge else None,
        "temperature": 0 if args.config == "det" else "défaut ChatGroq (0.7)",
        "seed": 42 if args.config == "det" else None,
        "golden_sha256": hashlib.sha256((EVAL_DIR / "golden_set.jsonl").read_bytes()).hexdigest()[:16],
    }
    (out_dir / f"{stamp}_{args.config}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    path = out_dir / f"{stamp}_{args.config}.jsonl"
    with path.open("w") as f:
        for run in range(1, args.runs + 1):
            for q in golden:
                rec = run_one(q, graph, vectorstore, args) | {"run": run, "config": args.config, "stamp": stamp,
                                                              "k": args.k}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                j = rec.get("judge", {})
                print(f"run {run} {q['id']:4} intent={rec['intent']!s:9} refus={rec['refused']!s:5} "
                      f"hit@{args.k}={rec.get(f'hit@{args.k}')!s:5} correct={j.get('correctness')} "
                      f"faith={j.get('faithfulness')} {rec['latency_s']}s {rec['error'] or ''}")
                time.sleep(args.sleep)
    print(f"\nRésultats : {path}\nAnalyse : .venv/bin/python evaluation/scripts/analyze_runs.py --k {args.k}")


if __name__ == "__main__":
    main()