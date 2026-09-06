import os
from functools import lru_cache
import chromadb
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

COLLECTION_NAME = "learning_materials"
EMBEDDING_MODEL = os.environ.get(
    "GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001"
)
LLM_MODEL = os.environ.get("GEMINI_LLM_MODEL", "gemini-flash-latest")
OCR_MODEL = os.environ.get("GEMINI_OCR_MODEL", LLM_MODEL)


def google_api_key():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ImproperlyConfigured(
            "Thiếu biến môi trường GOOGLE_API_KEY để dùng tính năng AI."
        )
    return api_key


@lru_cache(maxsize=1)
def get_embeddings():
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL, google_api_key=google_api_key()
    )


@lru_cache(maxsize=1)
def get_vector_store():
    client = chromadb.PersistentClient(path=str(settings.CHROMA_DB_PATH))
    return Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        collection_metadata={"hnsw:space": "cosine"},
    )


@lru_cache(maxsize=1)
def get_llm():
    return ChatGoogleGenerativeAI(model=LLM_MODEL, google_api_key=google_api_key())


@lru_cache(maxsize=1)
def get_ocr_llm():
    return ChatGoogleGenerativeAI(model=OCR_MODEL, google_api_key=google_api_key())
