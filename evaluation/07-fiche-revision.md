# 07 — Fiche de révision : évaluation

## Mes chiffres clés (mesurés le 01/11/2026, 1 run `prod`, juge Qwen3 27B)
| Chiffre | Valeur |
|---|---|
| Golden set | **42 questions**, 17 catégories (36 répondables, 6 sans réponse ou pièges) |
| **hit@3** / **hit@10** | **0,86** (31/36, IC [0,71 ; 0,94]) / **0,97** (35/36) |
| MRR@10 | 0,76 |
| **Correctness** (juge) | **0,79** sur 41 (27 × 1, 11 × 0,5, 3 × 0) ; 0,76 sur les répondables |
| **Faithfulness** (juge) | **0,98** (5 réponses avec des ajouts hors contexte ; pire cas F11 : 0,6) |
| Refus | **5/5 justes** hors périmètre et injection ; **3 faux refus sur 36** (F05, D11, M02) |
| Routage | 2/2 |
| Latence | médiane **2,4 s**, p90 5,4 s, max 7,2 s |
| Tokens (système) | ≈ 720 en entrée et 270 en sortie par message ; **63 % de la sortie est du raisonnement** |
| Scores de similarité | de 0,205 à 0,288, écart top-1 / top-10 ≈ 0,03 (très resserrés) |
| Tests unitaires | 23/23, 5 exécutions sur 5 |
| Chunks | 177 (80 FALC + 97 article), déterministes |
| **Variance entre runs** | **non mesurée** (1 seul run) |

## 10 choses à savoir sur l'évaluation de MON projet
1. Avant, il n'y avait **aucune** mesure de qualité ; seulement des tests de plomberie.
2. J'évalue le **vrai code de production**, sans réimplémentation.
3. Le retrieval est mesuré **sans LLM**, avec des phrases de preuve recopiées du texte.
4. Le **goulot est le classement à k=3** : 97 % dans le top-10, 86 % dans le top-3.
5. Le système est **prudent** : il invente très peu (faithfulness 0,98) mais refuse à tort 8 % du temps.
6. Environ **la moitié des « échecs » sont des réponses justes jugées incomplètes** par rapport à mes références trop détaillées.
7. Un vrai cas d'hallucination « gentille » : F11 est juste mais ajoute DSM-5 et CIM-11, absents des documents.
8. Le système **signale les contradictions** du document seulement quand les deux chunks sont récupérés (C02, C03 oui ; C01, C04 non).
9. Un défaut découvert par l'évaluation : une question en anglais reçoit une **réponse en français**, contre la règle du prompt.
10. Les **scores de similarité sont tassés** (environ 0,03 entre le rang 1 et le rang 10), ce qui explique la fragilité du classement et rend un seuil de score délicat.

## Mes 3 limites assumées
1. **Un seul run à température 0,7** : aucune mesure de la variance. Avec 36 questions, l'IC de hit@3 va de 0,71 à 0,94.
2. **Golden set petit**, écrit à partir du texte, avec des références parfois trop exigeantes (correctness sous-estimée).
3. **Juge non calibré** (Qwen3 27B, choisi parce que Llama 3.3 n'est pas disponible), et une fois au moins mal justifié (D11).

## Mes 3 améliorations prioritaires
1. **Mesurer la variance** : au moins 2 runs `prod` et 1 run `det` (température 0 + seed), sur l'offre gratuite.
2. **Améliorer le classement** : k=10 + reranker, puis re-mesurer hit@3 sur le même golden set.
3. **Golden set v2** : faits obligatoires et optionnels, version paraphrasée, et en CI.
