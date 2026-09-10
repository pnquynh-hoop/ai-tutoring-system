from django.utils import timezone
from rest_framework import serializers
from accounts.serializers import SimpleUserSerializer, TutorProfileSerializer
from core.validators import validate_document_upload, validate_video_url
from .models import Chapter, Comment, Course, LearningResource, Lesson

MAX_RESOURCE_CONTENT_LENGTH = 50000
MAX_CHAPTERS_PER_COURSE = 20
MAX_LESSONS_PER_CHAPTER = 50
MAX_COMMENT_LENGTH = 2000


class StudentListCourseSerializer(serializers.ModelSerializer):
    tutor_name = serializers.CharField(
        source="tutor.full_name", read_only=True, default=None
    )
    progress = serializers.SerializerMethodField()

    def get_progress(self, instance):
        if not instance.total_lessons:
            return 0.0
        completed = (
            instance.completed_lessons if instance.completed_lessons is not None else 0
        )
        return round(completed * 100 / instance.total_lessons, 1)

    class Meta:
        fields = ["id", "name", "tutor_name", "progress"]
        model = Course


class StudentDetailCourseSerializer(StudentListCourseSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    grade = serializers.CharField(source="grade.name", read_only=True)
    tutor = TutorProfileSerializer(
        source="tutor.tutorprofile", read_only=True, default=None
    )

    class Meta:
        model = StudentListCourseSerializer.Meta.model
        fields = StudentListCourseSerializer.Meta.fields + [
            "description",
            "subject_name",
            "grade",
            "tutor",
        ]


class TutorCourseSerializer(serializers.ModelSerializer):
    students_count = serializers.IntegerField(read_only=True)
    chapters_count = serializers.IntegerField(read_only=True)
    lessons_count = serializers.IntegerField(read_only=True)
    pending_submission_count = serializers.IntegerField(read_only=True)

    class Meta:
        fields = [
            "id",
            "name",
            "students_count",
            "chapters_count",
            "lessons_count",
            "pending_submission_count",
        ]
        model = Course


class LessonTreeSerializer(serializers.ModelSerializer):
    is_completed = serializers.BooleanField(read_only=True, default=False)
    is_published = serializers.BooleanField(read_only=True)

    class Meta:
        model = Lesson
        fields = ["id", "title", "order", "is_completed", "is_published"]


class ChapterTreeSerializer(serializers.ModelSerializer):
    lessons = LessonTreeSerializer(many=True, read_only=True)
    is_published = serializers.BooleanField(read_only=True)

    class Meta:
        model = Chapter
        fields = ["id", "title", "order", "lessons", "assignment", "is_published"]


class CourseTreeSerializer(serializers.ModelSerializer):
    chapters = ChapterTreeSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ["id", "name", "chapters"]


class StudentQuickStatsSerializer(serializers.Serializer):
    ongoing_courses_count = serializers.IntegerField()
    total_pending_assignments_count = serializers.IntegerField()
    streak = serializers.IntegerField()
    studied_today = serializers.BooleanField()


class TutorQuickStatsSerializer(serializers.Serializer):
    teaching_course_count = serializers.IntegerField()
    total_students_count = serializers.IntegerField()
    total_pending_submission_count = serializers.IntegerField()


class LearningResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningResource
        fields = [
            "id",
            "title",
            "resource_type",
            "content",
            "file_url",
            "video_url",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.file_url:
            try:
                data["file_url"] = instance.file_url.url
            except AttributeError:
                data["file_url"] = str(instance.file_url)
        return data


class TutorLearningResourceSerializer(LearningResourceSerializer):
    is_published = serializers.BooleanField(read_only=True)

    class Meta:
        model = LearningResourceSerializer.Meta.model
        fields = LearningResourceSerializer.Meta.fields + [
            "is_published",
            "rag_status",
            "rag_progress",
        ]


class LessonDetailSerializer(serializers.ModelSerializer):
    resources = LearningResourceSerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = ["id", "title", "resources"]


class CommentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Comment
        fields = [
            "id",
            "content",
            "is_right",
            "created_by",
            "parent",
            "created_at",
            "lesson",
        ]
        extra_kwargs = {
            "content": {"max_length": MAX_COMMENT_LENGTH},
            "created_at": {"read_only": True},
            "is_right": {"read_only": True},
            "created_by": {"read_only": True},
            "lesson": {"write_only": True},
        }

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        data["created_by"] = self.context["request"].user
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by"] = SimpleUserSerializer(instance.created_by).data
        return data

    def validate(self, attrs):
        parent = attrs.get("parent")
        lesson = attrs.get("lesson")

        if parent and lesson and parent.lesson_id != lesson.id:
            raise serializers.ValidationError(
                {"parent": "Bình luận gốc phải thuộc cùng một bài học."}
            )

        if parent and parent.parent_id is not None:
            raise serializers.ValidationError(
                {"parent": "Chỉ được trả lời bình luận gốc, không trả lời một bình luận trả lời."}
            )

        return attrs


class CourseProgressSerializer(serializers.Serializer):
    total_lessons = serializers.IntegerField()
    completed_lessons = serializers.IntegerField()
    progress_percent = serializers.FloatField()


class CourseOverviewSerializer(serializers.Serializer):
    progress = CourseProgressSerializer()
    average_score = serializers.FloatField(allow_null=True)
    pending_assignments_count = serializers.IntegerField()


class TutorStudentStatSerializer(serializers.Serializer):
    student = SimpleUserSerializer()
    completed_lessons = serializers.IntegerField()
    total_lessons = serializers.IntegerField()
    progress = serializers.FloatField()
    average_score = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )


class TutorAssignmentStatSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    chapter_title = serializers.CharField()
    due_date = serializers.DateTimeField()
    submitted_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    average_score = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )


class TutorCourseStatsSerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    total_lessons = serializers.IntegerField()
    students = TutorStudentStatSerializer(many=True)
    assignments = TutorAssignmentStatSerializer(many=True)


class ChapterStatSerializer(serializers.ModelSerializer):
    total_lessons = serializers.IntegerField(read_only=True)
    completed_lessons = serializers.IntegerField(read_only=True)
    score = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        allow_null=True,
        read_only=True,
    )
    has_pending_assignment = serializers.BooleanField(read_only=True)
    first_incomplete_lesson_id = serializers.IntegerField(
        allow_null=True, read_only=True
    )

    class Meta:
        model = Chapter
        fields = [
            "id",
            "title",
            "total_lessons",
            "completed_lessons",
            "score",
            "has_pending_assignment",
            "first_incomplete_lesson_id",
        ]


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ["id", "course", "title", "order"]

    def validate_course(self, course):
        if course.tutor_id != self.context["request"].user.id:
            raise serializers.ValidationError("Bạn không phụ trách khóa học này.")
        return course

    def validate(self, attrs):
        if self.instance is None:
            course = attrs.get("course")

            if course and course.chapters.count() >= MAX_CHAPTERS_PER_COURSE:
                raise serializers.ValidationError(
                    {
                        "course": (
                            f"Mỗi khóa học chỉ có tối đa "
                            f"{MAX_CHAPTERS_PER_COURSE} chương."
                        )
                    }
                )
            return attrs

        if "course" in attrs and attrs["course"] != self.instance.course:
            raise serializers.ValidationError(
                {"course": "Không được chuyển chương sang khóa học khác."}
            )
        return attrs


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id", "chapter", "title", "order"]

    def validate_chapter(self, chapter):
        if chapter.course.tutor_id != self.context["request"].user.id:
            raise serializers.ValidationError(
                "Bạn không phụ trách khóa học của chương này."
            )
        return chapter

    def validate(self, attrs):
        if self.instance is None:
            chapter = attrs.get("chapter")

            if chapter and chapter.lessons.count() >= MAX_LESSONS_PER_CHAPTER:
                raise serializers.ValidationError(
                    {
                        "chapter": f"Mỗi chương chỉ có tối đa {MAX_LESSONS_PER_CHAPTER} bài học."
                    }
                )
            return attrs

        if "chapter" in attrs and attrs["chapter"] != self.instance.chapter:
            raise serializers.ValidationError(
                {"chapter": "Không được chuyển bài học sang chương khác."}
            )
        return attrs


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningResource
        fields = [
            "id",
            "lesson",
            "title",
            "resource_type",
            "content",
            "file_url",
            "video_url",
        ]
        extra_kwargs = {
            "content": {"max_length": MAX_RESOURCE_CONTENT_LENGTH},
        }

    def validate_file_url(self, file):
        if file is not None and getattr(file, "size", None) is None:
            raise serializers.ValidationError(
                "Chỉ chấp nhận tệp tải lên trực tiếp, không nhận đường dẫn tệp có sẵn."
            )

        return validate_document_upload(file)


    def validate_video_url(self, url):
        return validate_video_url(url)

    def validate_lesson(self, lesson):
        if lesson.chapter.course.tutor_id != self.context["request"].user.id:
            raise serializers.ValidationError(
                "Bạn không phụ trách khóa học của bài học này."
            )
        return lesson

    def validate(self, attrs):
        current = self.instance

        if current is not None:
            if current.is_published:
                raise serializers.ValidationError(
                    "Tài nguyên đã công khai cho học sinh thì không sửa được nữa."
                )

            if (
                "resource_type" in attrs
                and attrs["resource_type"] != current.resource_type
            ):
                raise serializers.ValidationError(
                    {"resource_type": "Không được đổi loại tài nguyên."}
                )

        resource_type = attrs.get(
            "resource_type", getattr(current, "resource_type", None)
        )
        content = attrs.get("content", getattr(current, "content", None))
        file_url = attrs.get("file_url", getattr(current, "file_url", None))
        video_url = attrs.get("video_url", getattr(current, "video_url", None))

        if resource_type == LearningResource.ResourceType.VIDEO_URL:
            if not video_url:
                raise serializers.ValidationError(
                    {"video_url": "Tài nguyên dạng video phải có đường dẫn video."}
                )
            if content or file_url:
                raise serializers.ValidationError(
                    "Tài nguyên dạng video không được có nội dung văn bản hoặc tệp tài liệu."
                )
        elif resource_type == LearningResource.ResourceType.PDF_FILE:
            if not file_url:
                raise serializers.ValidationError(
                    {"file_url": "Tài nguyên dạng PDF phải có tệp tài liệu."}
                )
            if content or video_url:
                raise serializers.ValidationError(
                    "Tài nguyên dạng PDF không được có nội dung văn bản hoặc đường dẫn video."
                )
        elif resource_type == LearningResource.ResourceType.OTHERS:
            if not content:
                raise serializers.ValidationError(
                    {"content": "Tài nguyên dạng văn bản phải có nội dung."}
                )
            if file_url or video_url:
                raise serializers.ValidationError(
                    "Tài nguyên dạng văn bản không được có tệp tài liệu hoặc đường dẫn video."
                )
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.file_url:
            try:
                data["file_url"] = instance.file_url.url
            except AttributeError:
                data["file_url"] = str(instance.file_url)
        return data


class PublishChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ["id", "published_at"]
        extra_kwargs = {"published_at": {"read_only": True}}

    def validate(self, attrs):
        chapter = self.instance

        if chapter.is_published:
            raise serializers.ValidationError("Chương này đã được công khai.")

        return attrs

    def update(self, instance, validated_data):
        instance.published_at = timezone.now()
        instance.save(update_fields=["published_at", "updated_at"])
        return instance


class PublishLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id", "published_at"]
        extra_kwargs = {"published_at": {"read_only": True}}

    def validate(self, attrs):
        lesson = self.instance
        chapter = lesson.chapter

        if lesson.is_published:
            raise serializers.ValidationError("Bài học này đã được công khai.")

        if not chapter.is_published:
            raise serializers.ValidationError(
                "Phải công khai chương chứa bài học này trước."
            )

        return attrs

    def update(self, instance, validated_data):
        instance.published_at = timezone.now()
        instance.save(update_fields=["published_at", "updated_at"])
        return instance


class IngestResourceSerializer(serializers.Serializer):
    def validate(self, attrs):
        resource = self.instance

        if resource.rag_status == LearningResource.RAGStatus.PROCESSING:
            raise serializers.ValidationError(
                "Tài nguyên này đang được nạp, chờ nạp xong rồi thử lại."
            )

        if not resource.content and not resource.file_url:
            raise serializers.ValidationError(
                "Tài nguyên này không có nội dung văn bản hay tệp nào để nạp."
            )
        return attrs

    def update(self, instance, validated_data):
        instance.rag_status = LearningResource.RAGStatus.PENDING
        instance.rag_error = None
        instance.save(update_fields=["rag_status", "rag_error", "updated_at"])
        return instance


class PublishResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningResource
        fields = ["id", "published_at"]
        extra_kwargs = {"published_at": {"read_only": True}}

    def validate(self, attrs):
        resource = self.instance
        lesson = resource.lesson

        if resource.is_published:
            raise serializers.ValidationError("Tài nguyên này đã được công khai.")

        if not lesson.is_published:
            raise serializers.ValidationError(
                "Phải công khai bài học chứa tài nguyên này trước."
            )

        return attrs

    def update(self, instance, validated_data):
        instance.published_at = timezone.now()
        instance.save(update_fields=["published_at", "updated_at"])
        return instance
