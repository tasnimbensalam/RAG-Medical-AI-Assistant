# 05 — Plan d'amélioration de l'évaluation

Priorisé par rapport gain/effort. Les efforts sont des **estimations**.
Légende : ✅ déjà préparé dans `prep-entretien/evaluation/` · 🟡 à lancer (accord nécessaire) · 🔧 modification du projet (évolution, hors de cette mission).

## Avant l'entretien du 6 novembre : en moins de 2 heures, à fort impact

| # | Action | Effort | Gain | Statut |
|---|---|---|---|---|
| A1 | **Relire et corriger les 42 réponses attendues** du golden set (surtout D11 : un calcul est-il permis ? et M02, trop vague) | 30-45 min | C'est **votre** golden set ; vous pourrez le défendre ligne à ligne | ✅ fichier prêt, relecture à faire |
| A2 | **Run de fumée** : `run_eval.py --config prod --runs 1 --only F02 --no-judge --confirm` | 2 min, environ 2 appels LLM | Vérifie les clés, l'index et les quotas | 🟡 |
| A3 | **Campagne `prod` × 3 au minimum** (5 si le quota le permet) | 15-30 min d'exécution | **Premiers vrais chiffres**, avec écart-type entre runs | 🟡 |
| A4 | **Campagne `det` × 3** | 10-20 min | Montre l'effet de température 0 + seed sur la variance : c'est **la** réponse à « pourquoi ça varie ? » | 🟡 |
| A5 | `analyze_runs.py`, puis remplir le gabarit de `03` pour 5 bons, 5 mauvais et 5 ambigus | 30 min | Analyse d'erreurs **réelle**, prédictions 🔮 confirmées ou infirmées | ✅ script prêt |
| A6 | Annoter vous-même 10 à 20 réponses et comparer au juge | 20 min | Premier **accord juge–humain**, pour répondre à « pourquoi faire confiance au juge ? » | ✅ données produites par A3 |

Si le quota bloque A3 et A4 : faire au minimum `prod` × 1 + `det` × 1 sur un sous-ensemble équilibré, par exemple `--only F02 F05 F06 F09 D07 D11 C01 G01 H02 H03 P02 S02`, et **le dire** (n = 12, les IC sont larges).

## Évolutions à présenter (pas avant l'entretien)

| Priorité | Évolution | Effort | Gain |
|---|---|---|---|
| 1 | **Golden set versionné et séparé de l'ingestion** : dans git (`eval/golden_set.jsonl`), avec un hash noté dans chaque run (déjà fait dans `meta.json`), une version **paraphrasée** des questions (contre la fuite lexicale), 30 à 50 vraies questions d'utilisateurs, et plus de questions multi-documents et hors périmètre proche. Une **liste de chunks pertinents** par question (IDs déjà calculables via `offline_checks.json`) | 1 jour | Mesure représentative ; recall@k au sens strict |
| 2 | **Index ou namespace d'évaluation dédié** + vérification avant run (`describe_index_stats`, présence des IDs attendus) | 2 h | Supprime V9, V10 et V11 (variabilité due à l'état de l'index) |
| 3 | 🔧 **Paramètres explicites dans le produit** : `temperature` (0 à 0,2), `seed`, `reasoning_effort`, dans un `Settings` unique (`llm.py:14`, `graph.py:22`) | 1 h | Reproductibilité en production, et pas seulement en évaluation |
| 4 | **Évaluation séparée retrieval / génération** : retrieval sur 200 questions ou plus (peu cher : embeddings et Pinecone seulement, sans LLM) ; génération sur un sous-ensemble | 0,5 jour | Plus de puissance statistique là où c'est peu cher |
| 5 | **Évaluation en CI** : (a) à chaque PR, les contrôles hors ligne + 10 questions « canari » en `det` ; (b) chaque nuit, le golden set complet × 3. On échoue si une métrique baisse au-delà d'un seuil **calibré sur l'écart-type mesuré** (par exemple moins 2 écarts-types, ou un test de McNemar apparié). Nécessite git et une CI : 🔧 | 1 jour | Détection automatique des régressions (changement de prompt, de k, de chunking, de version de librairie) |
| 6 | **Calibrage du juge** : 50 réponses annotées par un humain, kappa de Cohen, ajustement du barème, rejugement × 3 pour mesurer la variance propre du juge | 0,5 jour | On sait combien croire le juge |
| 7 | **Analyse d'erreurs systématique** : étiquette de couche automatique (grille du `03`, §3), tableau de bord par catégorie, revue hebdomadaire des 10 pires réponses | 0,5 jour | On corrige la bonne couche |
| 8 | **Traces et logs des runs** : Langfuse ou LangSmith (prompt envoyé, chunks, scores, tokens et latence par nœud) | 0,5 jour | Diagnostic en production comme en évaluation |
| 9 | 🔧 **Améliorations du système guidées par l'évaluation**, une à la fois, avec mesure avant/après : seuil de score, k=10 + reranker, `cosine` / normalisation, déduplication, suppression de la bibliographie, source et page dans le contexte, chunking plus gros | variable | Chaque changement devient une **décision mesurée** |
| 10 | Métriques RAGAS standard (context precision et recall, answer relevancy) en complément | 0,5 jour | Comparabilité avec l'état de l'art |

## Ordre logique à expliquer au jury
**Mesurer** (golden set, protocole) → **stabiliser la mesure** (température 0, seed, index dédié, N runs) → **diagnostiquer** (couche responsable) → **corriger une couche** → **re-mesurer** → **automatiser** (CI).
