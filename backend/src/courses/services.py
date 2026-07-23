from django.shortcuts import get_object_or_404
from assignments.models import Assignment
from .models import Chapter, Course, Lesson, LessonProgress
from django.db.models import Count, Q, Exists, OuterRef, Prefetch
from django.utils import timezone
from datetime import timedelta


def get_courses_with_progress(student, query):
    """Hàm trả về queryset các course mà student đang học, kèm progress đã tính."""
    courses = query.filter(students=student).annotate(
        total_lessons=Count("chapters__lessons", distinct=True),
        completed_lessons=Count(
            "chapters__lessons__lessonprogress",
            filter=Q(
                chapters__lessons__lessonprogress__student=student,
                chapters__lessons__lessonprogress__is_completed=True,
            ),
            distinct=True,
        ),
    )

    for course in courses:
        course.progress = (
            round(course.completed_lessons * 100 / course.total_lessons, 1)
            if course.total_lessons > 0
            else 0
        )
    return courses


def get_learning_streak(student):
    """Tính số ngày học liên tục gần nhất."""
    completed_dates = list(
        LessonProgress.objects.filter(student=student, is_completed=True).dates(
            "complete_at", "day", order="DESC"
        )
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

    ongoing_courses_count = Course.objects.filter(
        students=student, is_active=True
    ).count()

    pending_assignments_count = (
        Assignment.objects.filter(
            chapter__course__students=student,
            chapter__course__is_active=True,
            chapter__is_active=True,
            due_date__gte=timezone.now(),
        )
        .exclude(submission__student=student)
        .count()
    )

    streak_data = get_learning_streak(student)

    return {
        "ongoing_courses_count": ongoing_courses_count,
        "pending_assignments_count": pending_assignments_count,
        "streak": streak_data["streak"],
        "studied_today": streak_data["studied_today"],
    }


def get_course_tree(course_id, student):
    """Hàm trả về cây thư mục khóa học dùng hiển thị sidebar có theo dõi tiến độ hoàn thành bài học theo học sinh đang đăng nhập."""
    lessons = Lesson.objects.order_by("order").annotate(
        is_completed=Exists(
            LessonProgress.objects.filter(
                lesson=OuterRef("pk"),
                student=student,
                is_completed=True,
            )
        )
    )
    chapters = Chapter.objects.order_by("order").prefetch_related(
        Prefetch(
            "lessons",
            queryset=lessons,
        )
    )

    return get_object_or_404(
        Course.objects.prefetch_related(
            Prefetch(
                "chapters",
                queryset=chapters,
            )
        ),
        pk=course_id,
        is_active=True,
    )
