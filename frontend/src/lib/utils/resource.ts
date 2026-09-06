export function fileNameFromUrl(url: string | null | undefined): string {
	if (!url) return '';

	const withoutQuery = url.split(/[?#]/)[0];
	const segment = decodeURIComponent(withoutQuery.split('/').pop() ?? '');
	if (!segment) return '';

	const dotIndex = segment.lastIndexOf('.');
	const baseName = dotIndex > 0 ? segment.slice(0, dotIndex) : segment;

	if (baseName.length > 60) return '';
	if (/^[0-9a-f]{12,}$/i.test(baseName)) return '';

	const letterCount = baseName.replace(/[^\p{L}]/gu, '').length;
	if (letterCount < 3) return '';

	return segment;
}
