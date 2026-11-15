from unittest.mock import MagicMock, patch

from routes import ask_question as ask_module
from routes import upload_pdfs as upload_module


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ask_requires_question(client):
    r = client.post("/ask/", data={})
    assert r.status_code == 422


def test_ask_returns_answer_and_sources(client):
    vectorstore = MagicMock()
    compiled_graph = MagicMock()
    compiled_graph.invoke.return_value = {
        "answer": "Some answer",
        "sources": ["doc.pdf"],
        "intent": "question",
    }

    with patch.object(ask_module, "get_vectorstore", return_value=vectorstore), \
         patch.object(ask_module, "get_llm_chain"), \
         patch.object(ask_module, "build_graph", return_value=compiled_graph):
        r = client.post("/ask/", data={"question": "What is diabetes?"})

    assert r.status_code == 200
    assert r.json() == {"response": "Some answer", "sources": ["doc.pdf"]}
    vectorstore.as_retriever.assert_called_once_with(search_kwargs={"k": ask_module.TOP_K})

def test_ask_returns_500_on_failure(client):
    with patch.object(ask_module, "get_vectorstore", side_effect=RuntimeError("pinecone down")):
        r = client.post("/ask/", data={"question": "What is diabetes?"})
    assert r.status_code == 500
    assert "pinecone down" in r.json()["error"]


def test_upload_pdfs_success(client):
    result = {"processed": {"doc.pdf": 4}, "errors": {}}
    with patch.object(upload_module, "load_vectorstore", return_value=result) as load:
        r = client.post(
            "/upload_pdfs/",
            files=[("files", ("doc.pdf", b"%PDF-1.4 fake", "application/pdf"))],
        )
    assert r.status_code == 200
    assert r.json() == result
    load.assert_called_once()


def test_upload_pdfs_returns_400_when_nothing_indexed(client):
    result = {"processed": {}, "errors": {"scan.pdf": "aucun texte trouvé"}}
    with patch.object(upload_module, "load_vectorstore", return_value=result):
        r = client.post(
            "/upload_pdfs/",
            files=[("files", ("scan.pdf", b"%PDF-1.4 fake", "application/pdf"))],
        )
    assert r.status_code == 400
    assert r.json() == result


def test_upload_pdfs_returns_500_on_failure(client):
    with patch.object(upload_module, "load_vectorstore", side_effect=RuntimeError("pinecone down")):
        r = client.post(
            "/upload_pdfs/",
            files=[("files", ("doc.pdf", b"not a pdf", "application/pdf"))],
        )
    assert r.status_code == 500
    assert "pinecone down" in r.json()["error"]
