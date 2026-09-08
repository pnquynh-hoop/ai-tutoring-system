import api from './axios';
import { ENDPOINTS } from './endpoints';
import type {
	AssignmentDetail,
	AssignmentPayload,
	Attempt,
	ChangePasswordPayload,
	Chapter,
	ChapterPayload,
	ChoiceOption,
	Comment,
	Course,
	CourseDetail,
	CourseTree,
	Grade,
	GradeAnswerItem,
	LessonDetail,
	LessonPayload,
	LessonResource,
	TutorLessonResource,
	Me,
	PublishResult,
	Question,
	QuestionType,
	RagAnswer,
	ResourcePayload,
	Submission,
	SubmissionDetail,
	SubmitAnswerItem,
	TutorCourse,
	TutorCourseStats,
	TutorQuestion,
	TutorQuestionPayload,
	TutorQuestionUpdatePayload,
	UpdateMePayload
} from './entities';
import type { ChapterStat, CourseOverview, LoginRequest } from './types';

interface Paginated<T> {
	count: number;
	next: string | null;
	previous: string | null;
	results: T[];
}

function toList<T>(data: Paginated<T> | T[]): T[] {
	return Array.isArray(data) ? data : data.results;
}

export async function loginApi(data: LoginRequest) {
	const response = await api.post(ENDPOINTS.LOGIN, data);
	return response.data;
}

export async function logoutApi() {
	return await api.post(ENDPOINTS.LOGOUT);
}

export async function getMeApi(cookieHeader?: string): Promise<Me> {
	const res = await api.get<Me>(ENDPOINTS.ME, {
		headers: cookieHeader ? { Cookie: cookieHeader } : undefined
	});
	return res.data;
}

export async function getListCourses(): Promise<Course[]> {
	return toList((await api.get<Paginated<Course> | Course[]>(ENDPOINTS.COURSES)).data);
}

export async function getTutorCourses(): Promise<TutorCourse[]> {
	return toList((await api.get<Paginated<TutorCourse> | TutorCourse[]>(ENDPOINTS.COURSES)).data);
}

export async function getQuickStats() {
	return (await api.get(ENDPOINTS.STATS)).data;
}

export async function getDetailCourse(courseId: number): Promise<CourseDetail> {
	return (await api.get<CourseDetail>(ENDPOINTS.DETAIL_COURSE(courseId))).data;
}

export async function getCourseTree(courseId: number): Promise<CourseTree> {
	return (await api.get<CourseTree>(ENDPOINTS.TREE_OF_COURSE(courseId))).data;
}

export async function getCourseOverview(courseId: number): Promise<CourseOverview> {
	return (await api.get<CourseOverview>(ENDPOINTS.OVERVIEW_OF_COURSE(courseId))).data;
}

export async function getChapterStats(courseId: number): Promise<ChapterStat[]> {
	return (await api.get<ChapterStat[]>(ENDPOINTS.CHAPTER_STATS_OF_COURSE(courseId))).data;
}

export async function createChapter(payload: ChapterPayload): Promise<Chapter> {
	return (await api.post<Chapter>(ENDPOINTS.CHAPTERS, payload)).data;
}

export async function updateChapter(chapterId: number, payload: Partial<ChapterPayload>) {
	return (await api.patch(ENDPOINTS.DETAIL_CHAPTER(chapterId), payload)).data;
}

export async function deleteChapter(chapterId: number) {
	await api.delete(ENDPOINTS.DETAIL_CHAPTER(chapterId));
}

export async function publishChapter(chapterId: number): Promise<PublishResult> {
	return (await api.post<PublishResult>(ENDPOINTS.PUBLISH_CHAPTER(chapterId))).data;
}

export async function getDetailLesson(lessonId: number): Promise<LessonDetail> {
	return (await api.get<LessonDetail>(ENDPOINTS.DETAIL_LESSON(lessonId))).data;
}

export async function createLesson(payload: LessonPayload) {
	return (await api.post(ENDPOINTS.LESSONS, payload)).data;
}

export async function updateLesson(lessonId: number, payload: Partial<LessonPayload>) {
	return (await api.patch(ENDPOINTS.DETAIL_LESSON(lessonId), payload)).data;
}

export async function deleteLesson(lessonId: number) {
	await api.delete(ENDPOINTS.DETAIL_LESSON(lessonId));
}

export async function publishLesson(lessonId: number): Promise<PublishResult> {
	return (await api.post<PublishResult>(ENDPOINTS.PUBLISH_LESSON(lessonId))).data;
}

export async function postCompleteLesson(lessonId: number) {
	return (await api.post(ENDPOINTS.COMPLETE_LESSON(lessonId))).data;
}

export async function getLessonResources(lessonId: number): Promise<TutorLessonResource[]> {
	return (await api.get<TutorLessonResource[]>(ENDPOINTS.RESOURCES_OF_LESSON(lessonId))).data;
}

function resourceBody(payload: Partial<ResourcePayload>): FormData | Partial<ResourcePayload> {
	if (!(payload.file_url instanceof File)) return payload;

	const body = new FormData();
	for (const [key, value] of Object.entries(payload)) {
		if (value === null || value === undefined) continue;
		body.append(key, value instanceof File ? value : String(value));
	}
	return body;
}

function multipartConfig(body: FormData | Partial<ResourcePayload>) {
	if (!(body instanceof FormData)) return undefined;
	return { headers: { 'Content-Type': 'multipart/form-data' } };
}

export async function createResource(payload: ResourcePayload): Promise<LessonResource> {
	const body = resourceBody(payload);
	return (await api.post<LessonResource>(ENDPOINTS.RESOURCES, body, multipartConfig(body))).data;
}

export async function updateResource(resourceId: number, payload: Partial<ResourcePayload>) {
	const body = resourceBody(payload);
	return (await api.patch(ENDPOINTS.DETAIL_RESOURCE(resourceId), body, multipartConfig(body))).data;
}

export async function deleteResource(resourceId: number) {
	await api.delete(ENDPOINTS.DETAIL_RESOURCE(resourceId));
}

export async function publishResource(resourceId: number): Promise<PublishResult> {
	return (await api.post<PublishResult>(ENDPOINTS.PUBLISH_RESOURCE(resourceId))).data;
}

export async function ingestResource(resourceId: number): Promise<TutorLessonResource> {
	return (await api.post<TutorLessonResource>(ENDPOINTS.INGEST_RESOURCE(resourceId))).data;
}

export async function getListComments(lessonId: number): Promise<Comment[]> {
	return toList(
		(await api.get<Paginated<Comment> | Comment[]>(ENDPOINTS.COMMENTS_OF_LESSON(lessonId))).data
	);
}

export async function postComment(
	lessonId: number,
	content: string,
	parentId?: number
): Promise<Comment> {
	return (
		await api.post<Comment>(ENDPOINTS.COMMENTS_OF_LESSON(lessonId), {
			content,
			...(parentId ? { parent: parentId } : {})
		})
	).data;
}

export async function toggleCommentRight(commentId: number): Promise<Comment> {
	return (await api.post<Comment>(ENDPOINTS.TOGGLE_RIGHT_COMMENT(commentId))).data;
}

export async function deleteComment(commentId: number): Promise<void> {
	await api.delete(ENDPOINTS.DETAIL_COMMENT(commentId));
}

export async function getDetailAssignment(assignmentId: number): Promise<AssignmentDetail> {
	return (await api.get<AssignmentDetail>(ENDPOINTS.DETAIL_ASSIGNMENT(assignmentId))).data;
}

export async function getListQuestions(assignmentId: number): Promise<Question[]> {
	return (await api.get<Question[]>(ENDPOINTS.QUESTIONS_OF_ASSIGNMENT(assignmentId))).data;
}

export async function startAssignment(assignmentId: number): Promise<Attempt> {
	return (await api.post<Attempt>(ENDPOINTS.START_ASSIGNMENT(assignmentId))).data;
}

export async function saveDraft(
	assignmentId: number,
	answers: SubmitAnswerItem[]
): Promise<Attempt> {
	return (await api.post<Attempt>(ENDPOINTS.SAVE_DRAFT_ASSIGNMENT(assignmentId), { answers })).data;
}

export async function submitAssignment(
	assignmentId: number,
	answers: SubmitAnswerItem[]
): Promise<Submission> {
	return (await api.post<Submission>(ENDPOINTS.SUBMIT_ASSIGNMENT(assignmentId), { answers })).data;
}

export async function createAssignment(payload: AssignmentPayload) {
	return (await api.post(ENDPOINTS.ASSIGNMENTS, payload)).data;
}

export async function updateAssignment(assignmentId: number, payload: Partial<AssignmentPayload>) {
	return (await api.patch(ENDPOINTS.DETAIL_ASSIGNMENT(assignmentId), payload)).data;
}

export async function deleteAssignment(assignmentId: number) {
	await api.delete(ENDPOINTS.DETAIL_ASSIGNMENT(assignmentId));
}

export async function publishAssignment(assignmentId: number): Promise<PublishResult> {
	return (await api.post<PublishResult>(ENDPOINTS.PUBLISH_ASSIGNMENT(assignmentId))).data;
}

export async function getTutorQuestions(assignmentId: number): Promise<TutorQuestion[]> {
	return (await api.get<TutorQuestion[]>(ENDPOINTS.QUESTIONS_OF_ASSIGNMENT(assignmentId))).data;
}

export async function createQuestion(payload: TutorQuestionPayload): Promise<TutorQuestion> {
	return (await api.post<TutorQuestion>(ENDPOINTS.QUESTIONS, payload)).data;
}

export async function updateQuestion(
	questionId: number,
	payload: Partial<TutorQuestionUpdatePayload>
): Promise<TutorQuestion> {
	return (await api.patch<TutorQuestion>(ENDPOINTS.DETAIL_QUESTION(questionId), payload)).data;
}

export async function deleteQuestion(questionId: number) {
	await api.delete(ENDPOINTS.DETAIL_QUESTION(questionId));
}

export async function getListSubmissions(params?: {
	course?: number;
	assignment?: number;
}): Promise<Submission[]> {
	return toList(
		(await api.get<Paginated<Submission> | Submission[]>(ENDPOINTS.SUBMISSIONS, { params })).data
	);
}

export async function getSubmissionDetail(submissionId: number): Promise<SubmissionDetail> {
	return (await api.get<SubmissionDetail>(ENDPOINTS.DETAIL_SUBMISSION(submissionId))).data;
}

export async function gradeSubmission(
	submissionId: number,
	answers: GradeAnswerItem[]
): Promise<SubmissionDetail> {
	return (await api.patch<SubmissionDetail>(ENDPOINTS.GRADE_SUBMISSION(submissionId), { answers }))
		.data;
}

export async function getCourseStats(courseId: number): Promise<TutorCourseStats> {
	return (await api.get<TutorCourseStats>(ENDPOINTS.STATS_OF_COURSE(courseId))).data;
}

export async function getMyProfile(): Promise<Me> {
	return (await api.get<Me>(ENDPOINTS.ME)).data;
}

export async function updateMyProfile(payload: UpdateMePayload): Promise<Me> {
	return (await api.patch<Me>(ENDPOINTS.ME, payload)).data;
}

export async function updateMyAvatar(file: File): Promise<Me> {
	const body = new FormData();
	body.append('avatar', file);
	return (await api.patch<Me>(ENDPOINTS.ME, body, multipartConfig(body))).data;
}

export async function changePassword(payload: ChangePasswordPayload) {
	return (await api.post(ENDPOINTS.CHANGE_PASSWORD, payload)).data;
}

export async function getGrades(): Promise<Grade[]> {
	return (await api.get<Grade[]>(ENDPOINTS.GRADES)).data;
}

export async function getAcademicLevels(): Promise<ChoiceOption[]> {
	return (await api.get<ChoiceOption[]>(ENDPOINTS.ACADEMIC_LEVELS)).data;
}

const AI_TIMEOUT_MS = 90_000;

export async function askAI(
	question: string,
	courseId: number,
	lessonId?: number
): Promise<RagAnswer> {
	return (
		await api.post<RagAnswer>(
			ENDPOINTS.RAG_ASK,
			{
				question,
				course_id: courseId,
				...(lessonId ? { lesson_id: lessonId } : {})
			},
			{ timeout: AI_TIMEOUT_MS }
		)
	).data;
}

export async function generateExercises(payload: {
	course_id: number;
	lesson_id?: number;
	question_type?: QuestionType;
	count?: number;
}) {
	return (await api.post(ENDPOINTS.RAG_GENERATE_EXERCISES, payload, { timeout: AI_TIMEOUT_MS }))
		.data;
}
