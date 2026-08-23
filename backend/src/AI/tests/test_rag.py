from types import SimpleNamespace

from langchain_core.documents import Document


from AI.ingest import (
    SOURCE_MATERIAL,
    document_id,
    material_metadata,
    select_new,
)
from AI.rag_service import (
    OUTSIDE_MATERIAL_PREFIX,
    TEXTBOOK_SOURCE_TYPE,
    build_chroma_filter,
    format_sources,
    message_text,
    split_grounding,
)



class TestChromaFilter:
    def test_course_and_lesson_scope_plus_textbook(self):
        assert build_chroma_filter(course_id=1, lesson_id=2) == {
            "$or": [
                {"$and": [{"course_id": 1}, {"lesson_id": 2}]},
                {"source_type": TEXTBOOK_SOURCE_TYPE},
            ]
        }

    def test_course_scope_plus_textbook(self):
        assert build_chroma_filter(course_id=5) == {
            "$or": [{"course_id": 5}, {"source_type": TEXTBOOK_SOURCE_TYPE}]
        }

    def test_textbook_only_when_no_course(self):
        assert build_chroma_filter() == {"source_type": TEXTBOOK_SOURCE_TYPE}

    def test_no_filter_when_textbook_excluded_and_no_course(self):
        assert build_chroma_filter(include_textbook=False) is None

    def test_course_only_when_textbook_excluded(self):
        assert build_chroma_filter(course_id=7, include_textbook=False) == {
            "course_id": 7
        }


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


class TestSplitGrounding:
    def test_answer_from_materials_is_grounded(self):
        answer, grounded = split_grounding("Theo Unit 3, mệnh đề quan hệ dùng để...")

        assert grounded is True
        assert answer.startswith("Theo Unit 3")

    def test_answer_outside_materials_is_flagged(self):
        raw = (
            f"{OUTSIDE_MATERIAL_PREFIX}\nPostpone, delay, defer đều nghĩa là trì hoãn."
        )

        answer, grounded = split_grounding(raw)

        assert grounded is False
        assert answer.startswith(OUTSIDE_MATERIAL_PREFIX)

    def test_strips_surrounding_whitespace(self):
        answer, grounded = split_grounding("  Câu trả lời  ")

        assert (answer, grounded) == ("Câu trả lời", True)

    def test_prefix_in_the_middle_is_not_treated_as_flag(self):
        raw = f"Theo tài liệu... {OUTSIDE_MATERIAL_PREFIX} ..."

        assert split_grounding(raw)[1] is True


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
