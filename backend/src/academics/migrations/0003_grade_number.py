import re

from django.db import migrations, models


def name_to_number(apps, schema_editor):
    """Bóc số ra khỏi chuỗi cũ: "Lớp 10" -> 10. Không tìm thấy số thì bỏ qua."""
    Grade = apps.get_model("academics", "Grade")
    for grade in Grade.objects.all():
        found = re.search(r"\d+", grade.name or "")
        if found:
            grade.number = int(found.group())
            grade.save(update_fields=["number"])


def number_to_name(apps, schema_editor):
    Grade = apps.get_model("academics", "Grade")
    for grade in Grade.objects.all():
        grade.name = f"Lớp {grade.number}"
        grade.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0002_alter_grade_is_active_alter_material_is_active_and_more"),
    ]

    operations = [
        # Thêm cột tạm cho phép null để còn chỗ đổ dữ liệu chuyển đổi vào.
        migrations.AddField(
            model_name="grade",
            name="number",
            field=models.PositiveSmallIntegerField(
                "Khối lớp", null=True, default=None
            ),
        ),
        migrations.RunPython(name_to_number, number_to_name),
        migrations.AlterField(
            model_name="grade",
            name="number",
            field=models.PositiveSmallIntegerField("Khối lớp", unique=True),
        ),
        migrations.RemoveField(model_name="grade", name="name"),
        migrations.AlterModelOptions(
            name="grade",
            options={"ordering": ["number"]},
        ),
        migrations.AlterModelOptions(
            name="subject",
            options={"ordering": ["name"]},
        ),
    ]
