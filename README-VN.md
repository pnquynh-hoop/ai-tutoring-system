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

* Trợ lý hỏi đáp — trả lời dựa trên tài nguyên khóa học và tài liệu trung tâm, có trích dẫn nguồn
* Sinh bài tập luyện tập — phần xử lý đã xong, chưa gắn vào giao diện
* Truy xuất tri thức bằng RAG, giới hạn phạm vi theo từng học sinh
* Cá nhân hóa cách giải thích theo học lực của học sinh

### Công nghệ sử dụng

**Backend**

* Django REST Framework
* MySQL

**Frontend**

* SvelteKit

**AI & RAG**

* Google Gemini
* LangChain
* ChromaDB

### Chạy dự án

Hệ thống cần ba tiến trình chạy song song: Redis làm hàng đợi, Celery worker chạy tác vụ nền (nạp tài liệu vào kho RAG), và máy chủ Django.

**Chuẩn bị** — mọi lệnh Python bên dưới đều chạy ở `backend/src` và trong venv:

```bash
cd backend\src
..\tutor_venv\Scripts\activate
```

**Redis** — Docker Desktop phải đang chạy:

```bash
docker run -d --name tutor-redis -p 6379:6379 redis:7-alpine   # tạo lần đầu
docker start tutor-redis                                       # bật lại các lần sau
```

**Celery worker** — nơi tác vụ nạp tài liệu chạy. `--pool=solo` bắt buộc trên Windows:

```bash
celery -A ai_tutoring_system worker -l info --pool=solo
```

**Celery beat** — tác vụ định kỳ đóng bài làm quá hạn:

```bash
celery -A ai_tutoring_system beat -l info
```

**Máy chủ Django**

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Bật Redis trước, rồi Celery worker, rồi runserver.

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
