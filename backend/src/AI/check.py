
import argparse
import logging
import os
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*fixed sampling defaults.*")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stdin.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_tutoring_system.settings")

import django

django.setup()

from AI.rag_service import (
    DEFAULT_TOP_K,
    HYBRID_PROMPT,
    STRICT_PROMPT,
    build_chroma_filter,
    format_sources,
    generate_exercises_rag,
    message_text,
    query_rag_answer,
    split_grounding,
)
from AI.vector_store import get_llm, get_vector_store
from assignments.models import Question

COMMANDS = ("ask", "compare", "exercises")
QUESTION_TYPES = Question.QuestionType.values




def log(message="", end="\n"):
    print(message, end=end, flush=True)


LINE = "-" * 78

REPL_HELP = """
Gõ nội dung rồi Enter để chạy. Lệnh trong phiên:
  :course <id>    đổi course_id      :count <n>     số câu bài tập
  :lesson <id|->  đổi lesson_id      :type <loại>   {types}
  :show           xem tham số        :q             thoát (hoặc quit/exit/Ctrl+C)
"""


def show_state(state):
    log(
        f"  course_id={state['course_id']}  lesson_id={state['lesson_id']}  "
        f"count={state['count']}  type={state['question_type']}"
    )


def apply_setting(command_line, state):
    parts = command_line[1:].split(maxsplit=1)
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

    show_state(state)


def print_answer(answer, grounded, sources):
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


def retrieve(query, state):
    search_kwargs = {"k": DEFAULT_TOP_K}
    chroma_filter = build_chroma_filter(state["course_id"], state["lesson_id"])
    if chroma_filter:
        search_kwargs["filter"] = chroma_filter

    retriever = get_vector_store().as_retriever(search_kwargs=search_kwargs)
    return retriever.invoke(query)


def handle_ask(question, state):
    result = query_rag_answer(
        query=question,
        course_id=state["course_id"],
        lesson_id=state["lesson_id"],
    )
    print_answer(result["answer"], result["grounded"], result["sources"])


def handle_compare(question, state):
    docs = retrieve(question, state)
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
        print_answer(answer, grounded, format_sources(docs) if grounded else [])


def handle_exercises(_, state):
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


def repl(handler, label, state, allow_empty=False):
    log(REPL_HELP.format(types="|".join(QUESTION_TYPES)))
    show_state(state)

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
                apply_setting(line, state)
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


def run_cli():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", nargs="?", default="ask", choices=COMMANDS,
                        help="Việc cần chạy, mặc định là ask")
    parser.add_argument("--course", type=int, help="course_id dùng để lọc tài liệu")
    parser.add_argument("--lesson", type=int, help="lesson_id dùng để lọc tài liệu")
    parser.add_argument("--count", type=int, default=5, help="Số câu bài tập cần sinh")
    parser.add_argument("--type", default=Question.QuestionType.MULTIPLE_CHOICE,
                        choices=QUESTION_TYPES, help="Loại câu hỏi cần sinh")
    args = parser.parse_args()

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
    run_cli()
