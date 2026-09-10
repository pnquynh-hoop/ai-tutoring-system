from rest_framework.permissions import SAFE_METHODS, BasePermission
from assignments.models import Assignment, Question, Submission
from courses.models import (
    Chapter,
    Comment,
    Course,
    Enrollment,
    LearningResource,
    Lesson,
)

def resolve_course(obj):
    if isinstance(obj, Course):
        return obj
    if isinstance(obj, Chapter):
        return obj.course
    if isinstance(obj, Lesson):
        return obj.chapter.course
    if isinstance(obj, (Comment, LearningResource)):
        return obj.lesson.chapter.course
    if isinstance(obj, Assignment):
        return obj.chapter.course
    if isinstance(obj, (Question, Submission)):
        return obj.assignment.chapter.course
    return None


def is_enrolled(user, course):
    if course is None or not user.is_authenticated:
        return False
    return Enrollment.objects.filter(
        course=course, student=user, is_active=True
    ).exists()


def is_course_tutor(user, course):
    if course is None or not user.is_authenticated:
        return False
    return course.tutor_id == user.id


def is_course_member(user, course):
    return is_course_tutor(user, course) or is_enrolled(user, course)


class IsStudent(BasePermission):
    message = "Chỉ học sinh mới được thực hiện thao tác này."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_student)


class IsTutor(BasePermission):
    message = "Chỉ gia sư mới được thực hiện thao tác này."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_tutor)


class IsStudentOrTutor(BasePermission):
    message = "Tài khoản chưa không thuộc bất kỳ nhóm người dùng nào trong hệ thống."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_student or user.is_tutor)
        )


class IsCourseMember(BasePermission):
    message = "Bạn không có quyền truy cập nội dung của khóa học này."

    def has_object_permission(self, request, view, obj):
        return is_course_member(request.user, resolve_course(obj))


class IsCourseTutor(BasePermission):
    message = "Chỉ gia sư phụ trách khóa học mới được chỉnh sửa nội dung này."

    def has_object_permission(self, request, view, obj):
        return is_course_tutor(request.user, resolve_course(obj))


class IsEnrolledStudent(BasePermission):
    message = "Bạn chưa ghi danh khóa học này."

    def has_object_permission(self, request, view, obj):
        return is_enrolled(request.user, resolve_course(obj))


class IsCourseMemberOrTutorWrite(BasePermission):
    message = "Bạn không có quyền thao tác trên nội dung của khóa học này."

    def has_object_permission(self, request, view, obj):
        course = resolve_course(obj)
        if request.method in SAFE_METHODS:
            return is_course_member(request.user, course)
        return is_course_tutor(request.user, course)


class IsSubmissionOwnerOrCourseTutor(BasePermission):
    message = "Bạn chỉ xem được bài nộp của chính mình."

    def has_object_permission(self, request, view, obj):
        if obj.student_id == request.user.id:
            return True
        return is_course_tutor(request.user, resolve_course(obj))
