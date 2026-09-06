# AI Tutoring Center

### Tổng quan

AI Tutoring Center là hệ thống quản lý học tập (LMS) tích hợp trí tuệ nhân tạo dành cho các trung tâm gia sư. Hệ thống hỗ trợ quản lý hoạt động giảng dạy và học tập, cho phép gia sư xây dựng nội dung khóa học, đồng thời cung cấp các công cụ AI hỗ trợ học sinh trong quá trình học tập.

### Chức năng chính

#### Quản trị viên (Admin)

* Quản lý tài khoản người dùng
* Quản lý gia sư
* Quản lý môn học và chủ đề kiến thức
* Quản lý khóa học
* Quản lý ghi danh học viên

#### Gia sư (Tutor)

* Quản lý khóa học được phân công
* Tạo chương học và bài học
* Quản lý tài liệu học tập
* Tạo bài tập và bài kiểm tra
* Theo dõi kết quả học tập của học sinh

#### Học sinh (Student)

* Truy cập các khóa học đã được ghi danh
* Học nội dung bài giảng
* Làm bài tập
* Thực hiện bài kiểm tra
* Theo dõi tiến độ học tập
* Sử dụng các công cụ AI hỗ trợ học tập

#### Chức năng AI

* AI Chat Tutor
* AI Giải bài tập
* AI Sinh bài tập
* Truy xuất tri thức bằng RAG
* Hỗ trợ học tập cá nhân hóa

### Công nghệ sử dụng

**Backend**

* Django REST Framework
* MySQL

**Frontend**

* Svelte

**AI & RAG**

* OpenAI / Gemini
* LangChain
* Vector Database
* FAISS / ChromaDB

### Chạy dự án

Hệ thống cần ba tiến trình chạy song song: Redis làm hàng đợi, Celery worker chạy tác vụ nền (nạp tài liệu vào kho RAG), và máy chủ Django.

**Chuẩn bị** — mọi lệnh Python bên dưới đều chạy ở `backend/src` và trong venv:

```bash
cd backend\src
..\tutor_venv\Scripts\activate
```

**Redis** — gõ ở thư mục nào cũng được, nhưng Docker Desktop phải đang chạy:

```bash
docker run -d --name tutor-redis -p 6379:6379 redis:7-alpine   # tạo lần đầu
docker start tutor-redis                                       # bật lại các lần sau
docker stop tutor-redis                                        # tắt
docker ps                                                      # xem còn chạy không
docker rm -f tutor-redis                                       # xoá hẳn để tạo lại từ đầu
```

**Celery worker** — nơi tác vụ nạp tài liệu thực sự chạy, tắt bằng Ctrl+C:

```bash
celery -A ai_tutoring_system worker -l info --pool=solo
```

`--pool=solo` bắt buộc trên Windows: pool prefork mặc định dựa trên `fork()` của Unix nên worker sẽ nhận việc rồi đứng im.

**Celery beat** — chỉ cần khi muốn chạy tác vụ định kỳ đóng bài làm quá hạn:

```bash
celery -A ai_tutoring_system beat -l info
```

**Máy chủ Django**

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**Thứ tự bật:** Redis trước, rồi Celery worker, rồi runserver. **Thứ tự tắt:** Ctrl+C hai cửa sổ Python, rồi `docker stop tutor-redis`.

Bật runserver khi Redis chưa lên rồi bấm nút nạp tài liệu sẽ làm hỏng kết nối Celery bên trong tiến trình web; lúc đó phải tắt và bật lại runserver, bật Redis thôi không đủ.

**Nạp tài liệu bằng dòng lệnh** — không cần Redis lẫn Celery worker:

```bash
python AI/check.py ingest --dry-run     # liệt kê tài liệu sẽ nạp, không gọi API
python AI/check.py ingest --id 9        # nạp một tài liệu
python AI/check.py ingest               # nạp mọi tài liệu Chờ nạp và Nạp lỗi
python AI/check.py ingest --redo        # nạp lại cả tài liệu đã nạp xong
python AI/check.py ask                  # hỏi thử chatbot ngay trong terminal
```

**Chạy test**

```bash
pytest
```

### Hướng phát triển

* Cá nhân hóa lộ trình học tập
* Phân tích dữ liệu học tập
* Chấm điểm tự luận bằng AI
* Lớp học trực tuyến
* Hệ thống gợi ý học tập nâng cao
