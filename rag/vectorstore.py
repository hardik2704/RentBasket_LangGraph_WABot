# RAG Vector Store for RentBasket Knowledge Base
# Uses ChromaDB with OpenAI embeddings

import os
from typing import List
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, RETRIEVER_K
from data.knowledge_base import RENTBASKET_KNOWLEDGE_BASE


def create_knowledge_vectorstore(persist_directory: str = None) -> Chroma:
    """
    Create a ChromaDB vector store from the RentBasket knowledge base.
    
    Args:
        persist_directory: Optional directory to persist the vector store
        
    Returns:
        Chroma vector store instance
    """
    # Initialize embeddings
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    
    # Create document from knowledge base
    documents = [Document(
        page_content=RENTBASKET_KNOWLEDGE_BASE,
        metadata={"source": "rentbasket_knowledge_base", "type": "company_info"}
    )]
    
    # Split into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks from knowledge base")
    
    # Create vector store
    if persist_directory:
        if not os.path.exists(persist_directory):
            os.makedirs(persist_directory)
        
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=persist_directory,
            collection_name="rentbasket_knowledge"
        )
    else:
        # In-memory store
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name="rentbasket_knowledge"
        )
    
    return vectorstore


def get_knowledge_retriever(vectorstore: Chroma = None, k: int = None):
    """
    Get a retriever for the knowledge base.
    
    Args:
        vectorstore: Optional existing vector store. Creates new if None.
        k: Number of chunks to retrieve (default from config)
        
    Returns:
        Retriever instance
    """
    if vectorstore is None:
        vectorstore = create_knowledge_vectorstore()
    
    if k is None:
        k = RETRIEVER_K
    
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )
    
    return retriever


def search_knowledge(query: str, vectorstore: Chroma = None, k: int = None) -> List[str]:
    """
    Search the knowledge base and return relevant chunks.
    
    Args:
        query: Search query
        vectorstore: Optional existing vector store
        k: Number of results to return
        
    Returns:
        List of relevant text chunks
    """
    retriever = get_knowledge_retriever(vectorstore, k)
    docs = retriever.invoke(query)
    
    if not docs:
        return ["No relevant information found in the knowledge base."]
    
    results = []
    for doc in docs:
        results.append(doc.page_content)
    
    return results
