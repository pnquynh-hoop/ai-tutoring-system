from types import SimpleNamespace
from unittest import mock

import pymupdf
import pytest

from AI import extract
from AI.extract import (
    clean_markdown,
    file_fingerprint,
    load_cache,
    save_cache,
    classify_pages,
    extract_scanned_pages,
    load_pdf,
    ocr_page,
    page_has_text,
)


class TestHtmlEntities:
    def test_nbsp_becomes_a_plain_space(self):
        cleaned = clean_markdown("| cloud nine/ &nbsp;&nbsp;over the moon")

        assert "&nbsp;" not in cleaned
        assert "\xa0" not in cleaned
        assert "over the moon" in cleaned

    def test_other_entities_are_decoded_too(self):
        assert clean_markdown("Tom &amp; Jerry &lt;3") == "Tom & Jerry <3"



def make_pdf(path, texts):
    doc = pymupdf.open()
    for text in texts:
        page = doc.new_page()
        if text is None:
            pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20))
            pixmap.clear_with(255)
            page.insert_image(pymupdf.Rect(0, 0, 100, 100), pixmap=pixmap)
        else:
            page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()
    return path


class TestPageClassification:
    def test_page_with_text_is_native(self, tmp_path):
        path = make_pdf(tmp_path / "a.pdf", ["Hello"])

        with pymupdf.open(str(path)) as doc:
            assert page_has_text(doc[0]) is True

    def test_image_only_page_needs_ocr(self, tmp_path):
        path = make_pdf(tmp_path / "b.pdf", [None])

        with pymupdf.open(str(path)) as doc:
            assert page_has_text(doc[0]) is False

    def test_splits_mixed_document_per_page(self, tmp_path):
        path = make_pdf(tmp_path / "c.pdf", ["A", None, "B", None])

        assert classify_pages(path) == ([0, 2], [1, 3])


class TestOcrCache:
    def test_fingerprint_follows_content_not_name(self, tmp_path):
        first = make_pdf(tmp_path / "ten-cu.pdf", ["X"])
        second = tmp_path / "ten-moi.pdf"
        second.write_bytes(first.read_bytes())

        assert file_fingerprint(first) == file_fingerprint(second)

    def test_fingerprint_differs_for_different_content(self, tmp_path):
        first = make_pdf(tmp_path / "a.pdf", ["X"])
        second = make_pdf(tmp_path / "b.pdf", ["Y"])

        assert file_fingerprint(first) != file_fingerprint(second)

    def test_cache_round_trip(self, tmp_path, settings):
        settings.RAG_CACHE_DIR = tmp_path / "cache"
        path = make_pdf(tmp_path / "a.pdf", ["X"])

        save_cache(path, {0: "# Trang 1", 3: "| a | b |"})

        assert load_cache(path) == {0: "# Trang 1", 3: "| a | b |"}

    def test_missing_cache_is_empty(self, tmp_path, settings):
        settings.RAG_CACHE_DIR = tmp_path / "cache"

        assert load_cache(make_pdf(tmp_path / "a.pdf", ["X"])) == {}


class TestOcrGate:
    def test_does_not_call_api_when_ocr_disabled(self, tmp_path, settings):
        settings.RAG_CACHE_DIR = tmp_path / "cache"
        settings.RAG_OCR_ENABLED = False
        path = make_pdf(tmp_path / "scan.pdf", [None, None])

        assert extract_scanned_pages(path, [0, 1]) == {}

    def test_serves_cached_pages_without_enabling_ocr(self, tmp_path, settings):
        settings.RAG_CACHE_DIR = tmp_path / "cache"
        settings.RAG_OCR_ENABLED = False
        path = make_pdf(tmp_path / "scan.pdf", [None])
        save_cache(path, {0: "# Đã OCR từ trước"})

        assert extract_scanned_pages(path, [0]) == {0: "# Đã OCR từ trước"}

    def test_scanned_file_yields_nothing_when_ocr_disabled(self, tmp_path, settings):
        settings.RAG_CACHE_DIR = tmp_path / "cache"
        settings.RAG_OCR_ENABLED = False

        assert load_pdf(make_pdf(tmp_path / "scan.pdf", [None, None])) == []


class TestLoadPdf:
    def test_pages_numbered_from_one(self, tmp_path, settings):
        settings.RAG_CACHE_DIR = tmp_path / "cache"
        path = make_pdf(tmp_path / "a.pdf", ["Trang mot", "Trang hai"])

        docs = load_pdf(path)

        assert [d.metadata["page"] for d in docs] == [1, 2]

    def test_drops_blank_pages(self, tmp_path, settings):
        settings.RAG_CACHE_DIR = tmp_path / "cache"
        settings.RAG_OCR_ENABLED = False
        path = make_pdf(tmp_path / "a.pdf", ["Co chu", "   "])

        assert len(load_pdf(path)) == 1

    def test_keeps_page_order_when_mixing_sources(self, tmp_path, settings):
        settings.RAG_CACHE_DIR = tmp_path / "cache"
        settings.RAG_OCR_ENABLED = False
        path = make_pdf(tmp_path / "a.pdf", ["Mot", None, "Ba"])
        save_cache(path, {1: "Hai (tu OCR)"})

        docs = load_pdf(path)

        assert [d.metadata["page"] for d in docs] == [1, 2, 3]
        assert "Hai (tu OCR)" in docs[1].page_content


class FakeLlm:
    def __init__(self, failures, error):
        self.calls = 0
        self.failures = failures
        self.error = error

    def invoke(self, _messages):
        self.calls += 1
        if self.calls <= self.failures:
            raise Exception(self.error)
        return SimpleNamespace(content="# Đọc xong")


def run_ocr(failures, error):
    llm = FakeLlm(failures, error)
    with mock.patch.object(extract.time, "sleep"):
        with mock.patch.object(extract, "get_ocr_llm", return_value=llm):
            return llm, ocr_page(b"anh-gia")


class TestOcrRetry:
    def test_retries_after_quota_error(self):
        llm, result = run_ocr(failures=2, error="429 RESOURCE_EXHAUSTED")

        assert result == "# Đọc xong"
        assert llm.calls == 3

    def test_gives_up_after_max_retry(self):
        with pytest.raises(Exception):
            run_ocr(failures=99, error="429 RESOURCE_EXHAUSTED")

    def test_does_not_retry_other_errors(self):
        llm = FakeLlm(failures=99, error="400 INVALID_ARGUMENT")

        with mock.patch.object(extract.time, "sleep"):
            with mock.patch.object(extract, "get_ocr_llm", return_value=llm):
                with pytest.raises(Exception, match="INVALID_ARGUMENT"):
                    ocr_page(b"anh-gia")

        assert llm.calls == 1

    def test_reads_text_from_content_blocks(self):
        llm = FakeLlm(failures=0, error="")
        llm.invoke = lambda _: SimpleNamespace(
            content=[{"type": "text", "text": "| a | b |"}]
        )

        with mock.patch.object(extract, "get_ocr_llm", return_value=llm):
            assert ocr_page(b"anh-gia") == "| a | b |"


@pytest.mark.parametrize("pages", [[], [None]])
def test_native_extraction_handles_empty_page_list(tmp_path, settings, pages):
    settings.RAG_CACHE_DIR = tmp_path / "cache"
    settings.RAG_OCR_ENABLED = False
    path = make_pdf(tmp_path / "a.pdf", pages or ["x"])

    assert isinstance(load_pdf(path), list)
