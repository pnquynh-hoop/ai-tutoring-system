from rest_framework import generics, viewsets
from .models import Grade
from .serializers import GradeSerializer


class GradeView(viewsets.ViewSet, generics.ListAPIView):
    queryset = Grade.objects.filter(is_active=True)
    serializer_class = GradeSerializer
