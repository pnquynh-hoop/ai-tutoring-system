import { marked } from 'marked';
import DOMPurify from 'dompurify';

const ALLOWED_TAGS = [
	'p',
	'br',
	'strong',
	'em',
	'del',
	'code',
	'pre',
	'blockquote',
	'ul',
	'ol',
	'li',
	'h1',
	'h2',
	'h3',
	'h4',
	'h5',
	'h6',
	'hr',
	'a',
	'table',
	'thead',
	'tbody',
	'tr',
	'th',
	'td'
];

const ALLOWED_ATTR = ['href', 'title', 'align', 'target', 'rel'];

const HTML_ESCAPES: Record<string, string> = {
	'&': '&amp;',
	'<': '&lt;',
	'>': '&gt;',
	'"': '&quot;',
	"'": '&#39;'
};

function escapeHtml(text: string): string {
	return text.replace(/[&<>"']/g, (character) => HTML_ESCAPES[character]);
}

let linkHookAdded = false;

function addLinkHook() {
	if (linkHookAdded) return;

	DOMPurify.addHook('afterSanitizeAttributes', (node) => {
		if (node.tagName !== 'A') return;

		node.setAttribute('target', '_blank');
		node.setAttribute('rel', 'noopener noreferrer');
	});

	linkHookAdded = true;
}

export function renderMarkdown(source: string): string {
	if (!DOMPurify.isSupported) return `<p>${escapeHtml(source)}</p>`;

	addLinkHook();

	const html = marked.parse(source, { async: false, gfm: true, breaks: true });

	return DOMPurify.sanitize(html, { ALLOWED_TAGS, ALLOWED_ATTR });
}
