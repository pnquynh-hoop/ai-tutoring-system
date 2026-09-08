import logging
from django.db.models import Prefetch
from rest_framework import generics, status, viewsets, views
from AI.tasks import ingest_resource_task
from rest_framework.decorators import action
from rest_framework.response import Response
from core.paginators import CommentPaginator, ItemPaginator
from core.permissions import (
    IsCourseMember,
    IsCourseTutor,
    IsStudent,
    IsStudentOrTutor,
    IsTutor,
)
from .models import Chapter, Comment, Course, LearningResource, Lesson
from .serializers import (
    ChapterSerializer,
    ChapterStatSerializer,
    CommentSerializer,
    StudentDetailCourseSerializer,
    CourseOverviewSerializer,
    CourseTreeSerializer,
    IngestResourceSerializer,
    LearningResourceSerializer,
    TutorLearningResourceSerializer,
    LessonDetailSerializer,
    LessonSerializer,
    PublishChapterSerializer,
    PublishLessonSerializer,
    PublishResourceSerializer,
    ResourceSerializer,
    StudentListCourseSerializer,
    StudentQuickStatsSerializer,
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

logger = logging.getLogger(__name__)


class CourseView(
    viewsets.ViewSet,
    generics.ListAPIView,
    generics.RetrieveAPIView,
):
    queryset = Course.objects.filter(is_active=True).order_by("id")
    pagination_class = ItemPaginator

    def get_permissions(self):
        if self.action == "tutor_stats":
            return [IsTutor(), IsCourseTutor()]
        if self.action in ["retrieve", "course_overview", "chapter_stat"]:
            return [IsStudent(), IsCourseMember()]
        return [IsStudentOrTutor(), IsCourseMember()]

    def get_queryset(self):
        query = super().get_queryset()
        user = self.request.user

        if self.action == "list":
            if user.is_tutor:
                return get_tutor_courses(tutor=user, query=query)
            return get_courses_with_progress(student=user, query=query)

        if self.action == "retrieve":
            query = query.select_related("subject", "grade", "tutor__tutorprofile")
            return get_courses_with_progress(student=user, query=query)

        return query

    def get_serializer_class(self):
        if self.action == "retrieve":
            return StudentDetailCourseSerializer
        if self.request.user.is_authenticated and self.request.user.is_tutor:
            return TutorCourseSerializer
        return StudentListCourseSerializer

    @action(methods=["get"], url_path="tree", detail=True)
    def get_tree(self, request, pk):
        course = get_course_tree(
            course=self.get_object(),
            user=request.user,
            include_drafts=request.user.is_tutor,
        )
        return Response(
            CourseTreeSerializer(course).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["get"], url_path="overview", detail=True)
    def course_overview(self, request, pk):
        data_overview = get_course_overview(
            course=self.get_object(),
            student=request.user,
        )
        return Response(
            CourseOverviewSerializer(data_overview).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["get"], url_path="stats", detail=True)
    def tutor_stats(self, request, pk):
        data_stats = get_course_tutor_stats(course=self.get_object())
        return Response(
            TutorCourseStatsSerializer(data_stats).data,
            status=status.HTTP_200_OK,
        )

    @action(methods=["get"], url_path="chapter-stats", detail=True)
    def chapter_stat(self, request, pk):
        data_chapter_stats = get_chapter_stats(
            course=self.get_object(),
            student=request.user,
        )
        return Response(
            ChapterStatSerializer(data_chapter_stats, many=True).data,
            status=status.HTTP_200_OK,
        )


class QuickStatsView(views.APIView):
    permission_classes = [IsStudentOrTutor]

    def get(self, request):
        user = request.user

        if user.is_tutor:
            stats = get_tutor_quick_stats(tutor=user)
            serializer = TutorQuickStatsSerializer(stats)
        else:
            stats = get_quick_stats(student=user)
            serializer = StudentQuickStatsSerializer(stats)

        return Response(
            serializer.data,
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

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "publish"]:
            return [IsTutor(), IsCourseTutor()]
        if self.action == "get_resources":
            return [IsTutor(), IsCourseTutor()]
        if self.action in ["retrieve", "mark_complete"]:
            return [IsStudent(), IsCourseMember()]
        return [IsStudentOrTutor(), IsCourseMember()]

    def get_queryset(self):
        query = super().get_queryset()
        if self.request.user.is_student:
            query = query.filter(
                published_at__isnull=False, chapter__published_at__isnull=False
            )
        if self.action == "retrieve":
            resources = LearningResource.objects.filter(
                is_active=True, published_at__isnull=False
            )
            return query.prefetch_related(Prefetch("resources", queryset=resources))
        return query

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return LessonSerializer
        if self.action == "get_comments":
            return CommentSerializer
        if self.action == "get_resources":
            return TutorLearningResourceSerializer
        return LessonDetailSerializer

    @action(methods=["get"], url_path="resources", detail=True)
    def get_resources(self, request, pk):
        resources = LearningResource.objects.filter(
            is_active=True, lesson=self.get_object()
        )
        return Response(
            self.get_serializer(resources, many=True).data, status=status.HTTP_200_OK
        )

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

    @action(methods=["post"], url_path="publish", detail=True)
    def publish(self, request, pk):
        lesson = self.get_object()
        serializer = PublishLessonSerializer(lesson, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["get", "post"], url_path="comments", detail=True)
    def get_comments(self, request, pk):
        lesson = self.get_object()

        if request.method == "POST":
            serializer = self.get_serializer(
                data={
                    "content": request.data.get("content"),
                    "parent": request.data.get("parent"),
                    "lesson": pk,
                }
            )
            serializer.is_valid(raise_exception=True)
            c = serializer.save()
            return Response(self.get_serializer(c).data, status=status.HTTP_201_CREATED)

        comments = (
            lesson.comments.filter(is_active=True)
            .select_related("created_by")
        )

        paginator = CommentPaginator()
        page = paginator.paginate_queryset(comments, request)
        if page is not None:
            return paginator.get_paginated_response(
                self.get_serializer(page, many=True).data
            )

        return Response(
            self.get_serializer(comments, many=True).data, status=status.HTTP_200_OK
        )


class CommentView(viewsets.ViewSet, generics.DestroyAPIView):
    queryset = Comment.objects.filter(is_active=True)
    serializer_class = CommentSerializer
    permission_classes = [IsTutor, IsCourseTutor]

    def perform_destroy(self, instance):
        instance.replies.update(is_active=False)
        instance.is_active = False
        instance.save(update_fields=["is_active"])

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
    permission_classes = [IsTutor, IsCourseTutor]

    @action(methods=["post"], url_path="publish", detail=True)
    def publish(self, request, pk):
        chapter = self.get_object()

        serializer = PublishChapterSerializer(chapter, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)


class ResourceView(
    viewsets.ViewSet,
    generics.CreateAPIView,
    generics.UpdateAPIView,
    generics.DestroyAPIView,
):

    queryset = LearningResource.objects.filter(is_active=True)
    serializer_class = ResourceSerializer
    permission_classes = [IsTutor, IsCourseTutor]

    def get_queryset(self):
        return super().get_queryset().select_related("lesson__chapter__course")

    @action(methods=["post"], url_path="publish", detail=True)
    def publish(self, request, pk):
        resource = self.get_object()

        serializer = PublishResourceSerializer(resource, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["post"], url_path="ingest", detail=True)
    def ingest(self, request, pk):
        resource = self.get_object()

        serializer = IngestResourceSerializer(resource, data={})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        try:
            ingest_resource_task.delay(resource.id)
        except Exception:
            logger.exception("Không đẩy được Resource ID %s vào hàng đợi", resource.id)
            resource.mark_rag_failed("Hàng đợi nạp đang không hoạt động.")
            return Response(
                {
                    "error": "Hàng đợi nạp tài liệu đang không hoạt động, vui lòng thử lại sau."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            TutorLearningResourceSerializer(resource).data,
            status=status.HTTP_202_ACCEPTED,
        )
