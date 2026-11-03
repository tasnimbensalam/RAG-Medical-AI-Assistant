# 04 — Le « random » et la reproductibilité

## 1. Toutes les sources de variation présentes dans le code

| # | Source | Où | Impact | Contrôlable ? |
|---|---|---|---|---|
| V1 | **Température du LLM de génération** : non réglée, donc **0,7** par défaut | `server/modules/llm.py:14-18` ; défaut vérifié dans `.venv/.../langchain_groq/chat_models.py:365` | La même question donne une formulation, voire un contenu, différent ; refus ou non selon le tirage | Oui : `temperature=0` (config `det` de `run_eval.py`, patch en mémoire) |
| V2 | **Température du LLM de routage** : 0,7 aussi | `server/modules/graph.py:22` | `classify_intent` peut répondre « smalltalk » sur un run et « question » sur un autre, ce qui change le **chemin entier** (pas de retrieval) | Oui : idem |
| V3 | **Absence de seed** | `llm.py`, `graph.py` (aucun `seed`) | Pas de rejouabilité même à température > 0 | Partiellement : `model_kwargs={"seed": 42}` ; Groq le traite en « best effort » (à vérifier dans la doc Groq) |
| V4 | **Non-déterminisme côté fournisseur** même à température 0 | Groq / `openai/gpt-oss-120b` (modèle à mélange d'experts, ou *MoE*), calcul en flottants et regroupement des requêtes sur GPU | Petites différences possibles même en `det` | **Non** : à **mesurer** (N runs `det`) |
| V5 | **Tokens de raisonnement** de `gpt-oss-120b` (longueur variable) | `llm.py:16`, `graph.py:22`, `reasoning_effort` non réglé | Latence et coût variables d'un run à l'autre ; parfois une réponse différente | Partiellement : `reasoning_effort="low"` |
| V6 | **Mise à jour du modèle par le fournisseur** | Noms de modèles non versionnés (`openai/gpt-oss-120b`, `models/gemini-embedding-001`) | Un même run, refait dans un mois, peut changer | Non : noter la date et le modèle (fait dans `meta.json`) |
| V7 | **Recherche ANN approximative de Pinecone** | `load_vectorstore.py:42-47` (serverless, algorithme géré) | En théorie, de légères différences de classement près des égalités de score | Non configurable ; à mesurer (comparer `diag_top` entre runs) |
| V8 | **Égalités de score et ordre des chunks** | Doublons proches (F09, F10 : la même définition dans 3 chunks) | Ordre instable entre chunks quasi identiques, et donc contexte différent | Déduplication (évolution) |
| V9 | **Cohérence à terme de Pinecone** | Interroger juste après un upload (`index_pdf`) | Résultats incomplets si l'évaluation suit de près une (ré)ingestion | Attendre, ou vérifier le nombre de vecteurs (`describe_index_stats`) avant le run |
| V10 | **État de l'index partagé** | Index unique `medical-docs`, pas de namespace (`load_vectorstore.py:22`) | D'autres PDF uploadés entre deux runs modifient le retrieval | Index ou namespace dédié à l'évaluation (**À CONFIRMER AVEC MOI**) |
| V11 | **Ré-indexation non atomique** | `index_pdf` : `delete_document` puis upsert (`load_vectorstore.py:108-120`) | Un upload interrompu laisse un document partiellement indexé | Vérifier les IDs attendus avant le run |
| V12 | **Versions de librairies non figées** | `server/requirements.txt` (aucune version) | Un rebuild Docker peut changer le splitter, le prompt par défaut des documents ou l'extraction pypdf, donc les chunks et les IDs | Figer les versions ; versions notées dans `meta.json` |
| V13 | **Extraction pypdf** | `load_pdf` (`load_vectorstore.py:59-75`) | Déterministe à version constante (**mesuré** : 2 exécutions, fichier identique `a7cd60cd…`) ; peut changer avec la version | Figer pypdf |
| V14 | **Embeddings Gemini** | `load_vectorstore.py:52-55` | En pratique quasi déterministes ; pas garanti | À mesurer (scores dans `diag_top` entre runs) |
| V15 | **Retries automatiques** | ChatGroq `max_retries=2`, timeout 60 s (`groq/_constants.py`) | Latence bimodale lors des erreurs 429 ou 5xx ; erreurs intermittentes | Logguer les erreurs (fait dans `rec["error"]`) |
| V16 | **Juge LLM** | `run_eval.py`, `judge()` : température 0, seed 42 | Variabilité résiduelle du score (V4 s'applique au juge aussi) | Rejuger les mêmes réponses plusieurs fois pour la mesurer |
| V17 | **Échantillonnage des questions** | — | **Aucun tirage au hasard** : les 42 questions sont toujours toutes jouées, dans le même ordre | Rien à faire |
| V18 | **Batching à l'ingestion** | `BATCH_SIZE = 64`, `load_vectorstore.py:29` | Aucun effet sur les vecteurs (même texte et mêmes IDs) | — |
| V19 | **Cache** | `@lru_cache` sur `get_vectorstore` (`load_vectorstore.py:36`) | Aucun cache de réponses ou d'embeddings, donc aucune variance due au cache ; le cache de la connexion n'influence pas les scores | — |
| V20 | **Tests unitaires** | `server/tests/` | **Aucune variance** : tout est mocké. **Mesuré** : 23/23 sur 5 exécutions sur 5 | — |

## 2. Ce que je peux et ne peux pas conclure aujourd'hui

**Je peux conclure (mesuré)** :
- La suite unitaire est déterministe (5/5).
- Le chunking est déterministe et ne perd aucune des preuves du golden set (36/36).
- La structure du corpus crée des pièges objectifs : 7 questions à plusieurs chunks, des chiffres contradictoires, 28,9 % de chunks de bibliographie et des définitions dupliquées.

**Mesuré depuis (1 run `prod`, `results/runs/20261101T131244Z_prod.*`)** : hit@3 0,86, correctness 0,79, faithfulness 0,98, etc. (voir `03`). Les IC bootstrap **entre questions** sont disponibles. Coût réel du système : 30 179 tokens en entrée et 11 294 en sortie pour 42 questions, **plus bas que l'estimation** (≈ 34 k / 25 k sans le juge).

**Je ne peux toujours pas conclure** :
- **Rien sur la variance entre runs** : un seul fichier de résultats. L'écart-type entre runs vaut `nan` dans le rapport. Il faut au moins 2 runs `prod` et 1 run `det`.
- Les tokens du juge ne sont pas comptés (le compteur n'entoure que `graph.invoke`).

**Même après un run, la taille d'échantillon limite les conclusions.** Ce sont des intervalles de Wilson à 95 %, que j'ai calculés :
| n questions | score observé 0,8 → IC 95 % | score observé 0,9 → IC 95 % |
|---|---|---|
| 6 (hors périmètre) | [0,41 ; 0,96] | [0,50 ; 0,99] |
| 36 (répondables) | [0,64 ; 0,90] | [0,76 ; 0,96] |
| 42 (tout) | [0,66 ; 0,89] | [0,77 ; 0,96] |
| 100 | [0,71 ; 0,87] | [0,83 ; 0,95] |
| 300 | [0,75 ; 0,84] | [0,86 ; 0,93] |

Conséquences à dire au jury :
- avec 36 questions, un hit@3 de 0,80 veut dire « **quelque part entre 0,64 et 0,90** » ;
- pour distinguer **de façon fiable** 0,80 de 0,90 avec deux jeux indépendants, il faudrait environ **199 questions par groupe** (α = 0,05, puissance 0,8 ; calcul classique de comparaison de deux proportions). En comparant **les mêmes questions** avant et après un changement (test apparié, type McNemar), il en faut moins, mais toujours bien plus que 36 ;
- donc **mon golden set de 42 questions sert à détecter de grosses régressions et à trouver des motifs d'erreur, pas à départager deux réglages proches.**

## 3. Comparaison de fichiers de résultats

**Aucun fichier de résultats n'existe** (`results/runs/` est vide). Quand il y en aura plusieurs, `analyze_runs.py` calcule automatiquement :
- l'écart-type des moyennes entre runs, par métrique ;
- les questions dont le score du juge change entre runs ;
- la part des réponses identiques au caractère près ;
- les écarts `prod` contre `det` (en mettant les deux tableaux côte à côte).

Pour expliquer un écart, appliquer dans l'ordre :
1. Même `golden_sha256` et mêmes `versions` dans `meta.json` ? Sinon, le jeu de questions ou le code a changé, et ce n'est pas du hasard.
2. Le nombre de vecteurs de l'index a-t-il changé (V10, V11) ?
3. Le routage a-t-il changé (V2) ? Comparer `intent` question par question.
4. Le contexte a-t-il changé (V7, V8) ? Comparer les IDs de `contexts`.
5. Sinon, c'est la génération (V1, V4, V5) ou le juge (V16).

## 4. Protocole de mesure proposé

**Objectif** : séparer la variance due au **LLM** (entre runs) de l'incertitude due au **petit jeu de questions** (entre questions).

| Étape | Commande | Ce qu'on obtient |
|---|---|---|
| 0. Hors ligne (fait) | `.venv/bin/python prep-entretien/evaluation/scripts/offline_checks.py` | Chunks, preuves, déterminisme |
| 1. Fumée (1 question, sans juge) | `run_eval.py --config prod --runs 1 --only F02 --no-judge --confirm` | Valide les clés, l'index et les quotas |
| 2. Production telle quelle | `run_eval.py --config prod --runs 5 --confirm` | Moyenne, écart-type et IC de la config **réelle** |
| 3. Déterministe | `run_eval.py --config det --runs 3 --confirm` | Variance **résiduelle** (fournisseur) ; gain apporté par la température 0 |
| 4. Stabilité du juge | (évolution) rejuger 3 fois les réponses d'un même run | Variance due au juge seul |
| 5. Analyse | `.venv/bin/python prep-entretien/evaluation/scripts/analyze_runs.py` | `results/report.md` |

**Calculs** (implémentés dans `analyze_runs.py`) :
- moyenne d'un run = moyenne sur les questions éligibles ; puis moyenne et **écart-type entre runs** (s = √(Σ(xᵢ − x̄)² / (N − 1))) ;
- **IC 95 % bootstrap** : on rééchantillonne les questions avec remise 2 000 fois, et on prend les percentiles 2,5 et 97,5 de la moyenne (seed 0, donc reproductible) ;
- **Wilson** pour les proportions.

**Fixer seed et température sans toucher au projet** : la config `det` fait `functools.partial(ChatGroq, temperature=0, model_kwargs={"seed": 42})` dans `modules.llm` et `modules.graph`. Pour l'appliquer au **produit**, il faudrait modifier `llm.py:14` et `graph.py:22` (évolution, voir `05`).

**Coût ESTIMÉ** (sortie du dry-run, hypothèse de 4 caractères par token ; les tokens de sortie, raisonnement inclus, sont une hypothèse) :
| Campagne | Appels Groq (classification + génération + juge) | Embeddings Google | Requêtes Pinecone | Tokens entrée / sortie (estimation) |
|---|---|---|---|---|
| Fumée F02 sans juge | 1 + 1 + 0 | 2 | 2 | ≈ 820 / 600 |
| `prod` × 5 | 210 + 205 + 205 | 415 | 415 | ≈ 394 k / 165 k |
| `det` × 3 | 126 + 123 + 123 | 249 | 249 | ≈ 237 k / 99 k |
| **Total recommandé (sans la fumée)** | **992** | **664** | **664** | **≈ 631 k / 264 k** |

- En dollars, aux tarifs publics de Groq tels que je m'en souviens, ce serait de l'ordre de **0,5 $** au total. **Estimation à vérifier** sur la page de tarifs de Groq.
- Le **vrai risque est le quota gratuit** : les limites de tokens par minute et par jour, surtout pour le juge `llama-3.3-70b-versatile`, qui consomme environ 45 k tokens d'entrée par run. **À CONFIRMER AVEC MOI** : quelle offre Groq avez-vous, et quelles limites affiche votre console ? Si besoin, on étale la campagne sur plusieurs jours (`--only` par paquet) ou on augmente `--sleep`.

**Je n'ai rien lancé de tout ça. J'attends votre accord** (voir le rapport dans le chat).
