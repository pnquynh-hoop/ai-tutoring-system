"""Nghiệp vụ làm bài và chấm bài.

Tách khỏi serializer để phần tính điểm gọi được từ management command, tác vụ nền
hay module AI mà không phải dựng một request giả chỉ để có ``context``.
"""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Question, StudentAnswer, Submission

TOTAL_SCORE = Decimal("10")
SUBMIT_GRACE = timedelta(seconds=30)
MAX_ATTEMPTS = 3


def count_submitted_attempts(student, assignment) -> int:
    return Submission.objects.filter(
        assignment=assignment, student=student, submitted_at__isnull=False
    ).count()


def get_open_attempt(student, assignment):
    """Lượt làm bài đang dở (chưa nộp) gần nhất của học sinh, nếu có."""
    return Submission.objects.filter(
        assignment=assignment, student=student, submitted_at__isnull=True
    ).first()


def point_per_question(assignment) -> Decimal:
    """Điểm tối đa mỗi câu, cũng là trần khi gia sư chấm tay."""
    total = assignment.questions.count()
    if not total:
        return Decimal(0)
    return (TOTAL_SCORE / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _ensure_within_due_date(assignment):
    if assignment.due_date and timezone.now() > assignment.due_date:
        raise ValidationError("Bài tập đã hết hạn nộp.")


def _ensure_attempt_available(student, assignment):
    """Lượt làm bài phải còn hạn mức hoặc còn trong thời gian của lượt đang mở."""
    attempt = get_open_attempt(student, assignment)

    if attempt is None:
        if count_submitted_attempts(student, assignment) >= MAX_ATTEMPTS:
            raise ValidationError(
                f"Bạn đã dùng hết {MAX_ATTEMPTS} lượt làm bài của bài tập này."
            )
        return

    deadline = attempt.deadline
    if deadline and timezone.now() > deadline + SUBMIT_GRACE:
        raise ValidationError("Đã hết thời gian làm bài của lượt làm này.")


def open_or_create_attempt(student, assignment):
    """Lấy lượt đang làm dở, chưa có thì mở lượt mới với mốc giờ của server."""
    attempt = get_open_attempt(student, assignment)
    if attempt is None:
        attempt = Submission.objects.create(
            assignment=assignment,
            student=student,
            started_at=timezone.now(),
            score=None,
        )
    return attempt


def start_attempt(student, assignment):
    """Mở lượt làm bài, dùng lại lượt đang dở nếu học sinh chưa nộp."""
    _ensure_within_due_date(assignment)

    if not assignment.questions.exists():
        raise ValidationError("Bài tập chưa có câu hỏi nào.")

    _ensure_attempt_available(student, assignment)
    return open_or_create_attempt(student, assignment)


def _ensure_answers_match_questions(questions, answers):
    """Mỗi câu trả lời gửi lên phải khớp với câu hỏi và phương án thật của bài tập."""
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
    """Nộp bài và chấm tự động phần trắc nghiệm/điền khuyết.

    ``answers`` là list dict ``{question_id, answer_id?, answer_text?}``.
    Còn câu tự luận thì điểm tổng để trống, chờ :func:`grade_submission`.
    """
    _ensure_within_due_date(assignment)

    questions = {q.id: q for q in assignment.questions.prefetch_related("answers")}
    if not questions:
        raise ValidationError("Bài tập chưa có câu hỏi nào.")

    _ensure_answers_match_questions(questions, answers)
    _ensure_attempt_available(student, assignment)

    # Giữ nguyên phần thập phân khi cộng dồn, chỉ làm tròn ở điểm tổng.
    point_per_answer = TOTAL_SCORE / len(questions)

    # Lượt làm bài phải được start trước để tính giờ; client nộp thẳng thì tạo mới.
    attempt = open_or_create_attempt(student, assignment)

    stu_answers = []
    has_essay = False
    earned_score = Decimal(0)

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
            earned = (
                point_per_answer if (selected and selected.is_correct) else Decimal(0)
            )

        elif question.question_type == Question.QuestionType.FILL_IN_BLANK:
            text = (item.get("answer_text") or "").strip()
            stu_answer.answer_text = text
            correct = next((a for a in question.answers.all() if a.is_correct), None)
            earned = (
                point_per_answer
                if correct and text.lower() == correct.content.strip().lower()
                else Decimal(0)
            )

        else:  # ESSAY: để trống điểm, chờ gia sư chấm tay
            stu_answer.answer_text = (item.get("answer_text") or "").strip()
            stu_answer.point = None
            has_essay = True
            continue

        stu_answer.point = earned.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        earned_score += earned

    StudentAnswer.objects.bulk_create(stu_answers)

    attempt.submitted_at = timezone.now()
    # Còn câu tự luận thì để điểm trống chờ gia sư chấm.
    attempt.score = (
        None
        if has_essay
        else earned_score.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    )
    attempt.save(update_fields=["score", "submitted_at"])
    return attempt


def _ensure_gradable(submission, answers):
    if submission.submitted_at is None:
        raise ValidationError("Bài làm này chưa được nộp nên chưa thể chấm.")

    owned_ids = set(submission.stu_answers.values_list("id", flat=True))
    unknown_ids = [item["id"] for item in answers if item["id"] not in owned_ids]
    if unknown_ids:
        raise ValidationError(
            {"answers": f"Các câu trả lời {unknown_ids} không thuộc bài nộp này."}
        )

    max_point = point_per_question(submission.assignment)
    if any(item["point"] > max_point for item in answers):
        raise ValidationError({"answers": f"Điểm mỗi câu tối đa là {max_point}."})


@transaction.atomic
def grade_submission(submission, answers):
    """Chấm tay các câu tự luận.

    ``answers`` là list dict ``{id, point, tutor_comment?}`` với ``id`` là
    StudentAnswer thuộc chính bài nộp này.
    """
    _ensure_gradable(submission, answers)

    stu_answers = {
        answer.id: answer
        for answer in submission.stu_answers.select_related("question")
    }

    graded = []
    for item in answers:
        answer = stu_answers[item["id"]]
        answer.point = item["point"]
        if "tutor_comment" in item:
            answer.tutor_comment = item["tutor_comment"]
        graded.append(answer)

    StudentAnswer.objects.bulk_update(graded, ["point", "tutor_comment"])

    # Còn câu chưa có điểm thì bài vẫn ở trạng thái chờ chấm.
    all_points = [answer.point for answer in stu_answers.values()]
    if any(point is None for point in all_points):
        submission.score = None
    else:
        submission.score = sum(all_points, Decimal(0)).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    submission.save(update_fields=["score"])
    return submission
