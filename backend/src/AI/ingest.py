import logging
import os
import tempfile
import time
from pathlib import Path

import requests
from django.conf import settings
from langchain_community.document_loaders import PyMuPDFLoader, PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from academics.models import Material
from courses.models import LearningResource

from .vector_store import get_vector_store

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
# Số chunk gửi đi nhúng vector mỗi lần.
EMBED_BATCH_SIZE = int(os.environ.get("GEMINI_EMBED_BATCH_SIZE", 50))
# Gemini free tier tính MỖI ĐOẠN TEXT là một request và giới hạn 100 request/phút,
# nên phải tự giãn nhịp thay vì bắn liên tục.
EMBED_RPM = int(os.environ.get("GEMINI_EMBED_RPM", 100))
EMBED_MAX_RETRY = 5

SOURCE_TEXTBOOK = "textbook"
SOURCE_MATERIAL = "material"
SOURCE_RESOURCE = "resource"


def _text_splitter():
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )


def select_new(documents, ids, existing_ids):
    """Bỏ các chunk đã có trong vector store để lần chạy sau nạp tiếp phần còn thiếu."""
    existing = set(existing_ids)
    pairs = [
        (doc, doc_id) for doc, doc_id in zip(documents, ids) if doc_id not in existing
    ]
    if not pairs:
        return [], []
    new_documents, new_ids = zip(*pairs)
    return list(new_documents), list(new_ids)


def _existing_ids(store, ids):
    try:
        return store.get(ids=ids).get("ids", [])
    except Exception:
        logger.exception("Không kiểm tra được id đã tồn tại, sẽ nạp lại toàn bộ")
        return []


def _embed_batch_with_retry(store, batch, batch_ids):
    """Gọi API nhúng, gặp 429 thì chờ rồi thử lại thay vì bỏ dở cả file."""
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


def _add_documents(documents, ids):
    """Nạp vector theo lô, dùng id cố định để chạy lại không bị nhân bản dữ liệu."""
    store = get_vector_store()
    documents, ids = select_new(documents, ids, _existing_ids(store, ids))

    if not documents:
        logger.info("Toàn bộ chunk đã có sẵn trong vector store, không cần nạp lại")
        return 0

    # Thời gian tối thiểu cho mỗi lô để không vượt giới hạn request/phút.
    min_seconds_per_batch = 60 * EMBED_BATCH_SIZE / EMBED_RPM if EMBED_RPM else 0

    for start in range(0, len(documents), EMBED_BATCH_SIZE):
        batch = documents[start : start + EMBED_BATCH_SIZE]
        started_at = time.monotonic()

        _embed_batch_with_retry(store, batch, ids[start : start + EMBED_BATCH_SIZE])
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


# ---------- Nguồn 1: tài liệu gốc đặt sẵn trong backend/data ----------


def local_pdf_paths(directory=None, pattern=None) -> list[Path]:
    """Danh sách file PDF dùng làm nguồn kiến thức nền, sắp xếp cho ổn định."""
    directory = Path(directory or settings.RAG_DATA_DIR)
    pattern = pattern or settings.RAG_DATA_PATTERN

    if not directory.exists():
        return []
    return sorted(directory.glob(pattern))


def textbook_metadata(path: Path, page: int) -> dict:
    """Metadata gắn cho mỗi chunk sách; source_type dùng để lọc lúc truy vấn."""
    return {
        "source_type": SOURCE_TEXTBOOK,
        "source": path.name,
        "title": path.stem.replace("_", " "),
        "page": page,
    }


def document_id(source_type: str, source: str, page: int, index: int) -> str:
    """Id cố định theo (nguồn, trang, thứ tự chunk) để lần nạp sau ghi đè đúng chỗ."""
    return f"{source_type}:{source}:{page}:{index}"


def load_local_pdf(path: Path) -> list[Document]:
    """Đọc PDF bằng PyMuPDF - giữ được lớp text của bản scan đã làm sạch."""
    return PyMuPDFLoader(str(path)).load()


def ingest_local_documents(directory=None, pattern=None, limit=None) -> int:
    """Nạp kiến thức nền từ các file PDF trong backend/data vào vector store."""
    paths = local_pdf_paths(directory, pattern)
    if not paths:
        logger.warning(
            "Không tìm thấy file PDF nào trong %s", directory or settings.RAG_DATA_DIR
        )
        return 0

    splitter = _text_splitter()
    total = 0

    for path in paths:
        logger.info("Đang đọc %s", path.name)
        try:
            pages = load_local_pdf(path)
        except Exception:
            logger.exception("Không đọc được file %s", path.name)
            continue

        documents, ids = [], []
        for page in pages:
            page_number = page.metadata.get("page", 0)
            chunks = splitter.split_documents([page])

            for index, chunk in enumerate(chunks):
                if not chunk.page_content.strip():
                    continue
                chunk.metadata = textbook_metadata(path, page_number)
                documents.append(chunk)
                ids.append(document_id(SOURCE_TEXTBOOK, path.name, page_number, index))

                if limit and len(documents) >= limit:
                    break
            if limit and len(documents) >= limit:
                break

        if not documents:
            logger.warning("File %s không có nội dung chữ để nạp", path.name)
            continue

        added = _add_documents(documents, ids)
        total += added
        logger.info("Đã nạp %s chunk mới từ %s", added, path.name)

    return total


# ---------- Nguồn 2 & 3: tài liệu trên Cloudinary của hệ thống ----------


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
    except requests.RequestException:
        logger.exception("Lỗi tải file từ Cloudinary: %s", file_url)
    return None


def ingest_materials() -> int:
    """Ingest tài liệu chung từ academics.Material"""
    materials = Material.objects.filter(is_rag_indexed=False, is_active=True)
    splitter = _text_splitter()
    total = 0

    for mat in materials:
        local_path = download_cloudinary_file(mat.file_url)
        if not local_path:
            continue

        try:
            chunks = splitter.split_documents(PyPDFLoader(local_path).load())
            documents, ids = [], []

            for index, chunk in enumerate(chunks):
                chunk.metadata.update(
                    {
                        "source_type": SOURCE_MATERIAL,
                        "material_id": mat.id,
                        "subject_id": mat.subject_id,
                        "grade_id": mat.grade_id,
                        "title": mat.name,
                    }
                )
                documents.append(chunk)
                ids.append(document_id(SOURCE_MATERIAL, str(mat.id), 0, index))

            if documents:
                total += _add_documents(documents, ids)

            mat.is_rag_indexed = True
            mat.save(update_fields=["is_rag_indexed"])
            logger.info("Đã ingest Material ID %s", mat.id)

        except Exception:
            logger.exception("Lỗi khi ingest Material ID %s", mat.id)
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    return total


def ingest_learning_resources() -> int:
    """Ingest tài liệu bài học từ courses.LearningResource"""
    resources = LearningResource.objects.filter(
        is_rag_indexed=False, is_active=True
    ).select_related("lesson__chapter__course")

    splitter = _text_splitter()
    total = 0

    for res in resources:
        chunks = []
        metadata = {
            "source_type": SOURCE_RESOURCE,
            "resource_id": res.id,
            "course_id": res.lesson.chapter.course_id,
            "lesson_id": res.lesson_id,
            "title": res.title,
        }

        # TH1: Nội dung bài học dạng text
        if res.content:
            doc = Document(page_content=res.content, metadata=metadata)
            chunks = splitter.split_documents([doc])

        # TH2: Tài liệu dạng PDF upload qua Cloudinary
        elif res.file_url:
            local_path = download_cloudinary_file(res.file_url)
            if local_path:
                try:
                    chunks = splitter.split_documents(PyPDFLoader(local_path).load())
                    for chunk in chunks:
                        chunk.metadata.update(metadata)
                except Exception:
                    logger.exception("Lỗi xử lý file Resource ID %s", res.id)
                finally:
                    if os.path.exists(local_path):
                        os.remove(local_path)

        # Không có nội dung nào để index thì bỏ qua, giữ nguyên cờ để lần sau thử lại.
        if not chunks:
            logger.warning("Resource ID %s không có nội dung để ingest", res.id)
            continue

        total += _add_documents(
            chunks,
            [
                document_id(SOURCE_RESOURCE, str(res.id), 0, i)
                for i in range(len(chunks))
            ],
        )

        res.is_rag_indexed = True
        res.save(update_fields=["is_rag_indexed"])
        logger.info("Đã ingest LearningResource ID %s", res.id)

    return total


def run_full_ingestion() -> dict:
    """Nạp toàn bộ nguồn: sách trong backend/data + tài liệu của hệ thống."""
    return {
        "textbook": ingest_local_documents(),
        "materials": ingest_materials(),
        "resources": ingest_learning_resources(),
    }
