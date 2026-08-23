from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Question, StudentAnswer, Submission

TOTAL_SCORE = Decimal("10")
SUBMIT_GRACE = timedelta(seconds=30)
MAX_ATTEMPTS = 3


def count_submitted_attempts(student, assignment):
    return Submission.objects.filter(
        assignment=assignment, student=student, submitted_at__isnull=False
    ).count()


def has_submissions(assignment):
    return Submission.objects.filter(
        assignment=assignment, submitted_at__isnull=False
    ).exists()


def delete_question(question):
    if has_submissions(question.assignment):
        raise ValidationError("Bài tập đã có bài nộp nên không xóa được câu hỏi.")
    question.delete()


def get_open_attempt(student, assignment):
    return Submission.objects.filter(
        assignment=assignment, student=student, submitted_at__isnull=True
    ).first()


def point_per_question(total_questions):
    if not total_questions:
        return Decimal(0)
    return (TOTAL_SCORE / total_questions).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def scale_to_total(points, total_questions):
    if any(point is None for point in points):
        return None

    max_total = point_per_question(total_questions) * total_questions
    if not max_total:
        return Decimal(0)
    return (sum(points, Decimal(0)) / max_total * TOTAL_SCORE).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )


def ensure_within_due_date(assignment):
    if assignment.due_date and timezone.now() > assignment.due_date:
        raise ValidationError("Bài tập đã hết hạn nộp.")


def is_expired(attempt):
    deadline = attempt.deadline
    return bool(deadline and timezone.now() > deadline + SUBMIT_GRACE)


def get_attempt_to_submit(student, assignment):
    attempt = get_open_attempt(student, assignment)
    if attempt is None:
        raise ValidationError("Bạn chưa bắt đầu lượt làm bài nào cho bài tập này.")

    if is_expired(attempt):
        raise ValidationError("Đã hết thời gian làm bài của lượt làm này.")
    return attempt


@transaction.atomic
def start_attempt(student, assignment):
    ensure_within_due_date(assignment)

    if not assignment.questions.exists():
        raise ValidationError("Bài tập chưa có câu hỏi nào.")

    attempt = get_open_attempt(student, assignment)
    if attempt is not None:
        if not is_expired(attempt):
            return attempt

        attempt.submitted_at = attempt.deadline
        attempt.score = Decimal("0.0")
        attempt.save(update_fields=["score", "submitted_at"])

    if count_submitted_attempts(student, assignment) >= MAX_ATTEMPTS:
        raise ValidationError(
            f"Bạn đã dùng hết {MAX_ATTEMPTS} lượt làm bài của bài tập này."
        )

    return Submission.objects.create(
        assignment=assignment,
        student=student,
        started_at=timezone.now(),
        score=None,
    )


def ensure_answers_match_questions(questions, answers):
    question_ids = [item["question_id"] for item in answers]

    unknown_ids = [qid for qid in question_ids if qid not in questions]
    if unknown_ids:
        raise ValidationError(
            {"answers": f"Các câu hỏi {unknown_ids} không thuộc bài tập này."}
        )

    if len(question_ids) != len(set(question_ids)):
        raise ValidationError({"answers": "Mỗi câu hỏi chỉ được trả lời một lần."})

    for item in answers:
        answer_id = item.get("answer_id")
        question = questions[item["question_id"]]
        if (
            answer_id is None
            or question.question_type != Question.QuestionType.MULTIPLE_CHOICE
        ):
            continue
        if not any(a.id == answer_id for a in question.answers.all()):
            raise ValidationError(
                {"answers": f"Phương án {answer_id} không thuộc câu hỏi {question.id}."}
            )


@transaction.atomic
def submit_assignment(student, assignment, answers):
    ensure_within_due_date(assignment)

    questions = {}
    for q in assignment.questions.prefetch_related("answers"):
        questions[q.id] = q

    if not questions:
        raise ValidationError("Bài tập chưa có câu hỏi nào.")

    attempt = get_attempt_to_submit(student, assignment)
    ensure_answers_match_questions(questions, answers)

    unit_point = point_per_question(len(questions))

    stu_answers = []

    for item in answers:
        question = questions[item["question_id"]]
        stu_answer = StudentAnswer(question=question, submission=attempt)
        stu_answers.append(stu_answer)

        if question.question_type == Question.QuestionType.MULTIPLE_CHOICE:
            selected = next(
                (a for a in question.answers.all() if a.id == item.get("answer_id")),
                None,
            )
            stu_answer.answer = selected
            stu_answer.point = (
                unit_point if (selected and selected.is_correct) else Decimal(0)
            )

        elif question.question_type == Question.QuestionType.FILL_IN_BLANK:
            text = (item.get("answer_text") or "").strip()
            stu_answer.answer_text = text
            correct = next((a for a in question.answers.all() if a.is_correct), None)
            stu_answer.point = (
                unit_point
                if correct and text.lower() == correct.content.strip().lower()
                else Decimal(0)
            )

        else:
            stu_answer.answer_text = (item.get("answer_text") or "").strip()
            stu_answer.point = None

    StudentAnswer.objects.bulk_create(stu_answers)

    attempt.submitted_at = timezone.now()
    attempt.score = scale_to_total(
        [answer.point for answer in stu_answers], len(questions)
    )
    attempt.save(update_fields=["score", "submitted_at"])
    return attempt


def ensure_gradable(submission, answers):
    if submission.submitted_at is None:
        raise ValidationError("Bài làm này chưa được nộp nên chưa thể chấm.")

    owned_ids = set(submission.stu_answers.values_list("id", flat=True))
    unknown_ids = [item["id"] for item in answers if item["id"] not in owned_ids]
    if unknown_ids:
        raise ValidationError(
            {"answers": f"Các câu trả lời {unknown_ids} không thuộc bài nộp này."}
        )

    max_point = point_per_question(submission.assignment.questions.count())
    if any(item["point"] > max_point for item in answers):
        raise ValidationError({"answers": f"Điểm mỗi câu tối đa là {max_point}."})


@transaction.atomic
def grade_submission(submission, answers):
    ensure_gradable(submission, answers)

    stu_answers = {}
    for answer in submission.stu_answers.all():
        stu_answers[answer.id] = answer

    graded = []
    for item in answers:
        answer = stu_answers[item["id"]]
        answer.point = item["point"]
        if "tutor_comment" in item:
            answer.tutor_comment = item["tutor_comment"]
        graded.append(answer)

    StudentAnswer.objects.bulk_update(graded, ["point", "tutor_comment"])

    submission.score = scale_to_total(
        [answer.point for answer in stu_answers.values()],
        submission.assignment.questions.count(),
    )

    submission.save(update_fields=["score"])
    return submission
