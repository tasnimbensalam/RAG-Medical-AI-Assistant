from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
from modules.llm import get_llm_chain
from modules.query_handlers import query_chain
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pinecone import Pinecone
from pydantic import Field, PrivateAttr
from typing import List, Optional
from logger import logger
import os

router = APIRouter()


class SimpleRetriever(BaseRetriever):
    tags: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[dict] = Field(default_factory=dict)
    _docs: List[Document] = PrivateAttr(default_factory=list)

    def __init__(self, documents: List[Document], **kwargs):
        super().__init__(**kwargs)
        self._docs = documents

    def _get_relevant_documents(self, query: str) -> List[Document]:
        return self._docs


@router.post("/ask/")
async def ask_question(question: str = Form(...)):
    try:
        logger.info(f"user query: {question}")

        # Embed model + Pinecone setup
        pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        index = pc.Index("medical-docs")
        embed_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", output_dimensionality=786)
        embedded_query = embed_model.embed_query(question)
        res = index.query(vector=embedded_query, top_k=3, include_metadata=True)

        docs = [
            Document(
                page_content=match["metadata"].get("text", ""),
                metadata=match["metadata"]
            ) for match in res["matches"]
        ]

        retriever = SimpleRetriever(docs)
        chain = get_llm_chain(retriever)
        result = query_chain(chain, question)

        logger.info("query successful")
        return result

    except Exception as e:
        logger.exception("Error processing question")
        return JSONResponse(status_code=500, content={"error": str(e)})