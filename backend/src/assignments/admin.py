from core.admin import admin_site

from assignments.models import Answer, Assignment, Question, StudentAnswer, Submission

admin_site.register([Assignment, Question, Answer, StudentAnswer, Submission])
