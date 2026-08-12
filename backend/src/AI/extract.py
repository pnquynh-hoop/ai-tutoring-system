import base64
import hashlib
import json
import logging
import re
import statistics
import time
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf
import pymupdf4llm
from django.conf import settings
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from .vector_store import get_ocr_llm

logger = logging.getLogger(__name__)

OCR_MAX_RETRY = 4

PAGE_NUMBER_LINE = re.compile(
    r"^[\s|*_\-–—]*(?:trang|page)?[\s.]*\d{1,4}\s*(?:/\s*\d{1,4})?[\s|*_\-–—]*$",
    re.IGNORECASE,
)


MOJIBAKE = {
    "â€™": "'",
    "â€˜": "'",
    "â€œ": '"',
    "â€\x9d": '"',
    "â€“": "–",
    "â€”": "—",
    "â€¦": "…",
}

STRAY_A_CIRCUMFLEX = re.compile("\u00c2(?=[\u00a0-\u00bf])")

INVISIBLE_CHARS = re.compile(r"[\u00ad\u200b-\u200f\u2028\u2029\ufeff]")
# \x09 = tab (\t)
# \x0a = newline (\n)
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
OCR_JUNK_CHARS = re.compile(r"[\ufffd\u25a0-\u25ff\u2b1b-\u2b1f\ue000-\uf8ff]")
BULLET_LINE = re.compile(r"(?m)^[ \t]*[\u2022\u2023\u25e6\u25aa\u25ab\u00b7][ \t]*")
HYPHEN_BREAK = re.compile(r"[^\W\d_]-$")

HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
LINE_BREAK_TAG = re.compile(r"<br\s*/?>", re.IGNORECASE)
HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")

MAX_REPEAT_WORDS = 8

TABLE_STRATEGY = "lines_strict"
WRAP_EDGE_TOLERANCE = 2
WRAP_EDGE_RATIO = 0.005
HEADING_SIZE_RATIO = 1.25
HEADING_MAX_LENGTH = 80
BLOCK_ALIGN_TOLERANCE = 3
BLOCK_GAP_RATIO = 1.0

# Dòng lặp lại ở nhiều trang là tiêu đề đầu trang, chân trang hoặc watermark.
REPEAT_EDGE_LINES = 3
REPEAT_MIN_PAGES = 3
REPEAT_MAX_LENGTH = 80
HEADER_MIN_RATIO = 0.4
WATERMARK_MIN_RATIO = 0.6

OCR_PROMPT = """Convert this textbook page to Markdown.

RULES:
- Reproduce ALL text exactly as printed, including phonetic symbols (IPA).
- Render any table as a Markdown table with a header row. Keep empty cells empty.
- Use # / ## for headings following the visual hierarchy of the page.
- Keep the reading order a human would follow, column by column.
- Do not summarise, translate or add commentary. Output Markdown only."""


def page_has_text(page) -> bool:
    """Trang có lớp text đọc được không.

    Trang scan chỉ là một tấm ảnh nên không đọc ra chữ nào; dựa vào đó để biết
    trang nào phải đưa qua OCR thay vì bỏ qua.
    """
    return bool(page.get_text("text").strip())


def classify_pages(path: Path) -> tuple[list[int], list[int]]:
    """Chia số trang thành (trang có text, trang cần OCR).

    Xét từng trang chứ không xét cả file, vì tài liệu thực tế thường lẫn lộn:
    phần soạn trên máy đi kèm phụ lục là bản scan.
    """
    with pymupdf.open(str(path)) as doc:
        native, scanned = [], []
        for index in range(doc.page_count):  # doc[index] = 1 page
            (native if page_has_text(doc[index]) else scanned).append(index)
    return native, scanned


def _file_fingerprint(path: Path) -> str:
    """Mã nhận dạng tính từ nội dung file, để đổi tên file không mất cache OCR."""
    digest = hashlib.sha1()
    with open(path, "rb") as file:
        chunk_size = 1024 * 1024  # 1 MB

        while True:
            chunk = file.read(chunk_size)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()[:16]


def _cache_path(path: Path) -> Path:
    dir = Path(settings.RAG_CACHE_DIR)
    dir.mkdir(parents=True, exist_ok=True)
    fingerprint = _file_fingerprint(path)
    return Path(dir, f"{fingerprint}.json")


def _load_cache(path: Path) -> dict[int, str]:
    cache_file = _cache_path(path)
    if not cache_file.exists():
        return {}
    try:
        raw = json.loads(cache_file.read_text(encoding="utf-8"))
        cache: dict[int, str] = {}

        for key, value in raw.items():
            page_number = int(key)
            cache[page_number] = value

        return cache
    except (ValueError, OSError):
        logger.exception("Cache OCR bị hỏng, sẽ OCR lại: %s", cache_file)
        return {}


def _save_cache(path: Path, pages: dict[int, str]) -> None:
    try:
        cache_file = _cache_path(path)
        cache_data = {}

        for page_number, ocr_text in pages.items():
            cache_data[str(page_number)] = ocr_text

        json_text = json.dumps(
            cache_data,
            ensure_ascii=False,
        )

        cache_file.write_text(
            json_text,
            encoding="utf-8",
        )

    except OSError:
        logger.exception("Không lưu được cache OCR của %s", path.name)


def _message_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []

        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                parts.append(text)
        return "\n".join(part for part in parts if part)
    return str(content)


def ocr_page(image_bytes: bytes) -> str:
    """Đọc một trang ảnh thành Markdown, bị chặn vì quá hạn mức thì chờ rồi thử lại.

    OCR cả quyển sách tốn hàng trăm request nên dính lỗi 429 giữa chừng là
    chuyện thường; dừng luôn ở đó thì phí những trang đã đọc xong.
    """
    image_base64 = base64.b64encode(image_bytes).decode()

    image_data_url = (
        "data:image/jpeg;base64,"
        + image_base64
    )
    # data:       dữ liệu được nhúng trực tiếp
    # image/jpeg: dữ liệu là ảnh JPEG
    # base64:     dữ liệu phía sau được mã hóa Base64
    message = HumanMessage(
        content=[
            {"type": "text", "text": OCR_PROMPT},
            {
                "type": "image_url",
                "image_url": image_data_url,
            },
        ]
    )

    for attempt in range(1, OCR_MAX_RETRY + 1):
        try:
            return _message_text(get_ocr_llm().invoke([message]).content)
        except Exception as exc:
            is_quota_error = "RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc)
            if not is_quota_error or attempt == OCR_MAX_RETRY:
                raise
            wait = 30 * attempt
            logger.warning(
                "OCR bị chặn vì quá hạn mức, chờ %ss rồi thử lại (lần %s/%s)",
                wait,
                attempt,
                OCR_MAX_RETRY,
            )
            time.sleep(wait)
    return ""


def extract_scanned_pages(path: Path, indexes: list[int]) -> dict[int, str]:
    """OCR các trang scan, xong trang nào lưu cache trang đó.

    Lưu theo từng trang là cố ý: OCR cả quyển sách mất hàng chục phút và dễ
    đứt giữa chừng vì quá hạn mức, lần chạy sau chỉ cần làm tiếp phần còn thiếu.
    """
    cached = _load_cache(path)
    todo = [index for index in indexes if index not in cached]

    if not todo:
        return cached

    if not settings.RAG_OCR_ENABLED:
        logger.warning(
            "%s có %s trang scan nhưng RAG_OCR_ENABLED=False nên bỏ qua",
            path.name,
            len(todo),
        )
        return cached

    delay = 60 / settings.RAG_OCR_RPM if settings.RAG_OCR_RPM else 0

    with pymupdf.open(str(path)) as doc:
        for position, index in enumerate(todo, start=1):
            started_at = time.monotonic()
            image = doc[index].get_pixmap(dpi=settings.RAG_OCR_DPI).tobytes("jpeg")

            try:
                cached[index] = ocr_page(image)
            except Exception:
                logger.exception("OCR lỗi ở trang %s của %s", index, path.name)
                break

            _save_cache(path, cached)
            logger.info("OCR %s: %s/%s trang", path.name, position, len(todo))

            remaining = delay - (time.monotonic() - started_at)
            if position < len(todo) and remaining > 0:
                time.sleep(remaining)

    return cached


def _page_has_table(page) -> bool:
    """Trang có bảng kẻ khung hay không."""
    try:
        return bool(page.find_tables(strategy=TABLE_STRATEGY).tables)
    except Exception:
        logger.exception("Không nhận ra bảng ở trang %s", page.number)
        return False


def _block_text(block) -> str:
    """Ghép các dòng trong một khối, chỉ nối lại khi dòng trên chạm mép phải."""
    left, right = block["bbox"][0], block["bbox"][2]
    limit = right - max(WRAP_EDGE_TOLERANCE, (right - left) * WRAP_EDGE_RATIO)

    result, wrapped = "", False
    for line in block["lines"]:
        text = "".join(span["text"] for span in line["spans"]).strip()
        if not text:
            continue

        if not result:
            result = text
        elif not wrapped:
            result += "\n" + text
        elif HYPHEN_BREAK.search(result):
            result = result[:-1] + text
        else:
            result += " " + text

        wrapped = line["bbox"][2] >= limit
    return result


def _block_heading(block, text: str, body_size: float) -> str:
    """Khối chỉ một dòng mà chữ to hơn chữ trong đoạn văn thì coi là tiêu đề."""
    size = max(
        (span["size"] for line in block["lines"] for span in line["spans"]), default=0
    )
    if "\n" in text or len(text) > HEADING_MAX_LENGTH:
        return text
    return f"## {text}" if size >= body_size * HEADING_SIZE_RATIO else text


def _block_separator(previous, block) -> str:
    """Hai khối thẳng hàng nhau và sát nhau là hai mục của cùng một danh sách."""
    if previous is None:
        return ""

    aligned = abs(block["bbox"][0] - previous["bbox"][0]) <= BLOCK_ALIGN_TOLERANCE
    gap = block["bbox"][1] - previous["bbox"][3]
    height = previous["bbox"][3] - previous["bbox"][1]
    return "\n" if aligned and gap <= height * BLOCK_GAP_RATIO else "\n\n"


def _layout_markdown(page) -> str:
    """Dựng Markdown từ toạ độ từng dòng, giữ đúng chỗ ngắt dòng như trên trang."""
    blocks = [
        block
        for block in page.get_text("dict")["blocks"]
        if block.get("type") == 0 and block.get("lines")
    ]
    sizes = [
        span["size"]
        for block in blocks
        for line in block["lines"]
        for span in line["spans"]
        if span["text"].strip()
    ]
    if not sizes:
        return ""

    body_size = statistics.median(sizes)
    parts, seen, previous = [], set(), None

    for block in blocks:
        text = _block_text(block)
        key = " ".join(text.split())
        if not key or key in seen:
            continue

        seen.add(key)
        parts.append(_block_separator(previous, block))
        parts.append(_block_heading(block, text, body_size))
        previous = block

    return "".join(parts)


def extract_native_pages(path: Path, indexes: list[int]) -> dict[int, str]:
    """Đọc trang có sẵn lớp text thành Markdown.

    Trang có bảng đưa qua pymupdf4llm để giữ nguyên bảng. Trang còn lại tự dựng
    lại theo toạ độ, vì pymupdf4llm gộp cả khối thành một đoạn làm các mục trong
    danh sách dính liền nhau.
    """
    if not indexes:
        return {}

    result, table_pages = {}, []
    with pymupdf.open(str(path)) as doc:
        for index in indexes:
            if _page_has_table(doc[index]):
                table_pages.append(index)
            else:
                result[index] = _layout_markdown(doc[index])

    if table_pages:
        pages = pymupdf4llm.to_markdown(str(path), page_chunks=True, pages=table_pages)
        result.update({index: page["text"] for index, page in zip(table_pages, pages)})

    return result


def _drop_page_number(lines: list[str]) -> list[str]:
    """Bỏ dòng chỉ chứa số trang ở đầu và cuối trang."""
    for position in (0, -1):
        if lines and PAGE_NUMBER_LINE.match(lines[position]):
            lines.pop(position)
    return lines


def _normalize_characters(text: str) -> str:
    """Sửa chữ lỗi font, chuẩn hoá Unicode, bỏ ký tự vô hình và rác OCR."""
    for wrong, right in MOJIBAKE.items():
        text = text.replace(wrong, right)

    text = STRAY_A_CIRCUMFLEX.sub("", text)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = BULLET_LINE.sub("- ", text)
    text = INVISIBLE_CHARS.sub("", text)
    text = CONTROL_CHARS.sub("", text)
    return OCR_JUNK_CHARS.sub("", text)


def _strip_html(text: str) -> str:
    """Bỏ comment và thẻ HTML, đổi <br> thành xuống dòng.

    Riêng trong một hàng của bảng Markdown thì <br> đổi thành dấu cách, xuống
    dòng ở đó sẽ làm vỡ bảng.
    """
    text = HTML_COMMENT.sub("", text)

    lines = []
    for line in text.split("\n"):
        separator = " " if line.lstrip().startswith("|") else "\n"
        lines.append(HTML_TAG.sub("", LINE_BREAK_TAG.sub(separator, line)))
    return "\n".join(lines)


def _repeatable_word(word: str) -> bool:
    """Một từ đứng lẻ có được phép coi là lặp thừa không."""
    stripped = word.strip("*_#|.,;:!?()-")
    return len(stripped) >= 3 and stripped.isupper()


def _collapse_repeats(line: str) -> str:
    """Gộp cụm từ lặp lại ngay sau chính nó: "A B A B" thành "A B"."""
    words = line.split(" ")
    result, index = [], 0

    while index < len(words):
        repeated = 0
        for size in range(min(MAX_REPEAT_WORDS, (len(words) - index) // 2), 0, -1):
            first = words[index : index + size]
            if first != words[index + size : index + 2 * size]:
                continue
            if size == 1 and not _repeatable_word(first[0]):
                continue
            repeated = size
            break

        if repeated:
            result.extend(words[index : index + repeated])
            index += 2 * repeated
        else:
            result.append(words[index])
            index += 1

    return " ".join(result)


def _dedupe_lines(text: str) -> str:
    """Bỏ phần lặp trên từng dòng, trừ bảng và khối code."""
    result, in_code = [], False

    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            result.append(line)
        elif in_code or line.lstrip().startswith("|"):
            result.append(line)
        else:
            result.append(_collapse_repeats(line))

    return "\n".join(result)


def _tidy_whitespace(text: str) -> str:
    """Bỏ tab, dấu cách dư và dòng trống thừa; giữ nguyên khối code."""
    lines, in_code = [], False

    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            lines.append(line.rstrip())
            continue
        if in_code:
            lines.append(line.rstrip())
            continue

        line = line.replace("\t", " ")
        indent = min(len(line) - len(line.lstrip(" ")), 4)
        lines.append(" " * indent + re.sub(r" {2,}", " ", line.strip()))

    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))


def clean_markdown(text: str) -> str:
    """Dọn nội dung một trang, giữ nguyên cấu trúc Markdown.

    Không nối dòng ở bước này: chỗ ngắt dòng đã xử lý theo toạ độ lúc đọc, nối
    thêm nữa sẽ làm các mục trong danh sách dính liền nhau.
    """
    text = _normalize_characters(text)
    text = _strip_html(text)
    text = _tidy_whitespace(text)
    text = _dedupe_lines("\n".join(_drop_page_number(text.strip().split("\n"))))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _repeated_lines(pages: dict[int, str]) -> set[str]:
    """Tìm dòng lặp ở nhiều trang: tiêu đề đầu trang, chân trang và watermark."""
    if len(pages) < REPEAT_MIN_PAGES:
        return set()

    edge, anywhere = Counter(), Counter()
    for text in pages.values():
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        edge.update(set(lines[:REPEAT_EDGE_LINES] + lines[-REPEAT_EDGE_LINES:]))
        anywhere.update(set(lines))

    repeated = set()
    for counter, ratio in ((edge, HEADER_MIN_RATIO), (anywhere, WATERMARK_MIN_RATIO)):
        threshold = max(REPEAT_MIN_PAGES, round(len(pages) * ratio))
        for line, count in counter.items():
            if (
                count >= threshold
                and len(line) <= REPEAT_MAX_LENGTH
                and not line.startswith("|")
            ):
                repeated.add(line)
    return repeated


def clean_pages(pages: dict[int, str]) -> dict[int, str]:
    """Dọn cả tài liệu: làm sạch từng trang rồi bỏ các dòng lặp ở nhiều trang."""
    cleaned = {index: clean_markdown(text) for index, text in pages.items()}
    repeated = _repeated_lines(cleaned)

    if not repeated:
        return cleaned

    logger.info("Bỏ %s dòng lặp ở nhiều trang", len(repeated))
    result = {}
    for index, text in cleaned.items():
        kept = [line for line in text.split("\n") if line.strip() not in repeated]
        result[index] = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    return result


def load_pdf(path: Path) -> list[Document]:
    """Đọc PDF thành Document theo từng trang, nội dung là Markdown.

    Mỗi trang chọn cách đọc riêng: có lớp text thì đọc thẳng, là ảnh scan thì
    OCR. Nhờ vậy file trộn cả hai loại vẫn nạp được đầy đủ.
    """
    native, scanned = classify_pages(path)

    if scanned:
        logger.info(
            "%s: %s trang có lớp text, %s trang cần OCR",
            path.name,
            len(native),
            len(scanned),
        )

    markdown = extract_native_pages(path, native)
    markdown.update(extract_scanned_pages(path, scanned))
    markdown = clean_pages(markdown)

    return [
        # Đánh số trang từ 1 cho khớp với số trang in trên tài liệu.
        Document(page_content=markdown[index], metadata={"page": index + 1})
        for index in sorted(markdown)
        if markdown[index]
    ]
