from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def get_llm_chain(retriever):
    llm = ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model="openai/gpt-oss-120b",

    )
#  {context} : rempli par les documents récupérés par le retriever (Pinecone)
#  {input}  : rempli par la question de l'utilisateur

    prompt = ChatPromptTemplate.from_template(
        """
        You are an AI-powered assistant that helps users understand the medicaldocuments they uploaded.

        Your job is to provide clear, accurate, and helpful responses based **only on the provided context**.

        ---

         **Context**:
        {context}   

         **User Question**:
        {input}

        ---

         **Answer**:
        - Respond in a calm, factual, and respectful tone.
        - Use simple explanations when needed.
        - You only answer questions about medical or health topics. If the question is not about a
          medical or health topic, or the context is not medical, say: "Désolé, je n'ai pas trouvé d'information pertinente dans les documents fournis."
        - If the context does not contain the answer, say: "Désolé, je n'ai pas trouvé d'information pertinente dans les documents fournis."
        - Do NOT make up facts.
        - Always answer in French. Only switch language if the question is a full sentence clearly
          written in another language (short keyword questions like "cancer sein ?" are French).
        - If the documents are medical, do NOT give personal medical advice or diagnoses.
        """
    )

    combine_docs_chain = create_stuff_documents_chain(llm, prompt)    #collecte les documents récupérés par le retriever et les passe au LLM pour générer la réponse
    return create_retrieval_chain(retriever, combine_docs_chain) 