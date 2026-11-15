# RAG Medical Assistant

Assistant conversationnel qui répond à des questions à partir de documents médicaux PDF uploadés par l'utilisateur.
Les réponses s'appuient uniquement sur le contenu des documents et citent leurs sources.

## Stack

- **Backend** : FastAPI + LangChain / LangGraph
- **Frontend** : Streamlit
- **LLM** : Groq (`openai/gpt-oss-120b`)
- **Embeddings** : Google Generative AI
- **Base vectorielle** : Pinecone
- **Déploiement** : Docker Compose + Makefile

## Fonctionnement

1. **Upload** (`POST /upload_pdfs/`) : lecture du PDF (pypdf), nettoyage, vérification que le document est bien médical, découpage en chunks, embeddings, puis indexation dans Pinecone. Un fichier déjà indexé est remplacé.
2. **Question** (`POST /ask/`) : un graphe LangGraph classe le message.
   - *smalltalk* (salutation, remerciement) : réponse directe, sans recherche.
   - *question* : récupération des `k` passages les plus proches, puis génération de la réponse en français avec les sources.

Si l'information n'est pas dans les documents, l'assistant le dit au lieu d'inventer. Il ne donne ni diagnostic ni conseil médical personnel.

## Structure

```
server/        API FastAPI (routes/, modules/, tests/)
client/        Interface Streamlit (chat, upload, export de l'historique)
evaluation/    Golden set (90 questions), scripts d'évaluation et rapports
Makefile       Commandes d'installation, de lancement et de test
```

## Installation

Créer `server/.env` :

```env
GOOGLE_API_KEY=...
GROQ_API_KEY=...
PINECONE_API_KEY=...
# optionnels
PINECONE_INDEX_NAME=medical-docs
RETRIEVER_K=10
```

### Avec Docker

```bash
make docker-init   # vérifie Docker et les clés, construit les images
make run           # lance le serveur et le client
```

### Sans Docker (nécessite `uv`)

```bash
make local-install
make local-run
```

- Interface : http://localhost:8501
- API : http://localhost:8000 (documentation : `/docs`)

## Commandes utiles

| Commande | Rôle |
|---|---|
| `make test` | Tests unitaires (Pinecone, Google et Groq sont mockés) |
| `make smoke` | Vérifie que les conteneurs répondent |
| `make logs` / `make status` | Logs et état des conteneurs |
| `make stop` / `make clean` | Arrêt / suppression des conteneurs, images et caches |

## Évaluation

Le golden set (`evaluation/golden_set.jsonl`) contient 90 questions avec réponse attendue, source et passages de preuve.

```bash
python evaluation/scripts/run_eval.py --k 5 --runs 3 --confirm   # sans --confirm : dry-run
python evaluation/scripts/analyze_runs.py --k 5                    # génère le rapport
```

Métriques : hit@k, evidence_recall, MRR, refus corrects, routage, et un LLM juge pour la justesse et la fidélité.
Exemple (k=5, 3 runs) : hit@5 ≈ 92 %, correctness ≈ 88 %, faithfulness ≈ 97 %. Détails dans `evaluation/results/`.