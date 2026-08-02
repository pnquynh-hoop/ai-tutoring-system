from django.db.models import Count
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from assignments.models import Assignment, Question, Submission
from assignments.serializers import (
    AssignmentDetailSerializer,
    AssignmentWriteSerializer,
    AttemptSerializer,
    GradeSubmissionSerializer,
    QuestionSerializer,
    QuestionWriteSerializer,
    StartAttemptSerializer,
    SubmissionDetailSerializer,
    SubmissionSerializer,
    SubmitAssignmentSerializer,
)
from core.permissions import (
    IsCourseMember,
    IsCourseTutor,
    IsRelatedCourseTutor,
    IsStudent,
    IsStudentOrTutor,
    IsSubmissionOwnerOrCourseTutor,
    IsTutor,
)
from courses.models import Chapter

WRITE_ACTIONS = ("create", "update", "partial_update", "destroy")


class AssignmentView(
    viewsets.ViewSet,
    generics.RetrieveAPIView,
    generics.CreateAPIView,
    generics.UpdateAPIView,
    generics.DestroyAPIView,
):
    queryset = Assignment.objects.filter(is_active=True)
    write_parent_lookup = ("chapter", Chapter)

    def get_permissions(self):
        if self.action in WRITE_ACTIONS:
            return [IsTutor(), IsRelatedCourseTutor(), IsCourseTutor()]
        if self.action in ("start", "submit"):
            return [IsStudent(), IsCourseMember()]
        return [IsStudentOrTutor, IsCourseMember]

    def get_queryset(self):
        query = super().get_queryset().select_related("chapter__course")
        if self.request.user.is_student:
            query = query.filter(
                published_at__isnull=False, chapter__published_at__isnull=False
            )
        if self.action == "retrieve":
            query = query.annotate(total_questions=Count("questions"))
        return query

    def get_serializer_class(self):
        if self.action in WRITE_ACTIONS:
            return AssignmentWriteSerializer
        if self.action == "get_questions":
            return QuestionSerializer
        if self.action == "submit":
            return SubmitAssignmentSerializer
        if self.action == "start":
            return AttemptSerializer
        return AssignmentDetailSerializer

    @action(methods=["get"], url_path="questions", detail=True)
    def get_questions(self, request, pk):
        questions = self.get_object().questions.prefetch_related("answers").all()
        return Response(
            self.get_serializer(questions, many=True).data, status=status.HTTP_200_OK
        )

    @action(methods=["post"], url_path="start", detail=True)
    def start(self, request, pk):
        serializer = StartAttemptSerializer(
            data={},
            context={"assignment": self.get_object(), "student": request.user},
        )
        serializer.is_valid(raise_exception=True)
        attempt = serializer.save()

        return Response(AttemptSerializer(attempt).data, status=status.HTTP_200_OK)

    @action(methods=["post"], url_path="submit", detail=True)
    def submit(self, request, pk):
        serializer = self.get_serializer(
            data=request.data,
            context={
                **self.get_serializer_context(),
                "assignment": self.get_object(),
                "student": request.user,
            },
        )
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()

        return Response(
            SubmissionSerializer(
                submission, context=self.get_serializer_context()
            ).data,
            status=status.HTTP_201_CREATED,
        )


class QuestionView(
    viewsets.ViewSet,
    generics.ListAPIView,
    generics.RetrieveAPIView,
    generics.CreateAPIView,
    generics.UpdateAPIView,
    generics.DestroyAPIView,
):
    """Soạn câu hỏi cho bài tập - chỉ gia sư phụ trách khóa học."""

    queryset = Question.objects.prefetch_related("answers")
    serializer_class = QuestionWriteSerializer
    permission_classes = [IsTutor, IsRelatedCourseTutor, IsCourseTutor]
    read_parent_lookup = ("assignment", Assignment)
    write_parent_lookup = ("assignment", Assignment)

    def list(self, request, *args, **kwargs):
        # Bắt buộc chỉ rõ bài tập để permission có căn cứ chặn trước khi truy vấn.
        assignment_id = request.query_params.get("assignment", "")
        if not assignment_id.isdigit():
            raise ValidationError(
                {
                    "assignment": "Bắt buộc truyền ?assignment=<id> để lấy danh sách câu hỏi."
                }
            )
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        query = super().get_queryset()
        if self.action == "list":
            query = query.filter(
                assignment_id=self.request.query_params.get("assignment")
            )
        return query


class SubmissionView(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    queryset = Submission.objects.filter(submitted_at__isnull=False)
    serializer_class = SubmissionSerializer
    permission_classes = [IsStudentOrTutor, IsSubmissionOwnerOrCourseTutor]

    def get_permissions(self):
        if self.action == "grade":
            return [IsTutor(), IsCourseTutor()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "grade":
            return GradeSubmissionSerializer
        if self.action == "retrieve":
            return SubmissionDetailSerializer
        return SubmissionSerializer

    def get_queryset(self):
        """Học sinh xem bài của mình, gia sư xem bài nộp trong khóa mình phụ trách."""
        user = self.request.user
        query = (
            super()
            .get_queryset()
            .select_related("assignment__chapter__course", "student")
        )

        if user.is_tutor:
            query = query.filter(assignment__chapter__course__tutor=user)
            assignment_id = self.request.query_params.get("assignment")
            if assignment_id:
                query = query.filter(assignment_id=assignment_id)
            course_id = self.request.query_params.get("course")
            if course_id:
                query = query.filter(assignment__chapter__course_id=course_id)
        else:
            query = query.filter(student=user)

        if self.action == "retrieve":
            query = query.prefetch_related("stu_answers__question__answers")

        return query.order_by("-submitted_at")

    @action(methods=["patch"], url_path="grade", detail=True)
    def grade(self, request, pk):
        serializer = self.get_serializer(self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)
        graded = serializer.save()

        return Response(
            SubmissionDetailSerializer(
                graded, context=self.get_serializer_context()
            ).data,
            status=status.HTTP_200_OK,
        )
