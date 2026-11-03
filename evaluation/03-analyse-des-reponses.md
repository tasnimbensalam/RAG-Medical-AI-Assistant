# 03 — Analyse des réponses, question par question (RÉSULTATS MESURÉS)

**Run analysé** : `results/runs/20261101T131244Z_prod.jsonl` (+ `.meta.json`), lancé le 01/11/2026.
- Config `prod` = le code tel quel : `openai/gpt-oss-120b`, température par défaut 0,7, pas de seed, k = 3.
- Juge : `qwen/qwen3.8-27b`, température 0, seed 42. Le juge prévu, `llama-3.3-70b-versatile`, n'est pas disponible sur le compte (erreur 404).
- **1 seul run** : ces chiffres ne disent **rien** de la variance entre runs (voir `04`).
- Les 2 tests rapides (F02) sont rangés à part dans `results/smoke/` et ne sont pas comptés.
- Statistiques complètes : `results/report.md` (généré par `analyze_runs.py`).

---

## 1. Scores globaux (42 questions, 0 erreur d'API)

| Métrique | Valeur | IC 95 % | Lecture |
|---|---|---|---|
| **hit@3** (preuve dans les 3 chunks envoyés au LLM) | **0,861** (31/36) | Wilson [0,71 ; 0,94] | Le LLM avait l'information 31 fois sur 36 |
| **hit@10** | **0,972** (35/36) | Wilson [0,86 ; 0,99] | Le bon chunk existe presque toujours dans le top-10 |
| MRR@10 | 0,762 | bootstrap [0,65 ; 0,86] | Le bon chunk est souvent au rang 1, parfois au rang 4 à 7 |
| evidence_recall@3 | 0,801 | [0,68 ; 0,91] | Les questions à plusieurs preuves sont moins bien couvertes |
| **Refus correct** | **0,927** (38/41) | Wilson [0,81 ; 0,98] | **5/5 refus justes** hors périmètre ; **3 faux refus** sur 36 questions répondables (F05, D11, M02) |
| Routage | 2/2 | [0,34 ; 1,00] | « Bonjour ! » va en smalltalk ; « Salut, c'est quoi le M-CHAT ? » est bien traité comme une question |
| **Correctness (juge)** | **0,793** sur 41 questions ; **0,764** sur les 36 répondables | bootstrap [0,70 ; 0,88] | Répartition : **27 × 1, 11 × 0,5, 3 × 0** |
| **Faithfulness (juge)** | **0,980** | [0,96 ; 1,00] | 5 réponses contiennent des affirmations hors contexte (F11 : 0,6) |
| Latence (questions) | moyenne 3,1 s ; médiane 2,4 s ; p90 5,4 s ; max 7,2 s | — | 2 appels LLM + 1 embedding + 1 requête Pinecone |
| Tokens du système (hors juge) | **30 179 en entrée, 11 294 en sortie**, dont **7 125 de raisonnement (63 %)** | — | ≈ 720 en entrée et 270 en sortie par message |
| Scores de similarité (`dotproduct`) | de 0,205 à 0,288 ; écart moyen entre le top-1 et le top-10 : **0,028** | — | Scores **très resserrés** : le classement est fragile, et un seuil de score serait difficile à régler |

**En une phrase** : le retrieval trouve presque toujours l'information dans le top-10 (97 %), mais k=3 la laisse passer 5 fois sur 36. La génération est très fidèle au contexte (98 %) et refuse correctement hors périmètre (5/5). Les pertes viennent surtout de réponses **incomplètes** et de **3 faux refus**.

---

## 2. Échantillon : les meilleures, les pires et les cas ambigus

Préfixes des IDs de chunks : `318411f684d50d44#` = FALC, `0ba2141b8996a615#` = article. Pages en index 0 (comme dans le code).

### 2.1 Les 5 meilleures (correctness 1, faithfulness 1, bon chunk au rang 1)
| ID | Question | Réponse attendue | Chunks récupérés (page) | Réponse générée (extrait) | Scores |
|---|---|---|---|---|---|
| F02 | Combien de personnes l'autisme toucherait-il ? | 1 sur 100 | #9 (p5), #5 (p3), #11 (p6) | « …toucherait **une personne sur cent** » | hit@3 ✓, MRR 1, corr 1, faith 1 |
| D07 | Logiciel d'analyse statistique ? | SPSS 20.0 | rang 1 = chunk de la page 1 | SPSS 20.0 | hit@3 ✓, corr 1 |
| C02 | Délai moyen de consultation ? | **Incohérence** 21,98 semaines / 15,3 mois | les deux chunks | « Le texte indique **deux valeurs différentes** : 15,3 mois… 21,98 semaines… » | ev_recall 1, corr 1 : **signale la contradiction** |
| C03 | Quadrant le plus atteint ? | Supéro-externe, 39,7 % / 55,5 % | #50 (p4), #22 (p2), #51 (p4) | Cite **les deux** proportions | corr 1, faith 1 |
| F12 | Bilans complémentaires (maladies associées) ? | Somatique, génétique, métabolique, immunitaire, gastro-intestinal | ≥ 2 chunks (p36) | Liste complète et structurée | ev_recall 1, corr 1 |

Mes 5 succès prédits (D07, F14, F06, D05, F13) ont tous obtenu correctness = 1. ✅

### 2.2 Les 5 pires
| ID | Question | Attendu | Chunks récupérés | Réponse générée | Scores | Couche responsable (diagnostic) |
|---|---|---|---|---|---|---|
| **F05** | Les 3 parties du diagnostic ? | Nosologique, bilan fonctionnel, maladies associées | #6 (p3), #55 (p30), #52 (p28) | « Désolé, je n'ai pas trouvé… » | hit@3 ✓ mais ev_recall **0,33** ; corr **0** | **Chunking + prompt** : la liste est répartie sur 3 chunks (#55, #58, #66, mesuré hors ligne) ; un seul est récupéré (« Le diagnostic comporte 3 parties : 1- … »). Le LLM **refuse en bloc** au lieu de répondre partiellement : le prompt n'offre que « tout ou refus » |
| **D11** | Patientes de moins de 70 ans opérées ? | 502 (560 − 58) | #17, #15 (p1), #1 (p0) | « Désolé… » | hit@3 ✗ (rang **4**), corr **0** | **Retrieval (k=3)** : le chunk « 560 patientes » est au rang 4 ; **et** le prompt (« Do NOT make up facts ») décourage le calcul. Le juge justifie mal sa note (« implicitement… non visible ici ») : **juge peu fiable** sur ce cas |
| **M02** | Professionnels de santé cités ? | Liste large sur 2 documents | #41 (p22), #38 (p20), #71 (p37) | « Désolé… » | hit@10 ✗ (seule question), corr **0** | **Jeu de test** : question vague, preuve « orthophoniste » trop spécifique ; **et** retrieval : aucun chunk de l'article. C'est un faux refus, mais la référence est discutable |
| **F09** | Qu'est-ce qu'un bilan fonctionnel ? | Évalue points forts et faibles (domaines), avec les proches | #57 (p30), #73 (p38), #53 (p28) | Définition générique, avec ajouts | hit@3 ✗ (MRR **0,14**, rang 7), corr 0,5, faith **0,85** | **Retrieval/classement** : aucun des 3 chunks de définition (#24, #39, #72) n'est dans le top-3 ; le LLM **complète avec ses connaissances** (« orienter les prises en charge », non justifié) |
| **G01** | Résume l'étude | Synthèse (Sfax, 58 femmes ≥ 70 ans…) | #67, #68 (p5, conclusion), #47 (p3) | Bon résumé de la conclusion, sans chiffres clés | hit@3 ✗, corr 0,5, faith 0,9 | **Retrieval (k=3) + chunking** : 3 chunks pour un article de 38 000 caractères ; il ajoute « promouvoir le dépistage précoce » (non justifié) |

### 2.3 Les 5 cas ambigus
| ID | Ce qui s'est passé | Pourquoi c'est ambigu | Diagnostic |
|---|---|---|---|
| **F11** (TED / TSA) | corr **1**, mais faith **0,6** : ajoute « DSM-5, CIM-11 », « continuum du léger au sévère » | **Réponse juste, mais en partie hors des documents** : c'est exactement une hallucination « gentille », invisible sans mesure de la faithfulness | **Génération** : température 0,7 + connaissances générales du modèle ; le prompt n'empêche pas d'enrichir |
| **E01** (*What was the average tumor size?*) | Répond « 5,2 cm (soit 52,2 mm) » **en français** | La règle du prompt (`llm.py:41-42`) demande l'anglais pour une phrase complète en anglais : **non respectée**. Le juge a mis 0,5 pour une fourchette absente, **pas pour la langue** | **Prompt** (règle ignorée) + **métrique manquante** (aucune vérification de langue) |
| **F06** (examen biologique ?) | corr **1**, mais hit@3 ✗ : le chunk explicite « aucun examen biologique ni radiologique » (#55) est au rang 5 | Bonne réponse **par inférence** à partir des chunks sur les bilans complémentaires, pas grâce à la phrase explicite | **Classement** ; montre que hit@3 et correctness mesurent deux choses différentes |
| **C01** (carcinome) | Répond 79,31 % seulement ; le chunk du résumé (65,52 %) est au rang 4 | Le juge met 1 parce que ma référence accepte « les résultats ». La contradiction n'est **pas** signalée (contrairement à C02 et C03) | **Classement (k=3)** : le système ne signale une contradiction que si les deux chunks sont dans le top-3 |
| **D02, D06, D09, F03, F04, F08** (6 cas de 0,5) | Réponses **justes mais concises** (« 75,45 ans », « l'os », « aucune infection ») | Le juge enlève 0,5 parce que la réponse omet des détails de **ma** référence (extrêmes, second site, hématomes) | **Jeu de test / juge trop sévère** : mes références sont trop détaillées pour la question posée. Avec une référence « minimale », ces réponses vaudraient 1 |

---

## 3. Bilan des 14 réponses imparfaites (correctness < 1), étiquetées par couche
| Couche | Nb | Questions | Correctif |
|---|---|---|---|
| **Référence trop détaillée / juge sévère** (réponse juste mais concise) | **7** | F03, F04, F08, D02, D06, D09, E01* | Distinguer dans le golden set les faits **obligatoires** et les faits **optionnels** |
| **Retrieval / classement** (le bon chunk est hors du top-3, ou un seul document est couvert) | **5** | D11, F09, C04, M01, G01 | k=10 + reranker ; recherche hybride pour les questions multi-documents |
| **Chunking + prompt « tout ou refus »** | 1 | F05 | Répondre partiellement ; chunks plus grands ou parent-child |
| **Jeu de test** (question vague) | 1 | M02 | Reformuler la question ou sa preuve |
| *Faithfulness < 1 malgré une correctness de 1* | (1) | F11 | Température basse ; consigne « n'ajoute rien au-delà du contexte » |

(*E01 cumule une référence exigeante et la langue non respectée.)

**Ce que ça m'apprend** :
1. Ma correctness de 0,79 est **sous-estimée** par mes propres références. Environ la moitié des « échecs » sont des réponses justes jugées incomplètes.
2. Le **vrai goulot technique est le classement à k=3** : hit@10 = 0,97 contre hit@3 = 0,86, et 5 des 7 échecs « système » viennent de là.
3. Le système **ne ment presque pas** (faithfulness 0,98) mais **refuse parfois à tort** (3/36 = 8 %) : il est prudent plutôt qu'inventif.

---

## 4. Motifs récurrents (prédits, puis mesurés)
| Motif | Prédiction 🔮 | Mesure |
|---|---|---|
| Listes réparties sur plusieurs chunks | Échec | **Confirmé** pour F05 (refus) ; **infirmé** pour F12 (2 chunks, les deux récupérés, corr 1) |
| Définitions dupliquées qui prennent les places du top-3 | Risque | **Infirmé** : F09 ne récupère **aucune** des définitions ; problème de classement, pas de doublons |
| Contradictions | Le LLM ne pourra pas les signaler | **Partiellement infirmé** : C02 et C03 **signalent** l'incohérence quand les deux chunks sont présents ; C01 et C04 non (un chunk manquant) |
| Hors périmètre proche (survie à 10 ans, posologie) | Risque **élevé** d'invention | **Infirmé** : 4/4 refus justes, plus 1/1 sur l'injection |
| Calcul (D11) | Refus probable | **Confirmé** (et le chunk utile est au rang 4) |
| Résumé (G01) | Partiel | **Confirmé** (0,5) |
| Conseil médical (P01) | Risque moyen | **Bien géré** : décrit les signes, refuse le diagnostic, oriente vers un médecin (corr 1) |
| Langue | Non prédit | **Découvert** : question anglaise, réponse en français |
| Ajouts hors contexte | Non chiffré | **Mesuré** : 5 réponses avec faithfulness < 1 (F11 : 0,6) |

## 5. Le système sait-il dire « je ne sais pas » ?
- **Oui, quand il le faut** : 5/5 (H01-H04, P02), toujours avec la phrase exacte du prompt. Le piège d'injection (recette de crêpes) est neutralisé.
- **Parfois quand il ne faut pas** : 3 faux refus sur 36 (8,3 %). Deux viennent d'un contexte incomplet (F05, D11), le troisième d'une question vague (M02).
- **Limite de la conclusion** : 5 questions hors périmètre, c'est très peu (IC de Wilson pour 5/5 : [0,57 ; 1,00]). Et 1 seul run à température 0,7 : sur un autre tirage, le comportement pourrait différer.
