import pytest
from model_bakery import baker

from core.testing import make_published

from courses.models import Course, LessonProgress
from courses.services import get_courses_with_progress


@pytest.mark.django_db
class TestCourseServices:
    @pytest.fixture
    def student(self):
        return baker.make("accounts.User")

    @pytest.fixture
    def tutor(self):
        return baker.make("accounts.User")

    @pytest.fixture
    def course(self, tutor):
        return baker.make("courses.Course", tutor=tutor)

    @pytest.fixture
    def chapter(self, course):
        return make_published("courses.Chapter", course=course)

    @pytest.fixture
    def course_query(self):
        return Course.objects.all()

    def enroll(self, course, student):
        return baker.make("courses.Enrollment", course=course, student=student)

    def make_lesson(self, chapter):
        return make_published("courses.Lesson", chapter=chapter)

    def test_course_without_lessons_returns_zero_progress(
        self, student, course, course_query
    ):
        self.enroll(course, student)

        result = list(get_courses_with_progress(student, course_query))

        assert len(result) == 1
        assert result[0].progress == 0

    def test_course_with_lessons_without_progress(
        self, student, course, course_query, chapter
    ):
        self.enroll(course, student)
        self.make_lesson(chapter)
        self.make_lesson(chapter)

        result = list(get_courses_with_progress(student, course_query))

        assert result[0].progress == 0

    def test_partial_completion_progress(self, student, course, course_query, chapter):
        self.enroll(course, student)
        lesson1 = self.make_lesson(chapter)
        lesson2 = self.make_lesson(chapter)
        self.make_lesson(chapter)
        self.make_lesson(chapter)
        baker.make(LessonProgress, student=student, lesson=lesson1, is_completed=True)
        baker.make(LessonProgress, student=student, lesson=lesson2, is_completed=True)

        result = list(get_courses_with_progress(student, course_query))

        assert result[0].progress == 50.0

    def test_full_completion_progress(self, student, course, course_query, chapter):
        self.enroll(course, student)
        lesson1 = self.make_lesson(chapter)
        lesson2 = self.make_lesson(chapter)
        baker.make(LessonProgress, student=student, lesson=lesson1, is_completed=True)
        baker.make(LessonProgress, student=student, lesson=lesson2, is_completed=True)

        result = list(get_courses_with_progress(student, course_query))

        assert result[0].progress == 100.0

    def test_incomplete_lesson_not_counted(
        self, student, course, course_query, chapter
    ):
        self.enroll(course, student)
        lesson1 = self.make_lesson(chapter)
        self.make_lesson(chapter)
        baker.make(LessonProgress, student=student, lesson=lesson1, is_completed=False)

        result = list(get_courses_with_progress(student, course_query))

        assert result[0].progress == 0

    def test_only_returns_enrolled_courses(self, student, course, tutor, course_query):
        baker.make("courses.Course", tutor=tutor)
        self.enroll(course, student)

        result = list(get_courses_with_progress(student, course_query))

        assert len(result) == 1
        assert result[0].id == course.id

    def test_progress_isolated_per_student(
        self, student, course, course_query, chapter
    ):
        other_student = baker.make("accounts.User")
        self.enroll(course, student)
        self.enroll(course, other_student)
        lesson1 = self.make_lesson(chapter)
        self.make_lesson(chapter)
        baker.make(
            LessonProgress, student=other_student, lesson=lesson1, is_completed=True
        )

        result = list(get_courses_with_progress(student, course_query))

        assert result[0].progress == 0

    def test_respects_prefiltered_query(self, student, tutor):
        subject_a = baker.make("academics.Subject")
        subject_b = baker.make("academics.Subject")
        course_a = baker.make("courses.Course", tutor=tutor, subject=subject_a)
        course_b = baker.make("courses.Course", tutor=tutor, subject=subject_b)
        self.enroll(course_a, student)
        self.enroll(course_b, student)

        filtered_query = Course.objects.filter(subject=subject_a)
        result = list(get_courses_with_progress(student, filtered_query))

        assert len(result) == 1
        assert result[0].id == course_a.id

    def test_no_n_plus_one_query(
        self, student, tutor, course_query, django_assert_num_queries
    ):
        for i in range(5):
            course = baker.make("courses.Course", tutor=tutor, name=f"Course {i}")
            self.enroll(course, student)
            chapter = make_published("courses.Chapter", course=course)
            lesson = self.make_lesson(chapter)
            baker.make(
                LessonProgress, student=student, lesson=lesson, is_completed=True
            )

        with django_assert_num_queries(1):
            result = list(get_courses_with_progress(student, course_query))

        assert len(result) == 5

    def test_multiple_courses_calculated_independently(
        self, student, tutor, course_query
    ):
        course_a = baker.make("courses.Course", tutor=tutor)
        course_b = baker.make("courses.Course", tutor=tutor)
        self.enroll(course_a, student)
        self.enroll(course_b, student)

        chapter_a = make_published("courses.Chapter", course=course_a)
        chapter_b = make_published("courses.Chapter", course=course_b)

        lesson_a1 = self.make_lesson(chapter_a)
        self.make_lesson(chapter_a)

        lesson_b1 = self.make_lesson(chapter_b)
        lesson_b2 = self.make_lesson(chapter_b)

        baker.make(LessonProgress, student=student, lesson=lesson_a1, is_completed=True)
        baker.make(LessonProgress, student=student, lesson=lesson_b1, is_completed=True)
        baker.make(LessonProgress, student=student, lesson=lesson_b2, is_completed=True)

        result = get_courses_with_progress(student, course_query)
        progress_map = {c.id: c.progress for c in result}

        assert progress_map[course_a.id] == 50.0
        assert progress_map[course_b.id] == 100.0

    def test_empty_query_returns_empty_list(self, student):
        empty_query = Course.objects.none()

        result = list(get_courses_with_progress(student, empty_query))

        assert result == []
