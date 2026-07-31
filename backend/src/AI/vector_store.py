import os
from functools import lru_cache

import chromadb
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

"""
    Khởi tạo lazy (singleton) cho embedding model, Chroma và LLM.

    Việc khởi tạo chỉ chạy ở lần gọi đầu tiên nên import module này không làm
    chậm quá trình khởi động Django, và toàn hệ thống chỉ dùng chung một
    PersistentClient trỏ vào cùng thư mục Chroma.
"""

COLLECTION_NAME = "learning_materials"
# Tên model đọc từ env để đổi được khi Google ngừng hỗ trợ phiên bản cũ
# (text-embedding-004 và gemini-1.5-flash đã bị gỡ khỏi API).
EMBEDDING_MODEL = os.environ.get(
    "GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001"
)
# Dùng alias "-latest" để không phải sửa code mỗi lần Google khai tử một phiên bản.
LLM_MODEL = os.environ.get("GEMINI_LLM_MODEL", "gemini-flash-latest")


def _google_api_key() -> str:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ImproperlyConfigured(
            "Thiếu biến môi trường GOOGLE_API_KEY để dùng tính năng AI."
        )
    return api_key


@lru_cache(maxsize=1)
def get_embeddings():
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL, google_api_key=_google_api_key()
    )


@lru_cache(maxsize=1)
def get_vector_store():
    client = chromadb.PersistentClient(path=str(settings.CHROMA_DB_PATH))
    return Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
    )


@lru_cache(maxsize=1)
def get_llm():
    return ChatGoogleGenerativeAI(
        model=LLM_MODEL, google_api_key=_google_api_key(), temperature=0.3
    )
