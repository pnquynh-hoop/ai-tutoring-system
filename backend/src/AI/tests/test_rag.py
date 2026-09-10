from types import SimpleNamespace

from langchain_core.documents import Document
from model_bakery import baker


from AI.ingest import (
    SOURCE_MATERIAL,
    document_id,
    material_metadata,
    select_new,
)
from accounts.models import StudentProfile
from AI.rag_service import (
    HYBRID_PROMPT,
    NO_ENROLLED_SUBJECT,
    NO_LESSON_CONTEXT,
    NO_STUDENT_PROFILE,
    OUTSIDE_MATERIAL_PREFIX,
    STRICT_PROMPT,
    TEACHING_STYLES,
    TOP_K,
    build_scope_filter,
    course_subjects_and_grades,
    describe_lesson,
    describe_subjects,
    material_scope,
    retrieve_documents,
    describe_student,
    document_key,
    format_sources,
    message_text,
    is_grounded,
    teaching_style_for,
)



class TestScopeFilter:
    def test_lesson_and_course_scopes_join_the_center_scope(self):
        assert build_scope_filter(course_ids=[1], lesson_id=2) == {
            "$or": [
                {"lesson_id": 2},
                {"course_id": {"$in": [1]}},
                {"source_type": SOURCE_MATERIAL},
            ]
        }

    def test_course_scope_covers_every_enrolled_course(self):
        assert build_scope_filter(course_ids=[5, 7, 9]) == {
            "$or": [
                {"course_id": {"$in": [5, 7, 9]}},
                {"source_type": SOURCE_MATERIAL},
            ]
        }

    def test_center_scope_stands_alone_when_there_is_nothing_to_join(self):
        assert build_scope_filter() == {"source_type": SOURCE_MATERIAL}

    def test_center_scope_uses_the_source_type_that_ingest_writes(self):
        assert build_scope_filter()["source_type"] == material_metadata(
            SimpleNamespace(id=1, subject_id=1, grade_id=1, name="SGK"), 0
        )["source_type"]

    def test_center_scope_narrows_to_subject_and_grade(self):
        scope = build_scope_filter(course_ids=[5], subject_ids=[2], grade_ids=[3])

        assert scope["$or"][-1] == {
            "$and": [
                {"source_type": SOURCE_MATERIAL},
                {"subject_id": {"$in": [2]}},
                {"grade_id": {"$in": [3]}},
            ]
        }

    def test_center_scope_keeps_source_type_alone_when_nothing_to_narrow(self):
        assert material_scope([], []) == {"source_type": SOURCE_MATERIAL}


class FakeStore:
    def __init__(self, hits):
        self.hits = hits
        self.searches = []

    def similarity_search_with_score(self, query, k, filter):
        self.searches.append({"query": query, "k": k, "filter": filter})
        return self.hits[:k]


class TestDistanceThreshold:
    def test_chunk_xa_hon_nguong_bi_bo(self, db, monkeypatch, settings):
        settings.RAG_MAX_DISTANCE = 0.62
        near = Document(page_content="gan", metadata={"material_id": 1, "page": 1})
        far = Document(page_content="xa", metadata={"material_id": 1, "page": 2})
        monkeypatch.setattr(
            "AI.rag_service.get_vector_store",
            lambda: FakeStore([(near, 0.50), (far, 0.71)]),
        )

        documents = retrieve_documents("câu hỏi lạc đề")

        assert [document.page_content for document in documents] == ["gan"]

    def test_khong_chunk_nao_du_gan_thi_tra_ve_rong(self, db, monkeypatch, settings):
        settings.RAG_MAX_DISTANCE = 0.62
        far = Document(page_content="xa", metadata={"material_id": 1, "page": 1})
        monkeypatch.setattr(
            "AI.rag_service.get_vector_store", lambda: FakeStore([(far, 0.72)])
        )

        assert retrieve_documents("kể một chuyện cười") == []


class TestSingleSearch:
    def test_only_one_search_asking_for_top_k(self, db, monkeypatch, settings):
        settings.RAG_MAX_DISTANCE = 0.62
        near = Document(page_content="gan", metadata={"material_id": 1, "page": 1})
        store = FakeStore([(near, 0.10)])
        monkeypatch.setattr("AI.rag_service.get_vector_store", lambda: store)

        retrieve_documents("đảo ngữ no sooner", course_ids=[], lesson_id=None)

        assert len(store.searches) == 1
        assert store.searches[0]["k"] == TOP_K

    def test_results_come_back_sorted_by_distance(self, db, monkeypatch, settings):
        settings.RAG_MAX_DISTANCE = 0.62
        far = Document(page_content="xa hon", metadata={"material_id": 1, "page": 1})
        near = Document(page_content="gan hon", metadata={"material_id": 1, "page": 2})
        monkeypatch.setattr(
            "AI.rag_service.get_vector_store",
            lambda: FakeStore([(far, 0.55), (near, 0.20)]),
        )

        documents = retrieve_documents("câu hỏi bất kỳ")

        assert [document.page_content for document in documents] == ["gan hon", "xa hon"]


class TestDescribeSubjects:
    def test_liet_ke_mon_cua_cac_khoa_dang_hoc(self, db):
        english = baker.make("academics.Subject", name="Tiếng Anh")
        maths = baker.make("academics.Subject", name="Toán")
        first = baker.make("courses.Course", subject=english)
        second = baker.make("courses.Course", subject=maths)

        assert describe_subjects([first.id, second.id]) == "Tiếng Anh, Toán"

    def test_chua_ghi_danh_khoa_nao(self, db):
        assert describe_subjects([]) == NO_ENROLLED_SUBJECT

    def test_prompt_hybrid_co_cho_dien_danh_sach_mon(self):
        assert "subjects" in HYBRID_PROMPT.input_variables


class TestCourseSubjectsAndGrades:
    def test_collects_subject_and_grade_of_every_course(self, db):
        grade_ten = baker.make("academics.Grade", number=10)
        grade_twelve = baker.make("academics.Grade", number=12)
        english = baker.make("academics.Subject", name="Tiếng Anh")
        maths = baker.make("academics.Subject", name="Toán")

        first = baker.make("courses.Course", subject=english, grade=grade_twelve)
        second = baker.make("courses.Course", subject=maths, grade=grade_ten)

        subject_ids, grade_ids = course_subjects_and_grades([first.id, second.id])

        assert subject_ids == sorted([english.id, maths.id])
        assert grade_ids == sorted([grade_ten.id, grade_twelve.id])

    def test_no_course_means_nothing_to_narrow(self, db):
        assert course_subjects_and_grades([]) == ([], [])


class TestLessonContext:
    def test_no_lesson_gives_the_fallback_line(self):
        assert describe_lesson(None) == NO_LESSON_CONTEXT

    def test_both_prompts_expect_every_context_variable(self):
        expected = {"lesson_context", "student_profile", "teaching_style"}

        assert expected <= set(STRICT_PROMPT.input_variables)
        assert expected <= set(HYBRID_PROMPT.input_variables)


class TestTeachingStyle:
    def test_no_profile_falls_back_to_average_level(self):
        average = TEACHING_STYLES[StudentProfile.AcademicLevel.AVERAGE]

        assert describe_student(None) == NO_STUDENT_PROFILE
        assert teaching_style_for(None) == average

    def test_weak_student_is_told_to_define_terms_first(self):
        weak = TEACHING_STYLES[StudentProfile.AcademicLevel.POOR]

        assert "Define every technical term" in weak

    def test_every_level_gets_its_own_instruction(self):
        instructions = list(TEACHING_STYLES.values())

        assert len(TEACHING_STYLES) == len(StudentProfile.AcademicLevel.choices)
        assert len(set(instructions)) == len(instructions)


class TestDocumentKey:
    def test_same_content_and_page_is_one_document(self):
        first = Document(page_content="abc", metadata={"resource_id": 3, "page": 1})
        second = Document(page_content="abc", metadata={"resource_id": 3, "page": 1})
        assert document_key(first) == document_key(second)

    def test_different_page_is_another_document(self):
        first = Document(page_content="abc", metadata={"resource_id": 3, "page": 1})
        second = Document(page_content="abc", metadata={"resource_id": 3, "page": 2})
        assert document_key(first) != document_key(second)



class TestMessageText:
    def test_plain_string_content(self):
        assert message_text(SimpleNamespace(content="Xin chào")) == "Xin chào"

    def test_content_blocks_of_new_gemini_models(self):
        message = SimpleNamespace(
            content=[
                {"type": "text", "text": "Đoạn 1"},
                {"type": "text", "text": "Đoạn 2"},
            ]
        )

        assert message_text(message) == "Đoạn 1\nĐoạn 2"

    def test_ignores_non_text_blocks(self):
        message = SimpleNamespace(
            content=[
                {"type": "thinking", "text": "suy nghĩ"},
                {"type": "text", "text": "Kết quả"},
            ]
        )

        assert message_text(message) == "Kết quả"

    def test_mixed_string_and_block(self):
        assert (
            message_text(SimpleNamespace(content=["a", {"type": "text", "text": "b"}]))
            == "a\nb"
        )


class TestIsGrounded:
    def test_answer_from_materials_is_grounded(self):
        assert is_grounded("Theo Unit 3, mệnh đề quan hệ dùng để...") is True

    def test_answer_outside_materials_is_flagged(self):
        raw = (
            f"{OUTSIDE_MATERIAL_PREFIX}\nPostpone, delay, defer đều nghĩa là trì hoãn."
        )

        assert is_grounded(raw) is False

    def test_leading_whitespace_does_not_hide_the_flag(self):
        raw = f"  {OUTSIDE_MATERIAL_PREFIX} Postpone nghĩa là trì hoãn."

        assert is_grounded(raw.strip()) is False

    def test_prefix_in_the_middle_is_not_treated_as_flag(self):
        raw = f"Theo tài liệu... {OUTSIDE_MATERIAL_PREFIX} ..."

        assert is_grounded(raw) is True


class TestFormatSources:
    def test_takes_title_and_page_from_metadata(self):
        docs = [
            Document(page_content="x", metadata={"title": "SGK 12", "page": 10}),
            Document(page_content="y", metadata={"title": "Bài 1", "page": None}),
        ]

        assert format_sources(docs) == [
            {"title": "SGK 12", "page": 10},
            {"title": "Bài 1", "page": None},
        ]

    def test_removes_duplicated_source(self):
        docs = [
            Document(page_content="x", metadata={"title": "SGK 12", "page": 10}),
            Document(page_content="y", metadata={"title": "SGK 12", "page": 10}),
        ]

        assert len(format_sources(docs)) == 1

    def test_falls_back_to_source_then_default_label(self):
        docs = [
            Document(page_content="x", metadata={"source": "SGK_12_clean.pdf"}),
            Document(page_content="y", metadata={}),
        ]

        assert [source["title"] for source in format_sources(docs)] == [
            "SGK_12_clean.pdf",
            "Tài liệu bài học",
        ]


class TestMaterialIngestHelpers:
    def test_metadata_marks_source_type_for_filtering(self):
        material = SimpleNamespace(
            id=12, subject_id=3, grade_id=5, name="Wordlist Tiếng Anh 12"
        )

        assert material_metadata(material, page_number=3) == {
            "source_type": SOURCE_MATERIAL,
            "material_id": 12,
            "subject_id": 3,
            "grade_id": 5,
            "title": "Wordlist Tiếng Anh 12",
            "page": 3,
        }

    def test_document_id_is_stable_for_same_chunk(self):
        first = document_id(SOURCE_MATERIAL, "12", 3, 0)
        second = document_id(SOURCE_MATERIAL, "12", 3, 0)

        assert first == second == "material:12:3:0"

    def test_document_id_differs_per_chunk(self):
        assert document_id(SOURCE_MATERIAL, "12", 1, 0) != document_id(
            SOURCE_MATERIAL, "12", 1, 1
        )


class TestSelectNew:
    def test_skips_chunks_already_in_store(self):
        docs = [Document(page_content=str(i)) for i in range(3)]
        ids = ["a:0", "a:1", "a:2"]

        new_docs, new_ids = select_new(docs, ids, existing_ids=["a:0", "a:2"])

        assert new_ids == ["a:1"]
        assert [d.page_content for d in new_docs] == ["1"]

    def test_returns_everything_when_store_is_empty(self):
        docs = [Document(page_content="x")]

        assert select_new(docs, ["a:0"], existing_ids=[]) == (docs, ["a:0"])

    def test_returns_empty_when_all_ingested(self):
        docs = [Document(page_content="x")]

        assert select_new(docs, ["a:0"], existing_ids=["a:0"]) == ([], [])
