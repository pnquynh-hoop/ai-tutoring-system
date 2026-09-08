from datetime import timedelta

import pytest
from django.utils import timezone
from model_bakery import baker

from assignments.models import Assignment
from courses.models import Chapter, Course, Lesson, LessonProgress
from courses.services import (
    get_chapter_stats,
    get_course_overview,
    get_course_tree,
    get_quick_stats,
    get_tutor_courses,
    get_tutor_quick_stats,
    mark_lesson_completed,
)


@pytest.mark.django_db
class TestCourseStatServices:
    def make_chapter_with_lessons(self, course, order, lesson_count):
        chapter = Chapter.objects.create(
            course=course,
            title=f"Chương {order}",
            order=order,
            published_at=timezone.now(),
        )
        lessons = [
            Lesson.objects.create(
                chapter=chapter,
                title=f"Bài {i}",
                order=i,
                published_at=timezone.now(),
            )
            for i in range(1, lesson_count + 1)
        ]
        return chapter, lessons

    def test_course_overview_counts_progress_and_pending(
        self, course, enrolled_student
    ):
        _, lessons = self.make_chapter_with_lessons(course, 1, 4)
        mark_lesson_completed(enrolled_student, lessons[0])
        Assignment.objects.create(
            chapter=lessons[0].chapter,
            title="Bài tập ôn chương",
            due_date=timezone.now() + timedelta(days=1),
            published_at=timezone.now(),
        )

        data = get_course_overview(course=course, student=enrolled_student)

        assert data["progress"]["total_lessons"] == 4
        assert data["progress"]["completed_lessons"] == 1
        assert data["progress"]["progress_percent"] == 25.0
        assert data["pending_assignments_count"] == 1
        assert data["average_score"] is None

    def test_course_overview_without_lessons(self, course, enrolled_student):
        data = get_course_overview(course=course, student=enrolled_student)

        assert data["progress"] == {
            "total_lessons": 0,
            "completed_lessons": 0,
            "progress_percent": 0,
        }

    def test_chapter_stats_returns_per_chapter_numbers(self, course, enrolled_student):
        chapter, lessons = self.make_chapter_with_lessons(course, 1, 3)
        mark_lesson_completed(enrolled_student, lessons[0])
        Assignment.objects.create(
            chapter=chapter,
            title="Bài tập ôn chương",
            due_date=timezone.now() + timedelta(days=1),
            published_at=timezone.now(),
        )

        stats = get_chapter_stats(course=course, student=enrolled_student)

        assert len(stats) == 1
        assert stats[0].total_lessons == 3
        assert stats[0].completed_lessons == 1
        assert stats[0].has_pending_assignment is True
        assert stats[0].first_incomplete_lesson_id == lessons[1].id
        assert stats[0].score is None

    def test_finished_chapter_has_no_incomplete_lesson(self, course, enrolled_student):
        _, lessons = self.make_chapter_with_lessons(course, 1, 2)
        for lesson in lessons:
            mark_lesson_completed(enrolled_student, lesson)

        stats = get_chapter_stats(course=course, student=enrolled_student)

        assert stats[0].first_incomplete_lesson_id is None

    def test_chapter_stats_marks_submitted_assignment_as_done(
        self, course, enrolled_student
    ):
        chapter, _ = self.make_chapter_with_lessons(course, 1, 1)
        assignment = Assignment.objects.create(
            chapter=chapter,
            title="Bài tập ôn chương",
            due_date=timezone.now() + timedelta(days=1),
            published_at=timezone.now(),
        )
        baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=enrolled_student,
            score=8,
            submitted_at=timezone.now(),
        )

        stats = get_chapter_stats(course=course, student=enrolled_student)

        assert stats[0].has_pending_assignment is False
        assert float(stats[0].score) == 8.0

    def test_chapter_stats_has_no_n_plus_one(
        self, course, enrolled_student, django_assert_max_num_queries
    ):
        for order in range(1, 6):
            chapter, lessons = self.make_chapter_with_lessons(course, order, 4)
            mark_lesson_completed(enrolled_student, lessons[0])
            baker.make(
                "assignments.Assignment",
                chapter=chapter,
                due_date=timezone.now() + timedelta(days=1),
            )

        with django_assert_max_num_queries(3):
            stats = get_chapter_stats(course=course, student=enrolled_student)

        assert len(stats) == 5

    def test_course_tree_flags_completed_lessons(self, course, enrolled_student):
        _, lessons = self.make_chapter_with_lessons(course, 1, 2)
        mark_lesson_completed(enrolled_student, lessons[0])

        tree = get_course_tree(course=course, user=enrolled_student)
        tree_lessons = list(tree.chapters.all()[0].lessons.all())

        assert [lesson.is_completed for lesson in tree_lessons] == [True, False]

    def test_student_quick_stats(self, course, enrolled_student):
        _, lessons = self.make_chapter_with_lessons(course, 1, 2)
        mark_lesson_completed(enrolled_student, lessons[0])
        Assignment.objects.create(
            chapter=lessons[0].chapter,
            title="Bài tập ôn chương",
            due_date=timezone.now() + timedelta(days=1),
            published_at=timezone.now(),
        )

        stats = get_quick_stats(student=enrolled_student)

        assert stats["ongoing_courses_count"] == 1
        assert stats["total_pending_assignments_count"] == 1
        assert stats["streak"] == 1
        assert stats["studied_today"] is True

    def test_streak_counts_consecutive_days(self, course, enrolled_student):
        _, lessons = self.make_chapter_with_lessons(course, 1, 3)
        now = timezone.now()
        for index, lesson in enumerate(lessons):
            LessonProgress.objects.create(
                student=enrolled_student,
                lesson=lesson,
                is_completed=True,
                complete_at=now - timedelta(days=index),
            )

        stats = get_quick_stats(student=enrolled_student)

        assert stats["streak"] == 3
        assert stats["studied_today"] is True

    def test_streak_breaks_on_gap(self, course, enrolled_student):
        _, lessons = self.make_chapter_with_lessons(course, 1, 2)
        now = timezone.now()
        LessonProgress.objects.create(
            student=enrolled_student,
            lesson=lessons[0],
            is_completed=True,
            complete_at=now,
        )
        LessonProgress.objects.create(
            student=enrolled_student,
            lesson=lessons[1],
            is_completed=True,
            complete_at=now - timedelta(days=3),
        )

        assert get_quick_stats(student=enrolled_student)["streak"] == 1

    def test_student_quick_stats_ignores_inactive_enrollment(self, tutor, student):
        other_course = baker.make("courses.Course", tutor=tutor)
        baker.make(
            "courses.Enrollment",
            course=other_course,
            student=student,
            is_active=False,
        )

        assert get_quick_stats(student=student)["ongoing_courses_count"] == 0

    def test_tutor_quick_stats(self, course, tutor, enrolled_student):
        chapter, _ = self.make_chapter_with_lessons(course, 1, 1)
        assignment = Assignment.objects.create(
            chapter=chapter,
            title="Bài tập ôn chương",
            due_date=timezone.now() + timedelta(days=1),
            published_at=timezone.now(),
        )
        baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=enrolled_student,
            score=None,
            submitted_at=timezone.now(),
        )

        stats = get_tutor_quick_stats(tutor=tutor)

        assert stats["teaching_course_count"] == 1
        assert stats["total_students_count"] == 1
        assert stats["total_pending_submission_count"] == 1

    def test_tutor_quick_stats_ignores_unsubmitted_attempt(
        self, course, tutor, enrolled_student
    ):
        chapter, _ = self.make_chapter_with_lessons(course, 1, 1)
        assignment = Assignment.objects.create(
            chapter=chapter,
            title="Bài tập ôn chương",
            due_date=timezone.now() + timedelta(days=1),
            published_at=timezone.now(),
        )
        baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=enrolled_student,
            score=None,
            started_at=timezone.now(),
            submitted_at=None,
        )

        assert get_tutor_quick_stats(tutor=tutor)["total_pending_submission_count"] == 0

    def test_get_tutor_courses_annotations(self, course, tutor, enrolled_student):
        chapter, _ = self.make_chapter_with_lessons(course, 1, 3)
        assignment = Assignment.objects.create(
            chapter=chapter,
            title="Bài tập ôn chương",
            due_date=timezone.now() + timedelta(days=1),
            published_at=timezone.now(),
        )
        baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=enrolled_student,
            score=None,
            submitted_at=timezone.now(),
        )

        result = list(get_tutor_courses(tutor=tutor, query=Course.objects.all()))

        assert len(result) == 1
        assert result[0].students_count == 1
        assert result[0].chapters_count == 1
        assert result[0].lessons_count == 3
        assert result[0].pending_submission_count == 1
