import os
from typing import List, Optional
import chromadb
from pydantic import BaseModel, Field
from django.conf import settings

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

CHROMA_PATH = getattr(settings, "CHROMA_DB_PATH", "./chroma_db")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path=CHROMA_PATH)
vector_store = Chroma(
    client=client, collection_name="learning_materials", embedding_function=embeddings
)

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.3,
)


def _build_chroma_filter(course_id: int, lesson_id: Optional[int] = None) -> dict:
    """Tạo filter chuẩn cho ChromaDB"""
    if lesson_id:
        return {"$and": [{"course_id": course_id}, {"lesson_id": lesson_id}]}
    return {"course_id": course_id}


def query_rag_answer(
    query: str, course_id: int, lesson_id: Optional[int] = None
) -> str:
    filter_dict = _build_chroma_filter(course_id, lesson_id)
    search_kwargs = {"k": 3, "filter": filter_dict}

    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
    docs = retriever.invoke(query)

    context = (
        "\n\n".join([doc.page_content for doc in docs])
        if docs
        else "There is no match results."
    )

    prompt = ChatPromptTemplate.from_template(
        """
        You are a professional AI learning assistant for an educational platform.
        RULES:
        1) Use ONLY the information provided in the lesson context to answer.
        2) If the answer is not clearly contained in the context, respond exactly:
        "I don't know based on the provided lesson materials."
        3) Do NOT use outside knowledge, assumptions, guesses, or web information.
        4) Keep explanations clear, accurate, concise, and easy for students to understand.
        5) When relevant, refer to the lesson content as the basis of your explanation.
        6) Do NOT invent facts, examples, definitions, or details that are not present in the context.
        7) If the context contains the answer, explain it using only the information from the lesson.

        Lesson Context:
        {context}

        Student Question:
        {question}
        """
    )

    chain = prompt | llm
    response = chain.invoke({"context": context, "question": query})
    return response.content


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
    filter_dict = _build_chroma_filter(course_id, lesson_id)

    # Dùng query tổng quan thay vì chuỗi rỗng ""
    docs = vector_store.similarity_search(
        "Kiến thức trọng tâm bài học", k=4, filter=filter_dict
    )

    context = (
        "\n\n".join([d.page_content for d in docs])
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
        6) Questions should be clear, educational, and appropriate for students.
        7) Return ONLY valid JSON that strictly follows the provided schema.
        8) Do NOT include explanations, markdown, comments, or any text outside the JSON output.

        Lesson Context:
        {context}

        JSON Schema:
        {format_instructions}
        """,
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser
    res = chain.invoke(
        {"count": count, "question_type": question_type, "context": context}
    )
    return res.get("questions", [])
