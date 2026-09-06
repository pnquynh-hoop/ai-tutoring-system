from decimal import Decimal

from django.db import migrations

TOTAL_SCORE = Decimal("10")
POINT_STEPS = [Decimal("0.25"), Decimal("0.1"), Decimal("0.05")]


def distribute_points(question_count):
    for step in POINT_STEPS:
        units = int(TOTAL_SCORE / step)
        if units < question_count:
            continue

        base, extra = divmod(units, question_count)
        bigger = [step * (base + 1)] * extra
        smaller = [step * base] * (question_count - extra)
        return bigger + smaller

    return [POINT_STEPS[-1]] * question_count


def split_points(apps, schema_editor):
    Assignment = apps.get_model("assignments", "Assignment")
    Question = apps.get_model("assignments", "Question")

    for assignment in Assignment.objects.all():
        questions = list(assignment.questions.order_by("order", "id"))
        if not questions:
            continue

        for question, point in zip(questions, distribute_points(len(questions))):
            question.point = point

        Question.objects.bulk_update(questions, ["point"])


class Migration(migrations.Migration):

    dependencies = [
        ("assignments", "0010_question_point_alter_submission_score"),
    ]

    operations = [
        migrations.RunPython(split_points, migrations.RunPython.noop),
    ]
