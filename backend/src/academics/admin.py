from django import forms
from django.contrib import admin, messages
from AI.tasks import ingest_material_task
from core.admin import admin_site
from core.validators import (
    LOCAL_STORAGE_THRESHOLD,
    MAX_MATERIAL_SIZE,
    validate_document_upload,
)
from .models import Grade, Material, Subject


class MaterialForm(forms.ModelForm):
    upload = forms.FileField(
        label="Tệp tài liệu",
        required=False,
        help_text=(
            f"Tối đa 100MB. Tệp trên {LOCAL_STORAGE_THRESHOLD // (1024 * 1024)}MB "
            "được lưu cục bộ trên máy chủ."
        ),
    )

    class Meta:
        model = Material
        fields = ["name", "subject", "grade", "is_active"]

    def clean_upload(self):
        return validate_document_upload(
            self.cleaned_data.get("upload"), MAX_MATERIAL_SIZE
        )

    def clean(self):
        cleaned = super().clean()
        upload = cleaned.get("upload")
        has_file = self.instance.pk and (
            self.instance.file_url or self.instance.local_file
        )

        if not upload and not has_file:
            self.add_error("upload", "Vui lòng chọn tệp tài liệu.")

        if upload:
            self.instance.file_url = None
            self.instance.local_file = None
            if upload.size > LOCAL_STORAGE_THRESHOLD:
                self.instance.local_file = upload
            else:
                self.instance.file_url = upload

            self.instance.rag_status = Material.RAGStatus.PENDING
            self.instance.rag_progress = 0
            self.instance.rag_error = None
            self.instance.rag_indexed_at = None

        return cleaned


def queue_materials(request, materials):
    queued, skipped = 0, 0

    for material in materials:
        if material.rag_status == Material.RAGStatus.PROCESSING:
            skipped += 1
            continue

        material.rag_status = Material.RAGStatus.PENDING
        material.rag_error = None
        material.save(update_fields=["rag_status", "rag_error", "updated_at"])
        ingest_material_task.delay(material.id)
        queued += 1

    if queued:
        messages.success(request, f"Đã đưa {queued} tài liệu vào hàng đợi nạp.")
    if skipped:
        messages.warning(request, f"Bỏ qua {skipped} tài liệu đang nạp dở.")


class MaterialAdmin(admin.ModelAdmin):
    form = MaterialForm
    list_display = ["name", "subject", "grade", "storage", "rag_status", "rag_progress"]
    list_filter = ["rag_status", "grade", "subject"]
    search_fields = ["name"]
    actions = ["ingest_into_rag"]
    readonly_fields = [
        "storage",
        "rag_status",
        "rag_progress",
        "rag_error",
        "rag_indexed_at",
    ]

    @admin.display(description="Nơi lưu tệp")
    def storage(self, obj):
        if obj.local_file:
            return f"Cục bộ: {obj.local_file.name}"
        if obj.file_url:
            return "Cloudinary"
        return "Chưa có tệp"

    @admin.action(description="Nạp tài liệu đã chọn vào kho RAG")
    def ingest_into_rag(self, request, queryset):
        queue_materials(request, queryset)


admin_site.register([Grade, Subject])
admin_site.register(Material, MaterialAdmin)
