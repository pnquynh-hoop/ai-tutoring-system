from django.contrib import admin, messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import redirect, render
from django.urls import path, reverse

from AI.models import Report

REPORTS_PER_PAGE = 20


def report_status_summary():
    counts = {
        row["status"]: row["total"]
        for row in Report.objects.values("status").annotate(total=Count("id"))
    }
    return [
        {"value": value, "label": label, "total": counts.get(value, 0)}
        for value, label in Report.ReportStatus.choices
    ]


class TutoringAdminSite(admin.AdminSite):
    site_header = "Trung tâm gia sư AI"
    site_title = "Quản trị hệ thống"
    index_title = "Bảng điều khiển"
    index_template = "admin/tutoring_index.html"

    def get_urls(self):
        custom_urls = [
            path(
                "reports/",
                self.admin_view(self.report_center_view),
                name="report_center",
            ),
        ]
        return custom_urls + super().get_urls()

    def tool_links(self, request):
        return [
            {
                "name": "Báo cáo của học sinh",
                "object_name": "ReportCenter",
                "admin_url": reverse("admin:report_center"),
                "add_url": None,
                "view_only": True,
                "description": "Xem và xử lý các câu hỏi bị học sinh báo lỗi.",
                "perms": {"add": False, "change": False, "delete": False, "view": True},
            },
        ]

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        if app_label:
            return app_list

        tools_app = {
            "name": "Công cụ quản trị",
            "app_label": "tools",
            "app_url": reverse("admin:report_center"),
            "has_module_perms": True,
            "models": self.tool_links(request),
        }
        return [tools_app] + app_list

    def each_context(self, request):
        context = super().each_context(request)
        context["tool_links"] = self.tool_links(request)
        return context

    def report_center_view(self, request):
        if request.method == "POST":
            self._apply_report_status(request)
            target = reverse("admin:report_center")
            current_status = request.POST.get("current_status", "")
            return redirect(f"{target}?status={current_status}")

        status_filter = request.GET.get("status", "")
        reports = Report.objects.select_related(
            "reporter", "question", "question__assignment"
        ).order_by("-reported_at")
        if status_filter in Report.ReportStatus.values:
            reports = reports.filter(status=status_filter)

        page = Paginator(reports, REPORTS_PER_PAGE).get_page(request.GET.get("page"))

        context = {
            **self.each_context(request),
            "title": "Báo cáo của học sinh",
            "page": page,
            "status_filter": status_filter,
            "status_choices": Report.ReportStatus.choices,
            "status_summary": report_status_summary(),
            "total_reports": Report.objects.count(),
        }
        return render(request, "admin/report_center.html", context)

    def _apply_report_status(self, request):
        report_id = request.POST.get("report_id")
        new_status = request.POST.get("status")

        if new_status not in Report.ReportStatus.values:
            messages.error(request, "Trạng thái không hợp lệ.")
            return

        updated = Report.objects.filter(pk=report_id).update(status=new_status)
        if updated:
            label = Report.ReportStatus(new_status).label
            messages.success(
                request, f"Đã chuyển báo cáo #{report_id} sang trạng thái “{label}”."
            )
        else:
            messages.error(request, f"Không tìm thấy báo cáo #{report_id}.")


admin_site = TutoringAdminSite(name="admin")
