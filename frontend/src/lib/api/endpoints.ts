export const ENDPOINTS = {
	LOGIN: 'users/login/',
	REFRESH: 'users/refresh/',
	LOGOUT: 'users/logout/',
	ME: 'users/me/',

	// Khóa học
	COURSES: 'courses/',
	STATS: 'courses/statistic/',
	COURSE_DETAIL: (courseId: string | number) => `courses/${courseId}/`,
	COURSE_TREE: (courseId: string | number) => `courses/${courseId}/tree/`,
	COURSE_OVERVIEW: (courseId: string | number) => `courses/${courseId}/overview/`,
	CHAPTER_STATS: (courseId: string | number) => `courses/${courseId}/chapter-stats/`,

	// Chương - gia sư phụ trách khóa học mới được thao tác
	CHAPTERS: 'chapters/',
	CHAPTER_DETAIL: (chapterId: string | number) => `chapters/${chapterId}/`,

	// Bài học
	LESSONS: 'lessons/',
	LESSONS_DETAIL: (lessonId: string | number) => `lessons/${lessonId}/`,
	COMPLETE_LESSON: (lessonId: string | number) => `lessons/${lessonId}/complete/`,
	COMMENTS: (lessonId: string | number) => `lessons/${lessonId}/comments/`,
	TOGGLE_RIGHT: (commentId: string | number) => `comments/${commentId}/toggle-mark-right/`,

	// Tài nguyên bài học - list bắt buộc kèm ?lesson=<id>
	RESOURCES: 'resources/',
	RESOURCES_BY_LESSON: (lessonId: string | number) => `resources/?lesson=${lessonId}`,
	RESOURCE_DETAIL: (resourceId: string | number) => `resources/${resourceId}/`,

	COURSE_STATS: (courseId: string | number) => `courses/${courseId}/stats/`,

	// Bài tập
	ASSIGNMENTS: 'assignments/',
	ASSIGNMENT_DETAIL: (assignmentId: string | number) => `assignments/${assignmentId}/`,
	QUESTIONS: (assignmentId: string | number) => `assignments/${assignmentId}/questions/`,
	START_ASSIGNMENT: (assignmentId: string | number) => `assignments/${assignmentId}/start/`,
	SUBMIT_ASSIGNMENT: (assignmentId: string | number) => `assignments/${assignmentId}/submit/`,
	SUBMISSIONS: 'submissions/',
	SUBMISSION_DETAIL: (submissionId: string | number) => `submissions/${submissionId}/`,
	GRADE_SUBMISSION: (submissionId: string | number) => `submissions/${submissionId}/grade/`,

	// Soạn câu hỏi (gia sư)
	QUESTIONS_ADMIN: 'questions/',
	QUESTIONS_BY_ASSIGNMENT: (assignmentId: string | number) =>
		`questions/?assignment=${assignmentId}`,
	QUESTION_DETAIL: (questionId: string | number) => `questions/${questionId}/`,

	// Tài khoản
	CHANGE_PASSWORD: 'users/change-password/',
	ACADEMIC_LEVELS: 'users/academic-levels/',

	// Danh mục dùng chung
	GRADES: 'grades/',

	// Trợ lý AI
	RAG_ASK: 'rag/ask/',
	RAG_GENERATE_EXERCISES: 'rag/generate-exercises/'
};