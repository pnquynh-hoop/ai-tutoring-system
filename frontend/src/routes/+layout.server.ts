// Lấy thông tin user từ locals do hooks thiết lập
export const load = ({ locals }) => {
	return { user: locals.user };
};
