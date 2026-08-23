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
	TutorCourseDetail,
	TutorCourseStats,
	TutorQuestion,
	TutorQuestionPayload,
	UpdateMePayload
} from './entities';
import type { ChapterStat, LoginRequest, MeResponse } from './types';

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

export async function getMeApi(cookieHeader?: string): Promise<MeResponse> {
	const res = await api.get<MeResponse>(ENDPOINTS.ME, {
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
	return (await api.get<CourseDetail>(ENDPOINTS.COURSE_DETAIL(courseId))).data;
}

export async function getTutorDetailCourse(courseId: number): Promise<TutorCourseDetail> {
	return (await api.get<TutorCourseDetail>(ENDPOINTS.COURSE_DETAIL(courseId))).data;
}

export async function getCourseTree(courseId: number): Promise<CourseTree> {
	return (await api.get<CourseTree>(ENDPOINTS.COURSE_TREE(courseId))).data;
}

export async function getCourseOverview(courseId: number) {
	return (await api.get(ENDPOINTS.COURSE_OVERVIEW(courseId))).data;
}

export async function getChapterStats(courseId: number): Promise<ChapterStat[]> {
	return (await api.get<ChapterStat[]>(ENDPOINTS.CHAPTER_STATS(courseId))).data;
}

export async function createChapter(payload: ChapterPayload): Promise<Chapter> {
	return (await api.post<Chapter>(ENDPOINTS.CHAPTERS, payload)).data;
}

export async function updateChapter(chapterId: number, payload: Partial<ChapterPayload>) {
	return (await api.patch(ENDPOINTS.CHAPTER_DETAIL(chapterId), payload)).data;
}

export async function deleteChapter(chapterId: number) {
	await api.delete(ENDPOINTS.CHAPTER_DETAIL(chapterId));
}

export async function publishChapter(chapterId: number): Promise<PublishResult> {
	return (await api.post<PublishResult>(ENDPOINTS.PUBLISH_CHAPTER(chapterId))).data;
}

export async function getDetailLesson(lessonId: number): Promise<LessonDetail> {
	return (await api.get<LessonDetail>(ENDPOINTS.LESSONS_DETAIL(lessonId))).data;
}

export async function createLesson(payload: LessonPayload) {
	return (await api.post(ENDPOINTS.LESSONS, payload)).data;
}

export async function updateLesson(lessonId: number, payload: Partial<LessonPayload>) {
	return (await api.patch(ENDPOINTS.LESSONS_DETAIL(lessonId), payload)).data;
}

export async function deleteLesson(lessonId: number) {
	await api.delete(ENDPOINTS.LESSONS_DETAIL(lessonId));
}

export async function publishLesson(lessonId: number): Promise<PublishResult> {
	return (await api.post<PublishResult>(ENDPOINTS.PUBLISH_LESSON(lessonId))).data;
}

export async function postCompleteLesson(lessonId: number) {
	return (await api.post(ENDPOINTS.COMPLETE_LESSON(lessonId))).data;
}

export async function getLessonResources(lessonId: number): Promise<LessonResource[]> {
	return (await api.get<LessonResource[]>(ENDPOINTS.RESOURCES_BY_LESSON(lessonId))).data;
}

export async function createResource(payload: ResourcePayload): Promise<LessonResource> {
	return (await api.post<LessonResource>(ENDPOINTS.RESOURCES, payload)).data;
}

export async function updateResource(resourceId: number, payload: Partial<ResourcePayload>) {
	return (await api.patch(ENDPOINTS.RESOURCE_DETAIL(resourceId), payload)).data;
}

export async function deleteResource(resourceId: number) {
	await api.delete(ENDPOINTS.RESOURCE_DETAIL(resourceId));
}

export async function publishResource(resourceId: number): Promise<PublishResult> {
	return (await api.post<PublishResult>(ENDPOINTS.PUBLISH_RESOURCE(resourceId))).data;
}

export async function getListComments(lessonId: number): Promise<Comment[]> {
	return toList((await api.get<Paginated<Comment> | Comment[]>(ENDPOINTS.COMMENTS(lessonId))).data);
}

export async function postComment(
	lessonId: number,
	content: string,
	parentId?: number
): Promise<Comment> {
	return (
		await api.post<Comment>(ENDPOINTS.COMMENTS(lessonId), {
			content,
			...(parentId ? { parent: parentId } : {})
		})
	).data;
}

export async function toggleCommentRight(commentId: number): Promise<Comment> {
	return (await api.post<Comment>(ENDPOINTS.TOGGLE_RIGHT(commentId))).data;
}

export async function getDetailAssignment(assignmentId: number): Promise<AssignmentDetail> {
	return (await api.get<AssignmentDetail>(ENDPOINTS.ASSIGNMENT_DETAIL(assignmentId))).data;
}

export async function getListQuestions(assignmentId: number): Promise<Question[]> {
	return (await api.get<Question[]>(ENDPOINTS.QUESTIONS(assignmentId))).data;
}

export async function startAssignment(assignmentId: number): Promise<Attempt> {
	return (await api.post<Attempt>(ENDPOINTS.START_ASSIGNMENT(assignmentId))).data;
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
	return (await api.patch(ENDPOINTS.ASSIGNMENT_DETAIL(assignmentId), payload)).data;
}

export async function deleteAssignment(assignmentId: number) {
	await api.delete(ENDPOINTS.ASSIGNMENT_DETAIL(assignmentId));
}

export async function publishAssignment(assignmentId: number): Promise<PublishResult> {
	return (await api.post<PublishResult>(ENDPOINTS.PUBLISH_ASSIGNMENT(assignmentId))).data;
}

export async function getTutorQuestions(assignmentId: number): Promise<TutorQuestion[]> {
	return (await api.get<TutorQuestion[]>(ENDPOINTS.QUESTIONS(assignmentId))).data;
}

export async function createQuestion(payload: TutorQuestionPayload): Promise<TutorQuestion> {
	return (await api.post<TutorQuestion>(ENDPOINTS.QUESTIONS_ADMIN, payload)).data;
}

export async function updateQuestion(
	questionId: number,
	payload: Partial<TutorQuestionPayload>
): Promise<TutorQuestion> {
	return (await api.patch<TutorQuestion>(ENDPOINTS.QUESTION_DETAIL(questionId), payload)).data;
}

export async function deleteQuestion(questionId: number) {
	await api.delete(ENDPOINTS.QUESTION_DETAIL(questionId));
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
	return (await api.get<SubmissionDetail>(ENDPOINTS.SUBMISSION_DETAIL(submissionId))).data;
}

export async function gradeSubmission(
	submissionId: number,
	answers: GradeAnswerItem[]
): Promise<SubmissionDetail> {
	return (await api.patch<SubmissionDetail>(ENDPOINTS.GRADE_SUBMISSION(submissionId), { answers }))
		.data;
}

export async function getCourseStats(courseId: number): Promise<TutorCourseStats> {
	return (await api.get<TutorCourseStats>(ENDPOINTS.COURSE_STATS(courseId))).data;
}

export async function getMyProfile(): Promise<Me> {
	return (await api.get<Me>(ENDPOINTS.ME)).data;
}

export async function updateMyProfile(payload: UpdateMePayload): Promise<Me> {
	return (await api.patch<Me>(ENDPOINTS.ME, payload)).data;
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
