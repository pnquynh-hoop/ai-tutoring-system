import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from model_bakery import baker
from academics.admin import MaterialForm
from core.validators import LOCAL_STORAGE_THRESHOLD


def make_pdf_upload(size, name="sgk.pdf"):
    pdf_header = b"%PDF-1.4\n"
    padding = b"0" * (size - len(pdf_header))
    return SimpleUploadedFile(
        name,
        pdf_header + padding,
        content_type="application/pdf",
    )


@pytest.fixture
def material_data(db):
    return {
        "name": "Sách giáo khoa Toán 10",
        "subject": baker.make("academics.Subject", name="Toán").pk,
        "grade": baker.make("academics.Grade", number=10).pk,
        "is_active": True,
    }


def build_form(material_data, upload):
    form = MaterialForm(data=material_data, files={"upload": upload})
    assert form.is_valid(), form.errors
    return form


@pytest.mark.django_db
class TestMaterialStorageRouting:
    def test_small_file_goes_to_cloudinary(self, material_data):
        form = build_form(material_data, make_pdf_upload(1024))

        material = form.save(commit=False)

        assert material.file_url
        assert not material.local_file

    def test_large_file_goes_to_local_disk(self, material_data, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        form = build_form(material_data, make_pdf_upload(LOCAL_STORAGE_THRESHOLD + 1))

        material = form.save()

        assert not material.file_url
        assert material.local_file.name.startswith("materials/Lop_10/")
        assert (tmp_path / material.local_file.name).exists()

    def test_local_file_goes_into_subfolder_not_root(
        self, material_data, settings, tmp_path
    ):
        settings.MEDIA_ROOT = tmp_path
        build_form(material_data, make_pdf_upload(LOCAL_STORAGE_THRESHOLD + 1)).save()

        assert list(tmp_path.glob("*.pdf")) == []

    def test_rejects_file_over_hard_limit(self, material_data):
        form = MaterialForm(
            data=material_data, files={"upload": make_pdf_upload(101 * 1024 * 1024)}
        )

        assert not form.is_valid()
        assert "100MB" in str(form.errors["upload"])

    def test_upload_is_required_when_creating(self, material_data):
        form = MaterialForm(data=material_data, files={})

        assert not form.is_valid()
        assert "upload" in form.errors


@pytest.mark.django_db
class TestMaterialRagStatus:
    def test_new_material_starts_pending(self, material_data, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path

        material = build_form(
            material_data, make_pdf_upload(LOCAL_STORAGE_THRESHOLD + 1)
        ).save()

        assert material.rag_status == material.RAGStatus.PENDING
        assert material.rag_progress == 0

    def test_reupload_resets_status_to_pending(self, material_data, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        material = build_form(
            material_data, make_pdf_upload(LOCAL_STORAGE_THRESHOLD + 1)
        ).save()
        material.mark_rag_indexed(chunks=42)

        form = MaterialForm(
            data=material_data,
            files={
                "upload": make_pdf_upload(LOCAL_STORAGE_THRESHOLD + 1, "sgk_v2.pdf")
            },
            instance=material,
        )
        assert form.is_valid(), form.errors
        updated = form.save()

        assert updated.rag_status == updated.RAGStatus.PENDING
        assert updated.rag_progress == 0
        assert updated.rag_indexed_at is None

    def test_mark_failed_keeps_reason(self, material_data, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        material = build_form(
            material_data, make_pdf_upload(LOCAL_STORAGE_THRESHOLD + 1)
        ).save()

        material.mark_rag_failed("PdfReadError: file hỏng")
        material.refresh_from_db()

        assert material.rag_status == material.RAGStatus.FAILED
        assert "PdfReadError" in material.rag_error
