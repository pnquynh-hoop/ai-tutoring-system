# Hệ thống quản lý trung tâm gia sư trực tuyến tích hợp trợ lý AI

## 1. Bối cảnh nghiệp vụ

Đề tài xây dựng hệ thống quản lý cho một trung tâm gia sư trực tuyến dạy chương trình phổ thông, có tích hợp trợ lý AI. Nghiệp vụ của trung tâm gồm bốn mảng liên kết với nhau:

- **Quản lý học thuật.** Trung tâm duy trì một kho tài liệu dùng chung — sách giáo khoa, tài liệu tham khảo — được phân loại theo môn học và khối lớp. Kho này thuộc về trung tâm chứ không thuộc về một lớp cụ thể nào.
- **Tổ chức giảng dạy.** Mỗi gia sư phụ trách một hoặc nhiều khoá học. Gia sư tự biên soạn nội dung khoá học của mình theo cấu trúc phân cấp, và tự quyết định thời điểm công khai từng phần cho học sinh.
- **Đánh giá.** Gia sư ra bài tập theo chương; học sinh làm bài trong giới hạn số lượt và thời gian; hệ thống chấm tự động phần trắc nghiệm và điền khuyết, còn phần tự luận do gia sư chấm tay.
- **Hỗ trợ bằng AI.** Học sinh có thể đặt câu hỏi cho trợ lý AI và yêu cầu sinh bài tập luyện tập. Trợ lý trả lời dựa trên tài liệu của chính khoá học và sách giáo khoa, có trích dẫn nguồn. Mức độ đã triển khai của từng phần được nêu ở mục 11.

Bài toán trung tâm mà hệ thống giải quyết là: làm sao để trợ lý AI trả lời đúng theo giáo trình của trung tâm, có dẫn nguồn kiểm chứng được, và mỗi học sinh chỉ tiếp cận được tài liệu thuộc phạm vi mình được phép.

## 2. Các vai trò trong hệ thống

Hệ thống phân biệt ba vai trò, cài đặt bằng cơ chế nhóm người dùng (group) của Django:

| Vai trò | Phạm vi hoạt động |
|---|---|
| Học sinh (Student) | Học bài trong khoá đã được ghi danh, làm bài tập, bình luận, hỏi trợ lý AI |
| Gia sư (Tutor) | Biên soạn nội dung khoá học mình phụ trách, ra đề, chấm bài tự luận |
| Quản trị viên (Admin) | Quản lý tài khoản, danh mục môn học, khối lớp, kho tài liệu trung tâm và việc ghi danh |

Một tài khoản người dùng gồm thông tin định danh chung — thư điện tử, số điện thoại (cả hai đều là duy nhất trong hệ thống), họ tên, ảnh đại diện — cộng với một hồ sơ chuyên biệt theo vai trò:

- **Hồ sơ gia sư** lưu giới thiệu ngắn, trình độ, số năm kinh nghiệm và cờ đã xác minh. Cờ xác minh do quản trị viên đặt, gia sư không tự sửa được.
- **Hồ sơ học sinh** lưu khối lớp đang học, mục tiêu học tập và học lực tự đánh giá theo bốn mức: yếu, trung bình, khá, giỏi.

Đây là quan hệ một-một với tài khoản: một người dùng có tối đa một hồ sơ mỗi loại. Cách tách này cho phép thêm vai trò mới về sau mà không phải nhồi thêm cột vào bảng người dùng.

## 3. Cấu trúc tổ chức nội dung học tập

### 3.1 Danh mục học thuật

Hai thực thể nền, do quản trị viên quản lý và dùng chung cho toàn hệ thống:

- **Môn học (Subject):** tên duy nhất, kèm mô tả. Ví dụ: Toán, Tiếng Anh, Vật lý.
- **Khối lớp (Grade):** một số nguyên duy nhất, hiển thị dưới dạng "Lớp 10", "Lớp 11".

Mọi khoá học và mọi tài liệu đều phải gắn với đúng một cặp môn học và khối lớp. Cặp này là trục phân loại xuyên suốt hệ thống.

### 3.2 Tài liệu trung tâm

Tài liệu (Material) là học liệu thuộc sở hữu trung tâm — sách giáo khoa, đề cương, tài liệu tham khảo — phân loại theo môn và khối, không gắn với khoá học cụ thể nào. Trong hệ thống RAG, đây là nguồn kiến thức nền: mọi học sinh đều truy xuất được, bất kể đang học khoá nào.

Tài liệu có một quy tắc lưu trữ đáng chú ý. Tệp dưới 10MB được đẩy lên dịch vụ lưu trữ đám mây Cloudinary; tệp từ 10MB đến 100MB được lưu trực tiếp trên đĩa máy chủ. Lý do là gói Cloudinary miễn phí giới hạn dung lượng mỗi tệp, trong khi sách giáo khoa bản scan thường vượt ngưỡng đó. Mỗi tài liệu chỉ tồn tại ở đúng một trong hai nơi.

### 3.3 Khoá học và cây nội dung

Nội dung giảng dạy tổ chức theo cấu trúc bốn tầng:

- **Khoá học (Course)** là đơn vị lớn nhất, gắn với một môn học, một khối lớp và một gia sư phụ trách. Tên khoá học là duy nhất toàn hệ thống.
- **Chương (Chapter)** chia khoá học thành các phần lớn, có số thứ tự. Trong một khoá học, số thứ tự và tiêu đề chương đều phải duy nhất — ràng buộc này ngăn việc tạo nhầm hai chương cùng số hoặc trùng tên.
- **Bài học (Lesson)** là đơn vị học tập nhỏ nhất mà học sinh tương tác, nằm trong một chương, cũng có số thứ tự duy nhất trong phạm vi chương.
- **Tài nguyên bài học (LearningResource)** là học liệu cụ thể gắn với một bài học, thuộc một trong ba dạng: đường dẫn video, tệp tài liệu, hoặc nội dung văn bản do gia sư nhập trực tiếp. Đây là nguồn tri thức riêng của khoá học trong hệ thống RAG — chỉ thành viên của khoá mới truy xuất được.

Cần phân biệt rõ hai khái niệm dễ nhầm:

| | Tài liệu (Material) | Tài nguyên bài học (LearningResource) |
|---|---|---|
| Chủ sở hữu | Trung tâm | Gia sư phụ trách khoá |
| Phân loại theo | Môn học + khối lớp | Bài học cụ thể |
| Ai truy xuất được | Mọi học sinh | Chỉ thành viên khoá học |
| Có trạng thái nháp | Không | Có |

### 3.4 Ghi danh

Ghi danh (Enrollment) là bảng trung gian nối học sinh với khoá học, cài đặt quan hệ nhiều-nhiều: một học sinh học nhiều khoá, một khoá có nhiều học sinh. Ràng buộc duy nhất trên cặp khoá học và học sinh bảo đảm không tạo được bản ghi ghi danh trùng.

Ghi danh không đơn thuần là một dòng dữ liệu — nó là điều kiện phân quyền. Toàn bộ nội dung khoá học, bài tập và phạm vi truy xuất của trợ lý AI đều kiểm tra bản ghi ghi danh đang hoạt động trước khi cho phép truy cập.

## 4. Đánh giá và chấm điểm

### 4.1 Bài tập và câu hỏi

Bài tập (Assignment) gắn với chương theo quan hệ một-một: mỗi chương có tối đa một bài tập, và bài tập đó thuộc về đúng một chương. Bài tập có hạn nộp, và tuỳ chọn giới hạn thời gian làm bài tính bằng phút.

Câu hỏi (Question) thuộc một bài tập, có số thứ tự duy nhất trong bài, và thuộc một trong ba loại:

- **Trắc nghiệm:** học sinh chọn một trong các phương án cho sẵn.
- **Điền khuyết:** học sinh gõ đáp án, hệ thống so khớp với đáp án chuẩn.
- **Tự luận:** học sinh viết bài, gia sư chấm tay.

Mỗi câu hỏi kèm lời giải chi tiết và, với hai loại đầu, một danh sách phương án (Answer) trong đó có cờ đánh dấu phương án đúng.

Điểm của từng câu do gia sư tự đặt qua trường `point` của câu hỏi, chứ không chia đều. Giá trị phải là bội của 0.05 và nằm trong khoảng từ 0.05 tới 10. Ràng buộc quan trọng nằm ở lúc công khai: bài tập chỉ công khai được khi mọi câu đều đã có điểm và tổng điểm các câu đúng bằng 10. Nhờ vậy thang điểm 10 được bảo đảm ngay từ đề, không cần quy đổi khi chấm.

Trước đây hệ thống chia đều 10 điểm cho số câu; migration `assignments/0011_split_points_for_existing_questions` là bước chuyển dữ liệu cũ sang cách đặt điểm theo từng câu.

### 4.2 Lượt làm bài

Bài nộp (Submission) đại diện cho một lượt làm bài của một học sinh với một bài tập, chứ không phải kết quả cuối cùng. Một học sinh có tối đa 3 lượt cho mỗi bài tập.

Vòng đời một lượt gồm hai mốc thời gian:

- **Bắt đầu:** hệ thống tạo bản ghi với thời điểm bắt đầu, điểm để trống. Nếu bài tập có giới hạn thời gian, hạn chót của lượt này được tính bằng thời điểm bắt đầu cộng số phút cho phép.
- **Nộp:** hệ thống ghi lại thời điểm nộp và tính điểm.

Lượt chưa nộp gọi là lượt đang mở. Học sinh chỉ được có tối đa một lượt đang mở tại một thời điểm: bấm bắt đầu lần nữa sẽ trả về đúng lượt đang mở đó thay vì tạo lượt mới. Nếu lượt đang mở đã quá hạn, hệ thống tự đóng lượt đó lại rồi mới cho mở lượt mới. Lượt bị đóng vẫn được chấm bình thường theo phần bài làm đã lưu được, chứ không mặc định 0 điểm — những câu chưa trả lời mới được 0.

Việc đóng lượt quá hạn không chờ học sinh quay lại. Một tác vụ định kỳ chạy mỗi 5 phút quét mọi lượt còn mở, lượt nào vượt hạn nộp của bài tập hoặc hạn riêng của lượt thì đóng và chấm ngay.

Hai loại thời hạn hoạt động độc lập và đều được kiểm tra: hạn nộp của bài tập (mốc tuyệt đối, chung cho cả lớp) và hạn của lượt làm (tính riêng cho từng học sinh từ lúc bắt đầu). Khi nộp, hệ thống cho phép trễ tối đa 30 giây so với hạn lượt làm, để bù cho độ trễ mạng.

Câu trả lời của học sinh (StudentAnswer) lưu bài làm cho từng câu: phương án đã chọn với câu trắc nghiệm, hoặc nội dung văn bản với câu điền khuyết và tự luận, kèm điểm số và nhận xét của gia sư.

### 4.3 Cơ chế chấm

Chấm chia thành hai giai đoạn:

**Chấm tự động ngay khi nộp.** Câu trắc nghiệm được chấm bằng cách đối chiếu phương án đã chọn với cờ đáp án đúng. Câu điền khuyết được chấm bằng so khớp chuỗi sau khi cắt khoảng trắng thừa và chuyển về chữ thường. Câu tự luận để điểm trống.

**Chấm tay sau đó.** Gia sư chấm từng câu tự luận, nhập điểm và nhận xét. Điểm mỗi câu không được vượt quá trọng số của câu đó.

Điểm tổng của lượt làm tuân theo một quy tắc quan trọng: chừng nào còn một câu chưa có điểm thì điểm tổng vẫn để trống, chứ không phải bằng tổng của các câu đã chấm. Điều này bảo đảm bài có phần tự luận chưa chấm không hiển thị một con số gây hiểu nhầm cho học sinh.

Điểm tổng chỉ xuất hiện khi tất cả các câu đều đã có điểm, và bằng đúng tổng điểm các câu — không có bước quy đổi hay làm tròn nào. Sở dĩ không cần quy đổi là vì tổng điểm các câu đã được ép bằng 10 từ lúc công khai bài tập.

## 5. Theo dõi học tập và tương tác

### 5.1 Tiến độ và chuỗi ngày học

Tiến độ bài học (LessonProgress) ghi nhận việc một học sinh đã hoàn thành một bài học, kèm thời điểm hoàn thành. Từ dữ liệu này hệ thống suy ra hai chỉ số:

- **Phần trăm tiến độ khoá học** — tỷ lệ bài học đã hoàn thành trên tổng số bài học đã công khai của khoá. Bài học còn ở dạng nháp không tính vào mẫu số, tránh việc tiến độ của học sinh tụt xuống mỗi khi gia sư soạn thêm bài mới chưa công khai.
- **Chuỗi ngày học liên tục (streak)** — số ngày liên tiếp gần nhất mà học sinh có hoàn thành ít nhất một bài. Chuỗi được tính lùi từ hôm nay hoặc hôm qua; nếu ngày hoàn thành gần nhất cũ hơn hôm qua thì chuỗi bằng 0. Đây là một cơ chế tạo động lực học tập phổ biến trong các ứng dụng giáo dục, dựa trên nguyên lý duy trì thói quen.

### 5.2 Bình luận

Bình luận (Comment) gắn với một bài học, cho phép trả lời lồng nhau qua tham chiếu tới bình luận cha — tạo thành cấu trúc cây thảo luận. Gia sư có thể đánh dấu một bình luận là câu trả lời đúng, hệ thống ghi lại ai đánh dấu và vào lúc nào. Cơ chế này giúp học sinh vào sau nhận ra ngay câu trả lời đã được xác nhận trong một luồng thảo luận dài.

### 5.3 Lưu bài làm dở

Học sinh đang làm bài không bị mất bài khi mất mạng hoặc đóng nhầm trình duyệt, nhờ hai lớp lưu tạm. Phía trình duyệt, bài làm được lưu vào bộ nhớ cục bộ theo mã lượt làm sau mỗi lần thay đổi. Phía máy chủ, giao diện gọi điểm truy cập lưu nháp mỗi 30 giây và mỗi lần học sinh chuyển câu.

Bản ghi câu trả lời dùng cơ chế ghi đè theo cặp (lượt làm, câu hỏi) nên lưu nháp nhiều lần không sinh ra bản ghi trùng. Đây cũng là dữ liệu dùng để chấm khi một lượt bị đóng do quá hạn.

## 6. Ba khái niệm xuyên suốt mọi thực thể

Hệ thống dùng kỹ thuật lớp trừu tượng (abstract model) để gom các trường và hành vi lặp lại. Lớp trừu tượng không tạo bảng riêng trong cơ sở dữ liệu; các trường của nó được sao vào bảng của từng lớp con. Có ba lớp như vậy, và ba khái niệm nghiệp vụ tương ứng.

### 6.1 Xoá mềm

Thay vì xoá hẳn bản ghi khỏi cơ sở dữ liệu, hệ thống chỉ hạ cờ `is_active` xuống. Mọi truy vấn dữ liệu đều lọc theo cờ này nên bản ghi biến mất khỏi giao diện, nhưng vẫn còn trong bảng.

**Vì sao cần.** Dữ liệu học tập có ràng buộc tham chiếu dày đặc: xoá cứng một khoá học sẽ kéo theo bài nộp, điểm số và tiến độ của học sinh. Xoá mềm giữ được toàn vẹn lịch sử học tập và cho phép khôi phục khi xoá nhầm. Kèm theo cờ này là hai mốc thời gian tạo và cập nhật, tự động ghi bởi hệ thống.

### 6.2 Nháp và công khai

Nội dung do gia sư biên soạn — chương, bài học, tài nguyên bài học, bài tập — có một trường thời điểm công khai. Trường để trống nghĩa là bản nháp, chỉ gia sư thấy; có giá trị nghĩa là đã công khai, học sinh mới thấy.

**Vì sao cần.** Gia sư cần soạn dần một chương trong nhiều buổi mà không để học sinh nhìn thấy nội dung dở dang. Cách dùng một mốc thời gian thay cho một cờ đúng/sai cho phép biết được thời điểm công khai, phục vụ thống kê và sắp xếp.

Lưu ý: tài liệu trung tâm không có trạng thái này, vì nó do quản trị viên quản lý và không có khái niệm bản nháp.

### 6.3 Trạng thái lập chỉ mục RAG

Mọi học liệu có thể đưa vào hệ thống AI — tài liệu trung tâm và tài nguyên bài học — mang thêm bốn trường theo dõi tiến trình nạp vào cơ sở dữ liệu vector: trạng thái, số đoạn đã nạp, lý do lỗi và thời điểm nạp xong.

Trạng thái đi qua bốn giá trị: chờ nạp (mặc định khi vừa tạo), đang nạp, đã nạp, nạp lỗi.

**Vì sao cần.** Quá trình nạp một cuốn sách hàng trăm trang mất hàng chục phút, có thể thất bại giữa chừng vì lỗi mạng hoặc vì vượt hạn mức gọi API. Lưu trạng thái ngay trong bảng dữ liệu cho phép biết tài liệu nào đã sẵn sàng cho trợ lý AI, tài liệu nào cần nạp lại, và vì sao lần nạp trước thất bại.

## 7. Mô hình phân quyền hai tầng

Đây là khái niệm quan trọng nhất khi phân tích và thiết kế hệ thống này, vì nó xuất hiện ở hầu hết mọi điểm truy cập.

**Tầng thứ nhất — quyền theo vai trò.** Kiểm tra người dùng thuộc nhóm nào. Ví dụ: chỉ gia sư mới được tạo chương; chỉ học sinh mới được nộp bài.

**Tầng thứ hai — quyền theo quan hệ với khoá học.** Kiểm tra người dùng có liên quan tới đúng khoá học chứa đối tượng đang thao tác hay không. Ba mức quan hệ:

- **Gia sư phụ trách:** người dùng chính là gia sư được gán cho khoá học đó.
- **Học sinh đã ghi danh:** tồn tại bản ghi ghi danh đang hoạt động.
- **Thành viên khoá học:** là một trong hai loại trên.

Điểm cốt lõi là mọi đối tượng trong hệ thống đều truy ngược được về một khoá học. Từ một bình luận, hệ thống đi ngược lên bài học, rồi chương, rồi khoá học. Từ một bài nộp, đi ngược lên bài tập, rồi chương, rồi khoá học. Nhờ chuỗi truy ngược này, quy tắc phân quyền chỉ cần viết một lần và áp dụng được cho mọi loại đối tượng.

Một biến thể thường gặp là **đọc thì mở, ghi thì hẹp**: thành viên khoá học đọc được nội dung, nhưng chỉ gia sư phụ trách mới sửa được. Với bài nộp còn có quy tắc riêng: học sinh chỉ xem được bài của chính mình, gia sư phụ trách xem được của mọi học sinh trong khoá.

Trường hợp đặc biệt là thao tác tạo mới, khi đối tượng chưa tồn tại nên chưa truy ngược được — tầng thứ hai không có gì để kiểm tra. Hệ thống chuyển việc kiểm tra đó xuống serializer: mỗi serializer tạo mới có một hàm kiểm tra riêng cho trường khoá ngoại trỏ tới đối tượng cha, và hàm đó so người phụ trách khoá học với người đang gửi yêu cầu. Tạo chương thì kiểm tra trên khoá học, tạo bài học thì kiểm tra trên chương, tạo câu hỏi thì kiểm tra trên bài tập.

Cách này có một hệ quả đáng lưu ý: dữ liệu vào từ thân yêu cầu được kiểm tra ở serializer, còn dữ liệu vào từ đường dẫn được kiểm tra ở lớp phân quyền. Khi thêm một điểm truy cập tạo mới, phải nhớ viết hàm kiểm tra ở serializer, vì lớp phân quyền sẽ không tự bắt được.

## 8. Nền tảng kỹ thuật

### 8.1 Kiến trúc tách rời máy khách và máy chủ

Hệ thống theo kiến trúc API thuần: máy chủ chỉ trả về dữ liệu dạng JSON qua giao thức HTTP, không sinh giao diện. Giao diện là một ứng dụng web riêng chạy trên trình duyệt, gọi API để lấy dữ liệu.

REST (Representational State Transfer) là phong cách thiết kế API dựa trên việc ánh xạ mỗi loại tài nguyên thành một đường dẫn, và mỗi thao tác thành một động từ HTTP: GET để đọc, POST để tạo, PATCH để sửa một phần, DELETE để xoá. Toàn bộ API của hệ thống nằm dưới tiền tố phiên bản `/api/v1/`, cho phép về sau ra phiên bản mới mà không phá vỡ máy khách cũ.

Tài liệu API được sinh tự động theo chuẩn OpenAPI từ chính mã nguồn, truy cập qua giao diện Swagger. Cách này bảo đảm tài liệu luôn khớp với mã, khác với việc viết tài liệu tay dễ lệch theo thời gian.

### 8.2 Ánh xạ đối tượng - quan hệ

ORM (Object-Relational Mapping) là lớp trung gian cho phép thao tác với cơ sở dữ liệu quan hệ thông qua các lớp và đối tượng của ngôn ngữ lập trình, thay vì viết câu lệnh SQL. Mỗi lớp mô hình tương ứng một bảng, mỗi thuộc tính tương ứng một cột, mỗi đối tượng tương ứng một dòng.

Hai kỹ thuật tối ưu được dùng xuyên suốt hệ thống:

- **Nạp trước quan hệ một chiều:** khi lấy danh sách khoá học kèm thông tin gia sư, ORM gộp thành một câu lệnh có phép nối bảng thay vì truy vấn riêng cho từng khoá.
- **Nạp trước quan hệ nhiều chiều:** khi lấy danh sách câu hỏi kèm các phương án, ORM dùng thêm một câu lệnh chung cho tất cả thay vì mỗi câu hỏi một lần truy vấn.

Không có hai kỹ thuật này, một trang danh sách 20 phần tử có thể sinh ra hàng chục câu lệnh cơ sở dữ liệu — hiện tượng thường gọi là truy vấn N+1.

Ngoài ra, các phép thống kê nặng như tính phần trăm tiến độ được viết dưới dạng biểu thức truy vấn để cơ sở dữ liệu tính trực tiếp, thay vì tải toàn bộ dữ liệu lên rồi tính bằng Python.

### 8.3 Xác thực bằng JWT lưu trong cookie

JWT (JSON Web Token) là chuỗi ký tự đã ký số, chứa thông tin định danh người dùng. Máy chủ không cần lưu phiên đăng nhập; nó chỉ cần kiểm tra chữ ký của chuỗi là biết được người gửi là ai.

Hệ thống dùng hai loại token:

- **Token truy cập**, hiệu lực 15 phút, gửi kèm mỗi yêu cầu để xác thực.
- **Token làm mới**, hiệu lực 7 ngày, chỉ dùng để xin token truy cập mới khi token cũ hết hạn.

Điểm thiết kế đáng chú ý: token không được trả về cho mã JavaScript mà được đặt vào cookie có cờ `HttpOnly`. Cờ này khiến trình duyệt không cho mã JavaScript đọc cookie, chỉ tự động gửi kèm khi gọi API. Mục đích là chống tấn công XSS (Cross-Site Scripting) — nếu kẻ tấn công chèn được mã độc vào trang, mã đó vẫn không đánh cắp được token.

Đổi lại, vì trình duyệt gửi cookie tự động, hệ thống trở nên dễ bị tấn công CSRF (Cross-Site Request Forgery) — trang web độc lừa trình duyệt gửi yêu cầu thay người dùng. Hệ thống chống lại bằng ba lớp: cookie đặt thuộc tính `SameSite=Lax` để trình duyệt không gửi cookie khi yêu cầu xuất phát từ trang khác, danh sách nguồn gốc được phép gọi API, và cơ chế token CSRF của Django.

Token làm mới được xoay vòng: mỗi lần dùng sẽ sinh token mới và đưa token cũ vào danh sách đen. Nhờ đó, nếu token bị đánh cắp và kẻ tấn công dùng trước, người dùng thật sẽ bị đăng xuất — dấu hiệu để phát hiện sự cố.

### 8.4 Giới hạn tần suất gọi

Các điểm truy cập AI bị giới hạn 30 lượt mỗi giờ cho mỗi người dùng. Đây không chỉ là biện pháp kỹ thuật mà là ràng buộc nghiệp vụ: mỗi lượt hỏi trợ lý AI phát sinh chi phí gọi API tới nhà cung cấp mô hình, nên phải chặn việc gọi quá mức dù vô tình hay cố ý.

### 8.5 Kiểm tra tệp tải lên

Hệ thống kiểm tra tệp tải lên theo ba lớp, không chỉ dựa vào tên tệp:

1. Phần mở rộng phải nằm trong danh sách cho phép.
2. Kiểu nội dung do trình duyệt khai báo phải khớp với phần mở rộng.
3. Chữ ký nhị phân — vài byte đầu của tệp — phải đúng với định dạng khai báo. Tệp PDF thật luôn bắt đầu bằng `%PDF-`; tệp docx bắt đầu bằng chữ ký của định dạng nén ZIP.

Lớp thứ ba là lớp quan trọng nhất, vì hai lớp đầu đều do phía máy khách cung cấp và có thể giả mạo. Giới hạn dung lượng: ảnh 2MB, tài liệu bài học 10MB, tài liệu trung tâm 100MB.

## 9. Khái niệm nền tảng về AI trong hệ thống

Phần này chỉ nêu các thuật ngữ cần thiết để đọc phần thiết kế; nguyên lý chi tiết trình bày ở chương phương pháp.

- **Mô hình ngôn ngữ lớn (LLM)** là mô hình học sâu được huấn luyện trên khối lượng văn bản lớn, có khả năng sinh văn bản theo ngữ cảnh được cung cấp. Hạn chế cố hữu là nó chỉ biết tri thức có trong dữ liệu huấn luyện và có xu hướng bịa — sinh ra thông tin nghe hợp lý nhưng sai sự thật.
- **Sinh có tăng cường truy xuất (RAG)** là kỹ thuật khắc phục hạn chế trên bằng cách truy xuất tài liệu liên quan từ kho riêng rồi đưa kèm vào lời nhắc, buộc mô hình trả lời dựa trên tài liệu đó.
- **Vector nhúng (embedding)** là biểu diễn một đoạn văn bản thành một dãy số thực, sao cho hai đoạn gần nhau về nghĩa thì hai vector gần nhau về khoảng cách hình học. Đây là thứ cho phép tìm kiếm theo ngữ nghĩa thay vì theo từ khoá.
- **Đoạn văn bản (chunk)** là đơn vị nhỏ mà tài liệu được cắt ra trước khi tạo vector. Cắt nhỏ là bắt buộc vì mô hình nhúng có giới hạn độ dài đầu vào, và vì một vector chỉ biểu diễn tốt khi đoạn văn bản có nội dung tập trung.
- **Cơ sở dữ liệu vector** là hệ lưu trữ chuyên dụng cho vector, hỗ trợ tìm k phần tử gần nhất với một vector truy vấn.
- **Lời nhắc (prompt)** là văn bản đầu vào gửi cho mô hình, gồm chỉ dẫn hành vi, ngữ cảnh tài liệu và câu hỏi của người dùng. Chất lượng lời nhắc quyết định phần lớn chất lượng câu trả lời.
- **Tính bám nguồn (grounding)** là mức độ câu trả lời dựa trên tài liệu được cung cấp thay vì dựa trên trí nhớ của mô hình. Hệ thống đánh dấu rõ mỗi câu trả lời là có bám nguồn hay không, và chỉ hiển thị trích dẫn cho loại có bám nguồn.

## 10. Bảng thuật ngữ

| Thuật ngữ | Tên trong hệ thống | Ý nghĩa nghiệp vụ |
|---|---|---|
| Môn học | Subject | Môn trong chương trình phổ thông |
| Khối lớp | Grade | Lớp 10, 11, 12… |
| Tài liệu | Material | Học liệu chung của trung tâm |
| Khoá học | Course | Lớp học do một gia sư phụ trách |
| Ghi danh | Enrollment | Bản ghi học sinh tham gia khoá học |
| Chương | Chapter | Phần lớn trong khoá học |
| Bài học | Lesson | Đơn vị học tập nhỏ nhất |
| Tài nguyên bài học | LearningResource | Học liệu gắn với một bài học |
| Tiến độ bài học | LessonProgress | Ghi nhận học sinh hoàn thành bài học |
| Bình luận | Comment | Thảo luận dưới bài học, có trả lời lồng nhau |
| Bài tập | Assignment | Đề bài gắn với một chương |
| Câu hỏi | Question | Một câu trong bài tập |
| Phương án | Answer | Lựa chọn của câu trắc nghiệm, kèm cờ đúng/sai |
| Bài nộp | Submission | Một lượt làm bài của một học sinh |
| Câu trả lời | StudentAnswer | Bài làm của học sinh cho một câu hỏi |
| Xoá mềm | is_active | Ẩn bản ghi thay vì xoá khỏi cơ sở dữ liệu |
| Nháp / công khai | published_at | Để trống là nháp, có giá trị là đã công khai |
| Trạng thái nạp AI | rag_status | Chờ nạp, đang nạp, đã nạp, nạp lỗi |

## 11. Trạng thái triển khai

Mục này phân biệt phần đã chạy được đầu-cuối với phần mới hoàn thành ở tầng xử lý. Đây là hiện trạng tại thời điểm viết tài liệu, không phải mô tả thiết kế.

### 11.1 Đã chạy đầu-cuối

Trợ lý hỏi đáp là phần hoàn chỉnh nhất: học sinh đặt câu hỏi trong giao diện, hệ thống truy xuất tài liệu theo phạm vi của học sinh đó, sinh câu trả lời có trích dẫn nguồn và đánh dấu rõ câu trả lời có bám tài liệu hay không.

Cùng nhóm này còn có: soạn và công khai nội dung khoá học, làm bài và chấm bài, thống kê tiến độ, bình luận dưới bài học, và toàn bộ luồng nạp tài liệu trung tâm vào kho vector.

### 11.2 Xong phần xử lý, chưa gắn giao diện

Sinh bài tập luyện tập bằng AI đã hoàn chỉnh ở tầng xử lý — nhận môn, bài học, loại câu hỏi và số lượng, trả về danh sách câu hỏi kèm phương án và lời giải theo đúng cấu trúc dữ liệu. Phần còn thiếu là màn hình cho học sinh gọi chức năng này.

Bảng lưu lịch sử hỏi đáp với trợ lý AI đã có trong cơ sở dữ liệu nhưng chưa được ghi vào. Mỗi lượt hỏi hiện trả kết quả thẳng cho người dùng rồi kết thúc, không lưu lại. Hệ quả là chưa thống kê được học sinh hay hỏi gì, và chưa có dữ liệu để đánh giá chất lượng trả lời theo thời gian.

### 11.3 Trạng thái dữ liệu của kho vector

Kho vector hiện chứa 643 đoạn văn bản, toàn bộ đến từ tài liệu trung tâm — chủ yếu là sách giáo khoa Tiếng Anh 12 và các tài liệu ôn tập kèm theo, cả 15 tài liệu đều đã nạp xong.

Nhánh tài nguyên bài học thì ngược lại: 81 tài nguyên do gia sư tạo đều đang ở trạng thái chờ nạp, chưa tài nguyên nào được đưa vào kho. Nghĩa là đường truy xuất theo khoá học đã cài đặt và kiểm thử xong, nhưng chưa có dữ liệu thật chạy qua. Trên thực tế, câu trả lời của trợ lý hiện lấy nguồn từ tài liệu trung tâm.

### 11.4 Hạn chế đã biết

**Phạm vi truy xuất theo bài học chưa được kiểm tra quyền.** Khi học sinh gửi câu hỏi, hệ thống kiểm tra học sinh đó có ghi danh khoá học hay không, nhưng không kiểm tra bài học đi kèm có thuộc khoá đó không. Vì ba nhánh phạm vi được ghép bằng phép hoặc, một mã bài học bất kỳ vẫn tạo thêm một nhánh truy xuất riêng. Hiện chưa khai thác được vì kho vector chưa có đoạn nào của tài nguyên bài học, nhưng lỗ hổng nằm sẵn ở đó và cần bịt trước khi nạp tài nguyên.

**Số trang trong trích dẫn lệch một đơn vị.** Số trang lưu trong kho vector đã đếm từ 1, nhưng giao diện cộng thêm 1 lần nữa khi hiển thị nhãn nguồn. Nội dung trích dẫn đúng, chỉ con số trang hiển thị bị lệch.

**Ghi danh và tạo tài khoản chỉ làm ở khu vực quản trị.** Không có luồng tự đăng ký cho học sinh và cũng không có luồng tự ghi danh khoá học. Đây là phạm vi đã chốt của đề tài chứ không phải phần bỏ sót, nhưng cần nói rõ để không bị hiểu là thiếu.

---

**Ghi chú về độ chính xác:** toàn bộ số liệu và quy tắc nêu trên đều đọc trực tiếp từ mã nguồn hiện tại — 3 lượt làm bài, thang điểm 10, bội số 0.05 cho điểm mỗi câu, 30 giây trễ cho phép, 15 phút và 7 ngày cho hai loại token, 30 lượt AI mỗi giờ, các ngưỡng dung lượng tệp. Số liệu ở mục 11 đọc trực tiếp từ cơ sở dữ liệu và kho vector đang chạy. Riêng phần mô tả bối cảnh nghiệp vụ ở mục 1 là diễn giải từ cấu trúc dữ liệu; nếu đề tài có tài liệu đặc tả yêu cầu riêng thì nên đối chiếu lại với tài liệu đó.
