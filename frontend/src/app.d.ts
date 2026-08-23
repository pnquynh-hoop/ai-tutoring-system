import type { SessionUser } from '$lib/api/entities';

declare global {
	namespace App {
		interface Locals {
			user: SessionUser | null;
		}
	}
}

export {};
