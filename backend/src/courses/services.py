from datetime import timedelta
from django.db.models import (
    Avg,
    Count,
    Exists,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
)
from django.db.models.functions import Round
from django.shortcuts import get_object_or_404
from django.utils import timezone
from accounts.models import User
from assignments.models import Assignment, Submission
from .models import Chapter, Course, Enrollment, Lesson, LessonProgress

STREAK_LOOKBACK_DAYS = 365


def get_courses_with_progress(student, query):
    completed_sq = (
        LessonProgress.objects.filter(
            student=student,
            is_completed=True,
            lesson__chapter__course=OuterRef("pk"),
            lesson__published_at__isnull=False,
            lesson__chapter__published_at__isnull=False,
        )
        .values("lesson__chapter__course")
        .annotate(c=Count("pk"))
        .values("c")
    )

    return (
        query.filter(enrollment__student=student, enrollment__is_active=True)
        .select_related("tutor")
        .annotate(
            total_lessons=Count(
                "chapters__lessons",
                filter=Q(
                    chapters__published_at__isnull=False,
                    chapters__lessons__published_at__isnull=False,
                ),
            ),
            completed_lessons=Subquery(completed_sq),
        )
    )


def get_tutor_courses(tutor, query):
    students_count_sq = (
        Enrollment.objects.filter(course=OuterRef("pk"), is_active=True)
        .values("course")
        .annotate(c=Count("pk"))
        .values("c")
    )
    chapters_count_sq = (
        Chapter.objects.filter(course=OuterRef("pk"))
        .values("course")
        .annotate(c=Count("pk"))
        .values("c")
    )
    lessons_count_sq = (
        Lesson.objects.filter(chapter__course=OuterRef("pk"))
        .values("chapter__course")
        .annotate(c=Count("pk"))
        .values("c")
    )
    pending_submission_sq = (
        Submission.objects.filter(
            assignment__chapter__course=OuterRef("pk"),
            score__isnull=True,
            submitted_at__isnull=False,
        )
        .values("assignment__chapter__course")
        .annotate(c=Count("pk"))
        .values("c")
    )

    return query.filter(tutor=tutor).annotate(
        students_count=Subquery(students_count_sq),
        chapters_count=Subquery(chapters_count_sq),
        lessons_count=Subquery(lessons_count_sq),
        pending_submission_count=Subquery(pending_submission_sq),
    )


def get_learning_streak(student):
    recent_progress = LessonProgress.objects.filter(
        student=student,
        is_completed=True,
        complete_at__isnull=False,
        complete_at__gte=timezone.now() - timedelta(days=STREAK_LOOKBACK_DAYS),
    ).values_list("complete_at", flat=True)

    studied_dates = {
        timezone.localtime(complete_at).date() for complete_at in recent_progress
    }

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    if today not in studied_dates and yesterday not in studied_dates:
        return {
            "streak": 0,
            "studied_today": False,
        }

    current_date = today if today in studied_dates else yesterday
    studied_today = today in studied_dates

    streak = 0

    while current_date in studied_dates:
        streak += 1
        current_date -= timedelta(days=1)

    return {
        "streak": streak,
        "studied_today": studied_today,
    }


def get_quick_stats(student):
    ongoing_courses_count = Course.objects.filter(
        enrollment__student=student,
        enrollment__is_active=True,
        is_active=True,
    ).count()

    total_pending_assignments_count = (
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
        "total_pending_assignments_count": total_pending_assignments_count,
        "streak": streak_data["streak"],
        "studied_today": streak_data["studied_today"],
    }


def get_tutor_quick_stats(tutor):
    teaching_course_count = Course.objects.filter(tutor=tutor, is_active=True).count()

    total_students_count = (
        Enrollment.objects.filter(
            course__tutor=tutor, course__is_active=True, is_active=True
        )
        .values("student")
        .distinct()
        .count()
    )

    total_pending_submission_count = Submission.objects.filter(
        assignment__chapter__course__tutor=tutor,
        assignment__chapter__course__is_active=True,
        assignment__chapter__is_active=True,
        submitted_at__isnull=False,
        score__isnull=True,
    ).count()

    return {
        "teaching_course_count": teaching_course_count,
        "total_students_count": total_students_count,
        "total_pending_submission_count": total_pending_submission_count,
    }


def get_course_tree(course, user, include_drafts=False):
    chapters = Chapter.objects.filter(is_active=True)
    lessons = Lesson.objects.filter(is_active=True)

    if not include_drafts:
        chapters = chapters.filter(published_at__isnull=False)
        lessons = lessons.filter(published_at__isnull=False).annotate(
            is_completed=Exists(
                LessonProgress.objects.filter(
                    lesson=OuterRef("pk"),
                    student=user,
                    is_completed=True,
                )
            )
        )
    chapters = chapters.prefetch_related(Prefetch("lessons", queryset=lessons))

    return get_object_or_404(
        Course.objects.prefetch_related(Prefetch("chapters", queryset=chapters)),
        pk=course.id,
    )


def get_course_overview(course, student):
    lessons = Lesson.objects.filter(
        chapter__course=course,
        chapter__is_active=True,
        is_active=True,
        published_at__isnull=False,
        chapter__published_at__isnull=False,
    )

    lesson_stats = lessons.aggregate(
        total=Count("id"),
        completed=Count(
            "lessonprogress",
            filter=Q(
                lessonprogress__student=student,
                lessonprogress__is_completed=True,
            )
        ),
    )

    total_lessons = lesson_stats["total"]
    completed_lessons = lesson_stats["completed"]

    if total_lessons is None:
        total_lessons = 0

    if completed_lessons is None:
        completed_lessons = 0

    if total_lessons > 0:
        progress_percent = completed_lessons / total_lessons * 100
        progress_percent = round(progress_percent, 1)
    else:
        progress_percent = 0

    assignments = Assignment.objects.filter(
        chapter__course=course,
        chapter__is_active=True,
        is_active=True,
        due_date__gte=timezone.now(),
        published_at__isnull=False,
        chapter__published_at__isnull=False,
    )

    pending_assignments_count = assignments.exclude(
        submission__student=student,
        submission__submitted_at__isnull=False,
    ).count()

    submissions = Submission.objects.filter(
        assignment__chapter__course=course,
        student=student,
        submitted_at__isnull=False,
    )

    result = submissions.aggregate(
        avg=Round(
            Avg("score"),
            precision=2,
        )
    )
    average_score = result["avg"]

    return {
        "progress": {
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "progress_percent": progress_percent,
        },
        "average_score": average_score,
        "pending_assignments_count": pending_assignments_count,
    }


def get_chapter_stats(course, student):
    submitted = Submission.objects.filter(
        student=student,
        submitted_at__isnull=False,
    )
    average_score = (
        submitted.filter(assignment__chapter=OuterRef("pk"))
        .values("assignment__chapter")
        .annotate(avg=Round(Avg("score"), precision=2))
        .values("avg")
    )

    pending_assignments = Assignment.objects.filter(
        chapter=OuterRef("pk"),
        is_active=True,
        published_at__isnull=False,
    ).exclude(
        submission__student=student,
        submission__submitted_at__isnull=False,
    )

    lessons = Lesson.objects.filter(
        is_active=True,
        published_at__isnull=False,
    ).annotate(
        is_completed=Exists(
            LessonProgress.objects.filter(
                lesson=OuterRef("pk"),
                student=student,
                is_completed=True,
            )
        )
    )

    visible_lesson = Q(lessons__is_active=True, lessons__published_at__isnull=False)

    chapters = (
        course.chapters.filter(
            is_active=True,
            published_at__isnull=False,
        )
        .prefetch_related(Prefetch("lessons", queryset=lessons))
        .annotate(
            total_lessons=Count(
                "lessons",
                filter=visible_lesson,
                distinct=True,
            ),
            completed_lessons=Count(
                "lessons__lessonprogress",
                filter=(
                    visible_lesson
                    & Q(
                        lessons__lessonprogress__student=student,
                        lessons__lessonprogress__is_completed=True,
                    )
                ),
                distinct=True,
            ),
            has_pending_assignment=Exists(pending_assignments),
            score=average_score,
        )
    )

    result = []
    for chapter in chapters:
        chapter.first_incomplete_lesson_id = None
        for lesson in chapter.lessons.all():
            if not lesson.is_completed:
                chapter.first_incomplete_lesson_id = lesson.id
                break
        result.append(chapter)
    return result


def get_course_tutor_stats(course):
    total_lessons = Lesson.objects.filter(
        chapter__course=course, chapter__is_active=True, is_active=True
    ).count()

    student_average_score = (
        Submission.objects.filter(
            student=OuterRef("pk"),
            assignment__chapter__course=course,
            submitted_at__isnull=False,
        )
        .values("student")
        .annotate(
            average=Round(
                Avg("score"),
                precision=2,
            )
        )
        .values("average")
    )

    students = (
        User.objects.filter(enrollment__course=course, enrollment__is_active=True)
        .annotate(
            completed_lessons=Count(
                "lessonprogress",
                filter=Q(
                    lessonprogress__lesson__chapter__course=course,
                    lessonprogress__is_completed=True,
                ),
            ),
            average_score=Subquery(student_average_score),
        )
        .order_by("last_name", "first_name")
    )

    student_stats = []
    for student in students:
        progress = (
            round(student.completed_lessons * 100 / total_lessons, 1)
            if total_lessons
            else 0
        )

        student_stats.append(
            {
                "student": student,
                "completed_lessons": student.completed_lessons,
                "total_lessons": total_lessons,
                "progress": progress,
                "average_score": student.average_score,
            }
        )

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
    )

    assignment_stats = []

    for assignment in assignments:
        assignment_stats.append(
            {
                "id": assignment.id,
                "title": assignment.title,
                "chapter_title": assignment.chapter.title,
                "due_date": assignment.due_date,
                "submitted_count": assignment.submitted_count,
                "pending_count": (assignment.submitted_count - assignment.graded_count),
                "average_score": assignment.average_score,
            }
        )

    return {
        "total_students": len(student_stats),
        "total_lessons": total_lessons,
        "students": student_stats,
        "assignments": assignment_stats,
    }


def mark_lesson_completed(student, lesson):
    progress, _ = LessonProgress.objects.get_or_create(
        student=student,
        lesson=lesson,
        defaults={
            "is_completed": True,
            "complete_at": timezone.now(),
        },
    )
    return progress


def toggle_comment_right(comment, user):
    comment.is_right = not comment.is_right

    if comment.is_right:
        comment.marked_right_by = user
        comment.marked_right_at = timezone.now()
    else:
        comment.marked_right_by = None
        comment.marked_right_at = None

    comment.save(update_fields=["is_right", "marked_right_by", "marked_right_at"])
    return comment
