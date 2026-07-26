import os
import sys
import chromadb
import fitz  # PyMuPDF - Thư viện trị dứt điểm lỗi Font PDF
from dotenv import load_dotenv

# 1. Load biến môi trường từ file .env
load_dotenv()

# 2. Import công cụ chuẩn LangChain & Google Gemini
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

# =====================================================================
# 1. KIỂM TRA ĐƯỜNG DẪN FILE & GOOGLE API KEY
# =====================================================================
PDF_FILE_PATH = r"D:\NHUQUYNH\HK3_25\ai-tutoring-system\backend\data\SGK_12_clean.pdf"
CHROMA_PATH = "./chroma_db_test"

if not os.path.exists(PDF_FILE_PATH):
    print(f"❌ LỖI: Không tìm thấy file PDF tại đường dẫn: {PDF_FILE_PATH}")
    sys.exit(1)

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ LỖI: Chưa lấy được GOOGLE_API_KEY từ file .env!")
    sys.exit(1)

# =====================================================================
# 2. KHỞI TẠO EMBEDDING & VECTOR DB BẰNG GOOGLE GEMINI
# =====================================================================
print("⏳ Đang khởi tạo Gemini Embeddings (text-embedding-004) & ChromaDB...")

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004", google_api_key=api_key, api_version="v1beta"
)

client = chromadb.PersistentClient(path=CHROMA_PATH)
vector_store = Chroma(
    client=client,
    collection_name="test_materials_gemini",
    embedding_function=embeddings,
)


# =====================================================================
# 3. BƯỚC INGEST: ĐỌC FILE PDF CỤC BỘ BẰNG PYMUPDF (FITZ)
# =====================================================================
def ingest_file_directly(file_path: str):
    print(f"📄 Đang bóc tách chữ từ PDF bằng PyMuPDF (fitz): {file_path}...")

    docs = []
    try:
        # Mở file PDF bằng engine fitz
        doc = fitz.open(file_path)
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")  # Bóc tách lớp chữ
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

    print(f"✂️  Thành công! Đã chia nhỏ thành {len(chunks)} đoạn văn bản (chunks).")

    if not chunks:
        print("❌ LỖI: Chunks bị rỗng!")
        return False

    print("💾 Đang gửi Gemini nhúng Vector và lưu vào ChromaDB local...")
    vector_store.add_documents(chunks)
    print("✅ Hoàn tất nạp dữ liệu vào Vector DB!\n")
    return True


# Chạy Ingest nạp dữ liệu từ file PDF
is_success = ingest_file_directly(PDF_FILE_PATH)

if not is_success:
    print("\n⛔ Không thể tiếp tục do chưa nạp được dữ liệu vào Vector DB.")
    sys.exit(1)

# =====================================================================
# 4. BƯỚC VÒNG LẶP HỎI ĐÁP (CHAT IN TERMINAL)
# =====================================================================
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=api_key,
    temperature=0.3,
)

prompt = ChatPromptTemplate.from_template(
    """
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
    """
)

chain = prompt | llm

print("=========================================================")
print("🤖 HỆ THỐNG RAG DẠY HỌC (GEMINI 100%) ĐÃ SẴN SÀNG TEST!")
print("💡 Gõ câu hỏi của bạn và nhấn Enter. Gõ 'exit' hoặc 'quit' để thoát.")
print("=========================================================\n")

while True:
    try:
        user_query = input("\n👤 Bạn hỏi: ").strip()

        if not user_query:
            continue

        if user_query.lower() in ["exit", "quit", "q"]:
            print("👋 Tạm biệt!")
            break

        print("🔍 AI đang tra cứu trong SGK Tiếng Anh 12...")

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
