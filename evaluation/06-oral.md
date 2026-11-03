# 06 — Présentation orale de l'évaluation

> **Chiffres mesurés (1 run `prod`, 01/11/2026)** à utiliser dans les crochets [APRÈS RUN] : hit@3 = **0,86** (31/36, IC [0,71 ; 0,94]) ; hit@10 = **0,97** ; MRR@10 = 0,76 ; correctness = **0,79** (27 × 1, 11 × 0,5, 3 × 0) ; faithfulness = **0,98** ; refus hors périmètre **5/5** ; faux refus **3/36** (F05, D11, M02) ; routage 2/2 ; latence médiane **2,4 s** (p90 5,4 s) ; 63 % des tokens de sortie sont du raisonnement. **Variance entre runs : non mesurée (1 run).** Analyse détaillée : `03-analyse-des-reponses.md`. N'annoncez jamais un chiffre qui n'est pas dans `results/report.md`.

## 1. En 1 minute
> « Au départ, mon projet avait 23 tests unitaires, tous verts, mais ils vérifient la **plomberie**, pas la **qualité des réponses**. Je l'ai reconnu, et j'ai construit une évaluation : 42 questions écrites à partir des deux PDF, dont des pièges délibérés (chiffres contradictoires dans l'article, questions hors périmètre proches, injection, salutation). Je mesure séparément le **retrieval** (le bon passage est-il dans les 3 chunks envoyés au LLM ?) et la **génération** (justesse et fidélité, avec un juge LLM différent du générateur). Comme mon LLM tourne à température 0,7 par défaut, je fais plusieurs runs et je donne une moyenne, un écart-type et un intervalle de confiance. [APRÈS RUN : « Résultat : hit@3 de X, correctness de Y ± Z ; mes échecs viennent surtout de… »]. Avec 42 questions, cette mesure détecte les grosses régressions ; elle ne permet pas de départager deux réglages proches. »

## 2. En 5 minutes
1. **Le point de départ, honnête (30 s)** : 23/23 tests, stables sur 5 exécutions, mais tout est mocké. Aucune mesure de qualité existait.
2. **Le jeu de test (1 min)** : 42 questions, 17 catégories. 36 sont répondables, et leurs preuves sont **recopiées du texte extrait** ; j'ai vérifié hors ligne qu'elles sont toutes dans au moins un chunk (36/36). Pièges trouvés en lisant le corpus : l'article se contredit (carcinome à 65,52 % dans le résumé, 79,31 % dans les résultats) ; « 65,52 % » désigne 3 faits différents dans 4 chunks ; 29 % des chunks de l'article sont de la bibliographie ; le FALC répète ses définitions et pypdf y coupe au moins 42 mots.
3. **Les métriques (1 min 30)** : retrieval déterministe sans LLM (hit@3, evidence_recall@3, hit@10, MRR@10) ; refus correct (des deux côtés) ; juge LLM (correctness et faithfulness), avec un modèle différent, température 0 et seed, et ses biais connus.
4. **La variabilité (1 min)** : température 0,7 sur la génération **et** sur le routage ; pas de seed ; modèle à raisonnement ; ANN ; index partagé. Protocole : 5 runs `prod` + 3 runs `det`, écart-type entre runs, bootstrap sur les questions, Wilson. [APRÈS RUN : écart-type mesuré.]
5. **Ce que j'en conclus et la suite (1 min)** : [APRÈS RUN : répartition des échecs par couche]. Prochaines étapes : golden set paraphrasé et plus grand, index dédié, température et seed dans le produit, évaluation en CI.

## 3. En 10 minutes avec écran partagé : script de démo

| Temps | Écran | Action | Ce qu'on dit |
|---|---|---|---|
| 0:00 | `server/tests/` + terminal | `make test` (23 passed) | « Ça, c'est la plomberie. Ça ne dit rien de la qualité. » |
| 1:00 | `prep-entretien/evaluation/golden_set.jsonl` | Montrer C01, H02, S02, P02 | « Chaque question a une preuve recopiée du texte. Voici mes pièges. » |
| 2:30 | Terminal | `.venv/bin/python prep-entretien/evaluation/scripts/offline_checks.py` (gratuit, 1 s) | « 177 chunks, toutes les preuves sont dans au moins un chunk : le plafond du retrieval est bon. Mais 7 questions demandent 2 ou 3 chunks avec k=3, et 29 % de l'article est de la bibliographie. » |
| 4:00 | `scripts/run_eval.py` (fonction `build_production_graph`, puis `run_one`) | Lire le code | « J'évalue le vrai chemin de production, sans le réimplémenter. La config `det` patche la température en mémoire. » |
| 5:00 | Terminal | `run_eval.py --config prod --runs 1 --only F02 D07 --no-judge --confirm` (environ 4 appels LLM) **ou** le dry-run | En direct : intent, refus, hit@3, latence |
| 6:30 | `results/report.md` (pré-calculé) | Tableau `prod` contre `det` | « Voici la moyenne, l'écart-type entre runs et l'IC. Voici ce que la température 0 change. » |
| 8:00 | Un JSONL : un échec réel | `contexts`, `diag_top`, `unsupported_claims` | Appliquer la grille : « hit@10 vrai et hit@3 faux, donc un problème de classement, donc un reranker ou un k plus grand. » |
| 9:15 | `05-plan-amelioration.md` | — | « Mesurer, stabiliser, diagnostiquer, corriger, re-mesurer, automatiser. » |

**Plan B** :
- pas de réseau ou quota épuisé : `results/report.md` et les JSONL **pré-calculés la veille** (garder une copie, plus une capture d'écran) ; `offline_checks.py` et `make test` marchent hors ligne ;
- aucun run n'a pu être fait avant l'entretien : présenter le dry-run (plan + coût) et les chiffres hors ligne, et **le dire** : « Je n'ai pas encore les résultats ; voici exactement comment je les obtiens et ce que je m'attends à voir. »

## 4. Présenter un mauvais score ou un résultat variable avec aplomb
Structure en 4 temps : **mesuré → pourquoi → appris → suite**.
> « J'ai mesuré un hit@3 de [X] sur 36 questions, avec un IC de [a ; b]. C'est moins bon que ce que j'espérais. En regardant les échecs, [n] viennent de questions dont la réponse est dans 2 ou 3 chunks, alors que je n'en récupère que 3, souvent occupés par des définitions dupliquées. Ce que j'ai appris : le goulot est le **classement**, pas les embeddings, puisque hit@10 est à [Y]. Prochaine étape : k=10 + reranker, re-mesuré sur le même golden set. »

Pour la variance :
> « Entre deux runs, ma correctness varie de [s] en écart-type. C'est attendu : ma génération **et** mon routage tournent à température 0,7, sans seed. En `det`, l'écart-type tombe à [s'], ce qui me donne la part du fournisseur. Donc une différence de moins de [2s] entre deux versions, je ne la considère pas comme réelle. »

## 5. Trente questions du jury

> Les réponses s'appuient sur les **chiffres mesurés hors ligne** ; les crochets [APRÈS RUN] sont à remplir.

**Q1. Comment sais-tu que ton RAG est bon ?**
R : Avant cette préparation, je ne le savais pas : j'avais 23 tests unitaires verts qui mockent tout. Aujourd'hui, j'ai un golden set de 42 questions et un protocole qui mesure le retrieval et la génération séparément. [APRÈS RUN : chiffres + IC.] Et je sais ce que ces chiffres ne disent pas : 42 questions écrites par moi ne représentent pas de vrais utilisateurs.
↪ *Alors tu ne sais toujours pas ?* — Je sais où il échoue sur des cas difficiles connus. Pour savoir s'il est « bon » pour des utilisateurs, il faudrait leurs questions réelles et leur retour.

**Q2. Pourquoi ce score change entre deux runs ?**
R : Température 0,7 par défaut sur la génération (`llm.py:14`) **et** sur le routage (`graph.py:22`), pas de seed, un modèle à raisonnement, et le juge lui-même. C'est pourquoi je fais N runs et je compare avec une config température 0 + seed.
↪ *À température 0, c'est déterministe ?* — Pas garanti : le fournisseur peut regrouper les requêtes sur GPU, le calcul en flottants n'est pas associatif, et le modèle est un mélange d'experts. Je le **mesure** au lieu de le supposer.

**Q3. Ton jeu de test est-il représentatif ?**
R : Non, et c'est voulu : c'est un jeu de **diagnostic**, avec environ 40 % de pièges, écrit à partir du texte, donc avec un vocabulaire proche de celui des documents, ce qui surestime le retrieval. Il manque de vraies questions d'utilisateurs et une version paraphrasée.
↪ *Comment le rendre représentatif ?* — Collecter les questions réelles (logs anonymisés), stratifier par type, et faire relire les réponses par un expert du domaine.

**Q4. Comment détectes-tu une hallucination ?**
R : Faithfulness par un juge LLM : part des affirmations justifiées **par les passages**, avec la liste `unsupported_claims`. Je la croise avec la correctness, parce qu'une réponse peut être fidèle à un mauvais passage (H02 : 63,79 % de patientes en vivantes présenté comme une survie à 10 ans).
↪ *Et en production ?* — Le même contrôle en ligne sur un échantillon, plus un seuil de score de retrieval pour refuser en amont, plus le retour utilisateur.

**Q5. Comment saurais-tu qu'un changement a dégradé le système ?**
R : On rejoue le même golden set, on compare **question par question** (test apparié), et on alerte si la baisse dépasse environ 2 écarts-types de la variance mesurée entre runs. En CI : des questions canari en `det` à chaque PR, le jeu complet chaque nuit.
↪ *Seuil arbitraire ?* — Il est calibré sur la variance **mesurée** ; sans cette mesure, tout seuil est arbitraire.

**Q6. Pourquoi faire confiance à un LLM comme juge ?**
R : Je ne lui fais pas confiance par défaut. J'ai pris un modèle différent du générateur, à température 0, avec un barème simple (0/0,5/1) et une sortie JSON vérifiée. Avant de l'utiliser pour décider, je mesure son accord avec mes propres annotations sur 20 réponses (kappa).
↪ *Et s'il est en désaccord avec toi ?* — Je regarde qui a raison : parfois c'est ma référence qui est mauvaise (M02 est vague). Je corrige le golden set et je le versionne.

**Q7. Quelle différence entre faithfulness et correctness ?**
R : Faithfulness : la réponse est-elle justifiée par le contexte fourni ? Correctness : est-elle juste par rapport à la référence ? Un refus a une faithfulness de 1 et une correctness de 0 si l'information existait.

**Q8. Pourquoi hit@3 plutôt que recall@k ?**
R : hit@3 est ce que voit réellement le LLM (k=3 en production). J'ai annoté une **preuve** par question, pas tous les chunks pertinents ; c'est donc un hit, pas un recall strict. evidence_recall@3 couvre les questions à plusieurs preuves.
↪ *Comment passer au vrai recall ?* — Les IDs des chunks qui contiennent les preuves sont déjà calculés hors ligne (`offline_checks.json`) ; il reste à les valider à la main.

**Q9. Ta métrique de retrieval par chaîne de caractères n'est-elle pas fragile ?**
R : Si, de deux façons. Les faux négatifs : une paraphrase n'est pas détectée. Les faux positifs : une preuve trop courte (« 5.2 » est dans 6 chunks, « 65,52 % » dans 4). J'ai mesuré ces cas hors ligne. L'avantage est qu'elle est déterministe et gratuite.

**Q10. Combien de questions faudrait-il ?**
R : Pour distinguer 0,80 de 0,90 avec deux jeux indépendants : environ 200 par groupe. Avec 36 questions répondables, un 0,80 a un IC de Wilson de [0,64 ; 0,90]. Pour le retrieval, c'est peu cher d'aller à 200 questions et plus (pas de LLM).

**Q11. Pourquoi 5 runs ?**
R : Compromis entre coût et estimation de l'écart-type : avec 5 valeurs, l'écart-type est grossier mais donne un ordre de grandeur. Au-delà de 5, ce n'est plus la variance du LLM qui limite la précision, mais le nombre de questions.

**Q12. Moyenne sur les runs ou sur les questions ?**
R : Les deux, pour deux incertitudes différentes : l'écart-type **entre runs** (le tirage du LLM) et l'IC **bootstrap sur les questions** (la taille du jeu). La seconde domine avec 42 questions.

**Q13. Ton « je ne sais pas » marche-t-il ?**
R : C'est une consigne de prompt, sans seuil de score : le LLM reçoit toujours 3 chunks. J'ai 6 questions pour le tester, dont 3 hors périmètre proches (survie à 10 ans, posologie du tamoxifène, rispéridone), qui sont les cas dangereux. [APRÈS RUN : taux de refus correct, et faux refus sur les 36 questions répondables.]

**Q14. Que se passe-t-il quand le document se contredit ?**
R : J'ai trouvé 4 contradictions dans l'article (carcinome 65,52 % / 79,31 %, délai 21,98 semaines / 15,3 mois…). Le LLM ne voit ni la page ni la section (prompt par défaut `{page_content}`), donc il ne peut pas dire « le résumé dit X, les résultats disent Y ». Une bonne réponse signale l'incohérence ; c'est un argument pour mettre la source et la page dans le contexte.

**Q15. Pourquoi ne pas utiliser RAGAS ?**
R : Ce n'est pas installé, et je voulais d'abord comprendre et contrôler chaque métrique. RAGAS ajouterait context precision et answer relevancy, avec ses propres juges, ses biais et ses coûts. C'est une évolution naturelle, pour comparer avec l'état de l'art.

**Q16. Comment évalues-tu le routage ?**
R : Deux questions dédiées (« Bonjour ! », « Salut, c'est quoi le M-CHAT ? »), plus le comptage des `intent=smalltalk` inattendus sur les 40 autres. Le routage tourne à 0,7 ; sa stabilité se mesure sur plusieurs runs.

**Q17. Tes tests unitaires ne servent donc à rien ?**
R : Ils servent à autre chose : non-régression rapide (0,4 s), déterministe (5 sur 5), sur l'ingestion, les codes HTTP et le routage. Ils ne mesurent pas la qualité. Les deux sont complémentaires.

**Q18. Le juge et le générateur sont chez le même fournisseur : biais ?**
R : Oui, le même fournisseur (Groq), mais des modèles différents (Llama 3.3 70B contre gpt-oss-120b). Idéalement, un juge d'une autre famille et d'un autre fournisseur ; contrainte pratique : coût et clés.

**Q19. Comment évites-tu la fuite entre test et données ?**
R : Aucun modèle n'est entraîné, donc pas de fuite au sens de l'apprentissage. Le risque est **lexical** : les questions reprennent les mots du texte. Solution : une version paraphrasée, et de vraies questions d'utilisateurs.

**Q20. Comment rends-tu un run reproductible ?**
R : `meta.json` par run : hash du golden set, modèles, température, seed, k, versions des librairies. Le chunking est vérifié déterministe (même empreinte sur 2 exécutions). Restent hors de contrôle : les mises à jour de modèle côté fournisseur et l'état de l'index, d'où un index dédié en évolution.

**Q21. L'index pourrait-il changer entre deux runs ?**
R : Oui : il est partagé, sans namespace, et la ré-indexation fait une suppression puis un ajout non atomiques. Avant de comparer deux runs, je vérifie le nombre de vecteurs et les IDs attendus (177 chunks calculés hors ligne).

**Q22. Pourquoi ne pas avoir fait ça plus tôt ?**
R : J'ai suivi le chemin classique du tutoriel : faire marcher, puis fiabiliser l'ingestion. L'évaluation, c'est ce qui manque à la plupart des prototypes RAG, et c'est la première chose que je mettrais en place sur un vrai projet.

**Q23. Quel est ton pire résultat et pourquoi ?**
R : [APRÈS RUN.] Prédiction avant mesure : G01 (le résumé), car 3 × 500 caractères représentent environ 4 % de l'article, et F05 (3 parties dans 3 chunks distants). Je compare toujours ma prédiction à la mesure.

**Q24. Que montre la comparaison prod / det ?**
R : [APRÈS RUN.] La part de la variance due à la température, et si la température 0 dégrade ou améliore la justesse (souvent, elle l'améliore en RAG factuel).

**Q25. Pourquoi un barème 0/0,5/1 et pas 1 à 10 ?**
R : Plus stable et plus facile à aligner avec un humain. Une note sur 10 donne une fausse précision avec un juge LLM.

**Q26. Un 100 % de refus correct, c'est bien ?**
R : Pas tout seul : un système qui refuse tout l'obtient. Je regarde aussi le taux de **faux refus** sur les 36 questions répondables.

**Q27. Et la latence et le coût, tu les mesures ?**
R : Oui, par question : latence de bout en bout, et tokens d'entrée et de sortie par modèle (callback LangChain). Le coût d'une campagne est estimé à environ 631 k tokens d'entrée et 264 k de sortie pour 8 runs (estimation, avant mesure réelle).

**Q28. Comment tu priorises les corrections après l'évaluation ?**
R : Chaque échec reçoit une étiquette de couche (routage, retrieval, classement, génération, juge ou référence). Je corrige la couche qui concentre le plus d'échecs, une seule à la fois, et je re-mesure.

**Q29. Que changerais-tu en premier dans le produit ?**
R : Température 0 à 0,2 et seed explicites (`llm.py:14`, `graph.py:22`), puis un seuil de score et la source avec la page dans le contexte. Chacun est validé par l'évaluation.

**Q30. En une phrase, qu'as-tu appris ?**
R : Qu'un RAG qui « a l'air de marcher » en démo peut cacher des échecs systématiques, et que la valeur n'est pas dans le score mais dans la capacité à dire **quelle couche** échoue et **avec quelle certitude**.

## 6. Les 10 phrases clés à placer
1. « Mes tests unitaires vérifient la plomberie, pas la qualité. »
2. « Je mesure le retrieval et la génération séparément, sinon je ne sais pas quoi corriger. »
3. « Toutes mes preuves sont dans au moins un chunk : le plafond est bon, le goulot est le classement à k=3. » (vérifié hors ligne ; à confirmer après le run)
4. « Mon "je ne sais pas" est une consigne, pas un mécanisme. Je l'ai testé avec des questions hors périmètre proches. »
5. « Ma génération et mon routage tournent à 0,7 sans seed : un seul run ne veut rien dire. »
6. « Avec 36 questions, 0,80 veut dire entre 0,64 et 0,90. »
7. « Mon jeu détecte les grosses régressions ; il ne départage pas deux réglages proches. »
8. « Je ne fais pas confiance au juge par défaut : je mesure son accord avec moi. »
9. « Le document se contredit lui-même : une bonne évaluation doit le savoir avant de noter le système. »
10. « Mesurer, stabiliser la mesure, diagnostiquer, corriger une couche, re-mesurer, automatiser. »
