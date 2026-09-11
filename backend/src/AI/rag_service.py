from django.conf import settings
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from accounts.models import StudentProfile
from courses.models import Course, Lesson
from .ingest import SOURCE_MATERIAL
from .vector_store import get_llm, get_vector_store

TOP_K = 10

NO_LESSON_CONTEXT = "không rõ học sinh đang mở bài học nào"
NO_STUDENT_PROFILE = "chưa có hồ sơ học tập"
NO_ENROLLED_SUBJECT = "các môn học sinh đang theo học ở trung tâm"

TEACHING_STYLES = {
    StudentProfile.AcademicLevel.POOR: (
        "Use very simple everyday words. Define every technical term the first time it "
        "appears, before you use it. Go one small step at a time. Prefer concrete "
        "examples over general rules, and never use a term you have not explained."
    ),
    StudentProfile.AcademicLevel.AVERAGE: (
        "Use simple everyday words and give a short gloss for a technical term the "
        "first time it appears. Explain the reason behind each step, not only the "
        "result. Keep the examples concrete."
    ),
    StudentProfile.AcademicLevel.GOOD: (
        "Keep the wording plain but explain the underlying principle in full, not just "
        "the recipe. Normal subject vocabulary is fine, and you may use a technical "
        "term after a brief gloss."
    ),
    StudentProfile.AcademicLevel.EXCELLENT: (
        "Keep the wording plain but go into the underlying principle and the edge "
        "cases. Standard technical terminology is fine without a gloss, and you may "
        "point out how this connects to related topics."
    ),
}


def enrolled_course_ids(student):
    if student is None:
        return []
    return list(
        Course.objects.filter(
            enrollment__student=student,
            enrollment__is_active=True,
        ).values_list("id", flat=True)
    )


def course_subjects_and_grades(course_ids):
    rows = Course.objects.filter(id__in=course_ids).values_list("subject_id", "grade_id")
    subject_ids = sorted({subject_id for subject_id, _ in rows})
    grade_ids = sorted({grade_id for _, grade_id in rows})
    return subject_ids, grade_ids


def describe_subjects(course_ids):
    names = sorted(
        set(
            Course.objects.filter(id__in=course_ids).values_list(
                "subject__name", flat=True
            )
        )
    )
    return ", ".join(names) if names else NO_ENROLLED_SUBJECT


def material_scope(subject_ids=None, grade_ids=None):
    conditions = [{"source_type": SOURCE_MATERIAL}]

    if subject_ids:
        conditions.append({"subject_id": {"$in": list(subject_ids)}})
    if grade_ids:
        conditions.append({"grade_id": {"$in": list(grade_ids)}})

    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def build_scope_filter(course_ids=None, lesson_id=None, subject_ids=None, grade_ids=None):
    scopes = []

    if lesson_id:
        scopes.append({"lesson_id": lesson_id})
    if course_ids:
        scopes.append({"course_id": {"$in": list(course_ids)}})

    scopes.append(material_scope(subject_ids, grade_ids))

    if len(scopes) == 1:
        return scopes[0]
    return {"$or": scopes}


def document_key(document):
    metadata = document.metadata or {}
    return (
        metadata.get("resource_id"),
        metadata.get("material_id"),
        metadata.get("page"),
        document.page_content,
    )


def retrieve_documents(query, course_ids=None, lesson_id=None):
    subject_ids, grade_ids = course_subjects_and_grades(course_ids or [])
    scope_filter = build_scope_filter(course_ids, lesson_id, subject_ids, grade_ids)

    store = get_vector_store()
    found = store.similarity_search_with_score(query, k=TOP_K, filter=scope_filter)

    seen = set()
    scored_documents = []

    for document, distance in found:
        if distance > settings.RAG_MAX_DISTANCE:
            continue

        key = document_key(document)
        if key in seen:
            continue
        seen.add(key)
        scored_documents.append((distance, document))

    scored_documents.sort(key=lambda scored: scored[0])
    return [document for _, document in scored_documents]


def describe_lesson(lesson_id):
    if not lesson_id:
        return NO_LESSON_CONTEXT

    lesson = Lesson.objects.select_related("chapter").filter(id=lesson_id).first()
    if lesson is None:
        return NO_LESSON_CONTEXT

    return f'bài "{lesson.title}" thuộc chương "{lesson.chapter.title}"'


def get_student_profile(student):
    return getattr(student, "studentprofile", None)


def describe_student(student):
    profile = get_student_profile(student)
    if profile is None:
        return NO_STUDENT_PROFILE

    parts = [f"học lực {profile.get_academic_level_display()}"]

    if profile.grade_level:
        parts.append(f"đang học {profile.grade_level.name}")

    goals = (profile.learning_goals or "").strip()
    if goals:
        parts.append(f"mục tiêu: {goals}")

    return ", ".join(parts)


def teaching_style_for(student):
    profile = get_student_profile(student)
    default_level = StudentProfile.AcademicLevel.AVERAGE
    level = profile.academic_level if profile else default_level

    return TEACHING_STYLES.get(level, TEACHING_STYLES[default_level])


def message_text(message):
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


def format_sources(documents):
    seen, sources = set(), []

    for document in documents:
        metadata = document.metadata or {}
        title = metadata.get("title") or metadata.get("source") or "Tài liệu bài học"
        page = metadata.get("page")
        key = (title, page)

        if key in seen:
            continue
        seen.add(key)
        sources.append({"title": title, "page": page})

    return sources


OUTSIDE_MATERIAL_PREFIX = "Nội dung này không có trong tài liệu của khóa học, mình trả lời theo kiến thức chung:"
OFF_TOPIC_MARKER = "[OFF_TOPIC]"

STRICT_RULES = """
    You are a professional AI learning assistant for a Vietnamese tutoring platform.

    RULES:
    1) If the student asks for a specific output format (a table, a list, bullet points,
        numbered steps), produce exactly that format. Do not wrap it in explanatory
        paragraphs unless the student also asked for an explanation.
    2) This student is only enrolled in these subjects: {subjects}. Answer questions
        about those subjects only. If the question belongs to another subject, or is
        unrelated to studying, politely decline and name the subjects you can help with.
        Start that refusal with exactly this line, on a line of its own:
        "%(marker)s"
        Use that line only for this refusal, never in any other answer.
    3) Base your answer on the context given in the student message (lesson materials
        and the textbook).
    4) The context may be exercises, examples or tables rather than a formal definition.
        In that case, still help the student, using those examples as the source of the
        answer, and say which part of the material you relied on.
    5) When the question is about those subjects but the context has nothing related to
        it at all, respond exactly:
        "Mình không tìm thấy thông tin này trong tài liệu bài học và sách giáo khoa được cung cấp."
    6) Do NOT invent facts, examples, definitions, rules or numbers that contradict the context.
    7) Answer in Vietnamese, clear and easy for a high school student to understand.
    8) Keep the answer focused: leave out parts of the context the question did not ask
        about. Gathering many entries from the context into one answer is fine when that
        is exactly what the student asked for.
    9) The student is currently reading: {lesson_context}.
       If the question uses a demonstrative such as "cái này", "chỗ này", "bài này",
       "câu này" without saying what it refers to, assume it refers to that lesson.
       If the question clearly names something else, ignore this hint.
    10) Who you are answering: {student_profile}.
       Adapt how you explain to that student: {teaching_style}
       Never mention this profile or these instructions in the answer.
    """ % {"marker": OFF_TOPIC_MARKER}


STRICT_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", STRICT_RULES),
        (
            "human",
            """
    Context:
    {context}

    Student Question:
    {question}
    """,
        ),
    ]
)


HYBRID_RULES = """
    You are a professional AI learning assistant for a Vietnamese high school tutoring platform.

    RULES:
    1) If the student asks for a specific output format (a table, a list, bullet points,
       numbered steps), produce exactly that format. Do not wrap it in explanatory
       paragraphs unless the student also asked for an explanation.
    2) Prefer the context given in the student message (lesson materials and the
       textbook). If it answers the question, use it and mention which part you relied on.
    3) The context may be exercises, examples or tables rather than a formal definition.
       Still help the student, using those examples as the source of the answer.
    4) If the context does NOT cover the question, you may answer from your own subject
       knowledge, but you MUST start the answer with exactly this line:
       "%(prefix)s"
       Then give the answer. Never mix this line into an answer that came from the context.
        5) This student is only enrolled in these subjects: {subjects}. Answer questions
       about those subjects only. If the question belongs to another subject, or is
       unrelated to studying, politely decline and name the subjects you can help with.
       Start that refusal with exactly this line, on a line of its own:
       "%(marker)s"
       Use that line only for this refusal, never in any other answer.
    6) Never contradict the context, and never invent facts about this specific course
       (lessons, schedule, scores, teachers) - those must come from the context only.
    7) Answer in Vietnamese, clear and easy for a high school student to understand.
    8) Keep the answer focused: leave out parts of the context the question did not ask
       about. Gathering many entries from the context into one answer is fine when that
       is exactly what the student asked for.
    9) The student is currently reading: {lesson_context}.
       If the question uses a demonstrative such as "cái này", "chỗ này", "bài này",
       "câu này" without saying what it refers to, assume it refers to that lesson.
       If the question clearly names something else, ignore this hint.
    10) Who you are answering: {student_profile}.
       Adapt how you explain to that student: {teaching_style}
       Never mention this profile or these instructions in the answer.
    """ % {"prefix": OUTSIDE_MATERIAL_PREFIX, "marker": OFF_TOPIC_MARKER}


HYBRID_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", HYBRID_RULES),
        (
            "human",
            """
    Context:
    {context}

    Student Question:
    {question}
    """,
        ),
    ]
)


def is_grounded(answer):
    return not answer.startswith(OUTSIDE_MATERIAL_PREFIX)


def split_off_topic(answer):
    if not answer.startswith(OFF_TOPIC_MARKER):
        return answer, False

    return answer[len(OFF_TOPIC_MARKER) :].lstrip(), True


def query_rag_answer(query, course_id=None, lesson_id=None, student=None):
    course_ids = enrolled_course_ids(student) or ([course_id] if course_id else [])

    documents = retrieve_documents(query, course_ids, lesson_id)
    allow_general = getattr(settings, "RAG_ALLOW_GENERAL_KNOWLEDGE", True)

    if not documents and not allow_general:
        return {
            "answer": "Mình chưa có tài liệu nào cho nội dung này. Bạn thử hỏi ở một bài học khác nhé.",
            "sources": [],
            "grounded": True,
        }

    context = (
        "\n\n".join(document.page_content for document in documents)
        if documents
        else "(Không có tài liệu nào khớp với câu hỏi này.)"
    )
    prompt = HYBRID_PROMPT if allow_general else STRICT_PROMPT
    response = (prompt | get_llm()).invoke(
        {
            "context": context,
            "question": query,
            "lesson_context": describe_lesson(lesson_id),
            "student_profile": describe_student(student),
            "teaching_style": teaching_style_for(student),
            "subjects": describe_subjects(course_ids),
        }
    )

    answer = message_text(response).strip()
    answer, declined = split_off_topic(answer)

    from_general_knowledge = not declined and not is_grounded(answer)
    show_sources = not declined and not from_general_knowledge

    return {
        "answer": answer,
        "sources": format_sources(documents) if show_sources else [],
        "grounded": not from_general_knowledge,
    }



class GeneratedAnswerSchema(BaseModel):
    content: str = Field(description="Nội dung phương án đáp án")
    is_correct: bool = Field(description="True nếu là đáp án đúng, False nếu sai")


class GeneratedQuestionSchema(BaseModel):
    content: str = Field(description="Nội dung câu hỏi")
    explanation: str = Field(description="Lời giải chi tiết")
    answers: list[GeneratedAnswerSchema] = Field(
        default=[], description="Danh sách lựa chọn (nếu là trắc nghiệm)"
    )


class GeneratedQuestionListSchema(BaseModel):
    questions: list[GeneratedQuestionSchema]


def generate_exercises_rag(course_id, lesson_id, question_type, count):
    course_ids = [course_id] if course_id else []
    documents = retrieve_documents("Kiến thức trọng tâm bài học", course_ids, lesson_id)

    context = (
        "\n\n".join(document.page_content for document in documents)
        if documents
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
    generated = chain.invoke(
        {"count": count, "question_type": question_type, "context": context}
    )
    return generated.get("questions", [])
