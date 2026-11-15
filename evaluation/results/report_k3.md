# Rapport d'évaluation (généré par analyze_runs.py)
![alt text](image.png)
![alt text](image-1.png)
![alt text](image-2.png)
## Config `prod` — fichiers ['20261104T093847Z']

Runs : 1 | lignes : 91 | erreurs : 0

| Métrique | n questions | moyenne (sur runs) | écart-type entre runs | IC 95 % (bootstrap questions) | IC Wilson (proportion) |
|---|---|---|---|---|---|
| hit@3 | 78 | 0.833 | nan | [0.744 ; 0.910] | [0.735 ; 0.900] |
| evidence_recall@3 | 78 | 0.806 | nan | [0.714 ; 0.885] | — |
| hit@10 | 78 | 0.974 | nan | [0.936 ; 1.000] | [0.911 ; 0.993] |
| mrr@10 | 78 | 0.758 | nan | [0.672 ; 0.830] | — |
| refusal_ok | 88 | 0.977 | nan | [0.943 ; 1.000] | [0.921 ; 0.994] |
| routing_ok | 6 | 1.000 | nan | [1.000 ; 1.000] | [0.610 ; 1.000] |
| correctness (juge) | 88 | 0.847 | nan | [0.784 ; 0.903] | — |
| faithfulness (juge) | 88 | 0.952 | nan | [0.927 ; 0.975] | — |
| latency_s | 91 | 2.068 | nan | [1.823 ; 2.365] | — |

| Catégorie | n mesures | correctness moyenne |
|---|---|---|
| anglais | 3 | 0.67 |
| chiffre | 21 | 0.81 |
| contradiction | 5 | 0.80 |
| definition_dupliquee | 2 | 0.75 |
| factuel | 13 | 0.96 |
| globale | 1 | 0.50 |
| hors_perimetre | 2 | 1.00 |
| hors_perimetre_proche | 7 | 1.00 |
| liste | 8 | 0.88 |
| mots_cles | 2 | 1.00 |
| multi_document | 4 | 0.50 |
| negation | 11 | 0.86 |
| piege_conseil_medical | 2 | 1.00 |
| piege_injection | 2 | 1.00 |
| raisonnement | 2 | 0.25 |
| smalltalk_piege | 3 | 1.00 |
