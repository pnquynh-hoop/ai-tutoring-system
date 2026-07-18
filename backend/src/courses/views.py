from rest_framework import status, permissions, viewsets, generics
from .models import Course
from .serializers import CourseSerializer

class CourseView(viewsets.ViewSet, generics.ListAPIView):
    serializer_class = CourseSerializer
    queryset = Course.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        query = super().get_queryset()
        query = query.filter(students=self.request.user)
        # print(query.query)
        return query
    