from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from assignments.models import Assignment, Submission
from assignments.serializers import AssignmentSerializer

class AssignmentView(viewsets.ViewSet, generics.RetrieveAPIView):
    queryset = Assignment.objects.filter(is_active=True)
    serializer_class = AssignmentSerializer

    @action(methods=["post"], url_path="submit", detail=True)
    def submit(self, request, pk):
        ...

    @action(methods=["get"], url_path="submission", detail=True)
    def get_submission(self, request, pk):
        ...

class SubmissionView(viewsets.ViewSet, generics.ListAPIView):
    
    def get_queryset(self):
        query = Submission.objects.filter(student=self.request.user)
        return query
    

