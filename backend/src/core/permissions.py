from django.core.exceptions import ValidationError as DjangoValidationError
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

"""
    Toàn bộ việc quyết định "user có được thực hiện hành động này không" nằm ở đây.

    Quyền truy cập học liệu luôn được quy chiếu về Course chứa nó: học sinh phải có
    Enrollment đang hoạt động, gia sư phải là tutor của khóa học. View và queryset
    không tự kiểm tra quyền nữa - tới được view nghĩa là đã qua permission.
"""


def resolve_course(obj):
    """Truy ngược một object bất kỳ trong cây học liệu về Course chứa nó.

    Model không có trong danh sách dưới sẽ trả về None, tức là mặc định bị từ
    chối quyền. Thêm model mới đi qua permission thì phải thêm nhánh ở đây.
    """
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


def is_enrolled(user, course) -> bool:
    """Kiểm tra học sinh có Enrollment đang hoạt động trong khóa học không."""
    if course is None or not user.is_authenticated:
        return False
    return Enrollment.objects.filter(
        course=course, student=user, is_active=True
    ).exists()


def is_course_tutor(user, course) -> bool:
    if course is None or not user.is_authenticated:
        return False
    return course.tutor_id == user.id


def is_course_member(user, course) -> bool:
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
    """Cấp object: chỉ học sinh đã ghi danh, gia sư phụ trách mới xem được."""

    message = "Bạn không có quyền truy cập nội dung của khóa học này."

    def has_object_permission(self, request, view, obj):
        return is_course_member(request.user, resolve_course(obj))


class IsCourseTutor(BasePermission):
    """Cấp object: chỉ gia sư phụ trách khóa học mới được chỉnh sửa."""

    message = "Chỉ gia sư phụ trách khóa học mới được chỉnh sửa nội dung này."

    def has_object_permission(self, request, view, obj):
        return is_course_tutor(request.user, resolve_course(obj))


class IsCourseMemberOrTutorWrite(BasePermission):
    """Cấp object: đọc cần là thành viên khóa học, ghi cần là gia sư phụ trách."""

    message = "Bạn không có quyền thao tác trên nội dung của khóa học này."

    def has_object_permission(self, request, view, obj):
        course = resolve_course(obj)
        if request.method in SAFE_METHODS:
            return is_course_member(request.user, course)
        return is_course_tutor(request.user, course)


class IsSubmissionOwnerOrCourseTutor(BasePermission):
    """Cấp object: chỉ chủ nhân bài nộp hoặc gia sư phụ trách mới xem được."""

    message = "Bạn chỉ xem được bài nộp của chính mình."

    def has_object_permission(self, request, view, obj):
        if obj.student_id == request.user.id:
            return True
        return is_course_tutor(request.user, resolve_course(obj))


def _resolve_parent(view, attr, source):
    """Lấy object cha được nêu trong chính request (payload hoặc query param).

    View khai báo ``read_parent_lookup`` / ``write_parent_lookup`` dạng
    ``("tên_field", Model)``. Trả về None khi request không nêu object cha -
    khi đó serializer sẽ trả 400 cho đúng ngữ nghĩa thay vì 403.
    """
    lookup = getattr(view, attr, None)
    if not lookup:
        return None

    field, model = lookup
    raw_id = source.get(field)
    if raw_id in (None, ""):
        return None

    try:
        return model.objects.filter(pk=raw_id).first()
    except (ValueError, TypeError, DjangoValidationError):
        return None


class RelatedCoursePermission(BasePermission):
    """Chặn dựa trên khóa học suy ra từ chính request, trước khi handler chạy.

    Nhờ vậy các endpoint tạo mới (chưa có object để kiểm tra cấp object) vẫn được
    chặn ở tầng permission chứ không phải trong serializer hay view.
    """

    def check_course(self, user, course) -> bool:
        raise NotImplementedError

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            parent = _resolve_parent(view, "read_parent_lookup", request.query_params)
        else:
            parent = _resolve_parent(view, "write_parent_lookup", request.data)

        if parent is None:
            return True

        return self.check_course(request.user, resolve_course(parent))


class IsRelatedCourseMember(RelatedCoursePermission):
    message = "Bạn không có quyền truy cập nội dung của khóa học này."

    def check_course(self, user, course) -> bool:
        return is_course_member(user, course)


class IsRelatedCourseTutor(RelatedCoursePermission):
    """Chỉ ràng buộc thao tác ghi; thao tác đọc để IsRelatedCourseMember quyết định."""

    message = "Chỉ gia sư phụ trách khóa học mới được thực hiện thao tác này."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return super().has_permission(request, view)

    def check_course(self, user, course) -> bool:
        return is_course_tutor(user, course)
