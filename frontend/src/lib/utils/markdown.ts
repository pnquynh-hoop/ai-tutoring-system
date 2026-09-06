export type InlineToken =
	| { kind: 'text'; text: string }
	| { kind: 'bold'; text: string }
	| { kind: 'italic'; text: string }
	| { kind: 'code'; text: string }
	| { kind: 'math'; text: string; display: boolean };

export type Block =
	| { kind: 'heading'; level: number; content: InlineToken[] }
	| { kind: 'paragraph'; content: InlineToken[] }
	| { kind: 'bullets'; items: InlineToken[][] }
	| { kind: 'numbers'; items: InlineToken[][] }
	| { kind: 'quote'; content: InlineToken[] }
	| { kind: 'code'; text: string }
	| { kind: 'rule' };

const INLINE_PATTERN =
	/(\$\$[^$]+\$\$|\$[^$\n]+\$|\*\*[^*]+\*\*|`[^`]+`|\*[^*\n]+\*|_[^_\n]+_)/g;

export function parseInline(line: string): InlineToken[] {
	const tokens: InlineToken[] = [];
	let cursor = 0;

	for (const match of line.matchAll(INLINE_PATTERN)) {
		const start = match.index ?? 0;
		if (start > cursor) {
			tokens.push({ kind: 'text', text: line.slice(cursor, start) });
		}

		const piece = match[0];
		if (piece.startsWith('$$')) {
			tokens.push({ kind: 'math', text: piece.slice(2, -2), display: true });
		} else if (piece.startsWith('$')) {
			tokens.push({ kind: 'math', text: piece.slice(1, -1), display: false });
		} else if (piece.startsWith('**')) {
			tokens.push({ kind: 'bold', text: piece.slice(2, -2) });
		} else if (piece.startsWith('`')) {
			tokens.push({ kind: 'code', text: piece.slice(1, -1) });
		} else {
			tokens.push({ kind: 'italic', text: piece.slice(1, -1) });
		}

		cursor = start + piece.length;
	}

	if (cursor < line.length) {
		tokens.push({ kind: 'text', text: line.slice(cursor) });
	}

	return tokens;
}

function isBullet(line: string): boolean {
	return /^\s*[-*+]\s+/.test(line);
}

function isNumbered(line: string): boolean {
	return /^\s*\d+[.)]\s+/.test(line);
}

function stripMarker(line: string): string {
	return line.replace(/^\s*(?:[-*+]|\d+[.)])\s+/, '');
}

export function parseMarkdown(source: string): Block[] {
	const lines = source.replace(/\r\n/g, '\n').split('\n');
	const blocks: Block[] = [];
	let index = 0;

	while (index < lines.length) {
		const line = lines[index];

		if (line.trim() === '') {
			index += 1;
			continue;
		}

		if (line.trim().startsWith('```')) {
			const body: string[] = [];
			index += 1;
			while (index < lines.length && !lines[index].trim().startsWith('```')) {
				body.push(lines[index]);
				index += 1;
			}
			index += 1;
			blocks.push({ kind: 'code', text: body.join('\n') });
			continue;
		}

		if (/^\s*(?:---+|\*\*\*+|___+)\s*$/.test(line)) {
			blocks.push({ kind: 'rule' });
			index += 1;
			continue;
		}

		const heading = /^(#{1,6})\s+(.*)$/.exec(line.trim());
		if (heading) {
			blocks.push({
				kind: 'heading',
				level: heading[1].length,
				content: parseInline(heading[2])
			});
			index += 1;
			continue;
		}

		if (line.trim().startsWith('>')) {
			const body: string[] = [];
			while (index < lines.length && lines[index].trim().startsWith('>')) {
				body.push(lines[index].trim().replace(/^>\s?/, ''));
				index += 1;
			}
			blocks.push({ kind: 'quote', content: parseInline(body.join(' ')) });
			continue;
		}

		if (isBullet(line) || isNumbered(line)) {
			const numbered = isNumbered(line);
			const items: InlineToken[][] = [];

			while (index < lines.length && (isBullet(lines[index]) || isNumbered(lines[index]))) {
				if (isNumbered(lines[index]) !== numbered) break;
				items.push(parseInline(stripMarker(lines[index])));
				index += 1;
			}

			blocks.push({ kind: numbered ? 'numbers' : 'bullets', items });
			continue;
		}

		const paragraph: string[] = [];
		while (
			index < lines.length &&
			lines[index].trim() !== '' &&
			!isBullet(lines[index]) &&
			!isNumbered(lines[index]) &&
			!lines[index].trim().startsWith('```') &&
			!lines[index].trim().startsWith('>') &&
			!/^#{1,6}\s/.test(lines[index].trim())
		) {
			paragraph.push(lines[index].trim());
			index += 1;
		}

		blocks.push({ kind: 'paragraph', content: parseInline(paragraph.join(' ')) });
	}

	return blocks;
}
