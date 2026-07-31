from datetime import timedelta

from django.db.models import (
    Avg,
    Case,
    Count,
    Exists,
    ExpressionWrapper,
    F,
    FloatField,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Round
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.models import User
from assignments.models import Assignment, Submission
from core.querysets import only_published

from .models import Chapter, Course, Enrollment, Lesson, LessonProgress

# Chỉ soi lại tối đa 1 năm khi tính chuỗi ngày học liên tục.
STREAK_LOOKBACK_DAYS = 365


def _progress_expression():
    """Biểu thức tính % tiến độ ngay dưới DB, tránh chia cho 0."""
    return Case(
        When(total_lessons=0, then=Value(0.0)),
        default=Round(
            ExpressionWrapper(
                F("completed_lessons") * 100.0 / F("total_lessons"),
                output_field=FloatField(),
            ),
            precision=1,
        ),
        output_field=FloatField(),
    )


def enrolled_courses(student, query=None):
    """Queryset các khóa học mà student có Enrollment đang hoạt động."""
    query = Course.objects.all() if query is None else query
    return query.filter(enrollment__student=student, enrollment__is_active=True)


def get_courses_with_progress(student, query):
    """Queryset các course student đang học, kèm progress tính sẵn dưới DB."""
    visible_lesson = Q(
        chapters__published_at__isnull=False,
        chapters__lessons__published_at__isnull=False,
    )

    return (
        enrolled_courses(student, query)
        .select_related("tutor", "subject", "grade")
        .annotate(
            total_lessons=Count("chapters__lessons", filter=visible_lesson, distinct=True),
            completed_lessons=Count(
                "chapters__lessons__lessonprogress",
                filter=visible_lesson
                & Q(
                    chapters__lessons__lessonprogress__student=student,
                    chapters__lessons__lessonprogress__is_completed=True,
                ),
                distinct=True,
            ),
        )
        .annotate(progress=_progress_expression())
    )


def get_tutor_courses(tutor, query):
    """Queryset các course do tutor phụ trách, kèm số liệu tổng quan."""
    return query.filter(tutor=tutor).annotate(
        students_count=Count(
            "enrollment",
            filter=Q(enrollment__is_active=True),
            distinct=True,
        ),
        chapters_count=Count("chapters", distinct=True),
        lessons_count=Count("chapters__lessons", distinct=True),
        pending_submission_count=Count(
            "chapters__assignment__submission",
            filter=Q(
                chapters__assignment__submission__score__isnull=True,
                chapters__assignment__submission__submitted_at__isnull=False,
            ),
            distinct=True,
        ),
    )


def get_learning_streak(student):
    """Tính số ngày học liên tục gần nhất.

    Quy đổi sang ngày theo giờ địa phương ở Python thay vì dùng ``.dates()``:
    trên MySQL, ``.dates()`` gọi CONVERT_TZ và trả về rỗng nếu server chưa nạp
    bảng timezone, khiến streak luôn bằng 0.
    """
    completed_at_values = LessonProgress.objects.filter(
        student=student,
        is_completed=True,
        complete_at__isnull=False,
        complete_at__gte=timezone.now() - timedelta(days=STREAK_LOOKBACK_DAYS),
    ).values_list("complete_at", flat=True)

    completed_dates = sorted(
        {timezone.localtime(value).date() for value in completed_at_values},
        reverse=True,
    )

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    if not completed_dates or completed_dates[0] not in (today, yesterday):
        return {"streak": 0, "studied_today": False}

    studied_today = completed_dates[0] == today

    streak = 0
    expected_date = completed_dates[0]
    for date in completed_dates:
        if date == expected_date:
            streak += 1
            expected_date -= timedelta(days=1)
        else:
            break

    return {"streak": streak, "studied_today": studied_today}


def get_quick_stats(student):
    """Trả về dict thống kê cho 3 thẻ ở dashboard học sinh."""

    ongoing_courses_count = enrolled_courses(student).filter(is_active=True).count()

    pending_assignments_count = (
        Assignment.objects.filter(
            chapter__course__enrollment__student=student,
            chapter__course__enrollment__is_active=True,
            chapter__course__is_active=True,
            chapter__is_active=True,
            chapter__published_at__isnull=False,
            published_at__isnull=False,
            is_active=True,
            due_date__gte=timezone.now(),
        )
        .exclude(submission__student=student, submission__submitted_at__isnull=False)
        .distinct()
        .count()
    )

    streak_data = get_learning_streak(student)

    return {
        "ongoing_courses_count": ongoing_courses_count,
        "pending_assignments_count": pending_assignments_count,
        "streak": streak_data["streak"],
        "studied_today": streak_data["studied_today"],
    }


def get_tutor_quick_stats(tutor):
    """Trả về dict thống kê cho 3 thẻ ở dashboard gia sư."""

    teaching_course_count = Course.objects.filter(tutor=tutor, is_active=True).count()

    students_count = (
        Enrollment.objects.filter(
            course__tutor=tutor, course__is_active=True, is_active=True
        )
        .values("student")
        .distinct()
        .count()
    )

    pending_submission_count = Submission.objects.filter(
        assignment__chapter__course__tutor=tutor,
        assignment__chapter__course__is_active=True,
        assignment__chapter__is_active=True,
        submitted_at__isnull=False,
        score__isnull=True,
    ).count()

    return {
        "teaching_course_count": teaching_course_count,
        "students_count": students_count,
        "pending_submission_count": pending_submission_count,
    }


def _lessons_with_completion(student, include_drafts=False):
    """Queryset Lesson kèm cờ is_completed theo học sinh đang đăng nhập."""
    query = Lesson.objects.filter(is_active=True)
    if not include_drafts:
        query = only_published(query)

    return (
        query.annotate(
            is_completed=Exists(
                LessonProgress.objects.filter(
                    lesson=OuterRef("pk"),
                    student=student,
                    is_completed=True,
                )
            )
        )
        .order_by("order")
    )


def get_course_tree(course_id, student, include_drafts=False):
    """Cây thư mục khóa học dùng cho sidebar, kèm tiến độ của học sinh đang đăng nhập."""
    chapters = Chapter.objects.filter(is_active=True)
    if not include_drafts:
        chapters = only_published(chapters)

    chapters = chapters.prefetch_related(
        Prefetch("lessons", queryset=_lessons_with_completion(student, include_drafts))
    )

    return get_object_or_404(
        Course.objects.prefetch_related(Prefetch("chapters", queryset=chapters)),
        pk=course_id,
        is_active=True,
    )


def get_course_overview(course, student, include_drafts=False):
    """Số liệu tổng quan của một khóa học đối với học sinh đang đăng nhập."""
    lessons = Lesson.objects.filter(
        chapter__course=course, chapter__is_active=True, is_active=True
    )
    if not include_drafts:
        lessons = only_published(lessons, "chapter")

    lesson_stats = lessons.aggregate(
        total=Count("id", distinct=True),
        completed=Count(
            "lessonprogress",
            filter=Q(
                lessonprogress__student=student,
                lessonprogress__is_completed=True,
            ),
            distinct=True,
        ),
    )

    total_lessons = lesson_stats["total"] or 0
    completed_lessons = lesson_stats["completed"] or 0
    progress_percent = (
        round(completed_lessons / total_lessons * 100, 1) if total_lessons else 0
    )

    assignments = Assignment.objects.filter(
        chapter__course=course,
        chapter__is_active=True,
        is_active=True,
        due_date__gte=timezone.now(),
    )
    if not include_drafts:
        assignments = only_published(assignments, "chapter")

    pending_assignments_count = assignments.exclude(
        submission__student=student, submission__submitted_at__isnull=False
    ).count()

    average_score = Submission.objects.filter(
        assignment__chapter__course=course,
        student=student,
        submitted_at__isnull=False,
    ).aggregate(avg=Round(Avg("score"), precision=2))["avg"]

    return {
        "progress": {
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "progress_percent": progress_percent,
        },
        "average_score": average_score,
        "pending_assignments_count": pending_assignments_count,
    }


def get_chapter_stats(course, student, include_drafts=False):
    """Thống kê từng chương của khóa học cho học sinh đang đăng nhập.

    Toàn bộ số liệu được annotate/prefetch sẵn nên không phát sinh query trong vòng lặp.
    """
    submitted = Submission.objects.filter(student=student, submitted_at__isnull=False)

    average_score = (
        submitted.filter(assignment__chapter=OuterRef("pk"))
        .values("assignment__chapter")
        .annotate(avg=Round(Avg("score"), precision=2))
        .values("avg")[:1]
    )

    visible_lesson = Q(lessons__is_active=True)
    chapter_assignments = Assignment.objects.filter(
        chapter=OuterRef("pk"), is_active=True
    )
    chapters = course.chapters.filter(is_active=True)

    if not include_drafts:
        visible_lesson &= Q(lessons__published_at__isnull=False)
        chapter_assignments = only_published(chapter_assignments)
        chapters = only_published(chapters)

    chapters = chapters.prefetch_related(
        Prefetch("lessons", queryset=_lessons_with_completion(student, include_drafts))
    ).annotate(
        total_lessons=Count("lessons", filter=visible_lesson, distinct=True),
        completed_lessons=Count(
            "lessons__lessonprogress",
            filter=visible_lesson
            & Q(
                lessons__lessonprogress__student=student,
                lessons__lessonprogress__is_completed=True,
            ),
            distinct=True,
        ),
        has_assignment=Exists(chapter_assignments),
        has_submission=Exists(submitted.filter(assignment__chapter=OuterRef("pk"))),
        score=average_score,
    )

    result = []
    for chapter in chapters:
        first_incomplete = next(
            (lesson.id for lesson in chapter.lessons.all() if not lesson.is_completed),
            None,
        )

        result.append(
            {
                "id": chapter.id,
                "title": chapter.title,
                "order": chapter.order,
                "total_lessons": chapter.total_lessons,
                "completed_lessons": chapter.completed_lessons,
                "score": chapter.score,
                "pending_assignments": int(
                    chapter.has_assignment and not chapter.has_submission
                ),
                "first_incomplete_lesson_id": first_incomplete,
            }
        )

    return result


def get_course_tutor_stats(course):
    """Thống kê một khóa học cho gia sư: tiến độ từng học sinh + tình hình từng bài tập."""
    total_lessons = Lesson.objects.filter(
        chapter__course=course, chapter__is_active=True, is_active=True
    ).count()

    average_score_subquery = (
        Submission.objects.filter(
            student=OuterRef("pk"),
            assignment__chapter__course=course,
            submitted_at__isnull=False,
        )
        .values("student")
        .annotate(value=Round(Avg("score"), precision=2))
        .values("value")[:1]
    )

    students = (
        User.objects.filter(enrollment__course=course, enrollment__is_active=True)
        .distinct()
        .annotate(
            completed_lessons=Count(
                "lessonprogress",
                filter=Q(
                    lessonprogress__lesson__chapter__course=course,
                    lessonprogress__is_completed=True,
                ),
                distinct=True,
            ),
            average_score=Subquery(average_score_subquery),
        )
        .order_by("last_name", "first_name")
    )

    student_stats = [
        {
            "id": student.id,
            "full_name": student.full_name,
            "avatar": student.avatar.url if student.avatar else None,
            "completed_lessons": student.completed_lessons,
            "total_lessons": total_lessons,
            "progress": (
                round(student.completed_lessons * 100 / total_lessons, 1)
                if total_lessons
                else 0
            ),
            "average_score": student.average_score,
        }
        for student in students
    ]

    assignments = (
        Assignment.objects.filter(chapter__course=course, is_active=True)
        .select_related("chapter")
        .annotate(
            submitted_count=Count(
                "submission",
                filter=Q(submission__submitted_at__isnull=False),
                distinct=True,
            ),
            graded_count=Count(
                "submission",
                filter=Q(
                    submission__submitted_at__isnull=False,
                    submission__score__isnull=False,
                ),
                distinct=True,
            ),
            average_score=Round(
                Avg(
                    "submission__score",
                    filter=Q(submission__submitted_at__isnull=False),
                ),
                precision=2,
            ),
        )
        .order_by("chapter__order")
    )

    assignment_stats = [
        {
            "id": assignment.id,
            "title": assignment.title,
            "chapter_title": assignment.chapter.title,
            "due_date": assignment.due_date,
            "submitted_count": assignment.submitted_count,
            "graded_count": assignment.graded_count,
            "pending_count": assignment.submitted_count - assignment.graded_count,
            "average_score": assignment.average_score,
        }
        for assignment in assignments
    ]

    return {
        "total_students": len(student_stats),
        "total_lessons": total_lessons,
        "students": student_stats,
        "assignments": assignment_stats,
    }


def mark_lesson_completed(student, lesson):
    """Đánh dấu hoàn thành bài học, ghi lại đúng thời điểm hoàn thành."""
    progress, _ = LessonProgress.objects.update_or_create(
        student=student,
        lesson=lesson,
        defaults={
            "is_completed": True,
            "complete_at": timezone.now(),
        },
    )
    return progress


def toggle_comment_right(comment, user):
    """Bật/tắt trạng thái 'câu trả lời đúng' của một bình luận."""
    comment.is_right = not comment.is_right

    if comment.is_right:
        comment.marked_right_by = user
        comment.marked_right_at = timezone.now()
    else:
        comment.marked_right_by = None
        comment.marked_right_at = None

    comment.save(update_fields=["is_right", "marked_right_by", "marked_right_at"])
    return comment
