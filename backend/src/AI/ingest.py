import logging
import os
import tempfile
import time
from pathlib import Path
import requests
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownTextSplitter,
    RecursiveCharacterTextSplitter,
)
from academics.models import Material
from courses.models import LearningResource
from .extract import load_pdf
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
EMBED_BATCH_SIZE = int(os.environ.get("GEMINI_EMBED_BATCH_SIZE", 50))
EMBED_RPM = int(os.environ.get("GEMINI_EMBED_RPM", 100))
EMBED_MAX_RETRY = 5

SOURCE_MATERIAL = "material"
SOURCE_RESOURCE = "resource"


def text_splitter():
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )


def markdown_splitter():
    return MarkdownTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)


def select_new(documents, ids, existing_ids):
    existing = set(existing_ids)
    new_documents = []
    new_ids = []

    for doc, doc_id in zip(documents, ids):
        if doc_id not in existing:
            new_documents.append(doc)
            new_ids.append(doc_id)
    return new_documents, new_ids


def fetch_existing_ids(store, ids):
    try:
        return store.get(ids=ids).get("ids", [])
    except Exception:
        logger.exception("Không kiểm tra được id đã tồn tại, sẽ nạp lại toàn bộ")
        return []


def embed_batch_with_retry(store, batch, batch_ids):
    for attempt in range(1, EMBED_MAX_RETRY + 1):
        try:
            store.add_documents(batch, ids=batch_ids)
            return True
        except Exception as exc:
            is_quota_error = "RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc)
            if not is_quota_error or attempt == EMBED_MAX_RETRY:
                raise
            wait = 60 * attempt
            logger.warning(
                "Chạm giới hạn quota, chờ %ss rồi thử lại (lần %s/%s)",
                wait,
                attempt,
                EMBED_MAX_RETRY,
            )
            time.sleep(wait)
    return False


def add_documents(documents, ids):
    store = get_vector_store()
    documents, ids = select_new(documents, ids, fetch_existing_ids(store, ids))

    if not documents:
        logger.info("Toàn bộ chunk đã có sẵn trong vector store, không cần nạp lại")
        return 0

    if EMBED_RPM:
        min_seconds_per_batch = 60 * EMBED_BATCH_SIZE / EMBED_RPM
    else:
        min_seconds_per_batch = 0

    for start in range(0, len(documents), EMBED_BATCH_SIZE):
        batch = documents[start : start + EMBED_BATCH_SIZE]
        batch_ids = ids[start : start + EMBED_BATCH_SIZE]

        started_at = time.monotonic()

        embed_batch_with_retry(store, batch, batch_ids)
        logger.info(
            "Đã nạp %s/%s chunk",
            min(start + len(batch), len(documents)),
            len(documents),
        )

        is_last_batch = start + EMBED_BATCH_SIZE >= len(documents)
        if not is_last_batch:
            remaining = min_seconds_per_batch - (time.monotonic() - started_at)
            if remaining > 0:
                time.sleep(remaining)

    return len(documents)


def material_metadata(material, page_number):
    return {
        "source_type": SOURCE_MATERIAL,
        "material_id": material.id,
        "subject_id": material.subject_id,
        "grade_id": material.grade_id,
        "title": material.name,
        "page": page_number,
    }


def document_id(source_type, source, page_number, chunk_index):
    return f"{source_type}:{source}:{page_number}:{chunk_index}"


def download_cloudinary_file(file_field):
    if not file_field:
        return None

    if hasattr(file_field, "url"):
        file_url = file_field.url
    else:
        file_url = str(file_field)
    try:
        response = requests.get(file_url, stream=True, timeout=20)
        if response.status_code == 200:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                temp_file.write(chunk)
            temp_file.close()
            return temp_file.name
    except requests.RequestException:
        logger.exception("Lỗi tải file từ Cloudinary: %s", file_url)
    return None


def resolve_source_file(instance):
    local_file = getattr(instance, "local_file", None)
    if local_file:
        return local_file.path, False
    return download_cloudinary_file(instance.file_url), True


def pending_queryset(model):
    return model.objects.filter(
        is_active=True,
        rag_status__in=[model.RAGStatus.PENDING, model.RAGStatus.FAILED],
    )


def ingest_material(material):
    splitter = markdown_splitter()
    material.mark_rag_processing()
    local_path, is_temp = resolve_source_file(material)

    if not local_path:
        material.mark_rag_failed("Không lấy được tệp tài liệu.")
        return 0

    added = 0
    try:
        pages = load_pdf(Path(local_path))
        documents, ids = [], []

        for page in pages:
            page_number = page.metadata.get("page", 0)

            for index, chunk in enumerate(splitter.split_documents([page])):
                if not chunk.page_content.strip():
                    continue
                chunk.metadata = material_metadata(material, page_number)
                documents.append(chunk)
                ids.append(
                    document_id(SOURCE_MATERIAL, str(material.id), page_number, index)
                )

        if documents:
            added = add_documents(documents, ids)

        material.mark_rag_indexed(len(documents))

    except Exception as exc:
        material.mark_rag_failed(f"{type(exc).__name__}: {exc}")
        logger.exception("Lỗi khi ingest Material ID %s", material.id)
    finally:
        if is_temp and os.path.exists(local_path):
            os.remove(local_path)

    return added


def ingest_materials():
    total = 0
    for material in pending_queryset(Material).select_related("subject", "grade"):
        total += ingest_material(material)
    return total


def ingest_resource(resource):
    resource.mark_rag_processing()
    chunks = []
    metadata = {
        "source_type": SOURCE_RESOURCE,
        "resource_id": resource.id,
        "course_id": resource.lesson.chapter.course_id,
        "lesson_id": resource.lesson_id,
        "title": resource.title,
    }

    if resource.content:
        document = Document(page_content=resource.content, metadata=metadata)
        chunks = text_splitter().split_documents([document])

    elif resource.file_url:
        local_path = download_cloudinary_file(resource.file_url)
        if not local_path:
            resource.mark_rag_failed("Không tải được tệp từ Cloudinary.")
            return 0
        try:
            pages = load_pdf(Path(local_path))
            chunks = markdown_splitter().split_documents(pages)
            for chunk in chunks:
                chunk.metadata.update(metadata)
        except Exception as exc:
            resource.mark_rag_failed(f"{type(exc).__name__}: {exc}")
            logger.exception("Lỗi xử lý file Resource ID %s", resource.id)
            return 0
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    if not chunks:
        resource.mark_rag_failed("Tài nguyên không có nội dung để nạp.")
        return 0

    ids = []
    for index in range(len(chunks)):
        ids.append(document_id(SOURCE_RESOURCE, str(resource.id), 0, index))

    try:
        added = add_documents(chunks, ids)
    except Exception as exc:
        resource.mark_rag_failed(f"{type(exc).__name__}: {exc}")
        logger.exception("Lỗi nạp vector Resource ID %s", resource.id)
        return 0

    resource.mark_rag_indexed(len(chunks))
    return added


def ingest_learning_resources():
    resources = pending_queryset(LearningResource).select_related(
        "lesson__chapter__course"
    )

    total = 0
    for resource in resources:
        total += ingest_resource(resource)
    return total
