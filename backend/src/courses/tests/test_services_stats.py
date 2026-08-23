from datetime import timedelta

import pytest
from django.utils import timezone
from model_bakery import baker

from core.testing import make_published

from courses.models import Course, LessonProgress
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
    @pytest.fixture
    def student(self):
        return baker.make("accounts.User")

    @pytest.fixture
    def tutor(self):
        return baker.make("accounts.User")

    @pytest.fixture
    def course(self, tutor, student):
        course = baker.make("courses.Course", tutor=tutor)
        baker.make("courses.Enrollment", course=course, student=student)
        return course

    def make_chapter_with_lessons(self, course, order, lesson_count):
        chapter = make_published("courses.Chapter", course=course, order=order)
        return chapter, [
            make_published("courses.Lesson", chapter=chapter, order=i)
            for i in range(1, lesson_count + 1)
        ]

    def test_course_overview_counts_progress_and_pending(self, course, student):
        _, lessons = self.make_chapter_with_lessons(course, 1, 4)
        mark_lesson_completed(student, lessons[0])
        make_published(
            "assignments.Assignment",
            chapter=lessons[0].chapter,
            due_date=timezone.now() + timedelta(days=1),
        )

        data = get_course_overview(course=course, student=student)

        assert data["progress"]["total_lessons"] == 4
        assert data["progress"]["completed_lessons"] == 1
        assert data["progress"]["progress_percent"] == 25.0
        assert data["pending_assignments_count"] == 1
        assert data["average_score"] is None

    def test_course_overview_without_lessons(self, course, student):
        data = get_course_overview(course=course, student=student)

        assert data["progress"] == {
            "total_lessons": 0,
            "completed_lessons": 0,
            "progress_percent": 0,
        }

    def test_chapter_stats_returns_per_chapter_numbers(self, course, student):
        chapter, lessons = self.make_chapter_with_lessons(course, 1, 3)
        mark_lesson_completed(student, lessons[0])
        make_published(
            "assignments.Assignment",
            chapter=chapter,
            due_date=timezone.now() + timedelta(days=1),
        )

        stats = get_chapter_stats(course=course, student=student)

        assert len(stats) == 1
        assert stats[0]["total_lessons"] == 3
        assert stats[0]["completed_lessons"] == 1
        assert stats[0]["pending_assignments"] == 1
        assert stats[0]["first_incomplete_lesson_id"] == lessons[1].id
        assert stats[0]["score"] is None

    def test_chapter_stats_marks_submitted_assignment_as_done(self, course, student):
        chapter, _ = self.make_chapter_with_lessons(course, 1, 1)
        assignment = make_published(
            "assignments.Assignment",
            chapter=chapter,
            due_date=timezone.now() + timedelta(days=1),
        )
        baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=student,
            score=8,
            submitted_at=timezone.now(),
        )

        stats = get_chapter_stats(course=course, student=student)

        assert stats[0]["pending_assignments"] == 0
        assert float(stats[0]["score"]) == 8.0

    def test_chapter_stats_has_no_n_plus_one(
        self, course, student, django_assert_max_num_queries
    ):
        for order in range(1, 6):
            chapter, lessons = self.make_chapter_with_lessons(course, order, 4)
            mark_lesson_completed(student, lessons[0])
            baker.make(
                "assignments.Assignment",
                chapter=chapter,
                due_date=timezone.now() + timedelta(days=1),
            )

        with django_assert_max_num_queries(3):
            stats = get_chapter_stats(course=course, student=student)

        assert len(stats) == 5

    def test_course_tree_flags_completed_lessons(self, course, student):
        _, lessons = self.make_chapter_with_lessons(course, 1, 2)
        mark_lesson_completed(student, lessons[0])

        tree = get_course_tree(course=course, student=student)
        tree_lessons = list(tree.chapters.all()[0].lessons.all())

        assert [lesson.is_completed for lesson in tree_lessons] == [True, False]

    def test_student_quick_stats(self, course, student):
        _, lessons = self.make_chapter_with_lessons(course, 1, 2)
        mark_lesson_completed(student, lessons[0])
        make_published(
            "assignments.Assignment",
            chapter=lessons[0].chapter,
            due_date=timezone.now() + timedelta(days=1),
        )

        stats = get_quick_stats(student=student)

        assert stats["ongoing_courses_count"] == 1
        assert stats["pending_assignments_count"] == 1
        assert stats["streak"] == 1
        assert stats["studied_today"] is True

    def test_streak_counts_consecutive_days(self, course, student):
        _, lessons = self.make_chapter_with_lessons(course, 1, 3)
        now = timezone.now()
        for index, lesson in enumerate(lessons):
            LessonProgress.objects.create(
                student=student,
                lesson=lesson,
                is_completed=True,
                complete_at=now - timedelta(days=index),
            )

        stats = get_quick_stats(student=student)

        assert stats["streak"] == 3
        assert stats["studied_today"] is True

    def test_streak_breaks_on_gap(self, course, student):
        _, lessons = self.make_chapter_with_lessons(course, 1, 2)
        now = timezone.now()
        LessonProgress.objects.create(
            student=student, lesson=lessons[0], is_completed=True, complete_at=now
        )
        LessonProgress.objects.create(
            student=student,
            lesson=lessons[1],
            is_completed=True,
            complete_at=now - timedelta(days=3),
        )

        assert get_quick_stats(student=student)["streak"] == 1

    def test_student_quick_stats_ignores_inactive_enrollment(self, tutor, student):
        other_course = baker.make("courses.Course", tutor=tutor)
        baker.make(
            "courses.Enrollment",
            course=other_course,
            student=student,
            is_active=False,
        )

        assert get_quick_stats(student=student)["ongoing_courses_count"] == 0

    def test_tutor_quick_stats(self, course, tutor, student):
        chapter, _ = self.make_chapter_with_lessons(course, 1, 1)
        assignment = make_published(
            "assignments.Assignment",
            chapter=chapter,
            due_date=timezone.now() + timedelta(days=1),
        )
        baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=student,
            score=None,
            submitted_at=timezone.now(),
        )

        stats = get_tutor_quick_stats(tutor=tutor)

        assert stats["teaching_course_count"] == 1
        assert stats["students_count"] == 1
        assert stats["pending_submission_count"] == 1

    def test_tutor_quick_stats_ignores_unsubmitted_attempt(
        self, course, tutor, student
    ):
        chapter, _ = self.make_chapter_with_lessons(course, 1, 1)
        assignment = make_published(
            "assignments.Assignment",
            chapter=chapter,
            due_date=timezone.now() + timedelta(days=1),
        )
        baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=student,
            score=None,
            started_at=timezone.now(),
            submitted_at=None,
        )

        assert get_tutor_quick_stats(tutor=tutor)["pending_submission_count"] == 0

    def test_get_tutor_courses_annotations(self, course, tutor, student):
        chapter, _ = self.make_chapter_with_lessons(course, 1, 3)
        assignment = make_published(
            "assignments.Assignment",
            chapter=chapter,
            due_date=timezone.now() + timedelta(days=1),
        )
        baker.make(
            "assignments.Submission",
            assignment=assignment,
            student=student,
            score=None,
            submitted_at=timezone.now(),
        )

        result = list(get_tutor_courses(tutor=tutor, query=Course.objects.all()))

        assert len(result) == 1
        assert result[0].students_count == 1
        assert result[0].chapters_count == 1
        assert result[0].lessons_count == 3
        assert result[0].pending_submission_count == 1

    def test_mark_lesson_completed_sets_timestamp(self, course, student):
        _, lessons = self.make_chapter_with_lessons(course, 1, 1)

        progress = LessonProgress.objects.create(
            student=student, lesson=lessons[0], is_completed=False
        )
        assert progress.complete_at is None

        progress = mark_lesson_completed(student, lessons[0])

        assert progress.is_completed is True
        assert progress.complete_at is not None
        assert LessonProgress.objects.filter(lesson=lessons[0]).count() == 1
