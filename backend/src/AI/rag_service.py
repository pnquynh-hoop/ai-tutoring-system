from typing import List, Optional

from django.conf import settings
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from .vector_store import get_llm, get_vector_store

TEXTBOOK_SOURCE_TYPE = "textbook"
# Sách giáo khoa chia thành hàng trăm chunk nên lấy rộng hơn để đủ ngữ cảnh trả lời.
DEFAULT_TOP_K = 8


def _build_chroma_filter(
    course_id: Optional[int] = None,
    lesson_id: Optional[int] = None,
    include_textbook: bool = True,
) -> Optional[dict]:
    """Phạm vi truy vấn: tài liệu của khóa/bài học + kiến thức nền từ SGK.

    Trả về None nghĩa là không giới hạn (dùng khi chỉ có mỗi nguồn SGK).
    """
    scopes = []

    if course_id and lesson_id:
        scopes.append({"$and": [{"course_id": course_id}, {"lesson_id": lesson_id}]})
    elif course_id:
        scopes.append({"course_id": course_id})

    if include_textbook:
        scopes.append({"source_type": TEXTBOOK_SOURCE_TYPE})

    if not scopes:
        return None
    return scopes[0] if len(scopes) == 1 else {"$or": scopes}


def message_text(message) -> str:
    """Lấy text thuần từ phản hồi của LLM.

    Các model Gemini mới trả về `content` dạng danh sách khối
    ``[{"type": "text", "text": "..."}]`` thay vì chuỗi, nên phải gộp lại.
    """
    content = getattr(message, "content", message)

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(part for part in parts if part).strip()

    return str(content)


def format_sources(documents) -> List[dict]:
    """Rút gọn tài liệu truy xuất được thành danh sách nguồn để hiển thị cho học sinh."""
    seen, sources = set(), []

    for doc in documents:
        metadata = doc.metadata or {}
        title = metadata.get("title") or metadata.get("source") or "Tài liệu bài học"
        page = metadata.get("page")
        key = (title, page)

        if key in seen:
            continue
        seen.add(key)
        sources.append({"title": title, "page": page})

    return sources


# Câu mở đầu bắt buộc khi trả lời ngoài giáo trình; service dựa vào đây để biết
# câu trả lời không còn bám tài liệu và bỏ phần trích nguồn cho khỏi gây hiểu nhầm.
OUTSIDE_MATERIAL_PREFIX = "Nội dung này không có trong tài liệu của khóa học, mình trả lời theo kiến thức chung:"

STRICT_PROMPT = ChatPromptTemplate.from_template("""
    You are a professional AI learning assistant for a Vietnamese tutoring platform.

    RULES:
    1) Base your answer on the context below (lesson materials and the textbook).
    2) The context may be exercises, examples or tables rather than a formal definition.
       In that case, still help the student: explain the point using those examples and
       say which part of the material you relied on.
    3) Only when the context has nothing related to the question at all, respond exactly:
    "Mình không tìm thấy thông tin này trong tài liệu bài học và sách giáo khoa được cung cấp."
    4) Do NOT invent facts, examples, definitions, rules or numbers that contradict the context.
    5) Answer in Vietnamese, clear and easy for a high school student to understand.
    6) Keep the answer focused; do not dump the whole context back to the student.

    Context:
    {context}

    Student Question:
    {question}
    """)

HYBRID_PROMPT = ChatPromptTemplate.from_template("""
    You are a professional AI learning assistant for a Vietnamese high school tutoring platform.

    RULES:
    1) Prefer the context below (lesson materials and the textbook). If it answers the
       question, use it and mention which part you relied on.
    2) The context may be exercises, examples or tables rather than a formal definition.
       Still help the student by explaining from those examples.
    3) If the context does NOT cover the question, you may answer from your own subject
       knowledge, but you MUST start the answer with exactly this line:
       "%(prefix)s"
       Then give the answer. Never mix this line into an answer that came from the context.
    4) Stay within school subjects (English, Maths, and the other high school subjects).
       If the question is unrelated to studying, politely decline.
    5) Never contradict the context, and never invent facts about this specific course
       (lessons, schedule, scores, teachers) - those must come from the context only.
    6) Answer in Vietnamese, clear and easy for a high school student to understand.
    7) Keep the answer focused; do not dump the whole context back to the student.

    Context:
    {context}

    Student Question:
    {question}
    """ % {"prefix": OUTSIDE_MATERIAL_PREFIX})


def split_grounding(answer: str) -> tuple[str, bool]:
    """Tách nhãn "ngoài tài liệu" khỏi câu trả lời.

    Trả về (câu trả lời, có bám tài liệu hay không). Câu trả lời ngoài giáo trình
    thì không kèm trích nguồn, vì các đoạn truy xuất được thực chất không được dùng.
    """
    stripped = answer.strip()
    if stripped.startswith(OUTSIDE_MATERIAL_PREFIX):
        return stripped, False
    return stripped, True


def query_rag_answer(
    query: str, course_id: Optional[int] = None, lesson_id: Optional[int] = None
) -> dict:
    """Trả lời câu hỏi của học sinh dựa trên tài liệu đã lập chỉ mục.

    Trả về dict gồm câu trả lời và danh sách nguồn đã dùng.
    """
    search_kwargs = {"k": DEFAULT_TOP_K}
    chroma_filter = _build_chroma_filter(course_id, lesson_id)
    if chroma_filter:
        search_kwargs["filter"] = chroma_filter

    retriever = get_vector_store().as_retriever(search_kwargs=search_kwargs)
    docs = retriever.invoke(query)

    allow_general = getattr(settings, "RAG_ALLOW_GENERAL_KNOWLEDGE", True)

    if not docs and not allow_general:
        return {
            "answer": "Mình chưa có tài liệu nào cho nội dung này. Bạn thử hỏi ở một bài học khác nhé.",
            "sources": [],
            "grounded": True,
        }

    context = (
        "\n\n".join(doc.page_content for doc in docs)
        if docs
        else "(Không có tài liệu nào khớp với câu hỏi này.)"
    )
    prompt = HYBRID_PROMPT if allow_general else STRICT_PROMPT
    response = (prompt | get_llm()).invoke({"context": context, "question": query})

    answer, grounded = split_grounding(message_text(response))

    return {
        "answer": answer,
        "sources": format_sources(docs) if grounded else [],
        "grounded": grounded,
    }


# --- Schema cấu trúc dữ liệu tạo bài tập ---


class GeneratedAnswerSchema(BaseModel):
    content: str = Field(description="Nội dung phương án đáp án")
    is_correct: bool = Field(description="True nếu là đáp án đúng, False nếu sai")


class GeneratedQuestionSchema(BaseModel):
    content: str = Field(description="Nội dung câu hỏi")
    explanation: str = Field(description="Lời giải chi tiết")
    answers: List[GeneratedAnswerSchema] = Field(
        default=[], description="Danh sách lựa chọn (nếu là trắc nghiệm)"
    )


class GeneratedQuestionListSchema(BaseModel):
    questions: List[GeneratedQuestionSchema]


def generate_exercises_rag(
    course_id: int, lesson_id: Optional[int], question_type: str, count: int
) -> List[dict]:
    search_kwargs = {"k": DEFAULT_TOP_K}
    chroma_filter = _build_chroma_filter(course_id, lesson_id)
    if chroma_filter:
        search_kwargs["filter"] = chroma_filter

    # Dùng query tổng quan thay vì chuỗi rỗng ""
    docs = get_vector_store().similarity_search(
        "Kiến thức trọng tâm bài học", **search_kwargs
    )

    context = (
        "\n\n".join(d.page_content for d in docs)
        if docs
        else "The content does not exist."
    )

    parser = JsonOutputParser(pydantic_object=GeneratedQuestionListSchema)

    prompt = ChatPromptTemplate.from_template(
        """
        You are an expert educational assessment designer.

        RULES:
        1) Generate exactly {count} questions of type "{question_type}".
        2) Use ONLY the information provided in the lesson context.
        3) Do NOT use outside knowledge, assumptions, guesses, or web information.
        4) Do NOT create questions whose answers cannot be found in the context.
        5) Ensure all generated questions are factually supported by the context.
        6) Write the questions in Vietnamese.
        7) Return ONLY valid JSON that strictly follows the provided schema.
        8) Do NOT include explanations, markdown, comments, or any text outside the JSON output.

        Lesson Context:
        {context}

        JSON Schema:
        {format_instructions}
        """,
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | get_llm() | parser
    res = chain.invoke(
        {"count": count, "question_type": question_type, "context": context}
    )
    return res.get("questions", [])
