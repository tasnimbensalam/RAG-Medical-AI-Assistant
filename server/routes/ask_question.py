from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
from modules.llm import get_llm_chain
from modules.graph import build_graph
from modules.load_vectorstore import get_vectorstore
from logger import logger

router = APIRouter()


@router.post("/ask/")
async def ask_question(question: str = Form(...)):
    try:
        logger.info(f"user query: {question}")

        retriever = get_vectorstore().as_retriever(search_kwargs={"k": 3})
        chain = get_llm_chain(retriever)

        graph = build_graph(retriever, chain)
        result = graph.invoke({"question": question})

        response = {
            "response": result["answer"],
            "sources": result.get("sources", [])
        }

        logger.info(f"query successful (intent: {result.get('intent')})")
        return response

    except Exception as e:
        logger.exception("Error processing question")
        return JSONResponse(status_code=500, content={"error": str(e)})
