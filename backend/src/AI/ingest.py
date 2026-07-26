import os
import tempfile
import requests
import chromadb
from django.conf import settings

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from academics.models import Material
from courses.models import LearningResource

CHROMA_PATH = getattr(settings, "CHROMA_DB_PATH", "./chroma_db")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path=CHROMA_PATH)
vector_store = Chroma(
    client=client,
    collection_name="learning_materials",
    embedding_function=embeddings,
)


def download_cloudinary_file(file_field) -> str | None:
    """Tải file từ Cloudinary URL về file tạm thời."""
    if not file_field:
        return None

    file_url = file_field.url if hasattr(file_field, "url") else str(file_field)
    try:
        response = requests.get(file_url, stream=True, timeout=20)
        if response.status_code == 200:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                temp_file.write(chunk)
            temp_file.close()
            return temp_file.name
    except Exception as e:
        print(f"Lỗi tải file từ Cloudinary ({file_url}): {e}")
    return None


def ingest_materials():
    """Ingest tài liệu chung từ academics.Material"""
    materials = Material.objects.filter(is_rag_indexed=False, is_active=True)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

    for mat in materials:
        local_path = download_cloudinary_file(mat.file_url)
        if not local_path:
            continue

        try:
            loader = PyPDFLoader(local_path)
            docs = loader.load()
            chunks = text_splitter.split_documents(docs)

            # Metadata chuẩn cho Material
            for chunk in chunks:
                chunk.metadata.update(
                    {
                        "source_type": "material",
                        "material_id": mat.id,
                        "subject_id": mat.subject_id,
                        "grade_id": mat.grade_id,
                        "title": mat.name,
                    }
                )

            if chunks:
                vector_store.add_documents(chunks)

            mat.is_rag_indexed = True
            mat.save(update_fields=["is_rag_indexed"])
            print(f"Đã Ingest thành công Material ID: {mat.id}")

        except Exception as e:
            print(f"Lỗi khi Ingest Material ID {mat.id}: {e}")
        finally:
            if local_path and os.path.exists(local_path):
                os.remove(local_path)


def ingest_learning_resources():
    """Ingest tài liệu bài học từ courses.LearningResource"""
    resources = LearningResource.objects.filter(
        is_rag_indexed=False, is_active=True
    ).select_related("lesson__chapter__course")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)

    for res in resources:
        all_chunks = []
        course_id = res.lesson.chapter.course_id
        lesson_id = res.lesson_id

        # TH1: Nội dung bài học dạng text
        if res.content:
            doc = Document(
                page_content=res.content,
                metadata={
                    "source_type": "resource",
                    "resource_id": res.id,
                    "course_id": course_id,
                    "lesson_id": lesson_id,
                    "title": res.title,
                },
            )
            all_chunks.extend(text_splitter.split_documents([doc]))

        # TH2: Tài liệu dạng PDF upload qua Cloudinary
        elif res.file_url:
            local_path = download_cloudinary_file(res.file_url)
            if local_path:
                try:
                    loader = PyPDFLoader(local_path)
                    docs = loader.load()
                    chunks = text_splitter.split_documents(docs)
                    for chunk in chunks:
                        chunk.metadata.update(
                            {
                                "source_type": "resource",
                                "resource_id": res.id,
                                "course_id": course_id,
                                "lesson_id": lesson_id,
                                "title": res.title,
                            }
                        )
                    all_chunks.extend(chunks)
                except Exception as e:
                    print(f"Lỗi xử lý file Resource ID {res.id}: {e}")
                finally:
                    if os.path.exists(local_path):
                        os.remove(local_path)

        if all_chunks:
            vector_store.add_documents(all_chunks)

        res.is_rag_indexed = True
        res.save(update_fields=["is_rag_indexed"])
        print(f"Đã Ingest thành công LearningResource ID: {res.id}")


def run_full_ingestion():
    """Hàm kích hoạt chạy toàn bộ tiến trình Ingest"""
    ingest_materials()
    ingest_learning_resources()
