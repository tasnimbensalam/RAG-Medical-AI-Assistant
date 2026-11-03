"""Analyse HORS LIGNE des runs (aucun appel d'API) : moyenne, écart-type entre runs, IC 95 %, stabilité.

Lit prep-entretien/evaluation/results/runs/*.jsonl et écrit results/report.md.

Méthode :
  - chaque métrique est d'abord moyennée sur les questions éligibles DANS un run, puis on donne
    la moyenne et l'écart-type de ces moyennes ENTRE runs (variabilité run à run) ;
  - IC 95 % par bootstrap sur les QUESTIONS (rééchantillonnage avec remise, 2000 tirages, seed fixe),
    car l'incertitude principale vient du petit nombre de questions, pas seulement du tirage du LLM ;
  - IC de Wilson pour les proportions (hit@3, refus correct...) ;
  - stabilité : part des questions dont le score change entre deux runs, et part des réponses identiques.
"""
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]
RUNS_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else EVAL_DIR / "results" / "runs"

METRICS = {
    "hit@3": lambda r: r.get("hit@3"),
    "evidence_recall@3": lambda r: r.get("evidence_recall@3"),
    "hit@10": lambda r: r.get("hit@10"),
    "mrr@10": lambda r: r.get("mrr@10"),
    "refusal_ok": lambda r: r.get("refusal_ok"),
    "routing_ok": lambda r: r.get("routing_ok"),
    "correctness (juge)": lambda r: (r.get("judge") or {}).get("correctness"),
    "faithfulness (juge)": lambda r: (r.get("judge") or {}).get("faithfulness"),
    "latency_s": lambda r: r.get("latency_s"),
}


def wilson(p, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


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
        by_run[r["run"]].append(r)
    lines = [f"Runs : {len(by_run)} | lignes : {len(rows)} | erreurs : {sum(1 for r in rows if r.get('error'))}", "",
             "| Métrique | n questions | moyenne (sur runs) | écart-type entre runs | IC 95 % (bootstrap questions) | IC Wilson (proportion) |",
             "|---|---|---|---|---|---|"]
    for name, get in METRICS.items():
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
        binary = name != "latency_s" and all(v in (0.0, 1.0) for vs in per_q.values() for v in vs)
        wl = wilson(mean, len(q_means)) if binary else (float("nan"), float("nan"))
        lines.append(f"| {name} | {len(q_means)} | {mean:.3f} | {sd:.3f} | [{lo:.3f} ; {hi:.3f}] | "
                     + (f"[{wl[0]:.3f} ; {wl[1]:.3f}]" if binary else "—") + " |")

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
    files = sorted(RUNS_DIR.glob("*.jsonl"))
    if not files:
        print(f"Aucun fichier de run dans {RUNS_DIR}. Lancez d'abord run_eval.py --confirm.")
        return
    rows = [json.loads(line) for f in files for line in f.read_text().splitlines() if line.strip()]
    report = ["# Rapport d'évaluation (généré par analyze_runs.py)", ""]
    for config in sorted({r["config"] for r in rows}):
        stamps = sorted({r["stamp"] for r in rows if r["config"] == config})
        report += [f"## Config `{config}` — fichiers {stamps}", ""]
        report += analyse([r for r in rows if r["config"] == config]) + [""]
    out = RUNS_DIR.parent / "report.md"  # à côté des runs analysés, jamais ailleurs
    out.write_text("\n".join(report))
    print("\n".join(report))
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
