from multiprocessing import context
from rest_framework import status, permissions, viewsets, generics, views
from yaml import serialize
from .services import get_course_tree, get_courses_with_progress, get_quick_stats
from .models import Course, Lesson, LessonProgress
from .serializers import (
    CommentSerializer,
    CourseDetailSerializer,
    CourseTreeSerializer,
    LessonDetailSerializer,
    LessonProgressSerializer,
    QuickStatsSerializer,
    StudentCourseSerializer,
)
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema


class CourseView(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    queryset = Course.objects.filter(is_active=True)

    def get_queryset(self):
        query = super().get_queryset()

        user = self.request.user
        if user.is_authenticated:
            if user.is_student:
                query = get_courses_with_progress(student=user, query=query)
            elif user.is_tutor:
                query = query.filter(tutors=user)
        # print(query.query)
        return query

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CourseDetailSerializer
        return StudentCourseSerializer

    @action(methods=["get"], url_path="tree", detail=True)
    def get_tree(self, request, pk):
        course = get_course_tree(course_id=pk, student=request.user)
        return Response(CourseTreeSerializer(course).data, status=status.HTTP_200_OK)


@extend_schema(responses=QuickStatsSerializer)
class QuickStatsView(views.APIView):
    def get(self, request):
        student = self.request.user
        stat_data = get_quick_stats(student)
        return Response(QuickStatsSerializer(stat_data).data, status=status.HTTP_200_OK)


class LessonView(viewsets.ViewSet, generics.RetrieveAPIView):
    serializer_class = LessonDetailSerializer
    queryset = Lesson.objects.filter(is_active=True)

    @action(methods=["post"], url_path="complete", detail=True)
    def mark_complete(self, request, pk):
        progress, _ = LessonProgress.objects.update_or_create(
            student=request.user,
            lesson=self.get_object(),
            defaults={
                "is_completed": True,
            },
        )
        return Response(
            {
                "lesson_id": progress.lesson_id,
                "is_completed": progress.is_completed,
            },
            status=status.HTTP_200_OK,
        )
    
    @action(methods=["get", "post"], url_path="comments", detail=True)
    def get_comments(self, request, pk):
        if request.method == "POST":
            s = CommentSerializer(data={
                **request.data,
                "lesson": pk,
            }, context={"request": request})
            s.is_valid(raise_exception=True)
            c = s.save()
            return Response(CommentSerializer(c).data, status=status.HTTP_200_OK)

        comments = self.get_object().comments.filter(is_active=True).all()
        return Response(CommentSerializer(comments, many=True).data, status=status.HTTP_200_OK)

class CommentView(viewsets.ViewSet):
    
    @action(methods=["post"], url_path="toggle-mark-right", detail=True)
    def toggle_right(self, request, pk):
        ...