from django import forms
from django.contrib import admin

from core.validators import MAX_DOCUMENT_SIZE, validate_material_upload

from .models import Grade, Material, Subject


class MaterialForm(forms.ModelForm):
    upload = forms.FileField(
        label="Tệp tài liệu",
        required=False,
        help_text=(
            f"Tối đa 100MB. Tệp trên {MAX_DOCUMENT_SIZE // (1024 * 1024)}MB "
            "được lưu cục bộ trên máy chủ thay vì Cloudinary."
        ),
    )

    class Meta:
        model = Material
        fields = ["name", "subject", "grade", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._replaced_local_file = None

    def clean_upload(self):
        return validate_material_upload(self.cleaned_data.get("upload"))

    def clean(self):
        cleaned = super().clean()
        has_file = self.instance.pk and (
            self.instance.file_url or self.instance.local_file
        )
        if not cleaned.get("upload") and not has_file:
            self.add_error("upload", "Vui lòng chọn tệp tài liệu.")
        return cleaned

    def _post_clean(self):
        """Gắn tệp vào instance trước khi Model.clean() kiểm tra nguồn tệp."""
        upload = self.cleaned_data.get("upload")
        if upload:
            self._attach(upload)
        super()._post_clean()

    def _attach(self, upload):
        if self.instance.local_file:
            self._replaced_local_file = self.instance.local_file.name

        self.instance.file_url = None
        self.instance.local_file = None
        if upload.size > MAX_DOCUMENT_SIZE:
            self.instance.local_file = upload
        else:
            self.instance.file_url = upload

        self.instance.rag_status = Material.RAGStatus.PENDING
        self.instance.rag_progress = 0
        self.instance.rag_error = None
        self.instance.rag_indexed_at = None

    def save(self, commit=True):
        material = super().save(commit)

        replaced = self._replaced_local_file
        if commit and replaced and replaced != material.local_file.name:
            material.local_file.storage.delete(replaced)
            self._replaced_local_file = None

        return material


class MaterialAdmin(admin.ModelAdmin):
    form = MaterialForm
    list_display = ["name", "subject", "grade", "storage", "rag_status", "rag_progress"]
    list_filter = ["rag_status", "grade", "subject"]
    search_fields = ["name"]
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


admin.site.register([Grade, Subject])
admin.site.register(Material, MaterialAdmin)
