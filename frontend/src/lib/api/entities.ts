export type Role = 'Student' | 'Tutor';
export type ResourceType = 'VIDEO_URL' | 'PDF_FILE' | 'OTHERS';
export type QuestionType = 'MULTIPLE_CHOICE' | 'FILL_IN_BLANK' | 'ESSAY';

export interface Course {
	id: number;
	name: string;
	tutor_name: string | null;
	progress: number | null;
}

export interface TutorCourse {
	id: number;
	name: string;
	students_count: number;
	chapters_count: number;
	lessons_count: number;
	pending_submission_count: number;
}

export interface CourseDetail extends Course {
	description: string;
	subject_name: string;
	grade: string;
	tutor: TutorProfile | null;
}

export interface Lesson {
	id: number;
	title: string;
	order: number;
	is_completed: boolean;
	is_published: boolean;
}

export interface Chapter {
	id: number;
	title: string;
	order: number;
	lessons: Lesson[];
	assignment: number | null;
	is_published: boolean;
}

export interface PublishResult {
	id: number;
	published_at: string;
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

export interface SessionUser {
	id: number;
	role: Role | null;
}

export interface CurrentUser extends SessionUser {
	full_name: string;
	avatar: string | null;
	grade: string | null;
}

export type RagStatus = 'PENDING' | 'PROCESSING' | 'INDEXED' | 'FAILED';

export interface LessonResource {
	id: number;
	lesson: number;
	title: string;
	resource_type: ResourceType;
	content: string | null;
	file_url: string | null;
	video_url: string | null;
}

export interface TutorLessonResource extends LessonResource {
	is_published: boolean;
	rag_status: RagStatus;
	rag_progress: number;
}

export interface LessonDetail {
	id: number;
	title: string;
	resources: LessonResource[];
}

export interface SimpleUser {
	id: number;
	full_name: string;
	avatar: string | null;
}

export interface Comment {
	id: number;
	content: string;
	is_right: boolean;
	created_by: SimpleUser;
	parent: number | null;
	created_at: string;
}

export interface Answer {
	id: number;
	content: string;
}

export interface Question {
	id: number;
	content: string;
	question_type: QuestionType;
	point: string | null;
	answers: Answer[];
}

export interface QuestionTypeStat {
	label: string;
	count: number;
}

export interface AssignmentDetail {
	id: number;
	title: string;
	time_limit_minutes: number | null;
	due_date: string;
	total_questions: number;
	question_types: QuestionTypeStat[];
	max_attempts: number;
	attempts_used: number;
	is_published: boolean;
}

export interface Attempt {
	id: number;
	assignment: number;
	started_at: string;
	deadline: string | null;
	time_limit_minutes: number | null;
	server_time: string;
}

export interface Submission {
	id: number;
	assignment: number;
	assignment_title: string;
	chapter_title: string;
	course_name: string;
	student: SimpleUser;
	score: string | null;
	started_at: string | null;
	submitted_at: string | null;
}

export interface StudentAnswerReview {
	id: number;
	question: number;
	question_content: string;
	question_type: QuestionType;
	explanation: string;
	question_point: string;
	answer: number | null;
	selected_answer: string | null;
	correct_answer: string | null;
	answer_text: string | null;
	point: string | null;
	tutor_comment: string | null;
	is_correct: boolean | null;
}

export interface SubmissionDetail extends Submission {
	stu_answers: StudentAnswerReview[];
}

export interface GradeAnswerItem {
	id: number;
	point: number | string;
	tutor_comment?: string | null;
}

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

export interface TutorQuestion {
	id: number;
	assignment: number;
	content: string;
	question_type: QuestionType;
	explanation: string;
	point: string | null;
	order: number | null;
	answers: TutorAnswer[];
}

export interface TutorQuestionPayload {
	assignment: number;
	content: string;
	question_type: QuestionType;
	explanation: string;
	point: number | null;
	answers: TutorAnswer[];
	order?: number | null;
}

export type TutorQuestionUpdatePayload = Omit<TutorQuestionPayload, 'assignment'>;

export interface TutorStudentStat {
	student: SimpleUser;
	completed_lessons: number;
	total_lessons: number;
	progress: number;
	average_score: string | null;
}

export interface TutorAssignmentStat {
	id: number;
	title: string;
	chapter_title: string;
	due_date: string;
	submitted_count: number;
	pending_count: number;
	average_score: string | null;
}

export interface TutorCourseStats {
	total_students: number;
	total_lessons: number;
	students: TutorStudentStat[];
	assignments: TutorAssignmentStat[];
}

export interface Grade {
	id: number;
	name: string;
}

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
}

export interface RagSource {
	title: string;
	page: number | null;
}

export interface RagAnswer {
	question: string;
	answer: string;
	sources: RagSource[];
	grounded: boolean;
}

export interface ChangePasswordPayload {
	old_password: string;
	new_password: string;
	confirm_password: string;
}

export type UserAnswer =
	{ type: 'MULTIPLE_CHOICE'; answerId: number } | { type: 'FILL_IN_BLANK' | 'ESSAY'; text: string };

export interface SubmitAnswerItem {
	question_id: number;
	answer_id?: number | null;
	answer_text?: string | null;
}

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
	file_url?: File | null;
}
