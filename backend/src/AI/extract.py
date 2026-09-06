import base64
import hashlib
import html
import json
import logging
import re
import statistics
import time
import unicodedata
from pathlib import Path

import pymupdf
import pymupdf4llm
from django.conf import settings
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from .vector_store import get_ocr_llm

logger = logging.getLogger(__name__)


def page_has_text(page):
    return bool(page.get_text("text").strip())


def classify_pages(path):
    with pymupdf.open(str(path)) as doc:
        native, scanned = [], []
        for index in range(doc.page_count):
            if page_has_text(doc[index]):
                native.append(index)
            else:
                scanned.append(index)
    return native, scanned


def file_fingerprint(path):
    digest = hashlib.sha1()
    with open(path, "rb") as file:
        chunk_size = 1024 * 1024

        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()[:16]


def cache_path(path):
    cache_dir = Path(settings.RAG_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fingerprint = file_fingerprint(path)
    return Path(cache_dir, f"{fingerprint}.json")


def load_cache(path):
    cache_file = cache_path(path)
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


def save_cache(path, page_texts):
    try:
        cache_file = cache_path(path)
        cache_data = {}

        for page_number, ocr_text in page_texts.items():
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


def content_text(llm_content):
    if isinstance(llm_content, str):
        return llm_content
    if isinstance(llm_content, list):
        parts = []

        for block in llm_content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                parts.append(text)
        return "\n".join(part for part in parts if part)
    return str(llm_content)


OCR_MAX_RETRY = 4
OCR_PROMPT = """
    Convert this textbook page to Markdown.

    RULES:
    - Reproduce ALL text exactly as printed, including phonetic symbols (IPA).
    - Render any table as a Markdown table with a header row. Keep empty cells empty.
    - Use # / ## for headings following the visual hierarchy of the page.
    - Keep the reading order a human would follow, column by column.
    - Do not summarise, translate or add commentary. Output Markdown only.
"""


def ocr_page(image_bytes):
    image_base64 = base64.b64encode(image_bytes).decode()

    image_data_url = "data:image/jpeg;base64," + image_base64
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
            return content_text(get_ocr_llm().invoke([message]).content)
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


def extract_scanned_pages(path, page_indexes):
    cached = load_cache(path)
    todo = [index for index in page_indexes if index not in cached]

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

            save_cache(path, cached)
            logger.info("OCR %s: %s/%s trang", path.name, position, len(todo))

            remaining = delay - (time.monotonic() - started_at)
            if position < len(todo) and remaining > 0:
                time.sleep(remaining)
    return cached


TABLE_STRATEGY = "lines_strict"


def page_has_table(page):
    try:
        return bool(page.find_tables(strategy=TABLE_STRATEGY).tables)
    except Exception:
        logger.exception("Không nhận ra bảng ở trang %s", page.number)
        return False


HYPHEN_BREAK = re.compile(r"[^\W\d_]-$")
WRAP_EDGE_TOLERANCE = 2
WRAP_EDGE_RATIO = 0.005


def block_text(block):
    left_edge, right_edge = block["bbox"][0], block["bbox"][2]
    wrap_threshold = right_edge - max(
        WRAP_EDGE_TOLERANCE, (right_edge - left_edge) * WRAP_EDGE_RATIO
    )

    paragraph, previous_line_wrapped = "", False
    for line in block["lines"]:
        line_text = ""
        for span in line["spans"]:
            line_text += span["text"]
        line_text = line_text.strip()

        if not line_text:
            continue

        if not paragraph:
            paragraph = line_text
        elif not previous_line_wrapped:
            paragraph += "\n" + line_text
        elif HYPHEN_BREAK.search(paragraph):
            paragraph = paragraph[:-1] + line_text
        else:
            paragraph += " " + line_text

        previous_line_wrapped = line["bbox"][2] >= wrap_threshold
    return paragraph


HEADING_SIZE_RATIO = 1.25
HEADING_MAX_LENGTH = 80


def block_heading(block, block_content, body_size):
    sizes = []
    for line in block["lines"]:
        for span in line["spans"]:
            sizes.append(span["size"])
    size = max(sizes, default=0)
    if "\n" in block_content or len(block_content) > HEADING_MAX_LENGTH:
        return block_content
    if size >= body_size * HEADING_SIZE_RATIO:
        return f"## {block_content}"
    return block_content


BLOCK_ALIGN_TOLERANCE = 3
BLOCK_GAP_RATIO = 1.0


def block_separator(previous_block, block):
    if previous_block is None:
        return ""
    aligned = abs(block["bbox"][0] - previous_block["bbox"][0]) <= BLOCK_ALIGN_TOLERANCE
    gap = block["bbox"][1] - previous_block["bbox"][3]
    height = previous_block["bbox"][3] - previous_block["bbox"][1]
    if aligned and gap <= height * BLOCK_GAP_RATIO:
        return "\n"
    return "\n\n"


def layout_markdown(page):
    blocks = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") == 0 and block.get("lines"):
            blocks.append(block)
    sizes = []
    for block in blocks:
        for line in block["lines"]:
            for span in line["spans"]:
                if span["text"].strip():
                    sizes.append(span["size"])
    if not sizes:
        return ""

    body_size = statistics.median(sizes)
    parts, seen, previous_block = [], set(), None

    for block in blocks:
        block_content = block_text(block)
        key = " ".join(block_content.split())
        if not key or key in seen:
            continue

        seen.add(key)
        parts.append(block_separator(previous_block, block))
        parts.append(block_heading(block, block_content, body_size))
        previous_block = block

    return "".join(parts)


def extract_native_pages(path, page_indexes):
    if not page_indexes:
        return {}

    result, table_pages = {}, []
    with pymupdf.open(str(path)) as doc:
        for index in page_indexes:
            if page_has_table(doc[index]):
                table_pages.append(index)
            else:
                result[index] = layout_markdown(doc[index])

    if table_pages:
        rendered_pages = pymupdf4llm.to_markdown(
            str(path), page_chunks=True, pages=table_pages
        )
        for index, rendered in zip(table_pages, rendered_pages):
            result[index] = rendered["text"]
    return result


PAGE_NUMBER_LINE = re.compile(
    r"^[\s|*_\-–—]*(?:trang|page)?[\s.]*\d{1,4}\s*(?:/\s*\d{1,4})?[\s|*_\-–—]*$",
    re.IGNORECASE,
)


def drop_page_number(lines):
    kept_lines = list(lines)
    if kept_lines and PAGE_NUMBER_LINE.match(kept_lines[0]):
        kept_lines.pop(0)
    if kept_lines and PAGE_NUMBER_LINE.match(kept_lines[-1]):
        kept_lines.pop()
    return kept_lines


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
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
OCR_JUNK_CHARS = re.compile(r"[\ufffd\u25a0-\u25ff\u2b1b-\u2b1f\ue000-\uf8ff]")
BULLET_LINE = re.compile(r"(?m)^[ \t]*[\u2022\u2023\u25e6\u25aa\u25ab\u00b7][ \t]*")


def normalize_characters(page_text):
    for wrong, right in MOJIBAKE.items():
        page_text = page_text.replace(wrong, right)

    page_text = html.unescape(page_text)
    page_text = STRAY_A_CIRCUMFLEX.sub("", page_text)
    page_text = unicodedata.normalize("NFKC", page_text)
    page_text = page_text.replace("\r\n", "\n").replace("\r", "\n")
    page_text = BULLET_LINE.sub("- ", page_text)
    page_text = INVISIBLE_CHARS.sub("", page_text)
    page_text = CONTROL_CHARS.sub("", page_text)
    return OCR_JUNK_CHARS.sub("", page_text)


HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
LINE_BREAK_TAG = re.compile(r"<br\s*/?>", re.IGNORECASE)
HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")


def strip_html(page_text):
    page_text = HTML_COMMENT.sub("", page_text)

    lines = []
    for line in page_text.split("\n"):
        if line.lstrip().startswith("|"):
            separator = " "
        else:
            separator = "\n"
        lines.append(HTML_TAG.sub("", LINE_BREAK_TAG.sub(separator, line)))
    return "\n".join(lines)


def repeatable_word(word):
    stripped = word.strip("*_#|.,;:!?()-")
    return len(stripped) >= 3 and stripped.isupper()


MAX_REPEAT_WORDS = 8


def repeated_group_size(words, position):
    longest_group = min(MAX_REPEAT_WORDS, (len(words) - position) // 2)

    for size in range(longest_group, 0, -1):
        group = words[position : position + size]
        next_group = words[position + size : position + 2 * size]

        if group != next_group:
            continue
        if size == 1 and not repeatable_word(group[0]):
            continue
        return size
    return 0


def collapse_repeats(line):
    words = line.split(" ")
    kept_words, position = [], 0

    while position < len(words):
        group_size = repeated_group_size(words, position)

        if group_size:
            kept_words.extend(words[position : position + group_size])
            position += group_size * 2
        else:
            kept_words.append(words[position])
            position += 1
    return " ".join(kept_words)


def dedupe_lines(page_text):
    result, in_code = [], False

    for line in page_text.split("\n"):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            result.append(line)
        elif in_code or line.lstrip().startswith("|"):
            result.append(line)
        else:
            result.append(collapse_repeats(line))

    return "\n".join(result)


def tidy_whitespace(page_text):
    lines, in_code = [], False

    for line in page_text.split("\n"):
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


def clean_markdown(page_text):
    page_text = normalize_characters(page_text)
    page_text = strip_html(page_text)
    page_text = tidy_whitespace(page_text)
    lines = drop_page_number(page_text.strip().split("\n"))
    page_text = dedupe_lines("\n".join(lines))
    return page_text.strip()


REPEAT_EDGE_LINES = 3
REPEAT_MIN_PAGES = 3
REPEAT_MAX_LENGTH = 80
HEADER_MIN_RATIO = 0.4
WATERMARK_MIN_RATIO = 0.6   


def page_lines(page_text):
    lines = []
    for line in page_text.split("\n"):
        if line.strip():
            lines.append(line.strip())
    return lines


def count_line_occurrences(page_texts):
    edge_counts, anywhere_counts = {}, {}

    for page_text in page_texts.values():
        lines = page_lines(page_text)
        edge_lines = set(lines[:REPEAT_EDGE_LINES] + lines[-REPEAT_EDGE_LINES:])

        for line in edge_lines:
            edge_counts[line] = edge_counts.get(line, 0) + 1
        for line in set(lines):
            anywhere_counts[line] = anywhere_counts.get(line, 0) + 1
    return edge_counts, anywhere_counts


def lines_over_threshold(counts, page_count, min_ratio):
    threshold = max(REPEAT_MIN_PAGES, round(page_count * min_ratio))
    found = set()

    for line, count in counts.items():
        if count < threshold:
            continue
        if len(line) > REPEAT_MAX_LENGTH:
            continue
        if line.startswith("|"):
            continue
        found.add(line)
    return found


def repeated_lines(page_texts):
    if len(page_texts) < REPEAT_MIN_PAGES:
        return set()

    page_count = len(page_texts)
    edge_counts, anywhere_counts = count_line_occurrences(page_texts)
    headers_and_footers = lines_over_threshold(
        edge_counts, page_count, HEADER_MIN_RATIO
    )
    watermarks = lines_over_threshold(
        anywhere_counts, page_count, WATERMARK_MIN_RATIO
    )
    return headers_and_footers | watermarks


def clean_pages(page_texts):
    cleaned_page_texts = {}
    for index, page_text in page_texts.items():
        cleaned_page_texts[index] = clean_markdown(page_text)

    repeated = repeated_lines(cleaned_page_texts)
    if not repeated:
        return cleaned_page_texts
    
    result = {}
    for index, page_text in cleaned_page_texts.items():
        kept_lines = []

        for line in page_text.split("\n"):
            if line.strip() not in repeated:
                kept_lines.append(line)

        kept_text = "\n".join(kept_lines)
        result[index] = re.sub(r"\n{3,}", "\n\n", kept_text).strip()
    return result


def load_pdf(path):
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

    documents = []
    for index in sorted(markdown):
        page_text = markdown[index]
        if not page_text:
            continue
        metadata = {"page": index + 1}
        document = Document(page_content=page_text, metadata=metadata)
        documents.append(document)
    return documents
