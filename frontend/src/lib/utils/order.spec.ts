import { describe, expect, it } from 'vitest';
import { nextOrder } from './order';

describe('nextOrder', () => {
	it('bắt đầu từ 1 khi chưa có phần tử nào', () => {
		expect(nextOrder([])).toBe(1);
	});

	it('lấy order lớn nhất + 1', () => {
		expect(nextOrder([{ order: 1 }, { order: 2 }, { order: 3 }])).toBe(4);
	});

	it('không đụng order đã tồn tại sau khi xoá phần tử ở giữa', () => {
		expect(nextOrder([{ order: 1 }, { order: 3 }])).toBe(4);
	});

	it('coi order null là 0', () => {
		expect(nextOrder([{ order: null }, { order: 2 }])).toBe(3);
	});
});
