from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from modules import graph


def _fake_llm(reply: str):
    llm = MagicMock()
    llm.invoke.return_value.content = reply
    return llm


def _fake_chain():
    chain = MagicMock()
    chain.invoke.return_value = {
        "answer": "Diabetes is a chronic condition.",
        "context": [
            Document(page_content="...", metadata={"source": "diabetes.pdf"}),
            Document(page_content="...", metadata={"source": "guide.pdf"}),
            Document(page_content="...", metadata={"source": "diabetes.pdf"}),
        ],
    }
    return chain


def test_route_intent():
    assert graph.route_intent({"intent": "question"}) == "retrieve_and_answer"
    assert graph.route_intent({"intent": "smalltalk"}) == "direct_response"


def test_classify_intent_question():
    with patch.object(graph, "ChatGroq", return_value=_fake_llm("Question")):
        state = graph.classify_intent({"question": "What is diabetes?"})
    assert state["intent"] == "question"


def test_classify_intent_defaults_to_question():
    with patch.object(graph, "ChatGroq", return_value=_fake_llm("unsure")):
        state = graph.classify_intent({"question": "Résume le chapitre 2"})
    assert state["intent"] == "question"


def test_classify_intent_smalltalk():
    with patch.object(graph, "ChatGroq", return_value=_fake_llm("smalltalk")):
        state = graph.classify_intent({"question": "hello"})
    assert state["intent"] == "smalltalk"


def test_retrieve_and_answer_collects_sources():
    state = graph.retrieve_and_answer({"question": "What is diabetes?"}, _fake_chain())
    assert state["answer"] == "Diabetes is a chronic condition."
    assert state["sources"] == ["diabetes.pdf", "guide.pdf"]


def test_graph_smalltalk_skips_retrieval():
    chain = _fake_chain()
    with patch.object(graph, "ChatGroq", return_value=_fake_llm("smalltalk")):
        result = graph.build_graph(chain).invoke({"question": "hi"})
    assert "vos documents" in result["answer"]
    assert result["sources"] == []
    chain.invoke.assert_not_called()


def test_graph_medical_uses_chain():
    chain = _fake_chain()
    with patch.object(graph, "ChatGroq", return_value=_fake_llm("question")):
        result = graph.build_graph(chain).invoke({"question": "What is diabetes?"})
    assert result["answer"] == "Diabetes is a chronic condition."
    assert result["sources"] == ["diabetes.pdf", "guide.pdf"]
    chain.invoke.assert_called_once_with({"input": "What is diabetes?"})