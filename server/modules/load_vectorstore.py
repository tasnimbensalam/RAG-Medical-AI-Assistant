import os
import time
from pathlib import Path
from dotenv import load_dotenv
from tqdm.auto import tqdm
from pinecone import Pinecone, ServerlessSpec
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings


load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = "europe-west1-gcp-free"
PINECONE_INDEX_NAME = "medical-docs"

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

UPLOAD_DIR = "./uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

#initialize pinecone instance 
pc=Pinecone(api_key=PINECONE_API_KEY)
spec=ServelessSpec(cloud="aws", region=PINECONE_ENV)
existing_indexes=[index.name for index in pc.list_indexes()]

if PINECONE_INDEX_NAME not in existing_indexes:
    print(f"Creating Pinecone index: {PINECONE_INDEX_NAME}")
    pc.create_index(name=PINECONE_INDEX_NAME, dimension=786, metric="dotproduct", spec=spec)
    while not pc.describe_index(PINECONE_INDEX_NAME).status.ready:
        print("Waiting for the index to be ready...")
        time.sleep(5)
index=pc.Index(PINECONE_INDEX_NAME)

#load,split and embed pdf documents
def load_vectorstore(uploaded_files):
    embed_model=GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    file_paths=[]

    #1. upload
    for file in uploaded_files:
        save_path=Path(UPLOAD_DIR)/file.filename
        with open(save_path,"wb") as f:
            f.write(file.file.read())
        file_paths.append(save_path)

    #2. split
    for file_path in file_path:
        loader=PyPDFLoader(file_path)
        documents=loader.load()

        splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )
        chunks = splitter.split_documents(documents)
        texts=[chunk.page_content for chunk in chunks]
        metadata=[chunk.metadata for chunk in chunks]
        ids=[f"{Path(file_path).stem}-{i}" for i in range(len(chunks))]


    #3. embed  
        print(f"Embedding and upserting {len(chunks)} chunks from {file_path} into Pinecone index...")

        embeddings = embed_model.embed_documents(texts)
        #4. upsert
        print("Upserting embeddings...")
        with tqdm(total=len(embeddings),desc="Upserting to Pinecone") as progress:
          index.upsert(vectors=zip(ids, embeddings, metadata))
          progress.update(len(embeddings))
        print(f"Upload complete for {file_path}")
  
