from django.contrib import admin

from courses.models import (
    Chapter,
    Comment,
    Course,
    Enrollment,
    LearningResource,
    Lesson,
    LessonProgress,
)

admin.site.register(
    [Course, Chapter, Lesson, LessonProgress, LearningResource, Comment, Enrollment]
)
