from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.documents import Document
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class GraphState(TypedDict):
    question: str
    intent: str            # "question" | "smalltalk"
    context: List[Document]
    answer: str
    sources: List[str]


def classify_intent(state: GraphState) -> GraphState:
    """Node 1: decide if the message needs the documents or is just small talk."""
    llm = ChatGroq(groq_api_key=GROQ_API_KEY, model="openai/gpt-oss-120b")

    prompt = (
        "Classify the user message as exactly one word: "
        "'smalltalk' only if it's a greeting, a thank-you or chit-chat that "
        "asks for no information, otherwise 'question'.\n\n"
        f"Message: {state['question']}\n\nAnswer with one word:"
    )
    result = llm.invoke(prompt).content.strip().lower()
    # Default to retrieval: a wrongly skipped question is worse than a greeting sent to RAG.
    state["intent"] = "smalltalk" if "smalltalk" in result else "question"
    return state


def route_intent(state: GraphState) -> str:
    """Conditional edge: pick the next node based on intent."""
    return "retrieve_and_answer" if state["intent"] == "question" else "direct_response"


def retrieve_and_answer(state: GraphState, chain) -> GraphState:
    """Node 2a: real RAG path — retrieve from Pinecone + generate."""
    result = chain.invoke({"input": state["question"]})
    state["answer"] = result["answer"]
    state["context"] = result.get("context", [])
    # dict.fromkeys dedupes while keeping order (several chunks often come from the same PDF).
    state["sources"] = list(dict.fromkeys(doc.metadata.get("source", "") for doc in state["context"]))
    return state


def direct_response(state: GraphState) -> GraphState:
    """Node 2b: skip retrieval entirely for greetings/off-topic."""
    state["answer"] = (
        "Bonjour ! Je suis un assistant qui répond à partir de vos documents — "
        "posez-moi une question sur les PDF que vous avez uploadés."
    )
    state["sources"] = []
    return state


def build_graph(retriever, chain):
    graph = StateGraph(GraphState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_and_answer", lambda s: retrieve_and_answer(s, chain))    
    graph.add_node("direct_response", direct_response)
    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "retrieve_and_answer": "retrieve_and_answer",
            "direct_response": "direct_response",
        },
    )
    graph.add_edge("retrieve_and_answer", END)
    graph.add_edge("direct_response", END)

    return graph.compile()