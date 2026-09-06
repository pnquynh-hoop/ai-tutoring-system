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

* AI Chat Tutor
* AI Exercise Solver
* AI Exercise Generator
* RAG-based knowledge retrieval
* Personalized learning support

### Technology Stack

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

### Running the Project

Three processes run side by side: Redis as the task queue, a Celery worker that runs background jobs (ingesting materials into the RAG store), and the Django server.

**Setup** — every Python command below runs from `backend/src` inside the venv:

```bash
cd backend\src
..\tutor_venv\Scripts\activate
```

**Redis** — the working directory does not matter, but Docker Desktop must be running:

```bash
docker run -d --name tutor-redis -p 6379:6379 redis:7-alpine   # create once
docker start tutor-redis                                       # start again later
docker stop tutor-redis                                        # stop
docker ps                                                      # check if it is up
docker rm -f tutor-redis                                       # remove it and start over
```

**Celery worker** — where the ingest job actually runs; stop it with Ctrl+C:

```bash
celery -A ai_tutoring_system worker -l info --pool=solo
```

`--pool=solo` is required on Windows: the default prefork pool relies on the Unix `fork()`, so the worker picks up jobs and then goes silent.

**Celery beat** — only needed to run the periodic job that closes overdue attempts:

```bash
celery -A ai_tutoring_system beat -l info
```

**Django server**

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**Start order:** Redis first, then the Celery worker, then runserver. **Stop order:** Ctrl+C both Python windows, then `docker stop tutor-redis`.

Starting runserver while Redis is down and then clicking the ingest button breaks the Celery connection inside the web process; runserver has to be restarted, bringing Redis up is not enough.

**Ingesting materials from the command line** — needs neither Redis nor the Celery worker:

```bash
python AI/check.py ingest --dry-run     # list what would be ingested, no API calls
python AI/check.py ingest --id 9        # ingest a single material
python AI/check.py ingest               # ingest everything pending or failed
python AI/check.py ingest --redo        # ingest again, including finished ones
python AI/check.py ask                  # try the chatbot in the terminal
```

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

