"""Công cụ dòng lệnh cho RAG: nạp dữ liệu và thử prompt trước khi gắn vào API.

Phần nạp đọc trang có sẵn lớp text và trang scan đã OCR trong rag_cache, không
gọi OCR mới. Phần thử prompt gọi thẳng service mà API đang dùng nên kết quả in
ra trong terminal giống hệt cái API sẽ trả về.

Chạy từ thư mục backend/src:
    python AI/check.py                          nạp vào vector store
    python AI/check.py ingest --dry-run         chỉ đếm chunk, không embedding
    python AI/check.py ingest --pattern "*.pdf"

    python AI/check.py ask --course 1           hỏi bài liên tục
    python AI/check.py compare --course 1       so sánh STRICT với HYBRID
    python AI/check.py exercises --course 1     sinh thử bài tập
"""

import argparse
import logging
import os
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*fixed sampling defaults.*")

# Console Windows mặc định không phải UTF-8, in tiếng Việt sẽ lỗi encode.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stdin.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_tutoring_system.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from langchain_core.documents import Document  # noqa: E402

from AI.extract import (  # noqa: E402
    _cache_path,
    _load_cache,
    classify_pages,
    clean_pages,
    extract_native_pages,
)
from AI.ingest import (  # noqa: E402
    SOURCE_TEXTBOOK,
    _add_documents,
    _markdown_splitter,
    document_id,
    textbook_metadata,
)
from AI.rag_service import (  # noqa: E402
    DEFAULT_TOP_K,
    HYBRID_PROMPT,
    STRICT_PROMPT,
    _build_chroma_filter,
    format_sources,
    generate_exercises_rag,
    message_text,
    query_rag_answer,
    split_grounding,
)
from AI.vector_store import get_llm, get_vector_store  # noqa: E402
from assignments.models import Question  # noqa: E402

OCR_PATTERN = "SGK_Tieng_anh_12_global_success-part-*.pdf"

COMMANDS = ("ingest", "ask", "compare", "exercises")
QUESTION_TYPES = Question.QuestionType.values


# ---------------------------------------------------------------------------
# PHẦN OCR ĐÃ CHẠY XONG - GIỮ LẠI ĐỂ THAM KHẢO, KHÔNG CHẠY NỮA
# Toàn bộ 159 trang đã nằm trong rag_cache, muốn OCR file mới thì mở lại khối này.
# ---------------------------------------------------------------------------
# import base64
# import pymupdf
# from langchain_core.messages import HumanMessage
# from AI.extract import OCR_PROMPT, _message_text, _save_cache
# from AI.vector_store import OCR_MODEL, get_ocr_llm
#
# MAX_RETRY = 3
# DEFAULT_RETRY_WAIT = 20
# RETRY_DELAY = re.compile(r"retry in ([\d.]+)s", re.IGNORECASE)
#
#
# class DailyQuotaExhausted(RuntimeError):
#     pass
#
#
# def is_quota_error(message):
#     return "RESOURCE_EXHAUSTED" in message or "429" in message
#
#
# def is_daily_quota(message):
#     return "PerDay" in message or "per day" in message.lower()
#
#
# def retry_wait(message, attempt):
#     found = RETRY_DELAY.search(message)
#     if found:
#         return float(found.group(1)) + 2
#     return DEFAULT_RETRY_WAIT * attempt
#
#
# def ocr_image(image_bytes):
#     message = HumanMessage(
#         content=[
#             {"type": "text", "text": OCR_PROMPT},
#             {
#                 "type": "image_url",
#                 "image_url": "data:image/jpeg;base64,"
#                 + base64.b64encode(image_bytes).decode(),
#             },
#         ]
#     )
#
#     for attempt in range(1, MAX_RETRY + 1):
#         try:
#             return _message_text(get_ocr_llm().invoke([message]).content)
#         except Exception as exc:
#             detail = str(exc)
#             if is_daily_quota(detail):
#                 raise DailyQuotaExhausted(detail) from exc
#             if not is_quota_error(detail) or attempt == MAX_RETRY:
#                 raise
#
#             wait = retry_wait(detail, attempt)
#             log(f"chạm giới hạn phút, chờ {wait:.0f}s rồi thử lại "
#                 f"(lần {attempt}/{MAX_RETRY})")
#             time.sleep(wait)
#     return ""
#
#
# def run_ocr(path, todo, cached):
#     delay = 60 / settings.RAG_OCR_RPM if settings.RAG_OCR_RPM else 0
#     fresh, durations, stopped = [], [], None
#
#     with pymupdf.open(str(path)) as doc:
#         for position, index in enumerate(todo, start=1):
#             started_at = time.monotonic()
#             log(f"[{position}/{len(todo)}] Trang {index + 1} ... ", end="")
#
#             image = doc[index].get_pixmap(dpi=settings.RAG_OCR_DPI).tobytes("jpeg")
#             try:
#                 text = ocr_image(image)
#             except DailyQuotaExhausted:
#                 log("HẾT QUOTA NGÀY")
#                 stopped = "daily"
#                 break
#             except Exception as exc:
#                 log(f"LỖI: {exc}")
#                 stopped = "error"
#                 break
#
#             cached[index] = text
#             _save_cache(path, cached)
#             fresh.append(index)
#
#             took = time.monotonic() - started_at
#             durations.append(took)
#             preview = " ".join(text.split())[:60]
#             log(f"{len(text)} ký tự, {took:.1f}s | {preview}")
#
#             if position >= len(todo):
#                 continue
#
#             average = max(sum(durations) / len(durations), delay)
#             log(f"        còn {len(todo) - position} trang, "
#                 f"ước tính {format_duration(average * (len(todo) - position))}")
#
#             remaining = delay - took
#             if remaining > 0:
#                 log(f"        chờ {remaining:.0f}s cho đủ "
#                     f"{settings.RAG_OCR_RPM} trang/phút")
#                 time.sleep(remaining)
#
#     return fresh, stopped
# ---------------------------------------------------------------------------


def log(message="", end="\n"):
    print(message, end=end, flush=True)


def format_duration(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes} phút {seconds:02d} giây" if minutes else f"{seconds} giây"


# ---------------------------------------------------------------------------
# PHẦN SO SÁNH TRƯỚC/SAU KHI LÀM SẠCH ĐÃ CHẠY XONG - GIỮ LẠI ĐỂ THAM KHẢO
# Kết quả nằm trong check_out.txt. Mở lại khối này thì cần import thêm
# difflib, re, Counter, _collapse_repeats, _normalize_characters, _repeated_lines,
# _strip_html, clean_markdown, local_pdf_paths.
# ---------------------------------------------------------------------------
# OUT_PATH = Path(__file__).resolve().parent.parent / "check_out.txt"
#
# MARKERS = {
#     "tiêu đề": re.compile(r"(?m)^#{1,6} "),
#     "dòng bảng": re.compile(r"(?m)^\|.*\|\s*$"),
#     "bullet": re.compile(r"(?m)^\s*[-*] "),
#     "IPA": re.compile(r"/[ˈˌːəæŋʃʒθðɪʊɔɜɑʌ][^/\n]{1,}/"),
#     "chỗ điền ___": re.compile(r"_{3,}|(?:\\_){3,}"),
#     "thẻ HTML": re.compile(r"</?[a-zA-Z][^>]*>"),
# }
#
#
# def percent(after, before):
#     return f"{(after - before) / before * 100:+.1f}%" if before else "n/a"
#
#
# def markers(text):
#     return {name: len(pattern.findall(text)) for name, pattern in MARKERS.items()}
#
#
# def sum_markers(pages):
#     total = Counter()
#     for text in pages.values():
#         total.update(markers(text))
#     return total
#
#
# def collect_ocr_pages(path):
#     return {index: text for index, text in _load_cache(path).items() if text.strip()}
#
#
# def collect_native_pages(path):
#     native, _ = classify_pages(path)
#     if not native:
#         return {}
#     return {
#         index: text
#         for index, text in extract_native_pages(path, native).items()
#         if text.strip()
#     }
#
#
# def squash_spaces(line):
#     line = line.replace("\t", " ")
#     indent = min(len(line) - len(line.lstrip(" ")), 4)
#     return " " * indent + re.sub(r" {2,}", " ", line.strip())
#
#
# STAGES = (
#     ("chuẩn hóa ký tự", _normalize_characters),
#     ("bỏ thẻ HTML", _strip_html),
#     ("gộp khoảng trắng", squash_spaces),
#     ("khử lặp cụm từ", _collapse_repeats),
# )
#
#
# def change_reasons(line):
#     reasons, text = [], line
#
#     for name, transform in STAGES:
#         if name == "khử lặp cụm từ" and text.lstrip().startswith("|"):
#             continue
#         changed = transform(text)
#         if changed.strip() != text.strip():
#             reasons.append(name)
#         text = changed
#
#     return tuple(reasons) if reasons else ("bị luật khác xử lý",)
#
#
# def diff_lines(before, after):
#     old = [line.strip() for line in before.split("\n") if line.strip()]
#     new = [line.strip() for line in after.split("\n") if line.strip()]
#
#     changed, dropped, added = [], [], []
#     matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
#
#     for tag, start_old, end_old, start_new, end_new in matcher.get_opcodes():
#         if tag == "delete":
#             dropped.extend(old[start_old:end_old])
#         elif tag == "insert":
#             added.extend(new[start_new:end_new])
#         elif tag == "replace":
#             pairs = max(end_old - start_old, end_new - start_new)
#             for offset in range(pairs):
#                 one = old[start_old + offset] if start_old + offset < end_old else None
#                 two = new[start_new + offset] if start_new + offset < end_new else None
#
#                 if one and two and difflib.SequenceMatcher(None, one, two).ratio() >= 0.5:
#                     changed.append((one, two))
#                 elif one and two:
#                     dropped.append(one)
#                     added.append(two)
#                 elif one:
#                     dropped.append(one)
#                 else:
#                     added.append(two)
#
#     return changed, dropped, added
#
#
# def compare_pages(raw):
#     cleaned = clean_pages(raw)
#     rows = []
#
#     for index in sorted(raw):
#         before = raw[index]
#         after = cleaned.get(index, "")
#         changed, dropped, added = diff_lines(before, after)
#         rows.append(
#             {
#                 "page": index,
#                 "before": before,
#                 "after": after,
#                 "changed": changed,
#                 "dropped": dropped,
#                 "added": added,
#             }
#         )
#     return cleaned, rows
#
#
# def chunk_count(path, pages):
#     splitter = _markdown_splitter()
#     from langchain_core.documents import Document
#
#     total, ids = 0, []
#     for index in sorted(pages):
#         page = Document(page_content=pages[index], metadata={"page": index + 1})
#         for order, chunk in enumerate(splitter.split_documents([page])):
#             if not chunk.page_content.strip():
#                 continue
#             chunk.metadata = textbook_metadata(path, index + 1)
#             ids.append(document_id(SOURCE_TEXTBOOK, path.name, index + 1, order))
#             total += 1
#     return total, ids
#
#
# def report_source(out, title, path, raw, samples, max_chars):
#     if not raw:
#         out.write(f"\n{title} - {path.name}: không có trang nào để so sánh\n")
#         return None
#
#     cleaned, rows = compare_pages(raw)
#     before_chars = sum(len(text) for text in raw.values())
#     after_chars = sum(len(text) for text in cleaned.values())
#     before_marks = sum_markers(raw)
#     after_marks = sum_markers(cleaned)
#     dropped_all = [line for row in rows for line in row["dropped"]]
#     changed_all = [pair for row in rows for pair in row["changed"]]
#     added_all = [line for row in rows for line in row["added"]]
#     repeated = _repeated_lines({i: clean_markdown(t) for i, t in raw.items()})
#     chunks, ids = chunk_count(path, cleaned)
#
#     out.write("\n" + "#" * 78 + "\n")
#     out.write(f"# {title}: {path.name}\n")
#     out.write("#" * 78 + "\n")
#     out.write(f"Số trang            : {len(raw)}\n")
#     out.write(f"Ký tự trước / sau   : {before_chars} -> {after_chars} "
#               f"({percent(after_chars, before_chars)})\n")
#     out.write(f"Trang bị rỗng sau khi dọn: "
#               f"{sum(1 for row in rows if row['before'].strip() and not row['after'].strip())}\n")
#     out.write(f"Dòng bị XÓA HẲN     : {len(dropped_all)}\n")
#     out.write(f"Dòng bị SỬA nội dung: {len(changed_all)}\n")
#     out.write(f"Dòng lạ thêm vào    : {len(added_all)}\n")
#     out.write(f"Dòng lặp qua trang bị bỏ : {len(repeated)}\n")
#     out.write(f"Số chunk sau khi cắt: {chunks}\n")
#     if ids:
#         out.write(f"Ví dụ id chunk      : {ids[0]}\n")
#
#     out.write("\nDấu hiệu cấu trúc giữ được:\n")
#     out.write(f"  {'loại':16s} {'trước':>8s} {'sau':>8s} {'chênh':>8s}\n")
#     for name in MARKERS:
#         before, after = before_marks[name], after_marks[name]
#         out.write(f"  {name:16s} {before:>8d} {after:>8d} "
#                   f"{percent(after, before):>8s}\n")
#
#     if dropped_all:
#         out.write("\n15 dòng bị XÓA HẲN nhiều nhất:\n")
#         for line, count in Counter(dropped_all).most_common(15):
#             out.write(f"  {count:>3d}x  {line[:90]}\n")
#
#     if changed_all:
#         groups = Counter(change_reasons(before) for before, _ in changed_all)
#         out.write("\nDòng bị SỬA, gom theo luật đã tác động:\n")
#         for reasons, count in groups.most_common():
#             out.write(f"  {count:>4d} dòng  <- {' + '.join(reasons)}\n")
#
#         out.write("\nVí dụ mỗi nhóm:\n")
#         seen = set()
#         for before, after in changed_all:
#             reasons = change_reasons(before)
#             if reasons in seen:
#                 continue
#             seen.add(reasons)
#             out.write(f"\n  [{' + '.join(reasons)}]\n")
#             out.write(f"    TRƯỚC: {before[:110]}\n")
#             out.write(f"    SAU  : {after[:110]}\n")
#
#     if added_all:
#         out.write("\nDòng xuất hiện thêm sau khi dọn (đáng ngờ):\n")
#         for line, count in Counter(added_all).most_common(10):
#             out.write(f"  {count:>3d}x  {line[:90]}\n")
#
#     if repeated:
#         out.write("\nDòng bị coi là header/footer/watermark:\n")
#         for line in sorted(repeated)[:15]:
#             out.write(f"  - {line[:90]}\n")
#
#     ranked = sorted(rows, key=lambda row: len(row["dropped"]), reverse=True)
#     for row in ranked[:samples]:
#         out.write("\n" + "=" * 78 + "\n")
#         out.write(f"TRANG {row['page'] + 1} - xóa {len(row['dropped'])} dòng, "
#                   f"sửa {len(row['changed'])} dòng, "
#                   f"{len(row['before'])} -> {len(row['after'])} ký tự\n")
#         out.write("=" * 78 + "\n")
#         out.write("--- TRƯỚC KHI DỌN " + "-" * 59 + "\n")
#         out.write(row["before"][:max_chars] + "\n")
#         out.write("--- SAU KHI DỌN " + "-" * 61 + "\n")
#         out.write(row["after"][:max_chars] + "\n")
#
#         if row["dropped"]:
#             out.write("--- DÒNG BỊ XÓA HẲN " + "-" * 57 + "\n")
#             for line in row["dropped"][:20]:
#                 out.write(f"  {line[:90]}\n")
#
#         if row["changed"]:
#             out.write("--- DÒNG BỊ SỬA " + "-" * 61 + "\n")
#             for before, after in row["changed"][:10]:
#                 out.write(f"  TRƯỚC: {before[:100]}\n")
#                 out.write(f"  SAU  : {after[:100]}\n")
#
#     return {
#         "name": path.name,
#         "pages": len(raw),
#         "before": before_chars,
#         "after": after_chars,
#         "dropped": len(dropped_all),
#         "changed": len(changed_all),
#         "added": len(added_all),
#         "reasons": Counter(change_reasons(before) for before, _ in changed_all),
#         "chunks": chunks,
#         "marks_before": before_marks,
#         "marks_after": after_marks,
#     }
#
#
# def write_summary(out, ocr_stats, native_stats):
#     out.write("\n" + "#" * 78 + "\n")
#     out.write("# TỔNG HỢP: TẦNG LÀM SẠCH TÁC ĐỘNG LÊN HAI NGUỒN\n")
#     out.write("#" * 78 + "\n")
#
#     for label, stats in (("OCR", ocr_stats), ("TEXT LAYER", native_stats)):
#         pages = sum(item["pages"] for item in stats)
#         before = sum(item["before"] for item in stats)
#         after = sum(item["after"] for item in stats)
#         dropped = sum(item["dropped"] for item in stats)
#         changed = sum(item["changed"] for item in stats)
#         chunks = sum(item["chunks"] for item in stats)
#
#         reasons = Counter()
#         for item in stats:
#             reasons.update(item["reasons"])
#
#         out.write(f"\n[{label}] {len(stats)} file, {pages} trang\n")
#         out.write(f"  Ký tự      : {before} -> {after} ({percent(after, before)})\n")
#         out.write(f"  Dòng xóa hẳn: {dropped}\n")
#         out.write(f"  Dòng bị sửa : {changed}\n")
#         for names, count in reasons.most_common():
#             out.write(f"      {count:>5d}  {' + '.join(names)}\n")
#         out.write(f"  Chunk      : {chunks}\n")
#         if pages:
#             out.write(f"  Trung bình : {after // max(pages, 1)} ký tự/trang, "
#                       f"{chunks / max(pages, 1):.1f} chunk/trang\n")
#
#         marks_before = Counter()
#         marks_after = Counter()
#         for item in stats:
#             marks_before.update(item["marks_before"])
#             marks_after.update(item["marks_after"])
#         for name in MARKERS:
#             out.write(f"  {name:16s} {marks_before[name]:>6d} -> "
#                       f"{marks_after[name]:>6d} {percent(marks_after[name], marks_before[name])}\n")
# ---------------------------------------------------------------------------


def collect_pages(path: Path) -> tuple[dict[int, str], list[int]]:
    """Gom nội dung một file rồi làm sạch, kèm danh sách trang scan chưa có cache.

    Trang có lớp text đọc thẳng, trang scan lấy lại từ cache OCR nên không tốn
    thêm request nào.
    """
    native, scanned = classify_pages(path)
    cached = _load_cache(path)

    pages = extract_native_pages(path, native)
    pages.update({index: cached[index] for index in scanned if index in cached})

    cleaned = {
        index: text for index, text in clean_pages(pages).items() if text.strip()
    }
    missing = [index for index in scanned if index not in cached]
    return cleaned, missing


def build_chunks(path: Path, pages: dict[int, str]) -> tuple[list[Document], list[str]]:
    """Cắt từng trang thành chunk Markdown kèm metadata và id cố định."""
    splitter = _markdown_splitter()
    documents, ids = [], []

    for index in sorted(pages):
        # Đánh số trang từ 1 cho khớp với số trang in trên tài liệu.
        page = Document(page_content=pages[index], metadata={"page": index + 1})

        for order, chunk in enumerate(splitter.split_documents([page])):
            if not chunk.page_content.strip():
                continue
            chunk.metadata = textbook_metadata(path, index + 1)
            documents.append(chunk)
            ids.append(document_id(SOURCE_TEXTBOOK, path.name, index + 1, order))

    return documents, ids


def ingest_path(path: Path, dry_run: bool) -> tuple[int, int]:
    """Nạp một file, trả về (số chunk cắt được, số chunk mới thêm vào store)."""
    if not _cache_path(path).exists():
        log("  chưa có cache OCR, bỏ qua")
        return 0, 0

    pages, missing = collect_pages(path)
    if missing:
        log(f"  {len(missing)} trang scan chưa OCR, bỏ qua các trang này")

    documents, ids = build_chunks(path, pages)
    if not documents:
        log("  không có nội dung để nạp")
        return 0, 0

    log(f"  {len(pages)} trang -> {len(documents)} chunk | id đầu: {ids[0]}")
    if dry_run:
        return len(documents), 0

    added = _add_documents(documents, ids)
    log(f"  nạp mới {added} chunk vào vector store")
    return len(documents), added


def run_ingest(pattern: str, dry_run: bool) -> None:
    paths = sorted(Path(settings.RAG_DATA_DIR).glob(pattern))
    if not paths:
        log(f"Không có file nào khớp {pattern} trong {settings.RAG_DATA_DIR}")
        return

    started_at = time.monotonic()
    total_chunks, total_added = 0, 0

    for path in paths:
        log(f"\n{path.name}")
        chunks, added = ingest_path(path, dry_run)
        total_chunks += chunks
        total_added += added

    log(f"\nTổng {total_chunks} chunk, nạp mới {total_added} chunk")
    log(f"Xong trong {format_duration(time.monotonic() - started_at)}")


# ---------------------------------------------------------------------------
# THỬ PROMPT TRONG TERMINAL
# ---------------------------------------------------------------------------

LINE = "-" * 78

REPL_HELP = """
Gõ nội dung rồi Enter để chạy. Lệnh trong phiên:
  :course <id>    đổi course_id      :count <n>     số câu bài tập
  :lesson <id|->  đổi lesson_id      :type <loại>   {types}
  :show           xem tham số        :q             thoát (hoặc quit/exit/Ctrl+C)
"""


def _show_state(state: dict) -> None:
    log(
        f"  course_id={state['course_id']}  lesson_id={state['lesson_id']}  "
        f"count={state['count']}  type={state['question_type']}"
    )


def _apply_setting(line: str, state: dict) -> None:
    """Đổi tham số ngay trong phiên mà không phải thoát ra chạy lại."""
    parts = line[1:].split(maxsplit=1)
    name = parts[0].lower() if parts else ""
    value = parts[1].strip() if len(parts) > 1 else ""

    if name in ("course", "lesson"):
        state[f"{name}_id"] = None if value in ("", "-", "none") else int(value)
    elif name == "count":
        state["count"] = int(value)
    elif name == "type":
        if value.upper() not in QUESTION_TYPES:
            log(f"  loại câu hỏi phải là một trong {QUESTION_TYPES}")
            return
        state["question_type"] = value.upper()
    elif name != "show":
        log(f"  không hiểu lệnh :{name}")
        return

    _show_state(state)


def _print_answer(answer: str, grounded: bool, sources: list) -> None:
    log(LINE)
    log(answer)
    log(LINE)
    log(f"grounded={grounded}")

    if not sources:
        return
    log("nguồn:")
    for source in sources:
        page = f", trang {source['page']}" if source.get("page") else ""
        log(f"  - {source['title']}{page}")


def _retrieve(query: str, state: dict) -> list:
    """Lấy chunk đúng cách service đang lấy, để so sánh prompt trên cùng context."""
    search_kwargs = {"k": DEFAULT_TOP_K}
    chroma_filter = _build_chroma_filter(state["course_id"], state["lesson_id"])
    if chroma_filter:
        search_kwargs["filter"] = chroma_filter

    retriever = get_vector_store().as_retriever(search_kwargs=search_kwargs)
    return retriever.invoke(query)


def handle_ask(question: str, state: dict) -> None:
    result = query_rag_answer(
        query=question,
        course_id=state["course_id"],
        lesson_id=state["lesson_id"],
    )
    _print_answer(result["answer"], result["grounded"], result["sources"])


def handle_compare(question: str, state: dict) -> None:
    """Chạy cùng một context qua hai prompt để thấy khác biệt do prompt gây ra."""
    docs = _retrieve(question, state)
    log(f"  {len(docs)} chunk khớp")

    context = (
        "\n\n".join(doc.page_content for doc in docs)
        if docs
        else "(Không có tài liệu nào khớp với câu hỏi này.)"
    )

    for label, prompt in (("STRICT", STRICT_PROMPT), ("HYBRID", HYBRID_PROMPT)):
        log(f"\n===== {label} " + "=" * (71 - len(label)))
        response = (prompt | get_llm()).invoke(
            {"context": context, "question": question}
        )
        answer, grounded = split_grounding(message_text(response))
        _print_answer(answer, grounded, format_sources(docs) if grounded else [])


def handle_exercises(_: str, state: dict) -> None:
    if not state["course_id"]:
        log("  cần course_id, dùng :course <id>")
        return

    questions = generate_exercises_rag(
        course_id=state["course_id"],
        lesson_id=state["lesson_id"],
        question_type=state["question_type"],
        count=state["count"],
    )
    log(f"  sinh được {len(questions)} câu")

    for order, question in enumerate(questions, start=1):
        log(f"\n{order}. {question.get('content', '')}")
        for answer in question.get("answers") or []:
            mark = "x" if answer.get("is_correct") else " "
            log(f"   [{mark}] {answer.get('content', '')}")
        if question.get("explanation"):
            log(f"   -> {question['explanation']}")


def repl(handler, label: str, state: dict, allow_empty: bool = False) -> None:
    """Vòng lặp nhập lệnh; lỗi một lượt không làm mất phiên đang chạy."""
    log(REPL_HELP.format(types="|".join(QUESTION_TYPES)))
    _show_state(state)

    while True:
        try:
            line = input(f"\n{label}> ").strip()
        except (EOFError, KeyboardInterrupt):
            log()
            return

        if line in ("quit", "exit", ":q"):
            return
        if line.startswith(":"):
            try:
                _apply_setting(line, state)
            except ValueError:
                log("  giá trị không hợp lệ")
            continue
        if not line and not allow_empty:
            continue

        started_at = time.monotonic()
        try:
            handler(line, state)
        except Exception as exc:
            log(f"  LỖI {type(exc).__name__}: {exc}")
            continue
        log(f"\n  ({time.monotonic() - started_at:.1f}s)")


HANDLERS = {
    "ask": (handle_ask, "hỏi", False),
    "compare": (handle_compare, "so sánh", False),
    "exercises": (handle_exercises, "sinh", True),
}


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", nargs="?", default="ingest", choices=COMMANDS,
                        help="Việc cần chạy, mặc định là ingest")
    parser.add_argument("--pattern", default=OCR_PATTERN,
                        help="Mẫu tên file trong RAG_DATA_DIR")
    parser.add_argument("--dry-run", action="store_true",
                        help="Chỉ cắt chunk để xem số lượng, không gọi embedding")
    parser.add_argument("--course", type=int, help="course_id dùng để lọc tài liệu")
    parser.add_argument("--lesson", type=int, help="lesson_id dùng để lọc tài liệu")
    parser.add_argument("--count", type=int, default=5, help="Số câu bài tập cần sinh")
    parser.add_argument("--type", default=Question.QuestionType.MULTIPLE_CHOICE,
                        choices=QUESTION_TYPES, help="Loại câu hỏi cần sinh")
    args = parser.parse_args()

    if args.command == "ingest":
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        run_ingest(args.pattern, args.dry_run)
        return

    # Chạy thử prompt thì chỉ cần thấy câu trả lời, log INFO của thư viện gây nhiễu.
    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    handler, label, allow_empty = HANDLERS[args.command]
    state = {
        "course_id": args.course,
        "lesson_id": args.lesson,
        "count": args.count,
        "question_type": args.type,
    }
    repl(handler, label, state, allow_empty)


if __name__ == "__main__":
    main()
