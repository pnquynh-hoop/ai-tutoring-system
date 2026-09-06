from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import redirect, render
from django.urls import path, reverse
from AI.tasks import ingest_material_task
from core.admin import admin_site
from core.validators import (
    LOCAL_STORAGE_THRESHOLD,
    MAX_MATERIAL_SIZE,
    validate_document_upload,
)
from .models import Grade, Material, Subject

MATERIALS_PER_PAGE = 20
INGEST_URL_NAME = "academics_material_ingest"


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


def rag_status_summary():
    counted_rows = Material.objects.values("rag_status").annotate(total=Count("id"))

    total_by_status = {}
    for row in counted_rows:
        total_by_status[row["rag_status"]] = row["total"]

    summary = []
    for status_value, status_label in Material.RAGStatus.choices:
        summary.append(
            {
                "value": status_value,
                "label": status_label,
                "total": total_by_status.get(status_value, 0),
            }
        )
    return summary


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

    def get_urls(self):
        custom_urls = [
            path(
                "ingest/",
                self.admin_site.admin_view(self.ingest_center_view),
                name=INGEST_URL_NAME,
            ),
        ]
        return custom_urls + super().get_urls()

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

    def ingest_center_view(self, request):
        if not self.has_change_permission(request):
            raise PermissionDenied

        if request.method == "POST":
            return self.queue_from_page(request)

        status_filter = request.GET.get("status", "")
        subject_filter = request.GET.get("subject", "")
        grade_filter = request.GET.get("grade", "")

        materials = Material.objects.select_related("subject", "grade").order_by(
            "grade__number", "subject__name", "name"
        )
        if status_filter in Material.RAGStatus.values:
            materials = materials.filter(rag_status=status_filter)
        if subject_filter.isdigit():
            materials = materials.filter(subject_id=subject_filter)
        if grade_filter.isdigit():
            materials = materials.filter(grade_id=grade_filter)

        page = Paginator(materials, MATERIALS_PER_PAGE).get_page(
            request.GET.get("page")
        )

        filter_query = request.GET.copy()
        filter_query.pop("page", None)

        context = {
            **self.admin_site.each_context(request),
            "title": "Nạp tài liệu vào kho RAG",
            "page": page,
            "status_filter": status_filter,
            "subject_filter": subject_filter,
            "grade_filter": grade_filter,
            "status_summary": rag_status_summary(),
            "subjects": Subject.objects.order_by("name"),
            "grades": Grade.objects.order_by("number"),
            "total_materials": Material.objects.count(),
            "filter_query": filter_query.urlencode(),
            "current_query": request.GET.urlencode(),
        }
        return render(request, "admin/ingest_center.html", context)

    def queue_from_page(self, request):
        selected_ids = request.POST.getlist("material_id")

        if not selected_ids:
            messages.error(request, "Chưa chọn tài liệu nào để nạp.")
        else:
            materials = Material.objects.filter(pk__in=selected_ids)
            queue_materials(request, materials)

        ingest_url = reverse(f"admin:{INGEST_URL_NAME}")
        current_query = request.POST.get("current_query", "")

        return redirect(f"{ingest_url}?{current_query}")


admin_site.register([Grade, Subject])
admin_site.register(Material, MaterialAdmin)
admin_site.register_nav_link(
    url_name=INGEST_URL_NAME,
    label="Nạp tài liệu",
    description="Chọn tài liệu và đưa vào hàng đợi nạp kho RAG.",
)
