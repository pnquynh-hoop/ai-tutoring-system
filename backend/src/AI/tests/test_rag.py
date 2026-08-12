from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

from core.testing import auth_client

from AI.ingest import (
    SOURCE_TEXTBOOK,
    document_id,
    local_pdf_paths,
    select_new,
    textbook_metadata,
)
from AI.rag_service import (
    OUTSIDE_MATERIAL_PREFIX,
    TEXTBOOK_SOURCE_TYPE,
    _build_chroma_filter,
    format_sources,
    message_text,
    split_grounding,
)

"""
    Test cho phần logic thuần của RAG: phạm vi truy vấn, metadata và id của chunk.
    Việc gọi Gemini/Chroma thật không nằm trong unit test.
"""


class TestChromaFilter:
    def test_course_and_lesson_scope_plus_textbook(self):
        assert _build_chroma_filter(course_id=1, lesson_id=2) == {
            "$or": [
                {"$and": [{"course_id": 1}, {"lesson_id": 2}]},
                {"source_type": TEXTBOOK_SOURCE_TYPE},
            ]
        }

    def test_course_scope_plus_textbook(self):
        assert _build_chroma_filter(course_id=5) == {
            "$or": [{"course_id": 5}, {"source_type": TEXTBOOK_SOURCE_TYPE}]
        }

    def test_textbook_only_when_no_course(self):
        assert _build_chroma_filter() == {"source_type": TEXTBOOK_SOURCE_TYPE}

    def test_no_filter_when_textbook_excluded_and_no_course(self):
        assert _build_chroma_filter(include_textbook=False) is None

    def test_course_only_when_textbook_excluded(self):
        assert _build_chroma_filter(course_id=7, include_textbook=False) == {
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
        # Giữ nguyên nhãn trong câu trả lời để học sinh biết đây là kiến thức ngoài sách.
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


class TestTextbookIngestHelpers:
    def test_metadata_marks_source_type_for_filtering(self):
        metadata = textbook_metadata(Path("/data/SGK_12_clean.pdf"), page=3)

        assert metadata == {
            "source_type": SOURCE_TEXTBOOK,
            "source": "SGK_12_clean.pdf",
            "title": "SGK 12 clean",
            "page": 3,
        }

    def test_document_id_is_stable_for_same_chunk(self):
        first = document_id(SOURCE_TEXTBOOK, "SGK_12_clean.pdf", 3, 0)
        second = document_id(SOURCE_TEXTBOOK, "SGK_12_clean.pdf", 3, 0)

        # Id cố định nên chạy lại lệnh ingest sẽ ghi đè thay vì nhân bản dữ liệu.
        assert first == second == "textbook:SGK_12_clean.pdf:3:0"

    def test_document_id_differs_per_chunk(self):
        assert document_id(SOURCE_TEXTBOOK, "a.pdf", 1, 0) != document_id(
            SOURCE_TEXTBOOK, "a.pdf", 1, 1
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

        # Nhờ vậy chạy lại lệnh ingest sau khi bị 429 sẽ nạp tiếp phần còn thiếu
        # thay vì nhúng lại từ đầu và đốt quota.
        assert select_new(docs, ["a:0"], existing_ids=["a:0"]) == ([], [])


class TestLocalPdfPaths:
    def test_returns_empty_when_directory_missing(self, tmp_path):
        assert local_pdf_paths(tmp_path / "khong-ton-tai") == []

    def test_only_matches_pattern(self, tmp_path):
        (tmp_path / "SGK_12_clean.pdf").write_bytes(b"%PDF-")
        (tmp_path / "SGK_raw.pdf").write_bytes(b"%PDF-")
        (tmp_path / "ghi_chu.txt").write_text("x", encoding="utf-8")

        names = [p.name for p in local_pdf_paths(tmp_path, "*clean*.pdf")]

        assert names == ["SGK_12_clean.pdf"]

    def test_sorted_for_stable_ingest_order(self, tmp_path):
        for name in ["b_clean.pdf", "a_clean.pdf"]:
            (tmp_path / name).write_bytes(b"%PDF-")

        assert [p.name for p in local_pdf_paths(tmp_path, "*clean*.pdf")] == [
            "a_clean.pdf",
            "b_clean.pdf",
        ]


@pytest.mark.django_db
class TestRagApiPermissions:
    def test_student_not_enrolled_cannot_ask(self, course, make_student):
        response = auth_client(make_student()).post(
            "/api/v1/rag/ask/",
            {"question": "Bài này nói gì?", "course_id": course.pk},
            format="json",
        )

        assert response.status_code == 403

    def test_student_not_enrolled_cannot_generate_exercises(
        self, course, make_student
    ):
        response = auth_client(make_student()).post(
            "/api/v1/rag/generate-exercises/",
            {"course_id": course.pk},
            format="json",
        )

        assert response.status_code == 403

    def test_tutor_cannot_ask(self, course, tutor):
        # Tính năng AI hiện chỉ mở cho học sinh, kể cả gia sư phụ trách khóa.
        response = auth_client(tutor).post(
            "/api/v1/rag/ask/",
            {"question": "Bài này nói gì?", "course_id": course.pk},
            format="json",
        )

        assert response.status_code == 403

    def test_tutor_cannot_generate_exercises(self, course, tutor):
        response = auth_client(tutor).post(
            "/api/v1/rag/generate-exercises/",
            {"course_id": course.pk},
            format="json",
        )

        assert response.status_code == 403

    def test_missing_question_returns_400(self, course, enrolled_student):
        response = auth_client(enrolled_student).post(
            "/api/v1/rag/ask/", {"course_id": course.pk}, format="json"
        )

        assert response.status_code == 400
        assert "question" in response.data
