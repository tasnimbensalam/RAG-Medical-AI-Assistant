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
    intent: str            # "medical" | "smalltalk"
    context: List[Document]
    answer: str
    sources: List[str]


def classify_intent(state: GraphState) -> GraphState:
    """Node 1: decide if this is a medical question or small talk."""
    llm = ChatGroq(groq_api_key=GROQ_API_KEY, model="openai/gpt-oss-120b")

    prompt = (
        "Classify the user message as exactly one word: "
        "'medical' if it's a health/medical question, "
        "'smalltalk' if it's a greeting or unrelated chit-chat.\n\n"
        f"Message: {state['question']}\n\nAnswer with one word:"
    )
    result = llm.invoke(prompt).content.strip().lower()
    state["intent"] = "medical" if "medical" in result else "smalltalk"
    return state


def route_intent(state: GraphState) -> str:
    """Conditional edge: pick the next node based on intent."""
    return "retrieve_and_answer" if state["intent"] == "medical" else "direct_response"


def retrieve_and_answer(state: GraphState, retriever, chain) -> GraphState:
    """Node 2a: real RAG path — retrieve from Pinecone + generate."""
    result = chain.invoke({"input": state["question"]})
    state["answer"] = result["answer"]
    state["context"] = result.get("context", [])
    state["sources"] = [doc.metadata.get("source", "") for doc in state["context"]]
    return state


def direct_response(state: GraphState) -> GraphState:
    """Node 2b: skip retrieval entirely for greetings/off-topic."""
    state["answer"] = (
        "Hello! I'm a medical assistant — ask me a health-related "
        "question and I'll look it up in the uploaded documents."
    )
    state["sources"] = []
    return state


def build_graph(retriever, chain):
    graph = StateGraph(GraphState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_and_answer", lambda s: retrieve_and_answer(s, retriever, chain))
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