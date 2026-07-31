from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from assignments.models import Question, StudentAnswer, Submission

TOTAL_SCORE = Decimal("10")
SUBMIT_GRACE = timedelta(seconds=30)
MAX_ATTEMPTS = 3


def _assert_not_overdue(assignment):
    if assignment.due_date and timezone.now() > assignment.due_date:
        raise ValidationError("Bài tập đã hết hạn nộp.")


def count_submitted_attempts(student, assignment) -> int:
    return Submission.objects.filter(
        assignment=assignment, student=student, submitted_at__isnull=False
    ).count()


def _assert_attempts_left(student, assignment):
    if count_submitted_attempts(student, assignment) >= MAX_ATTEMPTS:
        raise ValidationError(
            f"Bạn đã dùng hết {MAX_ATTEMPTS} lượt làm bài của bài tập này."
        )


def get_open_attempt(student, assignment):
    """Lượt làm bài đang dở (chưa nộp) gần nhất của học sinh, nếu có."""
    return (
        Submission.objects.filter(
            assignment=assignment, student=student, submitted_at__isnull=True
        )
        .order_by("-started_at", "-id")
        .first()
    )


def start_attempt(student, assignment):
    """Bắt đầu (hoặc lấy lại) một lượt làm bài, mốc thời gian được ghi tại server."""
    _assert_not_overdue(assignment)

    if not assignment.questions.exists():
        raise ValidationError("Bài tập chưa có câu hỏi nào.")

    attempt = get_open_attempt(student, assignment)
    if attempt is None:
        _assert_attempts_left(student, assignment)
        attempt = Submission.objects.create(
            assignment=assignment,
            student=student,
            started_at=timezone.now(),
            score=None,
        )
    return attempt


def _assert_within_time_limit(attempt):
    deadline = attempt.deadline
    if deadline and timezone.now() > deadline + SUBMIT_GRACE:
        raise ValidationError("Đã hết thời gian làm bài của lượt làm này.")


def _grade_answer(question, item, point_per_question):
    """Chấm một câu trả lời, trả về (StudentAnswer chưa lưu, điểm thô, cần chấm tay)."""
    stu_answer = StudentAnswer(question=question)

    if question.question_type == Question.QuestionType.MULTIPLE_CHOICE:
        answer_id = item.get("answer_id")
        selected = next(
            (a for a in question.answers.all() if a.id == answer_id),
            None,
        )
        if answer_id is not None and selected is None:
            raise ValidationError(
                {"answers": f"Phương án {answer_id} không thuộc câu hỏi {question.id}."}
            )
        stu_answer.answer = selected
        earned = (
            point_per_question if (selected and selected.is_correct) else Decimal(0)
        )

    elif question.question_type == Question.QuestionType.FILL_IN_BLANK:
        text = (item.get("answer_text") or "").strip()
        stu_answer.answer_text = text
        correct = next((a for a in question.answers.all() if a.is_correct), None)
        is_correct = bool(correct and text.lower() == correct.content.strip().lower())
        earned = point_per_question if is_correct else Decimal(0)

    else:  # ESSAY: chờ gia sư chấm tay
        stu_answer.answer_text = item.get("answer_text") or ""
        stu_answer.point = None
        return stu_answer, Decimal(0), True

    stu_answer.point = earned.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return stu_answer, earned, False


def point_per_question(assignment) -> Decimal:
    """Điểm tối đa của mỗi câu trong bài tập (chưa làm tròn)."""
    total = assignment.questions.count()
    if not total:
        return Decimal(0)
    return TOTAL_SCORE / total


@transaction.atomic
def grade_submission(submission, answers_data):
    """Gia sư chấm tay các câu tự luận, sau đó tính lại điểm tổng của bài nộp."""
    if submission.submitted_at is None:
        raise ValidationError("Bài làm này chưa được nộp nên chưa thể chấm.")

    student_answers = {
        answer.id: answer
        for answer in submission.stu_answers.select_related("question")
    }

    unknown_ids = [
        item["id"] for item in answers_data if item["id"] not in student_answers
    ]
    if unknown_ids:
        raise ValidationError(
            {"answers": f"Các câu trả lời {unknown_ids} không thuộc bài nộp này."}
        )

    max_point = point_per_question(submission.assignment).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    graded = []
    for item in answers_data:
        answer = student_answers[item["id"]]
        if item["point"] > max_point:
            raise ValidationError({"answers": f"Điểm mỗi câu tối đa là {max_point}."})
        answer.point = item["point"]
        if "tutor_comment" in item:
            answer.tutor_comment = item["tutor_comment"]
        graded.append(answer)

    StudentAnswer.objects.bulk_update(graded, ["point", "tutor_comment"])

    # Còn câu chưa có điểm thì bài vẫn ở trạng thái chờ chấm.
    all_points = [answer.point for answer in student_answers.values()]
    if any(point is None for point in all_points):
        submission.score = None
    else:
        submission.score = sum(all_points, Decimal(0)).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    submission.save(update_fields=["score"])
    return submission


@transaction.atomic
def submit_assignment(student, answers_data, assignment):
    """Chấm và nộp bài. Trả về Submission đã cập nhật điểm."""
    _assert_not_overdue(assignment)

    questions = {
        q.id: q for q in assignment.questions.prefetch_related("answers").all()
    }

    total_questions = len(questions)
    if total_questions == 0:
        raise ValidationError("Bài tập chưa có câu hỏi nào.")

    unknown_ids = [
        item.get("question_id")
        for item in answers_data
        if item.get("question_id") not in questions
    ]
    if unknown_ids:
        raise ValidationError(
            {"answers": f"Các câu hỏi {unknown_ids} không thuộc bài tập này."}
        )

    answered_ids = [item.get("question_id") for item in answers_data]
    if len(answered_ids) != len(set(answered_ids)):
        raise ValidationError({"answers": "Mỗi câu hỏi chỉ được trả lời một lần."})

    # Lượt làm bài phải được start trước để tính giờ; nếu client nộp thẳng thì tạo mới.
    attempt = get_open_attempt(student, assignment)
    if attempt is None:
        _assert_attempts_left(student, assignment)
        attempt = Submission.objects.create(
            assignment=assignment,
            student=student,
            started_at=timezone.now(),
            score=None,
        )
    else:
        _assert_within_time_limit(attempt)

    # Giữ nguyên phần thập phân khi cộng dồn, chỉ làm tròn ở điểm tổng.
    point_per_question = TOTAL_SCORE / total_questions

    student_answers = []
    has_essay = False
    earned_score = Decimal(0)

    for item in answers_data:
        question = questions[item["question_id"]]
        stu_answer, earned, needs_manual = _grade_answer(
            question, item, point_per_question
        )
        stu_answer.submission = attempt
        earned_score += earned
        has_essay = has_essay or needs_manual
        student_answers.append(stu_answer)

    StudentAnswer.objects.bulk_create(student_answers)

    attempt.submitted_at = timezone.now()
    # Còn câu tự luận thì để điểm trống chờ gia sư chấm.
    attempt.score = (
        None
        if has_essay
        else earned_score.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    )
    attempt.save(update_fields=["score", "submitted_at"])

    return attempt
