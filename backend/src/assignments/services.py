from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from .models import Question, StudentAnswer, Submission

TOTAL_SCORE = Decimal("10")
POINT_STEP = Decimal("0.05")
MIN_QUESTION_POINT = POINT_STEP
SUBMIT_GRACE = timedelta(seconds=30)
MAX_ATTEMPTS = 3


def count_used_attempts(student, assignment):
    return Submission.objects.filter(assignment=assignment, student=student).count()


def has_submissions(assignment):
    return Submission.objects.filter(
        assignment=assignment, submitted_at__isnull=False
    ).exists()


def get_open_attempt(student, assignment):
    return Submission.objects.filter(
        assignment=assignment, student=student, submitted_at__isnull=True
    ).first()


def is_expired(attempt):
    deadline = attempt.deadline
    return bool(deadline and timezone.now() > deadline + SUBMIT_GRACE)


def is_valid_point_step(point):
    return point % POINT_STEP == 0


def total_question_points(assignment):
    return assignment.questions.aggregate(total=Sum("point"))["total"] or Decimal(0)


def count_questions_without_point(assignment):
    return assignment.questions.filter(point__isnull=True).count()


def sum_points(points):
    if any(point is None for point in points):
        return None
    return sum(points, Decimal(0))


@transaction.atomic
def start_attempt(student, assignment, open_attempt):
    if open_attempt is not None:
        if not is_expired(open_attempt):
            return open_attempt

        finalize_attempt(open_attempt, open_attempt.deadline)

    return Submission.objects.create(
        assignment=assignment,
        student=student,
        started_at=timezone.now(),
        score=None,
    )


@transaction.atomic
def save_answer_draft(student, assignment, answers):
    questions = {}
    for question in assignment.questions.all():
        questions[question.id] = question

    attempt = get_open_attempt(student, assignment)

    rows = []
    for item in answers:
        question = questions[item["question_id"]]

        if question.question_type == Question.QuestionType.MULTIPLE_CHOICE:
            selected = next(
                (a for a in question.answers.all() if a.id == item.get("answer_id")),
                None,
            )
            answer_text = None
        else:
            selected = None
            answer_text = (item.get("answer_text") or "").strip()

        rows.append(
            StudentAnswer(
                submission=attempt,
                question=question,
                answer=selected,
                answer_text=answer_text,
            )
        )

    StudentAnswer.objects.bulk_create(
        rows,
        update_conflicts=True,
        update_fields=["answer", "answer_text"],
    )

    return attempt


def auto_point(stu_answer):
    question = stu_answer.question

    if stu_answer.answer is None and not (stu_answer.answer_text or "").strip():
        return Decimal(0)

    if question.question_type == Question.QuestionType.MULTIPLE_CHOICE:
        selected = stu_answer.answer
        return question.point if (selected and selected.is_correct) else Decimal(0)

    if question.question_type == Question.QuestionType.FILL_IN_BLANK:
        text = (stu_answer.answer_text or "").strip()
        correct = next((a for a in question.answers.all() if a.is_correct), None)
        if correct and text.lower() == correct.content.strip().lower():
            return question.point
        return Decimal(0)

    return None


def create_missing_answers(attempt):
    answered_ids = set(attempt.stu_answers.values_list("question_id", flat=True))
    missing = [
        StudentAnswer(submission=attempt, question=question)
        for question in attempt.assignment.questions.all()
        if question.id not in answered_ids
    ]

    if missing:
        StudentAnswer.objects.bulk_create(missing)


@transaction.atomic
def finalize_attempt(attempt, submitted_at):
    if attempt.submitted_at is not None:
        return attempt

    create_missing_answers(attempt)

    stu_answers = list(
        attempt.stu_answers.select_related("question", "answer").prefetch_related(
            "question__answers"
        )
    )

    for stu_answer in stu_answers:
        stu_answer.point = auto_point(stu_answer)

    StudentAnswer.objects.bulk_update(stu_answers, ["point"])

    attempt.submitted_at = submitted_at
    attempt.score = sum_points([stu_answer.point for stu_answer in stu_answers])
    attempt.save(update_fields=["score", "submitted_at"])
    return attempt


def overdue_cutoff(attempt, now):
    cutoffs = [attempt.deadline, attempt.assignment.due_date]
    passed = [cutoff for cutoff in cutoffs if cutoff and now > cutoff + SUBMIT_GRACE]
    return min(passed) if passed else None


@transaction.atomic
def close_overdue_attempt(attempt_id, now):
    attempt = (
        Submission.objects.select_for_update()
        .select_related("assignment")
        .filter(pk=attempt_id, submitted_at__isnull=True)
        .first()
    )

    if attempt is None:
        return False

    cutoff = overdue_cutoff(attempt, now)
    if cutoff is None:
        return False

    finalize_attempt(attempt, cutoff)
    return True


def close_overdue_attempts():
    now = timezone.now()
    open_ids = list(
        Submission.objects.filter(submitted_at__isnull=True).values_list(
            "id", flat=True
        )
    )

    return sum(close_overdue_attempt(attempt_id, now) for attempt_id in open_ids)


@transaction.atomic
def submit_assignment(student, assignment, answers):
    attempt = save_answer_draft(student, assignment, answers)
    return finalize_attempt(attempt, timezone.now())


@transaction.atomic
def grade_submission(submission, answers):
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

    submission.score = sum_points([answer.point for answer in stu_answers.values()])

    submission.save(update_fields=["score"])
    return submission
