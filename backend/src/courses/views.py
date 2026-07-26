from rest_framework import status, viewsets, generics, views
from assignments.models import Assignment, Submission
from .services import get_course_tree, get_courses_with_progress, get_quick_stats
from .models import Comment, Course, Lesson, LessonProgress
from .serializers import (
    ChapterStatSerializer,
    CommentSerializer,
    CourseDetailSerializer,
    CourseOverviewSerializer,
    CourseTreeSerializer,
    LessonDetailSerializer,
    QuickStatsSerializer,
    StudentCourseSerializer,
)
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models.functions import Round
from django.db.models import Avg

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

    @action(methods=["get"], url_path="overview", detail=True)
    def course_overview(self, request, pk):
        course = self.get_object()
        student = request.user

        lessons = Lesson.objects.filter(chapter__course=course)
        total_lessons = lessons.count()
        completed_lessons = LessonProgress.objects.filter(
            lesson__in=lessons, student=student, is_completed=True
        ).count()
        progress_percent = (
            round(completed_lessons / total_lessons * 100, 1) if total_lessons else 0
        )

        assignment_ids = list(
            Assignment.objects.filter(chapter__course=course).values_list(
                "id", flat=True
            )
        )

        submitted_ids = set(
            Submission.objects.filter(
                assignment_id__in=assignment_ids, student=student
            ).values_list("assignment_id", flat=True)
        )

        pending_assignments_count = Assignment.objects.filter(
            id__in=set(assignment_ids) - submitted_ids,
            due_date__gte=timezone.now(),
        ).count()

        avg_result = Submission.objects.filter(
            assignment_id__in=assignment_ids, student=student
        ).aggregate(avg=Round(Avg("score"), 2))
        average_score = avg_result["avg"]

        data = {
            "progress": {
                "total_lessons": total_lessons,
                "completed_lessons": completed_lessons,
                "progress_percent": progress_percent,
            },
            "average_score": average_score,
            "pending_assignments_count": pending_assignments_count,
        }
        return Response(CourseOverviewSerializer(data).data, status=status.HTTP_200_OK)

    @action(methods=["get"], url_path="chapter-stats", detail=True)
    def chapter_stat(self, request, pk):
        course = self.get_object()
        student = request.user

        result = []

        chapters = course.chapters.order_by("order").prefetch_related("lessons")

        for chapter in chapters:
            lessons = list(chapter.lessons.all())

            total_lessons = len(lessons)

            completed_lessons = LessonProgress.objects.filter(
                lesson__in=lessons,
                student=student,
                is_completed=True,
            ).count()

            first_incomplete = next(
                (
                    lesson.id
                    for lesson in lessons
                    if not LessonProgress.objects.filter(
                        lesson=lesson,
                        student=student,
                        is_completed=True,
                    ).exists()
                ),
                None,
            )

            assignments = Assignment.objects.filter(chapter=chapter)

            submitted = Submission.objects.filter(
                assignment__in=assignments,
                student=student,
            )

            pending_assignments = assignments.exclude(
                id__in=submitted.values_list("assignment_id", flat=True)
            ).count()

            score = submitted.aggregate(avg=Round(Avg("score"), 2))["avg"]

            result.append(
                {
                    "id": chapter.id,
                    "title": chapter.title,
                    "order": chapter.order,
                    "total_lessons": total_lessons,
                    "completed_lessons": completed_lessons,
                    "score": score,
                    "pending_assignments": pending_assignments,
                    "first_incomplete_lesson_id": first_incomplete,
                }
            )

        return Response(
            ChapterStatSerializer(result, many=True).data,
            status=status.HTTP_200_OK,
        )

@extend_schema(responses=QuickStatsSerializer)
class QuickStatsView(views.APIView):
    def get(self, request):
        student = request.user
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
            s = CommentSerializer(
                data={
                    **request.data,
                    "lesson": pk,
                },
                context={"request": request},
            )
            s.is_valid(raise_exception=True)
            c = s.save()
            return Response(CommentSerializer(c).data, status=status.HTTP_200_OK)

        comments = self.get_object().comments.filter(is_active=True).all()
        return Response(
            CommentSerializer(comments, many=True).data, status=status.HTTP_200_OK
        )


class CommentView(viewsets.ViewSet):
    @action(methods=["patch"], url_path="toggle-mark-right", detail=True)
    def toggle_right(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)

        comment.is_right = not comment.is_right

        if comment.is_right:
            comment.marked_right_by = request.user
            comment.marked_right_at = timezone.now()
        else:
            comment.marked_right_by = None
            comment.marked_right_at = None

        comment.save()

        return Response({"message": "Cập nhật thành công"}, status=status.HTTP_200_OK)