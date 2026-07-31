from django.conf import settings
from django.core.management.base import BaseCommand

from AI.ingest import (
    ingest_learning_resources,
    ingest_local_documents,
    ingest_materials,
    local_pdf_paths,
)


class Command(BaseCommand):
    help = (
        "Nạp dữ liệu cho RAG: sách PDF trong backend/data, tài liệu chung "
        "(academics.Material) và tài nguyên bài học (courses.LearningResource)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=["all", "textbook", "materials", "resources"],
            default="all",
            help="Chọn nguồn cần nạp (mặc định: all).",
        )
        parser.add_argument(
            "--pattern",
            default=None,
            help=f"Glob lọc file trong backend/data (mặc định: {settings.RAG_DATA_PATTERN}).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Giới hạn số chunk nạp mỗi file, dùng khi muốn chạy thử nhanh.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Chỉ liệt kê file sẽ nạp, không gọi API nhúng vector.",
        )

    def handle(self, *args, **options):
        source = options["source"]
        pattern = options["pattern"]

        if options["dry_run"]:
            paths = local_pdf_paths(pattern=pattern)
            self.stdout.write(f"Thư mục dữ liệu: {settings.RAG_DATA_DIR}")
            self.stdout.write(f"Pattern: {pattern or settings.RAG_DATA_PATTERN}")
            for path in paths:
                self.stdout.write(f"  - {path.name}")
            if not paths:
                self.stdout.write(self.style.WARNING("Không có file nào khớp."))
            return

        if source in ("all", "textbook"):
            count = ingest_local_documents(pattern=pattern, limit=options["limit"])
            self.stdout.write(self.style.SUCCESS(f"Sách giáo khoa: {count} chunk"))

        if source in ("all", "materials"):
            count = ingest_materials()
            self.stdout.write(self.style.SUCCESS(f"Tài liệu chung: {count} chunk"))

        if source in ("all", "resources"):
            count = ingest_learning_resources()
            self.stdout.write(self.style.SUCCESS(f"Tài nguyên bài học: {count} chunk"))
