# Management System for an Online Tutoring Center with Integrated AI Assistant

## 1. Business Context

This project builds a management system for an online tutoring center that teaches the K-12 curriculum, with an integrated AI assistant. The center's operations consist of four interconnected areas:

- **Academic management.** The center maintains a shared repository of materials — textbooks, reference documents — classified by subject and grade level. This repository belongs to the center as a whole, not to any specific class.
- **Teaching organization.** Each tutor is responsible for one or more courses. Tutors author their own course content in a hierarchical structure and decide for themselves when to publish each part to students.
- **Assessment.** Tutors create assignments per chapter; students complete them within limits on attempts and time; the system auto-grades multiple-choice and fill-in-the-blank questions, while essay questions are graded by hand by the tutor.
- **AI support.** Students can ask the AI assistant questions and request generated practice exercises. The assistant answers based on the course's own materials and textbooks, with citations. How far each part has actually been implemented is covered in Section 11.

The core problem the system solves is: how to make the AI assistant answer correctly according to the center's curriculum, with verifiable citations, while ensuring each student can only access materials within their authorized scope.

## 2. Roles in the System

The system distinguishes three roles, implemented using Django's user group mechanism:

| Role | Scope of activity |
|---|---|
| Student | Study within enrolled courses, complete assignments, comment, ask the AI assistant |
| Tutor | Author content for courses they are responsible for, create assignments, grade essay questions |
| Admin | Manage accounts, the subject/grade catalog, the center's material repository, and enrollments |

A user account holds shared identity information — email, phone number (both unique across the system), full name, avatar — plus a role-specific profile:

- **Tutor profile** stores a short bio, qualification level, years of experience, and a verified flag. The verified flag is set only by an admin; tutors cannot edit it themselves.
- **Student profile** stores the grade level currently being studied, learning goals, and a self-assessed academic level on a four-point scale: weak, average, good, excellent.

This is a one-to-one relationship with the account: a user has at most one profile of each type. This separation allows new roles to be added later without cramming extra columns into the user table.

## 3. Structure of Learning Content

### 3.1 Academic Catalog

Two foundational entities, managed by admins and shared system-wide:

- **Subject:** a unique name with a description. Examples: Math, English, Physics.
- **Grade:** a unique integer, displayed as "Grade 10", "Grade 11".

Every course and every material must be tied to exactly one subject–grade pair. This pair is the classification axis running throughout the system.

### 3.2 Center Materials

A Material is learning content owned by the center — textbooks, syllabi, reference documents — classified by subject and grade, not tied to any specific course. In the RAG system, this is the foundational knowledge source: every student can retrieve it, regardless of which course they're taking.

Materials follow a notable storage rule. Files under 10MB are uploaded to the Cloudinary cloud storage service; files between 10MB and 100MB are stored directly on the server disk. The reason is that the free Cloudinary tier limits file size per upload, while scanned textbooks often exceed that threshold. Each material exists in exactly one of the two locations.

### 3.3 Courses and the Content Tree

Teaching content is organized into a four-level structure:

- **Course** is the largest unit, tied to a subject, a grade level, and a responsible tutor. Course names are unique system-wide.
- **Chapter** divides a course into major sections, each with an order number. Within a course, both the order number and the chapter title must be unique — this constraint prevents accidentally creating two chapters with the same number or the same title.
- **Lesson** is the smallest learning unit that students interact with directly, belonging to a chapter, also with a unique order number within that chapter.
- **LearningResource** is specific learning content attached to a lesson, in one of three forms: a video link, a document file, or text content entered directly by the tutor. This is the course's own private knowledge source in the RAG system — retrievable only by course members.

Two easily confused concepts need to be distinguished clearly:

| | Material | LearningResource |
|---|---|---|
| Owner | The center | The tutor responsible for the course |
| Classified by | Subject + grade | A specific lesson |
| Who can retrieve it | Every student | Course members only |
| Has draft status | No | Yes |

### 3.4 Enrollment

Enrollment is the junction table linking students and courses, implementing a many-to-many relationship: a student can take many courses, and a course can have many students. A unique constraint on the course–student pair ensures no duplicate enrollment record can be created.

Enrollment is not merely a row of data — it is an authorization condition. All course content, assignments, and the AI assistant's retrieval scope check for an active enrollment record before granting access.

## 4. Assessment and Grading

### 4.1 Assignments and Questions

An Assignment has a one-to-one relationship with a chapter: each chapter has at most one assignment, and that assignment belongs to exactly one chapter. An assignment has a due date and an optional time limit in minutes.

A Question belongs to an assignment, has a unique order number within that assignment, and is one of three types:

- **Multiple choice:** the student selects one of the given options.
- **Fill-in-the-blank:** the student types an answer, which the system matches against the correct answer.
- **Essay:** the student writes a response, graded by hand by the tutor.

Every question comes with a detailed explanation and, for the first two types, a list of Answer options with a flag marking the correct one.

Each question's score is set by the tutor through the question's `point` field, rather than divided evenly. The value must be a multiple of 0.05 and fall between 0.05 and 10. The key constraint applies at publication time: an assignment can only be published once every question has a score and those scores add up to exactly 10. This guarantees the 10-point scale from the moment the assignment is written, with no conversion needed at grading time.

Earlier versions divided 10 points evenly across the questions; the migration `assignments/0011_split_points_for_existing_questions` is the step that moved existing data onto per-question scores.

### 4.2 Attempts

A Submission represents one attempt by a student at an assignment, not the final result. A student has at most 3 attempts per assignment.

An attempt's lifecycle has two timestamps:

- **Start:** the system creates a record with a start time and an empty score. If the assignment has a time limit, the attempt's deadline is calculated as the start time plus the allowed number of minutes.
- **Submit:** the system records the submission time and computes the score.

An attempt not yet submitted is called "open." A student can have at most one open attempt at a time: clicking "start" again returns that same open attempt rather than creating a new one. If an open attempt has expired, the system closes it before allowing a new attempt to start. A closed attempt is still graded normally against whatever work was saved — it does not default to zero; only unanswered questions score zero.

Closing expired attempts does not wait for the student to return. A periodic job runs every 5 minutes, scans every open attempt, and closes and grades any that passed either the assignment's due date or the attempt's own deadline.

Two kinds of deadlines operate independently and are both checked: the assignment's due date (an absolute deadline shared by the whole class) and the attempt's own deadline (calculated individually per student from their start time). When submitting, the system allows up to 30 seconds of lateness relative to the attempt deadline, to compensate for network latency.

A StudentAnswer stores the student's work for each question: the selected option for multiple-choice questions, or text content for fill-in-the-blank and essay questions, along with a score and the tutor's comments.

### 4.3 Grading Mechanism

Grading happens in two stages:

**Automatic grading upon submission.** Multiple-choice questions are graded by comparing the selected option against the correct-answer flag. Fill-in-the-blank questions are graded by string matching after trimming whitespace and converting to lowercase. Essay questions are left ungraded.

**Manual grading afterward.** The tutor grades each essay question, entering a score and comments. Each question's score cannot exceed that question's weight.

The attempt's total score follows an important rule: as long as even one question remains ungraded, the total score stays blank rather than equaling the sum of the graded questions so far. This ensures that an attempt with an ungraded essay portion doesn't display a misleading number to the student.

The total score appears only once every question has been scored, and equals the plain sum of the question scores — there is no conversion or rounding step. No conversion is needed because the question scores were already forced to add up to 10 when the assignment was published.

## 5. Learning Tracking and Interaction

### 5.1 Progress and Learning Streaks

LessonProgress records that a student has completed a lesson, along with the completion timestamp. From this data the system derives two metrics:

- **Course progress percentage** — the ratio of completed lessons to the total number of published lessons in the course. Lessons still in draft status don't count toward the denominator, preventing a student's progress from dropping every time the tutor drafts a new, unpublished lesson.
- **Learning streak** — the number of most recent consecutive days on which the student completed at least one lesson. The streak is counted backward from today or yesterday; if the most recent completion date is older than yesterday, the streak is 0. This is a common motivational mechanism in educational apps, based on the principle of habit maintenance.

### 5.2 Comments

A Comment is attached to a lesson and allows nested replies via a reference to a parent comment — forming a discussion tree. A tutor can mark a comment as the correct answer, and the system records who marked it and when. This mechanism lets students who arrive later immediately spot the confirmed answer within a long discussion thread.

### 5.3 Saving Work in Progress

A student taking an assignment does not lose their work to a dropped connection or a closed browser tab, thanks to two layers of draft saving. On the browser side, answers are written to local storage keyed by the attempt after every change. On the server side, the interface saves a draft every 30 seconds and every time the student moves to another question.

Answer records are written with upsert semantics on the (attempt, question) pair, so saving repeatedly never creates duplicates. This is also the data used for grading when an attempt is closed for being overdue.

## 6. Three Concepts Running Through Every Entity

The system uses the abstract model technique to group repeated fields and behavior. An abstract class does not create its own database table; its fields are copied into each subclass's table. There are three such classes, corresponding to three business concepts.

### 6.1 Soft Delete

Instead of permanently deleting a record from the database, the system simply lowers the `is_active` flag. Every data query filters on this flag, so the record disappears from the interface but remains in the table.

**Why it's needed.** Learning data has dense referential constraints: hard-deleting a course would cascade to students' submissions, scores, and progress. Soft delete preserves the integrity of learning history and allows recovery from accidental deletion. This flag comes paired with two timestamps — created and updated — automatically recorded by the system.

### 6.2 Draft and Published

Content authored by tutors — chapters, lessons, learning resources, assignments — has a "published at" timestamp field. An empty field means it's a draft, visible only to the tutor; a filled-in value means it's published and visible to students.

**Why it's needed.** Tutors need to build up a chapter gradually across multiple sessions without students seeing unfinished content. Using a timestamp instead of a true/false flag makes it possible to know exactly when something was published, which is useful for statistics and ordering.

Note: center materials do not have this status, since they are managed by admins and have no concept of a draft.

### 6.3 RAG Indexing Status

Every piece of content eligible for the AI system — center materials and learning resources — carries four additional fields tracking its ingestion progress into the vector database: status, number of chunks ingested, failure reason, and completion timestamp.

Status moves through four values: pending (the default when just created), processing, indexed, failed.

**Why it's needed.** Ingesting a textbook hundreds of pages long can take tens of minutes and may fail partway through due to network errors or API rate limits. Storing status directly in the data table makes it possible to know which materials are ready for the AI assistant, which need to be re-ingested, and why a previous ingestion attempt failed.

## 7. Two-Tier Authorization Model

This is the single most important concept in analyzing and designing this system, since it appears at nearly every access point.

**Tier one — role-based permission.** Checks which group the user belongs to. For example: only tutors can create chapters; only students can submit assignments.

**Tier two — course-relationship permission.** Checks whether the user is related to the specific course containing the object being acted on. Three levels of relationship:

- **Responsible tutor:** the user is the tutor assigned to that course.
- **Enrolled student:** an active enrollment record exists.
- **Course member:** either of the two above.

The core idea is that every object in the system can be traced back to a course. From a comment, the system traces up to the lesson, then the chapter, then the course. From a submission, it traces up to the assignment, then the chapter, then the course. Thanks to this traceback chain, the authorization rule only needs to be written once and applies to every type of object.

A common variant is **open for reading, narrow for writing**: course members can read content, but only the responsible tutor can edit it. Submissions have an additional rule of their own: a student can only view their own submissions, while the responsible tutor can view every student's submissions in the course.

A special case is the creation operation, where the object doesn't yet exist and so can't be traced back — tier two has nothing to check. The system pushes that check down into the serializer: every create serializer has a dedicated validation method for the foreign key pointing at the parent object, and that method compares the course's responsible tutor against the requesting user. Creating a chapter checks against the course, creating a lesson checks against the chapter, creating a question checks against the assignment.

This has a consequence worth noting: input arriving in the request body is checked in the serializer, while input arriving in the URL path is checked in the permission layer. When adding a new create endpoint, the serializer validation must be written by hand, because the permission layer will not catch it.

## 8. Technical Foundation

### 8.1 Decoupled Client–Server Architecture

The system follows a pure API architecture: the server only returns JSON data over HTTP and does not render any UI. The frontend is a separate web application running in the browser, which calls the API to fetch data.

REST (Representational State Transfer) is an API design style based on mapping each type of resource to a path, and each operation to an HTTP verb: GET to read, POST to create, PATCH to partially update, DELETE to remove. The entire API sits under the version prefix `/api/v1/`, allowing a new version to be released later without breaking existing clients.

API documentation is auto-generated in the OpenAPI standard directly from the source code, accessible via a Swagger interface. This approach guarantees the documentation always matches the code, unlike hand-written documentation which tends to drift out of sync over time.

### 8.2 Object-Relational Mapping

An ORM (Object-Relational Mapping) is a middle layer that allows working with a relational database through the classes and objects of a programming language, instead of writing raw SQL. Each model class corresponds to a table, each attribute to a column, and each object to a row.

Two optimization techniques are used throughout the system:

- **Eager loading of one-to-many/forward relations:** when fetching a list of courses along with tutor information, the ORM combines this into a single query with a join, instead of a separate query per course.
- **Eager loading of many-to-many/reverse relations:** when fetching a list of questions along with their answer options, the ORM issues one additional shared query for all of them instead of querying once per question.

Without these two techniques, a list page with 20 items could generate dozens of database queries — a phenomenon commonly known as the N+1 query problem.

In addition, heavy aggregate calculations such as progress percentage are written as query expressions so the database computes them directly, rather than loading all the data and computing it in Python.

### 8.3 JWT Authentication Stored in Cookies

A JWT (JSON Web Token) is a digitally signed string containing user identity information. The server doesn't need to store login sessions; it only needs to verify the string's signature to know who sent it.

The system uses two types of tokens:

- **Access token**, valid for 15 minutes, sent with every request for authentication.
- **Refresh token**, valid for 7 days, used only to request a new access token when the old one expires.

A notable design choice: tokens are not returned to JavaScript code but are instead placed in a cookie with the `HttpOnly` flag. This flag prevents JavaScript from reading the cookie; the browser only sends it automatically with API calls. The purpose is to defend against XSS (Cross-Site Scripting) attacks — even if an attacker injects malicious code into the page, that code still can't steal the token.

In exchange, because the browser sends the cookie automatically, the system becomes vulnerable to CSRF (Cross-Site Request Forgery) — a malicious website tricking the browser into sending a request on the user's behalf. The system defends against this with three layers: the cookie's `SameSite=Lax` attribute so the browser won't send it on requests originating from another site, an allow-list of origins permitted to call the API, and Django's CSRF token mechanism.

Refresh tokens are rotated: each use generates a new token and blacklists the old one. As a result, if a token is stolen and the attacker uses it first, the real user gets logged out — a signal that something went wrong.

### 8.4 Rate Limiting

AI endpoints are limited to 30 requests per hour per user. This is not purely a technical measure but a business constraint: every question sent to the AI assistant incurs an API cost to the model provider, so excessive calls — whether accidental or intentional — must be blocked.

### 8.5 Upload File Validation

The system validates uploaded files across three layers, not relying on the filename alone:

1. The file extension must be within an allow-list.
2. The content type declared by the browser must match the extension.
3. The binary signature — the first few bytes of the file — must match the declared format. A genuine PDF always starts with `%PDF-`; a docx file starts with the signature of the ZIP compression format.

The third layer is the most important, since the first two are both supplied by the client and can be forged. Size limits: images 2MB, lesson documents 10MB, center materials 100MB.

## 9. Foundational AI Concepts in the System

This section covers only the terms needed to read the design section; detailed principles are presented in the methodology chapter.

- **Large Language Model (LLM)** is a deep learning model trained on a large volume of text, capable of generating text conditioned on given context. Its inherent limitation is that it only knows what's in its training data and tends to hallucinate — generating information that sounds plausible but is factually wrong.
- **Retrieval-Augmented Generation (RAG)** is a technique that addresses this limitation by retrieving relevant documents from a private repository and feeding them into the prompt, forcing the model to answer based on those documents.
- **Embedding** is a representation of a piece of text as a vector of real numbers, such that two semantically similar passages have vectors that are close together geometrically. This is what enables semantic search rather than keyword search.
- **Chunk** is the small unit a document is cut into before generating vectors. Chunking is necessary because embedding models have input length limits, and because a vector only represents content well when the chunk is focused in content.
- **Vector database** is storage specialized for vectors, supporting k-nearest-neighbor search against a query vector.
- **Prompt** is the input text sent to the model, consisting of behavioral instructions, document context, and the user's question. Prompt quality largely determines answer quality.
- **Grounding** is the degree to which an answer is based on the provided documents rather than the model's memory. The system clearly marks each answer as grounded or not, and only shows citations for the grounded type.

## 10. Glossary

| Term | System name | Business meaning |
|---|---|---|
| Subject | Subject | A subject in the K-12 curriculum |
| Grade | Grade | Grade 10, 11, 12… |
| Material | Material | Shared learning content owned by the center |
| Course | Course | A class taught by a responsible tutor |
| Enrollment | Enrollment | Record of a student joining a course |
| Chapter | Chapter | A major section within a course |
| Lesson | Lesson | The smallest learning unit |
| LearningResource | LearningResource | Learning content attached to a lesson |
| LessonProgress | LessonProgress | Record of a student completing a lesson |
| Comment | Comment | Discussion under a lesson, with nested replies |
| Assignment | Assignment | A set of questions attached to a chapter |
| Question | Question | A single question within an assignment |
| Answer | Answer | A multiple-choice option, with a correct/incorrect flag |
| Submission | Submission | One attempt at an assignment by a student |
| StudentAnswer | StudentAnswer | A student's work on a single question |
| Soft delete | is_active | Hides a record instead of deleting it from the database |
| Draft / Published | published_at | Empty means draft; a value means published |
| RAG indexing status | rag_status | Pending, processing, indexed, failed |

## 11. Implementation Status

This section separates what works end to end from what is finished only in the processing layer. It describes the state at the time of writing, not the design.

### 11.1 Working End to End

The AI assistant is the most complete part: a student asks a question in the interface, the system retrieves documents within that student's scope, and produces an answer with citations, clearly marked as grounded in the materials or not.

Also in this group: authoring and publishing course content, taking and grading assignments, progress statistics, lesson comments, and the full pipeline that ingests center materials into the vector store.

### 11.2 Processing Layer Done, Interface Missing

AI exercise generation is complete in the processing layer — it takes a subject, lesson, question type and count, and returns questions with options and explanations in the system's own data shape. What is missing is the screen from which a student would invoke it.

The table for storing AI conversation history exists in the database but is never written to. Each question currently returns its answer to the user and ends there, unrecorded. As a result, there is no data on what students actually ask, and no basis for evaluating answer quality over time.

### 11.3 Vector Store Data

The vector store currently holds 643 text chunks, all of them from center materials — mainly the Grade 12 English textbook and its companion revision documents. All 15 materials finished indexing.

The lesson-resource branch is the opposite: all 81 resources created by tutors sit in the pending state, none indexed. The course-scoped retrieval path is implemented and tested, but no real data has passed through it. In practice, the assistant's answers currently draw on center materials.

### 11.4 Known Limitations

**Lesson-scoped retrieval is not authorization-checked.** When a student sends a question, the system checks whether they are enrolled in the course, but not whether the accompanying lesson belongs to that course. Because the three scope branches are joined by a logical OR, an arbitrary lesson identifier still adds its own retrieval branch. It is not exploitable today because the vector store holds no lesson-resource chunks, but the hole is there and must be closed before resources are ingested.

**Citation page numbers are off by one.** Page numbers stored in the vector store already count from 1, but the interface adds 1 again when rendering the source label. The cited content is correct; only the displayed page number is wrong.

**Enrollment and account creation happen only in the admin area.** There is no student self-registration and no self-enrollment flow. This is the agreed scope of the project rather than an oversight, but it should be stated plainly so it is not read as missing work.

---

**Note on accuracy:** all figures and rules stated above are read directly from the current source code — 3 attempts, a 10-point scale, the 0.05 step for per-question scores, 30 seconds of allowed lateness, 15 minutes and 7 days for the two token types, 30 AI requests per hour, and the file-size thresholds. The figures in Section 11 are read directly from the running database and vector store. The business-context description in Section 1, specifically, is an interpretation derived from the data structures; if the project has its own requirements specification, it should be cross-checked against that document.
