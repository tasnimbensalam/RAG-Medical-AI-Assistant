"""Analyse HORS LIGNE des runs (aucun appel d'API) : moyenne, écart-type entre runs, IC 95 %, stabilité.

Lit results/runs_k{K}/*.jsonl et écrit results/report_runs_k{K}.md.

Usage :
  python analyze_runs.py --k 5                 # lit results/runs_k5
  python analyze_runs.py chemin/vers/dossier  

Les métriques de retrieval (hit@N, evidence_recall@N, mrr@N) sont détectées automatiquement
dans les données : aucune valeur de k n'est codée en dur.

Méthode :
  - chaque métrique est d'abord moyennée sur les questions éligibles DANS un run, puis on donne
    la moyenne et l'écart-type de ces moyennes ENTRE runs (variabilité run à run) ;
  - un run est identifié par (stamp, numéro de run) : plusieurs fichiers d'une même config
    ne sont donc jamais fusionnés par erreur ;
  - IC 95 % par bootstrap sur les QUESTIONS ),
    car l'incertitude principale vient du petit nombre de questions, pas seulement du tirage du LLM ;
  - stabilité : part des questions dont le score change entre deux runs, et part des réponses identiques.
"""
import argparse
import json
import os
import random
import re
import statistics
from collections import defaultdict
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]


def build_metrics(rows):
    """Détecte hit@N, evidence_recall@N, mrr@N présents dans les lignes, quel que soit k."""
    keys = {key for r in rows for key in r}

    def ordered(prefix):
        found = [k for k in keys if re.fullmatch(rf"{prefix}@\d+", k)]
        return sorted(found, key=lambda k: int(k.split("@")[1]))

    names = ordered("hit") + ordered("evidence_recall") + ordered("mrr") + ["refusal_ok", "routing_ok"]
    metrics = {n: (lambda r, n=n: r.get(n)) for n in names}
    metrics["correctness (juge)"] = lambda r: (r.get("judge") or {}).get("correctness")
    metrics["faithfulness (juge)"] = lambda r: (r.get("judge") or {}).get("faithfulness")
    return metrics


def bootstrap_ci(per_question, iters=2000, seed=0):
    rng = random.Random(seed)
    vals = list(per_question.values())
    if len(vals) < 2:
        return (float("nan"), float("nan"))
    means = sorted(statistics.mean(rng.choices(vals, k=len(vals))) for _ in range(iters))
    return means[int(0.025 * iters)], means[int(0.975 * iters)]


def as_num(v):
    return float(v) if isinstance(v, (int, float, bool)) else None


def analyse(rows):
    by_run = defaultdict(list)
    for r in rows:
        by_run[(r["stamp"], r["run"])].append(r)
    lines = [f"Runs : {len(by_run)} | lignes : {len(rows)} | erreurs : {sum(1 for r in rows if r.get('error'))}", "",
             "| Métrique | n questions | moyenne (sur runs) | écart-type entre runs | IC 95 % (bootstrap questions) |",
             "|---|---|---|---|---|"]
    for name, get in build_metrics(rows).items():
        run_means, per_q = [], defaultdict(list)
        for run_rows in by_run.values():
            vals = [(r["id"], as_num(get(r))) for r in run_rows if as_num(get(r)) is not None]
            if vals:
                run_means.append(statistics.mean(v for _, v in vals))
                for qid, v in vals:
                    per_q[qid].append(v)
        if not run_means:
            continue
        q_means = {q: statistics.mean(v) for q, v in per_q.items()}
        mean = statistics.mean(run_means)
        sd = statistics.stdev(run_means) if len(run_means) > 1 else float("nan")
        lo, hi = bootstrap_ci(q_means)
        lines.append(f"| {name} | {len(q_means)} | {mean:.3f} | {sd:.3f} | [{lo:.3f} ; {hi:.3f}] |")

    # Stabilité question par question
    per_q_corr, per_q_ans = defaultdict(list), defaultdict(list)
    for r in rows:
        c = (r.get("judge") or {}).get("correctness")
        if c is not None:
            per_q_corr[r["id"]].append(c)
        per_q_ans[r["id"]].append(r.get("answer", ""))
    if len(by_run) > 1:
        changed = [q for q, v in per_q_corr.items() if len(set(v)) > 1]
        identical = [q for q, v in per_q_ans.items() if len(set(v)) == 1]
        lines += ["", f"Questions dont le score du juge change entre runs : {len(changed)}/{len(per_q_corr)} {sorted(changed)}",
                  f"Questions dont la réponse est identique au caractère près sur tous les runs : {len(identical)}/{len(per_q_ans)}"]

    # Par catégorie (dernier niveau de détail utile pour l'analyse d'erreurs)
    cat = defaultdict(list)
    for r in rows:
        c = (r.get("judge") or {}).get("correctness")
        if c is not None:
            cat[r["category"]].append(c)
    if cat:
        lines += ["", "| Catégorie | n mesures | correctness moyenne |", "|---|---|---|"]
        lines += [f"| {k} | {len(v)} | {statistics.mean(v):.2f} |" for k, v in sorted(cat.items())]
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs_dir", nargs="?", help="dossier de runs (sinon results/runs_k{k})")
    ap.add_argument("--k", type=int, default=int(os.getenv("RETRIEVER_K", "10")))
    args = ap.parse_args()
    runs_dir = Path(args.runs_dir) if args.runs_dir else EVAL_DIR / "results" / f"runs_k{args.k}"

    files = sorted(runs_dir.glob("*.jsonl"))
    if not files:
        print(f"Aucun fichier de run dans {runs_dir}. Lancez d'abord run_eval.py --confirm.")
        return
    rows = [json.loads(line) for f in files for line in f.read_text().splitlines() if line.strip()]
    report = ["# Rapport d'évaluation (généré par analyze_runs.py)", "", f"Dossier analysé : `{runs_dir.name}`", ""]
    for config in sorted({r["config"] for r in rows}):
        stamps = sorted({r["stamp"] for r in rows if r["config"] == config})
        report += [f"## Config `{config}` — fichiers {stamps}", ""]
        report += analyse([r for r in rows if r["config"] == config]) + [""]
    out = runs_dir.parent / f"report_{runs_dir.name}.md"
    out.write_text("\n".join(report))
    print("\n".join(report))
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()