export type Role = 'Student' | 'Tutor';
export type ResourceType = 'VIDEO_URL' | 'PDF_FILE' | 'OTHERS';
export type QuestionType = 'MULTIPLE_CHOICE' | 'FILL_IN_BLANK' | 'ESSAY';

/** GET /courses/ khi user là học sinh */
export interface Course {
	id: number;
	name: string;
	tutor_name: string | null;
	progress: number | null;
}

/** GET /courses/ khi user là gia sư */
export interface TutorCourse {
	id: number;
	name: string;
	students_count: number;
	chapters_count: number;
	lessons_count: number;
	pending_submission_count: number;
}

/** Gia sư phụ trách kèm hồ sơ, hiển thị ở đầu trang chi tiết khóa học. */
export interface CourseTutor {
	id: number;
	full_name: string;
	avatar: string | null;
	tutor_profile: TutorProfile | null;
}

export interface CourseDetail extends Course {
	description: string;
	subject_name: string;
	grade: string;
	tutor: CourseTutor | null;
}

export interface TutorCourseDetail extends TutorCourse {
	description: string;
	subject_name: string;
	grade: string;
}

export interface Lesson {
	id: number;
	title: string;
	order: number;
	is_completed: boolean;
}

export interface Chapter {
	id: number;
	title: string;
	order: number;
	lessons: Lesson[];
	/** id của Assignment gắn với chương (quan hệ 1-1), null nếu chương chưa có bài tập */
	assignment: number | null;
}

export interface CourseTree {
	id: number;
	name: string;
	chapters: Chapter[];
}

export interface Student {
	role: Role;
	full_name: string;
	avatar: string;
	grade: string;
}

/** Thông tin đọc được từ claim của access token, dùng cho điều hướng và hiển thị.
 *  Ít field hơn `Me` vì nó không đi qua API mà nằm sẵn trong token. */
export interface SessionUser {
	id: number;
	role: Role | null;
	full_name: string;
	avatar: string | null;
	grade: string | null;
}

export interface LessonResource {
	id: number;
	lesson: number;
	title: string;
	resource_type: ResourceType;
	content: string | null;
	file_url: string | null;
	video_url: string | null;
}

export interface LessonDetail {
	id: number;
	title: string;
	resources: LessonResource[];
}

export interface CommentUser {
	id: number;
	full_name: string;
	avatar: string | null;
}

export interface Comment {
	id: number;
	content: string;
	is_right: boolean;
	created_by: CommentUser;
	parent: number | null;
	created_at: string;
	lesson: number;
	is_active: boolean;
}

export interface Answer {
	id: number;
	content: string;
}

export interface Question {
	id: number;
	content: string;
	question_type: QuestionType;
	answers: Answer[];
}

export interface QuestionTypeStat {
	label: string;
	count: number;
}

/** GET /assignments/{id}/ */
export interface AssignmentDetail {
	id: number;
	title: string;
	time_limit_minutes: number | null;
	due_date: string;
	total_questions: number;
	question_types: QuestionTypeStat[];
	max_attempts: number;
	attempts_used: number;
}

/** POST /assignments/{id}/start/ - lượt làm bài đang mở */
export interface Attempt {
	id: number;
	assignment: number;
	started_at: string;
	/** Thời điểm hết giờ do server tính, null nếu bài không giới hạn thời gian */
	deadline: string | null;
	time_limit_minutes: number | null;
}

/** POST /assignments/{id}/submit/ và GET /submissions/ */
export interface Submission {
	id: number;
	assignment: number;
	assignment_title: string;
	chapter_title: string;
	course_name: string;
	student: CommentUser;
	/** null khi bài còn câu tự luận chờ gia sư chấm */
	score: string | null;
	started_at: string | null;
	submitted_at: string | null;
}

/** Một câu trả lời trong bài nộp, dùng cho màn xem lại và chấm bài */
export interface StudentAnswerReview {
	id: number;
	question: number;
	question_content: string;
	question_type: QuestionType;
	explanation: string;
	answer: number | null;
	selected_answer: string | null;
	correct_answer: string | null;
	answer_text: string | null;
	point: string | null;
	tutor_comment: string | null;
	/** null nghĩa là câu tự luận chưa được chấm */
	is_correct: boolean | null;
}

/** GET /submissions/{id}/ */
export interface SubmissionDetail extends Submission {
	point_per_question: number;
	stu_answers: StudentAnswerReview[];
}

/** Một phần tử trong payload PATCH /submissions/{id}/grade/ */
export interface GradeAnswerItem {
	id: number;
	point: number | string;
	tutor_comment?: string | null;
}

/** Bài tập của chương dưới góc nhìn gia sư */
export interface AssignmentPayload {
	chapter: number;
	title: string;
	due_date: string;
	time_limit_minutes?: number | null;
}

export interface TutorAnswer {
	id?: number;
	content: string;
	is_correct: boolean;
}

/** GET/POST /questions/ - bản đầy đủ dành cho gia sư (kèm đáp án đúng, lời giải) */
export interface TutorQuestion {
	id: number;
	assignment: number;
	content: string;
	question_type: QuestionType;
	explanation: string;
	order: number | null;
	answers: TutorAnswer[];
}

export interface TutorQuestionPayload {
	assignment: number;
	content: string;
	question_type: QuestionType;
	explanation: string;
	answers: TutorAnswer[];
	order?: number | null;
}

// ----- Thống kê khóa học của gia sư: GET /courses/{id}/stats/ -----

export interface TutorStudentStat {
	id: number;
	full_name: string;
	avatar: string | null;
	completed_lessons: number;
	total_lessons: number;
	progress: number;
	average_score: number | null;
}

export interface TutorAssignmentStat {
	id: number;
	title: string;
	chapter_title: string;
	due_date: string;
	submitted_count: number;
	graded_count: number;
	pending_count: number;
	average_score: number | null;
}

export interface TutorCourseStats {
	total_students: number;
	total_lessons: number;
	students: TutorStudentStat[];
	assignments: TutorAssignmentStat[];
}

// ----- Hồ sơ cá nhân: GET/PATCH /users/me/ -----

/** Khối lớp do quản trị viên khai báo (academics.Grade) */
export interface Grade {
	id: number;
	name: string;
}

/** Một lựa chọn khai báo bằng TextChoices trong model, ví dụ học lực */
export interface ChoiceOption {
	value: string;
	label: string;
}

export interface StudentProfile {
	grade_level: number | null;
	grade_name: string | null;
	learning_goals: string;
	academic_level: 'POOR' | 'AVERAGE' | 'GOOD' | 'EXCELLENT';
}

export interface TutorProfile {
	bio: string;
	qualification: string;
	experience_years: number;
	is_verified: boolean;
}

export interface Me {
	id: number;
	username: string;
	first_name: string;
	last_name: string;
	full_name: string;
	email: string;
	phone: string;
	avatar: string | null;
	role: Role | null;
	student_profile: StudentProfile | null;
	tutor_profile: TutorProfile | null;
}

export interface UpdateMePayload {
	first_name?: string;
	last_name?: string;
	email?: string;
	phone?: string;
	student_profile?: Partial<Omit<StudentProfile, 'grade_name'>>;
	tutor_profile?: Partial<Omit<TutorProfile, 'is_verified'>>;
}

/** POST /rag/ask/ - câu trả lời kèm nguồn tài liệu AI đã dùng */
export interface RagSource {
	title: string;
	/** Số trang trong PDF, đánh số từ 0; null với tài liệu không phân trang */
	page: number | null;
}

export interface RagAnswer {
	question: string;
	answer: string;
	sources: RagSource[];
	/** false nghĩa là câu trả lời lấy từ kiến thức chung, không có trong tài liệu khóa học */
	grounded: boolean;
}

export interface ChangePasswordPayload {
	old_password: string;
	new_password: string;
	confirm_password: string;
}

export type UserAnswer =
	{ type: 'MULTIPLE_CHOICE'; answerId: number } | { type: 'FILL_IN_BLANK' | 'ESSAY'; text: string };

/** Một phần tử trong mảng `answers` gửi lên khi nộp bài */
export interface SubmitAnswerItem {
	question_id: number;
	answer_id?: number | null;
	answer_text?: string | null;
}

// ----- Payload cho các thao tác thêm mới / chỉnh sửa của gia sư -----

export interface ChapterPayload {
	course: number;
	title: string;
	order: number;
}

export interface LessonPayload {
	chapter: number;
	title: string;
	order: number;
}

export interface ResourcePayload {
	lesson: number;
	title: string;
	resource_type: ResourceType;
	content?: string | null;
	video_url?: string | null;
	file_url?: string | null;
}
