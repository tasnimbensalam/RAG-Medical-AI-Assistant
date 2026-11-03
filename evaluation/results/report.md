# Rapport d'évaluation (généré par analyze_runs.py)

## Config `prod` — fichiers ['20261101T131244Z']

Runs : 1 | lignes : 42 | erreurs : 0

| Métrique | n questions | moyenne (sur runs) | écart-type entre runs | IC 95 % (bootstrap questions) | IC Wilson (proportion) |
|---|---|---|---|---|---|
| hit@3 | 36 | 0.861 | nan | [0.750 ; 0.944] | [0.713 ; 0.939] |
| evidence_recall@3 | 36 | 0.801 | nan | [0.681 ; 0.912] | — |
| hit@10 | 36 | 0.972 | nan | [0.917 ; 1.000] | [0.858 ; 0.995] |
| mrr@10 | 36 | 0.762 | nan | [0.648 ; 0.862] | — |
| refusal_ok | 41 | 0.927 | nan | [0.829 ; 1.000] | [0.806 ; 0.975] |
| routing_ok | 2 | 1.000 | nan | [1.000 ; 1.000] | [0.342 ; 1.000] |
| correctness (juge) | 41 | 0.793 | nan | [0.695 ; 0.878] | — |
| faithfulness (juge) | 41 | 0.980 | nan | [0.956 ; 0.996] | — |
| latency_s | 42 | 3.061 | nan | [2.567 ; 3.540] | — |

| Catégorie | n mesures | correctness moyenne |
|---|---|---|
| anglais | 1 | 0.50 |
| chiffre | 9 | 0.83 |
| contradiction | 4 | 0.88 |
| definition_dupliquee | 2 | 0.75 |
| factuel | 7 | 0.93 |
| globale | 1 | 0.50 |
| hors_perimetre | 1 | 1.00 |
| hors_perimetre_proche | 3 | 1.00 |
| liste | 2 | 0.50 |
| mots_cles | 1 | 1.00 |
| multi_document | 2 | 0.25 |
| negation | 4 | 0.75 |
| piege_conseil_medical | 1 | 1.00 |
| piege_injection | 1 | 1.00 |
| raisonnement | 1 | 0.00 |
| smalltalk_piege | 1 | 1.00 |
