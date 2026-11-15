# Rapport d'évaluation (généré par analyze_runs.py)

## Config `prod` — fichiers ['20261103T192838Z']

Runs : 3 | lignes : 126 | erreurs : 1

| Métrique | n questions | moyenne (sur runs) | écart-type entre runs | IC 95 % (bootstrap questions) | IC Wilson (proportion) |
|---|---|---|---|---|---|
| hit@3 | 36 | 0.860 | 0.002 | [0.750 ; 0.972] | [0.712 ; 0.938] |
| evidence_recall@3 | 36 | 0.804 | 0.005 | [0.676 ; 0.917] | — |
| hit@10 | 36 | 0.972 | 0.000 | [0.917 ; 1.000] | [0.858 ; 0.995] |
| mrr@10 | 36 | 0.755 | 0.004 | [0.641 ; 0.864] | — |
| refusal_ok | 41 | 0.943 | 0.014 | [0.870 ; 1.000] | [0.827 ; 0.983] |
| routing_ok | 2 | 1.000 | 0.000 | [1.000 ; 1.000] | [0.342 ; 1.000] |
| correctness (juge) | 41 | 0.799 | 0.017 | [0.711 ; 0.882] | — |
| faithfulness (juge) | 41 | 0.968 | 0.008 | [0.943 ; 0.988] | — |
| latency_s | 42 | 3.955 | 0.665 | [3.610 ; 4.293] | — |

Questions dont le score du juge change entre runs : 2/41 ['C02', 'F06']
Questions dont la réponse est identique au caractère près sur tous les runs : 11/42

| Catégorie | n mesures | correctness moyenne |
|---|---|---|
| anglais | 3 | 0.50 |
| chiffre | 27 | 0.83 |
| contradiction | 11 | 0.77 |
| definition_dupliquee | 6 | 0.75 |
| factuel | 21 | 0.93 |
| globale | 3 | 0.50 |
| hors_perimetre | 3 | 1.00 |
| hors_perimetre_proche | 9 | 1.00 |
| liste | 6 | 0.50 |
| mots_cles | 3 | 1.00 |
| multi_document | 6 | 0.50 |
| negation | 12 | 0.79 |
| piege_conseil_medical | 3 | 1.00 |
| piege_injection | 3 | 1.00 |
| raisonnement | 3 | 0.00 |
| smalltalk_piege | 3 | 1.00 |
