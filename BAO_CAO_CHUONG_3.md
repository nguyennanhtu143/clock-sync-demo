3.1. Hạ tầng kỹ thuật

3.1.1. Cấu hình
Về phần cứng, môi trường thực nghiệm gồm năm máy tính vật lý hoạt động đồng thời: một máy đóng vai trò máy chủ (Node 0) và bốn máy còn lại đóng vai trò các máy khách (Node 1 đến Node 4). Tất cả các máy kết nối với nhau qua mạng nội bộ hoặc qua mạng riêng ảo (trong trường hợp các máy thuộc các mạng vật lý khác nhau). Mỗi máy chạy hệ điều hành Windows và sử dụng Python 3.x làm môi trường thực thi. Môi trường ảo (virtual environment) được tạo độc lập trên từng máy, không chia sẻ thư viện giữa các máy, đảm bảo tính độc lập và tái tạo được của môi trường chạy.

Bảng 3.1. Cấu hình phần mềm môi trường thực nghiệm
Thành phần	Thông số	Ghi chú
Ngôn ngữ lập trình	Python 3.x	Chạy trên tất cả 5 máy
Môi trường ảo	venv (Python built-in)	Tạo riêng biệt trên từng máy
Thư viện máy chủ	Flask, Flask-SocketIO, colorama	Cài qua requirements.txt
Thư viện máy khách	requests, colorama	Cài qua requirements.txt
Giao thức truyền thông	TCP (socket thuần)	Dùng cho NTP và đồng hồ logic
Giao thức giao diện web	HTTP / WebSocket (SocketIO)	Dùng cho bảng điều khiển web
Kết nối mạng	Mạng nội bộ hoặc Radmin VPN	Tùy trường hợp triển khai
Trình duyệt kiểm thử	Google Chrome	Xem bảng điều khiển web


3.1.2. Kiến trúc tổng thể của hệ thống
Toàn bộ hệ thống hoạt động theo mô hình máy chủ – máy khách (client-server), trong đó một máy duy nhất đóng vai trò máy chủ trung tâm và bốn máy còn lại là các máy khách. Máy chủ khởi động ba thành phần cùng lúc trong các luồng (thread) riêng biệt: máy chủ đồng bộ thời gian vật lý, máy chủ điều phối đồng hồ logic, và bảng điều khiển web. Ba thành phần này hoạt động song song, cùng chia sẻ không gian bộ nhớ của một tiến trình Python duy nhất.

[Hình 3.1 - Sơ đồ kiến trúc tổng thể 5 máy vật lý]
Mô tả: Sơ đồ thể hiện 1 máy chủ (Node 0) ở trung tâm kết nối với 4 máy khách (Node 1–4). Máy chủ mở 3 cổng: 5000 (NTP), 5001 (đồng hồ logic), 8080 (bảng điều khiển web). Các máy khách kết nối TCP đến cổng 5000 và 5001; trình duyệt trên bất kỳ máy nào cũng có thể mở bảng điều khiển qua cổng 8080.

Khi lệnh python dashboard.py được thực thi trên máy chủ, hệ thống khởi động theo thứ tự sau:
•	Luồng 1: Máy chủ đồng bộ thời gian vật lý (ntp_server.py) khởi động, lắng nghe kết nối TCP trên cổng 5000. Đây là "đồng hồ gốc" của hệ thống — thời gian của máy chủ được coi là chuẩn tham chiếu.
•	Luồng 2: Máy chủ điều phối đồng hồ logic (logic_server.py) khởi động, lắng nghe kết nối TCP trên cổng 5001. Máy chủ này đóng vai trò "bưu cục trung tâm" — các máy khách không giao tiếp trực tiếp với nhau mà thông qua máy chủ để chuyển tiếp thông điệp.
•	Luồng chính: Bảng điều khiển web (dashboard.py với Flask và Flask-SocketIO) khởi động trên cổng 8080, tổng hợp dữ liệu từ cả hai máy chủ trên và đẩy lên trình duyệt theo thời gian thực qua WebSocket.

Bảng 3.2. Các thành phần chạy trên máy chủ
Thành phần	Cổng	Giao thức	Vai trò
Máy chủ NTP	5000	TCP	Nhận yêu cầu đồng bộ thời gian từ máy khách
Máy chủ đồng hồ logic	5001	TCP	Điều phối và chuyển tiếp sự kiện Lamport/Vector Clock
Bảng điều khiển web	8080	HTTP / WebSocket	Trực quan hoá kết quả theo thời gian thực


3.1.3. Cách các máy giao tiếp
Về công nghệ giao tiếp, hệ thống sử dụng hai kênh truyền thông độc lập. Kênh thứ nhất là socket TCP thuần (Python socket module) dùng cho cả đồng bộ thời gian vật lý và đồng hồ logic; kênh này đảm bảo truyền dữ liệu đáng tin cậy, có thứ tự. Kênh thứ hai là HTTP/REST dùng để máy khách báo cáo kết quả đồng bộ NTP lên bảng điều khiển web sau khi hoàn tất phiên đồng bộ.

Mọi thông điệp trao đổi giữa máy khách và máy chủ đều được mã hoá theo định dạng JSON. Đối với máy chủ đồng hồ logic, mỗi thông điệp được kết thúc bằng ký tự xuống dòng (\n) để phân tách ranh giới giữa các thông điệp — kỹ thuật này được gọi là giao thức có đệm theo dòng (line-buffered protocol), nhằm xử lý đúng trường hợp nhiều thông điệp đến trong cùng một lần nhận dữ liệu.

Về cấu hình mạng, hệ thống hỗ trợ hai trường hợp triển khai:

Trường hợp 1 — Tất cả máy cùng mạng nội bộ (WiFi hoặc cáp mạng): Đây là cấu hình đơn giản nhất. Tất cả năm máy kết nối vào cùng một bộ phát WiFi hoặc bộ chuyển mạch (switch). Người vận hành chạy lệnh ipconfig trên máy chủ để lấy địa chỉ IP nội bộ (dạng 192.168.x.x), sau đó thông báo địa chỉ này cho bốn máy khách. Các máy khách sử dụng địa chỉ IP này làm tham số --server-ip khi khởi động chương trình. Lưu ý rằng một số mạng WiFi công cộng (trường học, quán cà phê) có thể bật tính năng cô lập thiết bị (AP Isolation) — ngăn các thiết bị trong cùng mạng giao tiếp trực tiếp với nhau — khiến kết nối thất bại.

Trường hợp 2 — Các máy thuộc các mạng khác nhau, sử dụng Radmin VPN: Khi các máy không thể kết nối trực tiếp qua mạng nội bộ, phần mềm Radmin VPN được cài đặt trên tất cả năm máy để tạo một mạng nội bộ ảo (Virtual LAN) qua Internet. Radmin VPN cấp cho mỗi máy một địa chỉ IP ảo (dạng 26.x.x.x). Máy chủ tạo một "mạng" (Network) trên Radmin VPN với tên và mật khẩu được chia sẻ cho các máy khách để tham gia. Sau khi tất cả năm máy đã gia nhập cùng một mạng Radmin, người vận hành đọc địa chỉ IP ảo của máy chủ và dùng làm tham số --server-ip. Lưu ý rằng trong trường hợp này, độ trễ mạng có thể cao hơn đáng kể so với mạng nội bộ vật lý (20–100 mili giây thay vì 1–5 mili giây), vì dữ liệu phải đi qua cơ sở hạ tầng Internet trước khi đến đích. Tuy nhiên điều này không ảnh hưởng đến tính đúng đắn của kết quả — ngược lại, độ trễ lớn hơn giúp cho phần đồng bộ thời gian vật lý trực quan hơn.

[Hình 3.2 - Sơ đồ kết nối mạng hai trường hợp]
Mô tả: Hai sơ đồ cạnh nhau. Trái: 5 máy nối vào cùng 1 router/switch, sử dụng IP nội bộ 192.168.x.x. Phải: 5 máy ở các địa điểm khác nhau, kết nối qua Internet thông qua Radmin VPN, sử dụng IP ảo 26.x.x.x.

Tường lửa (Firewall) trên máy chủ cần được cấu hình cho phép kết nối đến ba cổng 5000, 5001 và 8080. Trong môi trường thực nghiệm, cách nhanh nhất là tắt tạm tường lửa Windows trong thời gian thực nghiệm và bật lại sau đó.


3.1.4. Kiến trúc mã nguồn
Mã nguồn được tổ chức thành hai thư mục độc lập: server/ chứa toàn bộ mã nguồn dành cho máy chủ, và client/ chứa mã nguồn dành cho máy khách. Mỗi thư mục có môi trường ảo và tệp khai báo thư viện (requirements.txt) riêng, không chia sẻ với nhau.

Bảng 3.3. Các tệp mã nguồn chính và trách nhiệm
Tệp	Thư mục	Trách nhiệm chính
ntp_server.py	server/	Lắng nghe yêu cầu đồng bộ thời gian từ máy khách qua TCP cổng 5000; ghi nhận T2, T3; lưu kết quả vào vùng nhớ chung (shared state)
logic_server.py	server/	Lắng nghe kết nối từ máy khách qua TCP cổng 5001; điều phối sự kiện đồng hồ logic; chuyển tiếp thông điệp giữa các node; phát (emit) sự kiện realtime lên bảng điều khiển web
dashboard.py	server/	Khởi động toàn bộ hệ thống; cung cấp giao diện web Flask trên cổng 8080; cung cấp các điểm cuối REST API; đẩy cập nhật theo thời gian thực qua WebSocket (SocketIO)
index.html	server/templates/	Giao diện bảng điều khiển web với ba tab: Đồng bộ NTP, Đồng hồ Logic, So sánh
dashboard.js	server/static/js/	Nhận sự kiện WebSocket; vẽ biểu đồ (Chart.js) và sơ đồ không-thời gian (Canvas); phát hiện sự kiện đồng thời (concurrent events)
ntp_client.py	client/	Thực hiện giao thức đồng bộ thời gian Cristian với máy chủ; tính độ lệch (offset) và độ trễ (delay); báo cáo kết quả lên bảng điều khiển web qua HTTP POST
logic_client.py	client/	Duy trì Lamport Clock và Vector Clock song song; kết nối TCP đến máy chủ đồng hồ logic; cung cấp giao diện dòng lệnh tương tác để tạo sự kiện

Luồng giao tiếp giữa các hàm trong mã nguồn được thiết kế theo hướng trách nhiệm rõ ràng:

Đối với đồng bộ thời gian vật lý: ntp_client.py::perform_ntp_sync() → tạo kết nối TCP đến máy chủ → ghi T1 → nhận T2, T3 từ máy chủ → ghi T4 → tính toán (delay, offset) tại chỗ → gọi report_to_dashboard() gửi HTTP POST lên bảng điều khiển. Phía máy chủ: ntp_server.py::handle_client() chạy trong một luồng riêng cho mỗi kết nối → ghi T2, mô phỏng độ trễ xử lý 50 mili giây → ghi T3 → gửi phản hồi.

Đối với đồng hồ logic: logic_client.py::LogicalClockClient::local_event() / send_event() / _handle_receive() cập nhật cả Lamport Clock lẫn Vector Clock theo quy tắc tương ứng, sau đó gửi thông báo lên máy chủ. Phía máy chủ: logic_server.py::handle_client() tiếp nhận thông điệp → gọi record_event() → record_event() lưu sự kiện vào danh sách và ngay lập tức gọi con trỏ hàm _emit_callback() — đây chính là hàm socketio.emit() được dashboard.py tiêm vào (inject) lúc khởi động — để đẩy sự kiện lên trình duyệt theo thời gian thực mà không gây phụ thuộc vòng tròn giữa hai mô-đun.

[Hình 3.3 - Sơ đồ luồng giao tiếp giữa các hàm chính]
Mô tả: Sơ đồ dạng sequence diagram thể hiện 3 luồng song song: (1) NTP: ntp_client → TCP → ntp_server::handle_client → response → ntp_client::report_to_dashboard → HTTP POST → dashboard; (2) Logic: logic_client::local_event → TCP → logic_server::handle_client → record_event → _emit_callback → SocketIO → browser; (3) Browser polling: browser → HTTP GET /api/ntp/results và /api/logic/events → dashboard trả về JSON.


---

3.2. Các trang màn hình và luồng thực nghiệm
Phần này trình bày chi tiết giao diện bảng điều khiển web, các bước tương tác trong từng kịch bản thực nghiệm, và nhật ký hệ thống minh chứng cơ chế đồng bộ thời gian vật lý và đồng hồ logic hoạt động đúng theo thiết kế. Các kịch bản được thực hiện theo thứ tự từ thành phần cơ bản đến kịch bản phức tạp, tương ứng với các trường hợp quan trọng cần kiểm chứng trong hệ thống phân tán.

3.2.1. Đồng bộ thời gian vật lý

Đồng bộ thời gian vật lý được triển khai dựa trên thuật toán Cristian (1989), sử dụng một vòng trao đổi thông điệp duy nhất giữa máy khách và máy chủ để đo độ trễ mạng và tính độ lệch đồng hồ. Máy chủ đóng vai trò "đồng hồ gốc" (Master Clock) — thời gian của máy chủ được coi là chuẩn tham chiếu tuyệt đối.

Cơ chế hoạt động của thuật toán gồm bốn mốc thời gian:
•	T1: Thời điểm máy khách ghi lại trước khi gửi yêu cầu (có cộng thêm độ lệch giả được thiết lập trước để mô phỏng đồng hồ bị chạy lệch).
•	T2: Thời điểm máy chủ ghi lại ngay khi nhận được yêu cầu.
•	T3: Thời điểm máy chủ ghi lại ngay trước khi gửi phản hồi (sau một khoảng ngủ giả 50 mili giây mô phỏng thời gian xử lý).
•	T4: Thời điểm máy khách ghi lại ngay khi nhận được phản hồi (có cộng thêm độ lệch giả).

Từ bốn mốc thời gian trên, máy khách tính toán:
•	Độ trễ mạng (δ) = ((T2 − T1) + (T4 − T3)) / 2 — đây là thời gian trung bình cho một chiều truyền, loại bỏ ảnh hưởng của độ lệch đồng hồ bằng cách cộng hai chiều lại.
•	Độ lệch đồng hồ (θ) = ((T2 − T1) − (T4 − T3)) / 2 — đây là độ lệch giữa đồng hồ máy khách so với đồng hồ máy chủ, loại bỏ ảnh hưởng của độ trễ mạng bằng cách lấy hiệu hai chiều.

Trong mã nguồn, hàm perform_ntp_sync() trong ntp_client.py thực hiện toàn bộ quy trình trên. Độ lệch giả (fake_offset) được thiết lập qua tham số dòng lệnh --fake-offset, hoặc được sinh ngẫu nhiên trong khoảng [-10, +10] giây nếu không chỉ định. Giá trị này được cộng vào T1 và T4 để giả lập máy khách đang chạy lệch giờ so với thực tế. Sau khi tính được θ, thời gian đã hiệu chỉnh được tính là:

Thời gian hiệu chỉnh = time.time() + fake_offset + θ ≈ thời gian máy chủ

Sau khi đồng bộ, máy khách hiển thị 30 giây bảng so sánh liên tục trên màn hình dòng lệnh, mỗi giây một dòng, so sánh ba cột: thời gian máy chủ (chuẩn tham chiếu), thời gian chưa đồng bộ (thời gian bị lệch), và thời gian đã hiệu chỉnh (sau khi áp dụng θ).

[Hình 3.4 - Màn hình dòng lệnh của máy khách sau khi đồng bộ NTP]
Mô tả: Ảnh chụp màn hình console của ntp_client.py, thể hiện hộp kết quả với T1, T2, T3, T4, độ trễ, độ lệch, thời gian trước và sau đồng bộ, sai lệch còn lại (mili giây), và bảng so sánh 30 giây.

[Hình 3.5 - Tab NTP Sync trên bảng điều khiển web]
Mô tả: Ảnh chụp tab NTP Sync trên trình duyệt, thể hiện 4 thẻ thống kê (số node đã đồng bộ, độ trễ trung bình, độ lệch trung bình, sai lệch còn lại trung bình) và 2 biểu đồ cột (Độ lệch giả so với Độ lệch NTP tính được; Độ trễ mạng của từng node).


3.2.2. Đồng bộ thời gian logic với Lamport Clock và Vector Clock

Đồng bộ thời gian logic được triển khai song song hai thuật toán trong cùng một chương trình máy khách (logic_client.py):

Lamport Clock (1978) sử dụng một số nguyên duy nhất làm đồng hồ. Quy tắc cập nhật:
•	Sự kiện nội bộ (local): LC += 1
•	Gửi thông điệp (send): LC += 1, rồi gửi LC theo thông điệp
•	Nhận thông điệp (receive): LC = max(LC, LC_nhận_được) + 1

Vector Clock (Fidge/Mattern, 1988) sử dụng một mảng N phần tử (N là số node) làm đồng hồ. Quy tắc cập nhật:
•	Sự kiện nội bộ: VC[self] += 1
•	Gửi thông điệp: VC[self] += 1, rồi gửi toàn bộ VC theo thông điệp
•	Nhận thông điệp: VC[i] = max(VC[i], VC_nhận[i]) cho mọi i, sau đó VC[self] += 1

Hai thuật toán cùng cập nhật sau mỗi sự kiện và cùng hiển thị trạng thái lên màn hình dòng lệnh. Việc duy trì đồng thời cả hai cho phép so sánh trực tiếp sự khác biệt: Lamport Clock đảm bảo quan hệ "xảy ra trước" một chiều (nếu A xảy ra trước B thì LC(A) < LC(B)), trong khi Vector Clock đảm bảo quan hệ hai chiều đầy đủ và có khả năng phát hiện các sự kiện đồng thời (concurrent events) — điều mà Lamport Clock không làm được.

Máy khách kết nối TCP đến máy chủ đồng hồ logic (cổng 5001) và đăng ký bằng thông điệp {"type": "register"}. Sau đó, một luồng lắng nghe riêng (_listen_incoming) được tạo nền để nhận thông điệp do máy chủ chuyển tiếp, trong khi luồng chính hiển thị menu tương tác cho người vận hành.

[Hình 3.6 - Menu tương tác trên màn hình dòng lệnh của máy khách logic]
Mô tả: Ảnh chụp màn hình console của logic_client.py, thể hiện hộp menu với 5 lựa chọn: [1] Sự kiện nội bộ, [2] Gửi thông điệp, [3] Xem trạng thái Clock, [4] Xem lịch sử sự kiện, [5] Thoát.

[Hình 3.7 - Tab So sánh trên bảng điều khiển web]
Mô tả: Ảnh chụp tab So sánh trên trình duyệt, thể hiện hai thẻ Lamport Clock và Vector Clock đặt cạnh nhau với các hàng so sánh: Loại clock, Hỗ trợ happened-before, Phát hiện sự kiện đồng thời, Kích thước, Quy tắc Send, Quy tắc Receive, Ưu điểm, Nhược điểm.


3.2.3. Kịch bản 1 — Hai máy đồng bộ thời gian vật lý với máy chủ

Kịch bản này kiểm chứng khả năng đồng bộ thời gian vật lý của hệ thống khi nhiều máy khách thực hiện đồng bộ cùng lúc. Giả sử Node 1 được thiết lập độ lệch giả +5.2 giây (đồng hồ chạy nhanh hơn thực tế) và Node 2 được thiết lập độ lệch giả −3.7 giây (đồng hồ chạy chậm hơn thực tế).

Người vận hành kích hoạt cả hai máy khách gần như cùng lúc bằng cách nhấn Enter theo hiệu lệnh điều phối. Mỗi máy khách lập tức thực hiện vòng trao đổi thông điệp NTP với máy chủ và hiển thị kết quả:
•	Node 1: θ ≈ −5.2 giây (thuật toán phát hiện đồng hồ đang chạy nhanh và cần lùi lại 5.2 giây để khớp với máy chủ).
•	Node 2: θ ≈ +3.7 giây (thuật toán phát hiện đồng hồ đang chạy chậm và cần tiến lên 3.7 giây để khớp với máy chủ).

Sau khi đồng bộ, cả hai node hiển thị thời gian đã hiệu chỉnh lệch với thời gian máy chủ chỉ vài mili giây — minh chứng tính hiệu quả của thuật toán. Đồng thời, kết quả được gửi lên bảng điều khiển web và biểu đồ cập nhật theo thời gian thực với hai cột đại diện cho Node 1 và Node 2.

[Hình 3.8 - Màn hình dòng lệnh của Node 1 sau khi đồng bộ (độ lệch +5.2 giây)]
Mô tả: Ảnh chụp console của Node 1 với hộp KẾT QUẢ ĐỒNG BỘ NTP, thể hiện T1, T2, T3, T4, độ trễ, độ lệch ≈ −5.2 giây, thời gian trước đồng bộ (lớn hơn thực tế 5.2 giây), thời gian sau đồng bộ (khớp với máy chủ), sai lệch còn lại (mili giây).

[Hình 3.9 - Tab NTP Sync sau khi cả Node 1 và Node 2 hoàn thành đồng bộ]
Mô tả: Ảnh chụp tab NTP Sync trên trình duyệt với 2 node đã đồng bộ, biểu đồ cột thể hiện Node 1 có độ lệch giả +5.2 giây đối lập với độ lệch tính được ≈ −5.2 giây, Node 2 có độ lệch giả −3.7 giây đối lập với độ lệch tính được ≈ +3.7 giây.


3.2.4. Kịch bản 2 — Một máy bất kỳ thực hiện sự kiện nội bộ

Kịch bản này kiểm chứng cơ chế cập nhật đồng hồ logic khi xảy ra sự kiện nội bộ — tức là sự kiện không liên quan đến bất kỳ node nào khác. Giả sử Node 1 chọn mục [1] trong menu để tạo sự kiện nội bộ.

Khi người vận hành xác nhận, logic_client.py thực hiện:
1.	Tăng Lamport Clock: LC = LC + 1 (ví dụ từ 0 lên 1).
2.	Tăng phần tử tương ứng trong Vector Clock: VC[1] = VC[1] + 1 (ví dụ từ [0,0,0,0,0] lên [0,1,0,0,0]).
3.	Gửi thông báo lên máy chủ: {"type": "local_event", "lamport_clock": 1, "vector_clock": [0,1,0,0,0]}.

Màn hình dòng lệnh ngay lập tức hiển thị hộp trạng thái với giá trị mới của cả hai đồng hồ. Máy chủ nhận thông báo, ghi nhận sự kiện và đẩy cập nhật lên bảng điều khiển web qua WebSocket.

Điểm quan trọng cần quan sát: sự kiện này chỉ làm thay đổi đồng hồ của Node 1. Các node còn lại (Node 2, 3, 4) không biết về sự kiện này và đồng hồ của họ không thay đổi, phản ánh đúng nguyên lý của hệ thống phân tán — không có trạng thái toàn cục chia sẻ.

[Hình 3.10 - Màn hình dòng lệnh của Node 1 sau sự kiện nội bộ]
Mô tả: Ảnh chụp console của Node 1, thể hiện hộp NODE 1 — CLOCK STATE với dòng "Sự kiện: LOCAL EVENT", Lamport Clock: 1, Vector Clock: [0,1,0,0,0].

[Hình 3.11 - Tab Đồng hồ Logic trên bảng điều khiển web sau sự kiện nội bộ]
Mô tả: Ảnh chụp tab Logical Clocks trên trình duyệt, thể hiện sự kiện LOCAL của Node 1 xuất hiện trên sơ đồ không-thời gian (space-time diagram) và bảng sự kiện.


3.2.5. Kịch bản 3 — Hai máy đồng bộ logic, Lamport và Vector Clock cập nhật như thế nào

Kịch bản này mở rộng từ kịch bản trước, khi cả hai Node 1 và Node 2 đều đã có lịch sử sự kiện. Giả sử Node 1 đã có LC=2, VC=[0,2,0,0,0] và Node 2 đã có LC=1, VC=[0,0,1,0,0].

Người vận hành trên Node 1 chọn [1] để tạo thêm một sự kiện nội bộ và đồng thời người vận hành trên Node 2 cũng chọn [1] để tạo sự kiện nội bộ. Hai sự kiện này xảy ra gần như đồng thời, không có mối quan hệ nhân quả với nhau.

Sau khi mỗi node tự cập nhật:
•	Node 1: LC = 3, VC = [0,3,0,0,0]
•	Node 2: LC = 2, VC = [0,0,2,0,0]

Cả hai node báo cáo sự kiện của mình lên máy chủ. Trên bảng điều khiển, phần phân tích sự kiện đồng thời hiện ra kết quả quan trọng: Lamport Clock của hai sự kiện (LC=3 và LC=2) có thể so sánh được (3 > 2), dẫn đến nhận định sai rằng sự kiện của Node 1 "xảy ra trước" sự kiện của Node 2. Trong khi đó, Vector Clock ([0,3,0,0,0] và [0,0,2,0,0]) không thể so sánh theo chiều nào — phần tử thứ hai của Node 1 lớn hơn, nhưng phần tử thứ ba của Node 2 lại lớn hơn — do đó hai sự kiện được xác định chính xác là đồng thời (concurrent), không có quan hệ nhân quả.

Đây là minh chứng cụ thể cho hạn chế của Lamport Clock so với Vector Clock: Lamport Clock không đủ để phân biệt "xảy ra trước" và "đồng thời".

[Hình 3.12 - Hai hộp trạng thái đồng hồ trên Node 1 và Node 2 sau các sự kiện nội bộ]
Mô tả: Ảnh chụp màn hình của 2 máy khách cạnh nhau: Node 1 hiện LC=3, VC=[0,3,0,0,0]; Node 2 hiện LC=2, VC=[0,0,2,0,0].

[Hình 3.13 - Phần phát hiện sự kiện đồng thời trên bảng điều khiển web]
Mô tả: Ảnh chụp phần Concurrent Events Detection trên bảng điều khiển, thể hiện hai sự kiện được đánh dấu là đồng thời với giải thích: Lamport Clock có thể so sánh được (3 > 2) nhưng Vector Clock không thể so sánh ([0,3,0,0,0] vs [0,0,2,0,0]).


3.2.6. Kịch bản 4 — Máy 1 gửi thông điệp cho máy 2, Lamport và Vector Clock cập nhật như thế nào

Kịch bản này kiểm chứng cơ chế cập nhật đồng hồ logic khi có sự kiện truyền thông điệp giữa hai node — đây là loại sự kiện quan trọng nhất vì nó thiết lập quan hệ nhân quả (causal relationship) giữa hai tiến trình. Giả sử tại thời điểm bắt đầu: Node 1 có LC=2, VC=[0,2,0,0,0] và Node 2 có LC=1, VC=[0,0,1,0,0].

Người vận hành trên Node 1 chọn mục [2] trong menu, nhập số 2 là node đích, nhập nội dung thông điệp. Quy trình diễn ra như sau:

Phía Node 1 (bên gửi):
1.	Tăng Lamport Clock: LC = 2 + 1 = 3
2.	Tăng Vector Clock: VC[1] = 2 + 1 = 3, kết quả VC = [0,3,0,0,0]
3.	Gửi lên máy chủ: {"type": "send_event", "target_node": 2, "lamport_clock": 3, "vector_clock": [0,3,0,0,0]}
4.	Màn hình hiển thị hộp trạng thái: LC=3, VC=[0,3,0,0,0], loại sự kiện: SEND EVENT → Node 2.

Phía máy chủ:
Máy chủ nhận thông điệp từ Node 1, tra cứu kết nối socket của Node 2 trong bảng node_connections, và chuyển tiếp thông điệp: {"type": "receive_event", "from_node": 1, "lamport_clock": 3, "vector_clock": [0,3,0,0,0]}.

Phía Node 2 (bên nhận):
Luồng lắng nghe nền của Node 2 nhận được thông điệp được chuyển tiếp và gọi _handle_receive():
1.	Cập nhật Lamport Clock: LC = max(1, 3) + 1 = 4
2.	Cập nhật Vector Clock theo phần tử: max([0,0,1,0,0], [0,3,0,0,0]) = [0,3,1,0,0], sau đó VC[2] += 1 → VC = [0,3,2,0,0]
3.	Gửi xác nhận (ACK) lên máy chủ: {"type": "receive_ack", ...}
4.	Màn hình của Node 2 tự động hiển thị thông báo nhận thông điệp và hộp trạng thái mới: LC=4, VC=[0,3,2,0,0].

Sau khi truyền thông điệp, quan hệ nhân quả được thiết lập rõ ràng. Trên bảng điều khiển web, sơ đồ không-thời gian thể hiện một mũi tên từ điểm sự kiện gửi trên đường thẳng đứng của Node 1 đến điểm sự kiện nhận trên đường thẳng đứng của Node 2. Vector Clock của Node 2 sau khi nhận ([0,3,2,0,0]) "nhớ" rằng nó đã quan sát tất cả 3 sự kiện của Node 1 (VC[1]=3) và 2 sự kiện của chính nó (VC[2]=2), phản ánh đúng lịch sử nhân quả.

[Hình 3.14 - Màn hình dòng lệnh của Node 1 sau sự kiện gửi thông điệp]
Mô tả: Ảnh chụp console của Node 1, thể hiện hộp NODE 1 — CLOCK STATE với dòng "Sự kiện: SEND EVENT → Node 2", Lamport Clock: 3, Vector Clock: [0,3,0,0,0].

[Hình 3.15 - Màn hình dòng lệnh của Node 2 khi nhận thông điệp từ Node 1]
Mô tả: Ảnh chụp console của Node 2, thể hiện dòng thông báo "📨 MESSAGE NHẬN TỪ NODE 1: [nội dung]", sau đó là hộp NODE 2 — CLOCK STATE với LC=4, VC=[0,3,2,0,0].

[Hình 3.16 - Sơ đồ không-thời gian trên bảng điều khiển web sau khi gửi thông điệp]
Mô tả: Ảnh chụp phần Space-Time Diagram trên tab Logical Clocks, thể hiện đường thẳng đứng của Node 1 và Node 2 với các điểm sự kiện, và một mũi tên nối từ điểm SEND của Node 1 đến điểm RECEIVE của Node 2 biểu diễn quan hệ nhân quả.
