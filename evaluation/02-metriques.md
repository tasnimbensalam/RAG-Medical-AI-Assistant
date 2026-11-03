# 02 — Les métriques

> **Statut honnête** : dans le **code du projet**, aucune métrique de qualité RAG n'est calculée. Le seul indicateur existant est le **taux de réussite des tests unitaires** (23/23).
> Les métriques des sections B et C sont celles que j'ai implémentées dans `prep-entretien/evaluation/scripts/`. **Aucun chiffre de qualité n'existe encore** ; les exemples chiffrés ci-dessous sont soit **mesurés hors ligne**, soit marqués *illustration*.

---

## A. Métrique réellement présente dans le projet

### A1. Taux de réussite des tests unitaires
- **Définition** : nombre de tests pytest qui passent / nombre total.
- **Calcul** : `make test`, soit `pytest tests` (`Makefile`, cible `test`).
- **Ce qu'elle mesure** : que les routes renvoient les bons codes HTTP, que le routage du graphe suit l'intention donnée par un **LLM simulé**, que l'ingestion découpe, identifie et remplace correctement.
- **Ce qu'elle ne mesure pas** : la pertinence des chunks récupérés, la justesse des réponses, les hallucinations, le comportement réel de Groq, Gemini et Pinecone, la latence, le coût.
- **Comment elle peut mentir** : 23/23 donne une impression de qualité alors que **tout le comportement du LLM et de la recherche est mocké**. Un test peut même figer un défaut : `test_ask_returns_500_on_failure` vérifie que le message interne « pinecone down » **est** renvoyé au client.
- **Exemple chiffré (mesuré)** : 23 passed sur 5 exécutions sur 5, en 0,40 à 0,45 s (`results/offline/pytest_repeat.txt`).

---

## B. Métriques implémentées dans `run_eval.py` (pas encore exécutées)

### B1. Routage correct (`routing_ok`)
- **Définition** : l'intention prédite par `classify_intent` (`server/modules/graph.py:20-33`) est égale à l'intention attendue.
- **Calcul** : `rec["intent"] == q["expected_intent"]` (`run_eval.py`, fonction `run_one`). Seulement sur S01 et S02 (2 questions).
- **Mesure** : la fiabilité du nœud de routage, c'est-à-dire le risque qu'une vraie question reçoive « Bonjour ! … ».
- **Ne mesure pas** : le routage sur des formulations variées (2 questions, c'est un indicateur, pas une mesure). Sur les 40 autres questions, on peut aussi compter les `intent=smalltalk` inattendus, ce qui est visible dans le JSONL.
- **Peut mentir** : la classification tourne à **température 0,7** en config `prod` (`graph.py:22`, ChatGroq sans `temperature`), donc le résultat peut changer d'un run à l'autre ; un seul run ne suffit pas.

### B2. Refus détecté et refus correct (`refused`, `refusal_ok`)
- **Définition** : `refused` vaut vrai si la réponse contient la phrase imposée par le prompt « Désolé, je n'ai pas trouvé… » (`server/modules/llm.py:39`). `refusal_ok` vaut vrai si le système refuse **exactement quand il le doit** : refus sur les questions sans réponse, pas de refus sur les questions répondables.
- **Calcul** : recherche de la chaîne normalisée `"désolé, je n'ai pas trouvé"` (apostrophes typographiques unifiées, minuscules).
- **Mesure** : le comportement « je ne sais pas » (H01-H04, P02) et les **faux refus** (refus alors que la réponse est dans les documents, typiquement quand le retrieval a échoué).
- **Ne mesure pas** : un refus formulé autrement (« Je ne peux pas vous donner de recette… »), qui serait compté **faux** ; d'où le juge en complément. Pour P01 (demande de diagnostic), un refus de diagnostic qui oriente vers un médecin est le bon comportement, mais il n'emploie pas forcément la phrase exacte.
- **Peut mentir** : un système qui refuse tout aurait 100 % sur les 5 questions hors périmètre. Il faut **toujours lire les deux côtés** (refus sur les questions sans réponse **et** absence de refus sur les questions répondables).

### B3. hit@3 et evidence_recall@3 (retrieval de production)
- **Définition** :
  - **hit@3** : au moins un des 3 chunks réellement envoyés au LLM contient une phrase de preuve ;
  - **evidence_recall@3** : part des phrases de preuve présentes dans ces 3 chunks (utile pour les listes, contradictions et questions multi-documents, qui en ont plusieurs).
- **Calcul** : `evidence_hits()` cherche chaque preuve normalisée (espaces fusionnés, minuscules, apostrophes unifiées) dans le `page_content` de `state["context"]`, c'est-à-dire **exactement** le contexte du prompt de production.
- **Mesure** : si le LLM **avait** l'information. C'est la métrique la plus importante pour séparer « échec du retrieval » et « échec de la génération ».
- **Ne mesure pas** : la pertinence de chunks qui contiennent l'information **avec d'autres mots** (une paraphrase n'est pas reconnue, ce qui fait un faux négatif) ; elle ignore aussi l'ordre.
- **Peut mentir** : (1) une preuve trop courte est trouvée partout, ce qui fait des faux positifs. Exemple mesuré : la preuve de E01 (« 5.2 ») apparaît dans **6 chunks** et « 65,52% » dans **4 chunks** pour 3 faits différents. (2) Les mots coupés par pypdf : une preuve recopiée sans la coupure ne serait pas trouvée. J'ai donc copié les preuves **depuis le texte extrait**, et les 36/36 sont retrouvées hors ligne.

### B4. hit@10 et MRR@10 (diagnostic)
- **Définition** : on relance `similarity_search_with_score(question, k=10)`. **hit@10** vaut vrai si une preuve est dans les 10 premiers. **MRR@10** = 1 / rang du premier chunk qui contient une preuve (0 si absent). Exemple : bon chunk au rang 1, MRR = 1 ; au rang 4, MRR = 0,25.
- **Mesure** : **est-ce que k=3 est le goulot ?** Si hit@10 est nettement au-dessus de hit@3, l'information existe mais est mal classée, et un reranker ou un k plus grand aiderait. Si hit@10 est aussi bas, le problème est dans les embeddings, le chunking ou la formulation.
- **Ne mesure pas** : ce que voit le LLM (c'est hit@3).
- **Peut mentir** : la recherche de diagnostic est **un second appel**. Avec un index ANN, l'ordre peut légèrement différer de celui du retriever de production (voir `04-variabilite.md`). Les scores (`dotproduct`) sont aussi enregistrés pour étudier le biais de norme.

### B5. Correctness (juge LLM)
- **Définition** : 1 si la réponse contient l'information essentielle de la réponse de référence, 0,5 si elle est partielle, 0 si elle est fausse ou si le système refuse à tort. Pour une référence « REFUS », 1 si le système refuse.
- **Calcul** : `judge()` dans `run_eval.py`, avec le prompt `JUDGE_PROMPT` (question, référence, passages numérotés, réponse), et une sortie JSON analysée par regex. Si le JSON est invalide, on écrit `correctness=None` et `judge_error=True` : **aucun score n'est inventé**.
- **Mesure** : la justesse de bout en bout, du point de vue de l'utilisateur.
- **Ne mesure pas** : si la réponse est justifiée par les passages (c'est la faithfulness), le style, la langue, la longueur.
- **Peut mentir** : voir la section D sur les biais du juge.

### B6. Faithfulness (juge LLM)
- **Définition** : la part des affirmations factuelles de la réponse qui sont **justifiées par les passages fournis**. C'est la métrique « anti-hallucination ».
- **Calcul** : même appel au juge ; le champ `unsupported_claims` liste les affirmations non justifiées, ce qui rend l'analyse d'erreurs lisible.
- **Mesure** : si le LLM invente au-delà du contexte (avec la température 0,7 et un modèle généraliste qui « sait » des choses sur le cancer du sein, c'est le risque principal).
- **Ne mesure pas** : la justesse. Une réponse fidèle à un **mauvais** chunk (par exemple 65,52 % attribué au carcinome alors qu'il s'agit de la technique de Patey) peut être fidèle **et** fausse. Il faut donc toujours lire correctness et faithfulness ensemble.
- **Peut mentir** : un refus vaut 1 par construction. Un système qui refuse beaucoup a une faithfulness parfaite.

### B7. Latence et tokens
- **Calcul** : `time.perf_counter()` autour de `graph.invoke`, et `get_usage_metadata_callback()` (langchain-core) qui additionne `input_tokens` et `output_tokens` par modèle, soit la classification et la génération.
- **Mesure** : le coût réel et la durée des 2 appels LLM + embedding + Pinecone. Les tokens de raisonnement de `gpt-oss-120b` sont inclus dans la sortie si Groq les déclare (à vérifier sur le premier run).
- **Ne mesure pas** : la latence perçue dans l'UI (Streamlit, réseau), le temps d'attente dû aux quotas.

---

## C. Statistiques d'agrégation (`analyze_runs.py`, hors ligne)
- **Moyenne par run, puis moyenne et écart-type entre runs** : mesure la variabilité due au tirage du LLM (température, routage).
- **IC 95 % par bootstrap sur les questions** : on rééchantillonne les 42 questions avec remise 2 000 fois (seed 0). Il mesure l'incertitude liée au **petit nombre de questions**, qui est la plus grande ici.
- **IC de Wilson** pour les proportions (hit@3, refus correct) : plus juste que « p ± 1,96·√(p(1−p)/n) » quand n est petit.
- **Stabilité** : nombre de questions dont le score du juge change entre runs ; nombre de réponses identiques au caractère près.
- **Par catégorie** : correctness moyenne par type de question, pour l'analyse d'erreurs.

---

## D. Le juge LLM : prompt, modèle, biais, variabilité

- **Modèle proposé** : `llama-3.3-70b-versatile` sur Groq, à **température 0 et seed 42**. **À CONFIRMER AVEC MOI** : ce modèle est-il disponible sur votre compte, et ses quotas suffisent-ils ? Vérifiez dans la console Groq.
- **Pourquoi un autre modèle que le générateur** (`openai/gpt-oss-120b`) : limiter l'**auto-complaisance** (un modèle juge plus favorablement des textes qui lui ressemblent).
- **Biais connus des juges LLM**, et ce que j'ai fait :
  | Biais | Effet | Mitigation |
  |---|---|---|
  | Complaisance / auto-préférence | Surnote | Modèle juge différent |
  | Biais de longueur | Préfère les réponses longues | Barème centré sur « information essentielle » ; à surveiller |
  | Sensibilité au prompt | Le score dépend des mots du barème | Prompt figé, versionné dans le script |
  | Non-déterminisme | Même entrée, score différent | Température 0 et seed, mais pas de garantie côté fournisseur : **à mesurer** en rejugeant les mêmes réponses |
  | Juge « qui sait » | Valide une réponse vraie dans le monde mais absente du contexte | La faithfulness est jugée **contre les passages**, pas contre le monde |
  | Granularité grossière | 0 / 0,5 / 1 est sommaire | Assumé : c'est plus stable qu'une note sur 10 |
- **Calibrage nécessaire avant de faire confiance au juge** : noter vous-même 20 réponses, puis mesurer l'accord avec le juge (part d'accord exact et kappa de Cohen). Sans ce calibrage, je présenterais les scores du juge comme **indicatifs**.

---

## E. Métriques qui manquent (et pourquoi)
| Métrique | Pourquoi elle manque | Comment l'ajouter |
|---|---|---|
| Recall@k au sens strict (tous les chunks pertinents) | Il faudrait annoter **tous** les chunks pertinents par question, pas seulement une preuve | Annoter les IDs de chunks pertinents (calculables hors ligne : `offline_checks.json` donne déjà les IDs qui contiennent les preuves) |
| nDCG | Demande des niveaux de pertinence gradués | Après annotation graduée |
| Context precision (RAGAS) | Part des chunks récupérés qui sont utiles | Juge LLM ou annotation |
| Answer relevancy (RAGAS) | La réponse répond-elle à la question posée ? | RAGAS, ou ajout d'un champ au juge |
| Citation accuracy | Le projet ne produit **pas** de citations (le LLM ne voit pas la source : prompt par défaut `{page_content}`) | Prérequis : modifier le prompt (évolution) |
| Respect de la langue | Règle `llm.py:41-42` non mesurée | Détection de langue sur E01 et K01 |
| Coût par question en euros | Tarifs non figés | tokens × tarif publié (à vérifier) |
| Accord juge–humain | Non fait | 20 annotations humaines |
| Robustesse aux reformulations | Golden set lexicalement proche du texte | Version paraphrasée du golden set |

---

## F. Exemples chiffrés disponibles aujourd'hui
| Chiffre | Valeur | Statut |
|---|---|---|
| Tests unitaires | 23/23, 5 exécutions sur 5 | Mesuré |
| Chunks indexables | 80 (FALC) + 97 (article) = 177 | Mesuré hors ligne (= ce que `index_pdf` produit, si l'index a été construit avec le même code et la même version de pypdf : **À CONFIRMER**) |
| Preuves présentes dans au moins un chunk | 36/36 | Mesuré hors ligne : **plafond** du hit@k, pas le hit@k réel |
| Bibliographie | 28,9 % des chunks de `document.pdf` | Mesuré, ce sont des chunks de bruit potentiels |
| Contexte envoyé au LLM | ≤ 3 × 499 caractères | Déduit du code et des longueurs mesurées |
| Coût d'une campagne de 5 runs `prod` | ≈ 394 k tokens d'entrée et 165 k de sortie | **Estimation** (dry-run) |
| hit@3, correctness, faithfulness | — | **Non mesurés** : il faut lancer `run_eval.py` |
