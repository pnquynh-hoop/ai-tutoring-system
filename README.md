# AI Tutoring Center

### Overview

AI Tutoring Center is an AI-powered Learning Management System (LMS) designed for tutoring centers. The platform helps administrators manage courses and learning activities, enables tutors to create and organize educational content, and supports students throughout their learning journey with AI-assisted tools.

### Key Features

#### Administration

* User management
* Tutor management
* Subject and topic management
* Course management
* Student enrollment management

#### Tutor

* Manage assigned courses
* Create chapters and lessons
* Upload learning resources
* Create assignments and assessments
* Monitor student progress and performance

#### Student

* Access enrolled courses
* Study learning materials
* Complete assignments
* Take assessments
* Track learning progress
* Use AI learning assistants

#### AI Features

* AI Chat Tutor — answers grounded in course resources and center materials, with citations
* AI Exercise Generator — backend complete, not yet wired to the interface
* RAG-based knowledge retrieval, scoped per student
* Personalized explanations driven by the student's academic level

### Technology Stack

**Backend**

* Django REST Framework
* MySQL

**Frontend**

* SvelteKit

**AI & RAG**

* Google Gemini
* LangChain
* ChromaDB

### Running the Project

Three processes run side by side: Redis as the task queue, a Celery worker that runs background jobs (ingesting materials into the RAG store), and the Django server.

**Setup** — every Python command below runs from `backend/src` inside the venv:

```bash
cd backend\src
..\tutor_venv\Scripts\activate
```

**Redis** — Docker Desktop must be running:

```bash
docker run -d --name tutor-redis -p 6379:6379 redis:7-alpine   # create once
docker start tutor-redis                                       # start again later
```

**Celery worker** — runs the background ingest jobs. `--pool=solo` is required on Windows:

```bash
celery -A ai_tutoring_system worker -l info --pool=solo
```

**Celery beat** — periodic job that closes overdue attempts:

```bash
celery -A ai_tutoring_system beat -l info
```

**Django server**

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Start Redis first, then the Celery worker, then runserver.

**Running tests**

```bash
pytest
```

### Future Enhancements

* Adaptive learning paths
* Learning analytics dashboard
* AI-powered grading
* Online tutoring sessions
* Advanced personalization

