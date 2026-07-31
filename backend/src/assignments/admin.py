from django.contrib import admin

from assignments.models import Answer, Assignment, Question, StudentAnswer, Submission

admin.site.register([Assignment, Question, Answer, StudentAnswer, Submission])
