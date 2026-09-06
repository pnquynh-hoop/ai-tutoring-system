export const FIELD_LIMITS = {
	title: 255,
	questionContent: 5000,
	explanation: 5000,
	answerContent: 1000,
	answerText: 10000,
	resourceContent: 50000,
	comment: 2000,
	tutorComment: 2000,
	url: 255,
	aiQuestion: 1000,
	timeLimitMinutes: 1440
} as const;

export const ENTITY_CAPS = {
	chaptersPerCourse: 20,
	lessonsPerChapter: 50,
	questionsPerAssignment: 100,
	answersPerQuestion: 5,
	itemsPerRequest: 200
} as const;

export function capError(current: number, cap: number, label: string): string {
	return current >= cap ? `${label} tối đa ${cap}, hiện đã có ${current}.` : '';
}

export function requiredError(value: string, label: string): string {
	return value.trim() ? '' : `${label} không được bỏ trống.`;
}

export function tooLongError(value: string, limit: number, label: string): string {
	const length = value.trim().length;
	return length > limit ? `${label} tối đa ${limit} ký tự, đang có ${length}.` : '';
}

export function textError(value: string, limit: number, label: string): string {
	return requiredError(value, label) || tooLongError(value, limit, label);
}

export function futureDateError(value: string, label: string): string {
	if (!value.trim()) return `${label} không được bỏ trống.`;
	const picked = new Date(value);
	if (Number.isNaN(picked.getTime())) return `${label} không hợp lệ.`;
	return picked.getTime() <= Date.now() ? `${label} phải sau thời điểm hiện tại.` : '';
}

export function rangeError(value: string, min: number, max: number, label: string): string {
	if (!value.trim()) return '';
	const parsed = Number(value);
	if (!Number.isInteger(parsed)) return `${label} phải là số nguyên.`;
	return parsed < min || parsed > max ? `${label} phải nằm trong khoảng ${min}-${max}.` : '';
}

export function hasError(errors: Record<string, string>): boolean {
	return Object.values(errors).some((message) => message !== '');
}

export function emailError(value: string, label: string): string {
	const required = requiredError(value, label);
	if (required) return required;
	return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim()) ? '' : `${label} không đúng định dạng.`;
}

export function phoneError(value: string, label: string): string {
	const required = requiredError(value, label);
	if (required) return required;
	return /^0\d{9}$/.test(value.trim()) ? '' : `${label} phải gồm 10 chữ số và bắt đầu bằng 0.`;
}

export const DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx', '.md', '.markdown'];
export const MAX_DOCUMENT_MB = 10;

export function documentFileError(file: File | null, label: string): string {
	if (!file) return `${label} không được bỏ trống.`;

	const name = file.name.toLowerCase();
	if (!DOCUMENT_EXTENSIONS.some((extension) => name.endsWith(extension))) {
		return `${label} chỉ chấp nhận ${DOCUMENT_EXTENSIONS.join(', ')}.`;
	}

	const sizeInMb = file.size / (1024 * 1024);
	return sizeInMb > MAX_DOCUMENT_MB ? `${label} tối đa ${MAX_DOCUMENT_MB} MB.` : '';
}

export function quotaLabel(current: number, cap: number): string {
	return `${current}/${cap}`;
}

export function isNearCap(current: number, cap: number, warnWhenLeft = 5): boolean {
	return cap - current <= warnWhenLeft;
}

export const IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp'];
export const MAX_IMAGE_MB = 2;

export function imageFileError(file: File | null, label: string): string {
	if (!file) return `${label} không được bỏ trống.`;

	const name = file.name.toLowerCase();
	if (!IMAGE_EXTENSIONS.some((extension) => name.endsWith(extension))) {
		return `${label} chỉ chấp nhận ${IMAGE_EXTENSIONS.join(', ')}.`;
	}

	const sizeInMb = file.size / (1024 * 1024);
	return sizeInMb > MAX_IMAGE_MB ? `${label} tối đa ${MAX_IMAGE_MB} MB.` : '';
}
