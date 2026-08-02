from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.permissions import (
    IsCourseMember,
    IsCourseMemberOrTutorWrite,
    IsCourseTutor,
    IsRelatedCourseMember,
    IsRelatedCourseTutor,
    IsStudentOrTutor,
    IsTutor,
)

from .models import Chapter, Comment, Course, LearningResource, Lesson
from .serializers import (
    ChapterSerializer,
    ChapterStatSerializer,
    CommentSerializer,
    CourseDetailSerializer,
    CourseOverviewSerializer,
    CourseTreeSerializer,
    LessonDetailSerializer,
    LessonSerializer,
    ResourceSerializer,
    StudentCourseSerializer,
    StudentQuickStatsSerializer,
    TutorCourseDetailSerializer,
    TutorCourseSerializer,
    TutorCourseStatsSerializer,
    TutorQuickStatsSerializer,
)
from .services import (
    get_chapter_stats,
    get_course_overview,
    get_course_tree,
    get_course_tutor_stats,
    get_courses_with_progress,
    get_quick_stats,
    get_tutor_courses,
    get_tutor_quick_stats,
    mark_lesson_completed,
    toggle_comment_right,
)


class CourseView(
    viewsets.ViewSet,
    generics.ListAPIView,
    generics.RetrieveAPIView,
):
    queryset = Course.objects.filter(is_active=True)

    def get_permissions(self):
        if self.action == "tutor_stats":
            return [IsTutor(), IsCourseTutor()]
        return [IsStudentOrTutor(), IsCourseMember()]

    def get_queryset(self):
        query = super().get_queryset()
        user = self.request.user

        if self.action == "retrieve":
            query = query.select_related("subject", "grade", "tutor__tutorprofile")

        if user.is_tutor:
            return get_tutor_courses(tutor=user, query=query)
        if user.is_student:
            return get_courses_with_progress(student=user, query=query)
        return query

    def get_serializer_class(self):
        user = self.request.user
        is_tutor = user.is_authenticated and user.is_tutor

        if self.action == "retrieve":
            return TutorCourseDetailSerializer if is_tutor else CourseDetailSerializer
        return TutorCourseSerializer if is_tutor else StudentCourseSerializer

    @action(methods=["get"], url_path="tree", detail=True)
    def get_tree(self, request, pk):
        self.get_object()
        course = get_course_tree(
            course_id=pk, student=request.user, include_drafts=request.user.is_tutor
        )
        return Response(
            CourseTreeSerializer(course, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["get"], url_path="overview", detail=True)
    def course_overview(self, request, pk):
        data = get_course_overview(
            course=self.get_object(),
            student=request.user,
            include_drafts=request.user.is_tutor,
        )
        return Response(
            CourseOverviewSerializer(data, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["get"], url_path="stats", detail=True)
    def tutor_stats(self, request, pk):
        """Thống kê khóa học dành cho gia sư phụ trách."""
        data = get_course_tutor_stats(course=self.get_object())
        return Response(
            TutorCourseStatsSerializer(
                data, context=self.get_serializer_context()
            ).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["get"], url_path="chapter-stats", detail=True)
    def chapter_stat(self, request, pk):
        data = get_chapter_stats(
            course=self.get_object(),
            student=request.user,
            include_drafts=request.user.is_tutor,
        )
        return Response(
            ChapterStatSerializer(
                data, many=True, context=self.get_serializer_context()
            ).data,
            status=status.HTTP_200_OK,
        )


class QuickStatsView(generics.GenericAPIView):
    permission_classes = [IsStudentOrTutor]
    serializer_class = StudentQuickStatsSerializer

    def get(self, request):
        user = request.user

        if user.is_tutor:
            data = get_tutor_quick_stats(tutor=user)
            serializer_class = TutorQuickStatsSerializer
        else:
            data = get_quick_stats(student=user)
            serializer_class = StudentQuickStatsSerializer

        return Response(
            serializer_class(data, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )


class LessonView(
    viewsets.ViewSet,
    generics.RetrieveAPIView,
    generics.CreateAPIView,
    generics.UpdateAPIView,
    generics.DestroyAPIView,
):
    queryset = Lesson.objects.filter(is_active=True)
    write_parent_lookup = ("chapter", Chapter)

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsTutor(), IsRelatedCourseTutor(), IsCourseTutor()]
        return [IsStudentOrTutor(), IsCourseMember()]

    def get_queryset(self):
        query = super().get_queryset()
        if self.request.user.is_student:
            query = query.filter(
                published_at__isnull=False, chapter__published_at__isnull=False
            )
        if self.action == "retrieve":
            return query.prefetch_related("resources")
        return query

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return LessonSerializer
        if self.action == "get_comments":
            return CommentSerializer
        return LessonDetailSerializer

    @action(methods=["post"], url_path="complete", detail=True)
    def mark_complete(self, request, pk):
        progress = mark_lesson_completed(student=request.user, lesson=self.get_object())
        return Response(
            {
                "lesson_id": progress.lesson_id,
                "is_completed": progress.is_completed,
                "complete_at": progress.complete_at,
            },
            status=status.HTTP_200_OK,
        )

    @action(methods=["get", "post"], url_path="comments", detail=True)
    def get_comments(self, request, pk):
        lesson = self.get_object()

        if request.method == "POST":
            # created_by do serializer tự gán từ context request, client không gửi lên.
            serializer = self.get_serializer(data={**request.data, "lesson": lesson.id})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        comments = (
            lesson.comments.filter(is_active=True)
            .select_related("created_by")
            .order_by("created_at")
        )
        return Response(
            self.get_serializer(comments, many=True).data, status=status.HTTP_200_OK
        )


class CommentView(viewsets.ViewSet, generics.GenericAPIView):
    queryset = Comment.objects.filter(is_active=True)
    serializer_class = CommentSerializer
    permission_classes = [IsCourseTutor]

    @action(methods=["post"], url_path="toggle-mark-right", detail=True)
    def toggle_right(self, request, pk):
        comment = toggle_comment_right(comment=self.get_object(), user=request.user)
        return Response(self.get_serializer(comment).data, status=status.HTTP_200_OK)


class ChapterView(
    viewsets.ViewSet,
    generics.CreateAPIView,
    generics.UpdateAPIView,
    generics.DestroyAPIView,
):
    queryset = Chapter.objects.filter(is_active=True)
    serializer_class = ChapterSerializer
    write_parent_lookup = ("course", Course)
    permission_classes = [IsTutor, IsRelatedCourseTutor, IsCourseTutor]


class ResourceView(
    viewsets.ViewSet,
    generics.ListAPIView,
    generics.CreateAPIView,
    generics.UpdateAPIView,
    generics.DestroyAPIView,
):
    queryset = LearningResource.objects.filter(is_active=True)
    serializer_class = ResourceSerializer
    read_parent_lookup = ("lesson", Lesson)
    write_parent_lookup = ("lesson", Lesson)
    permission_classes = [
        IsStudentOrTutor,
        IsRelatedCourseMember,
        IsRelatedCourseTutor,
        IsCourseMemberOrTutorWrite,
    ]

    def list(self, request, *args, **kwargs):
        # Bắt buộc chỉ rõ bài học để permission có căn cứ chặn trước khi truy vấn.
        lesson_id = request.query_params.get("lesson", "")
        if not lesson_id.isdigit():
            raise ValidationError(
                {"lesson": "Bắt buộc truyền ?lesson=<id> để lấy tài nguyên bài học."}
            )
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        query = super().get_queryset().select_related("lesson__chapter__course")
        if self.request.user.is_student:
            query = query.filter(
                published_at__isnull=False,
                lesson__published_at__isnull=False,
                lesson__chapter__published_at__isnull=False,
            )
        if self.action == "list":
            query = query.filter(lesson_id=self.request.query_params.get("lesson"))
        return query
