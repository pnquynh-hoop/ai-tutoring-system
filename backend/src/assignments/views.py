from django.db.models import Count, Prefetch
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from assignments.models import Assignment, Question, StudentAnswer, Submission
from assignments.serializers import (
    AssignmentDetailSerializer,
    AssignmentWriteSerializer,
    AttemptSerializer,
    DeleteAssignmentSerializer,
    DeleteQuestionSerializer,
    GradeSubmissionSerializer,
    PublishAssignmentSerializer,
    QuestionSerializer,
    QuestionWriteSerializer,
    SubmissionDetailSerializer,
    SubmissionSerializer,
    StartAttemptSerializer,
    SubmitAssignmentSerializer,
    TutorSubmissionDetailSerializer,
    TutorSubmissionSerializer,
)
from assignments.services import (
    grade_submission,
    save_answer_draft,
    start_attempt,
    submit_assignment,
)
from core.paginators import ItemPaginator
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

class AssignmentView(
    viewsets.ViewSet,
    generics.RetrieveAPIView,
    generics.CreateAPIView,
    generics.UpdateAPIView,
    generics.DestroyAPIView,
):
    queryset = Assignment.objects.filter(is_active=True).select_related(
        "chapter__course"
    )
    write_parent_lookup = ("chapter", Chapter)

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "publish"]:
            return [IsTutor(), IsRelatedCourseTutor(), IsCourseTutor()]
        if self.action in ("start", "submit", "save_draft"):
            return [IsStudent(), IsCourseMember()]
        return [IsStudentOrTutor(), IsCourseMember()]

    def get_queryset(self):
        query = super().get_queryset()
        if self.request.user.is_student:
            query = query.filter(
                published_at__isnull=False, chapter__published_at__isnull=False
            )
        if self.action == "retrieve":
            query = query.annotate(total_questions=Count("questions"))
        return query

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return AssignmentWriteSerializer
        if self.action == "get_questions":
            if self.request.user.is_tutor:
                return QuestionWriteSerializer
            return QuestionSerializer
        if self.action in ("submit", "save_draft"):
            return SubmitAssignmentSerializer
        if self.action == "start":
            return AttemptSerializer
        return AssignmentDetailSerializer

    def perform_destroy(self, instance):
        serializer = DeleteAssignmentSerializer(
            instance, data={}, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        instance.delete()

    @action(methods=["get"], url_path="questions", detail=True)
    def get_questions(self, request, pk):
        questions = self.get_object().questions.prefetch_related("answers").all()
        return Response(
            self.get_serializer(questions, many=True).data, status=status.HTTP_200_OK
        )

    @action(methods=["post"], url_path="publish", detail=True)
    def publish(self, request, pk):
        assignment = self.get_object()

        serializer = PublishAssignmentSerializer(assignment, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["post"], url_path="start", detail=True)
    def start(self, request, pk):
        assignment = self.get_object()

        serializer = StartAttemptSerializer(
            assignment, data={}, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)

        attempt = start_attempt(student=request.user, assignment=assignment)

        return Response(AttemptSerializer(attempt).data, status=status.HTTP_200_OK)

    @action(methods=["post"], url_path="save-draft", detail=True)
    def save_draft(self, request, pk):
        assignment = self.get_object()

        serializer = SubmitAssignmentSerializer(
            assignment, data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)

        attempt = save_answer_draft(
            student=request.user,
            assignment=assignment,
            answers=serializer.validated_data["answers"],
        )

        return Response(AttemptSerializer(attempt).data, status=status.HTTP_200_OK)

    @action(methods=["post"], url_path="submit", detail=True)
    def submit(self, request, pk):
        assignment = self.get_object()
        
        serializer = SubmitAssignmentSerializer(
            assignment, data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        
        submission = submit_assignment(
            student=request.user,
            assignment=assignment,
            answers=serializer.validated_data["answers"],
        )

        return Response(
            SubmissionSerializer(submission).data,
            status=status.HTTP_201_CREATED,
        )


class QuestionView(
    viewsets.ViewSet,
    generics.RetrieveAPIView,
    generics.CreateAPIView,
    generics.UpdateAPIView,
    generics.DestroyAPIView,
):
    queryset = Question.objects.prefetch_related("answers")
    serializer_class = QuestionWriteSerializer
    permission_classes = [IsTutor, IsRelatedCourseTutor, IsCourseTutor]
    write_parent_lookup = ("assignment", Assignment)

    def perform_destroy(self, instance):
        serializer = DeleteQuestionSerializer(
            instance, data={}, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        instance.delete()


class SubmissionView(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    queryset = Submission.objects.filter(submitted_at__isnull=False)
    serializer_class = SubmissionSerializer
    pagination_class = ItemPaginator

    def get_permissions(self):
        if self.action == "grade":
            return [IsTutor(), IsCourseTutor()]
        return [IsStudentOrTutor(), IsSubmissionOwnerOrCourseTutor()]

    def get_serializer_class(self):
        if self.action == "grade":
            return GradeSubmissionSerializer

        is_tutor = self.request.user.is_tutor
        if self.action == "retrieve":
            return (
                TutorSubmissionDetailSerializer
                if is_tutor
                else SubmissionDetailSerializer
            )
        return TutorSubmissionSerializer if is_tutor else SubmissionSerializer

    def get_int_query_param(self, param_name):
        raw_value = self.request.query_params.get(param_name)
        if raw_value is None or not raw_value.isdigit():
            return None
        return int(raw_value)

    def get_queryset(self):
        user = self.request.user
        query = super().get_queryset().select_related("assignment__chapter__course")

        if user.is_tutor:
            query = query.select_related("student")
            query = query.filter(assignment__chapter__course__tutor=user)
            assignment_id = self.get_int_query_param("assignment")
            if assignment_id:
                query = query.filter(assignment_id=assignment_id)
            course_id = self.get_int_query_param("course")
            if course_id:
                query = query.filter(assignment__chapter__course_id=course_id)
        else:
            query = query.filter(student=user)

        if self.action in ("retrieve", "grade"):
            ordered_answers = StudentAnswer.objects.select_related(
                "question", "answer"
            ).order_by("question__order", "question_id")
            query = query.prefetch_related(
                Prefetch("stu_answers", queryset=ordered_answers),
                "stu_answers__question__answers",
            )
        return query

    @action(methods=["patch"], url_path="grade", detail=True)
    def grade(self, request, pk):
        submission = self.get_object()

        serializer = GradeSubmissionSerializer(
            submission, data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        graded = grade_submission(
            submission=submission,
            answers=serializer.validated_data["answers"],
        )

        return Response(
            TutorSubmissionDetailSerializer(graded).data,
            status=status.HTTP_200_OK,
        )
