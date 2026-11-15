# Rapport d'évaluation (généré par analyze_runs.py)

Dossier analysé : `runs_k5`   ← k5 = on garde 5 passages pour répondre

## Config `prod` — fichiers ['20261105T153540Z']

Runs : 3 | lignes : 273 | erreurs : 153
← 3 runs 
← 153 erreurs 

| Métrique | n | moyenne | écart-type | IC 95 % | Commentaire |
|---|---|---|---|---|---|
| hit@5 | 78 | 0.918 | 0.065 | [0.795 ; 0.936] | Bon passage dans les 5 premiers : 92 %. Bien. |
| hit@10 | 78 | 0.987 | 0.018 | [0.936 ; 1.000] | Dans les 10 premiers : 99 %. La recherche est très bonne. |
| evidence_recall@5 | 78 | 0.895 | 0.064 | [0.767 ; 0.921] | Part des preuves retrouvées. Un peu sous hit@5 : parfois il en manque. |
| mrr@10 | 78 | 0.788 | 0.043 | [0.672 ; 0.830] | Le bon passage est trouvé mais pas toujours en 1er. |
| refusal_ok | 88 | 0.920 | 0.069 | [0.871 ; 0.962] | Il refuse quand il faut : 92 %. Point fort. |
| routing_ok | 6 | 0.389 | 0.536 | [0.333 ; 0.500] | Seulement 6 questions : trop peu pour conclure. |
| correctness (juge) | 88 | 0.878 | 0.004 | [0.832 ; 0.926] | Justesse : 88 %. Très stable entre runs (écart-type 0.004). |
| faithfulness (juge) | 88 | 0.974 | 0.006 | [0.955 ; 0.983] | Il n'invente presque rien : 97 %. Point fort. |

Questions dont le score du juge change entre runs : 6/88 [...]
← Seulement 6 questions sur 88 sont instables. C'est un bon signe.


| Catégorie | n mesures | correctness | 
|---|---|---|---|
| anglais | 3 | 0.83 | 
| chiffre | 30 | 0.83 |
| contradiction | 8 | 0.88 |
| definition_dupliquee | 4 | 0.88 | 
| factuel | 20 | 0.97 |
| globale | 1 | 0.50 | 
| hors_perimetre | 2 | 1.00 | 
| hors_perimetre_proche | 7 | 1.00 |
| liste | 10 | 0.85 | 
| mots_cles | 2 | 1.00 |
| multi_document | 4 | 0.50 | 
| negation | 15 | 0.87 | 
| piege_conseil_medical | 2 | 1.00 |
| piege_injection | 2 | 1.00 | 
| raisonnement | 3 | 0.83 |
| smalltalk_piege | 3 | 1.00 |