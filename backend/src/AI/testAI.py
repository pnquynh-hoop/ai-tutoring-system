"""Script thử nghiệm pipeline RAG ngoài Django (chạy tay trong terminal).

Cách chạy:
    python AI/testAI.py [đường_dẫn_pdf]
hoặc đặt biến môi trường RAG_TEST_PDF. Mặc định lấy file trong backend/data/.

Script chỉ chạy khi được gọi trực tiếp, import module này sẽ không thực thi gì.
"""

import os
import sys
from pathlib import Path

import chromadb
import fitz  # PyMuPDF - đọc lớp text của PDF, tránh lỗi font
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_PDF_PATH = BASE_DIR / "data" / "SGK_12_clean.pdf"
CHROMA_PATH = str(BASE_DIR / "chroma_db_test")


def resolve_pdf_path() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    return Path(os.getenv("RAG_TEST_PDF", DEFAULT_PDF_PATH))


def build_vector_store(api_key: str):
    embeddings = GoogleGenerativeAIEmbeddings(
        model=os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001"),
        google_api_key=api_key,
    )
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return Chroma(
        client=client,
        collection_name="test_materials_gemini",
        embedding_function=embeddings,
    )


def ingest_file_directly(vector_store, file_path: Path) -> bool:
    print(f"📄 Đang bóc tách chữ từ PDF bằng PyMuPDF: {file_path}...")

    docs = []
    try:
        doc = fitz.open(file_path)
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text and text.strip():
                docs.append(Document(page_content=text, metadata={"page": page_num}))
    except Exception as e:
        print(f"❌ Lỗi khi đọc file bằng PyMuPDF: {e}")
        return False

    if not docs:
        print("❌ LỖI: Không tìm thấy nội dung chữ trong file PDF!")
        return False

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = text_splitter.split_documents(docs)

    print(f"✂️  Đã chia nhỏ thành {len(chunks)} đoạn văn bản (chunks).")

    print("💾 Đang gửi Gemini nhúng Vector và lưu vào ChromaDB local...")
    vector_store.add_documents(chunks)
    print("✅ Hoàn tất nạp dữ liệu vào Vector DB!\n")
    return True


def chat_loop(vector_store, api_key: str):
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_LLM_MODEL", "gemini-flash-latest"),
        google_api_key=api_key,
        temperature=0.3,
    )

    prompt = ChatPromptTemplate.from_template("""
        You are a professional AI learning assistant for an educational platform.
        RULES:
        1) Use ONLY the information provided in the lesson context to answer.
        2) If the answer is not clearly contained in the context, respond exactly:
           "Tôi không tìm thấy thông tin này trong tài liệu SGK được cung cấp."
        3) Do NOT use outside knowledge, assumptions, guesses, or web information.
        4) Keep explanations clear, accurate, concise, and in Vietnamese.

        Lesson Context:
        {context}

        Student Question:
        {question}
        """)

    chain = prompt | llm

    print("=========================================================")
    print("🤖 HỆ THỐNG RAG DẠY HỌC (GEMINI) ĐÃ SẴN SÀNG TEST!")
    print("💡 Gõ câu hỏi và nhấn Enter. Gõ 'exit' hoặc 'quit' để thoát.")
    print("=========================================================\n")

    while True:
        try:
            user_query = input("\n👤 Bạn hỏi: ").strip()

            if not user_query:
                continue

            if user_query.lower() in ["exit", "quit", "q"]:
                print("👋 Tạm biệt!")
                break

            print("🔍 AI đang tra cứu trong tài liệu...")

            docs = vector_store.similarity_search(user_query, k=3)
            context = "\n\n".join([doc.page_content for doc in docs]) if docs else ""

            response = chain.invoke({"context": context, "question": user_query})

            print("\n🤖 AI Trả lời:")
            print(response.content)
            print("-" * 50)

        except KeyboardInterrupt:
            print("\n👋 Đã dừng chương trình!")
            break
        except Exception as e:
            print(f"❌ Lỗi xử lý: {e}")


def main() -> int:
    load_dotenv()

    pdf_path = resolve_pdf_path()
    if not pdf_path.exists():
        print(f"❌ LỖI: Không tìm thấy file PDF tại: {pdf_path}")
        return 1

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ LỖI: Chưa lấy được GOOGLE_API_KEY từ file .env!")
        return 1

    print("⏳ Đang khởi tạo Gemini Embeddings & ChromaDB...")
    vector_store = build_vector_store(api_key)

    if not ingest_file_directly(vector_store, pdf_path):
        print("\n⛔ Không thể tiếp tục do chưa nạp được dữ liệu vào Vector DB.")
        return 1

    chat_loop(vector_store, api_key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
