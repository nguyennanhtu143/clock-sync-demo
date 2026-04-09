Kịch bản demo cho thuật toán NTP với 5 máy vật lý bằng Python cần sự trực quan để thầy cô (hoặc người xem) thấy rõ được **trước khi đồng bộ thì sai lệch ra sao** và **sau khi đồng bộ thì kết quả chính xác thế nào**.

Vì các máy tính trong cùng mạng LAN thường có thời gian khá sát nhau, độ lệch tự nhiên có thể chỉ vài mili-giây (rất khó để biểu diễn "hiệu ứng" đồng bộ). Do đó, điểm mấu chốt của kịch bản này là chúng ta sẽ **cố tình bơm thêm một độ lệch giả (fake skew)** vào các client ngay khi khởi động.

Dưới đây là kịch bản demo chi tiết cho Phase 1 (Đồng bộ vật lý \- NTP):

### **1\. Phân vai và Chuẩn bị (Setup)**

* **Máy Server (Máy của bạn \- Node 0):** Chạy một script Python đóng vai trò Time Server. Lắng nghe yêu cầu đồng bộ từ các client qua một cổng nhất định (ví dụ: Port 5000). Thời gian của máy này được coi là "Thời gian gốc" (Master Clock).  
* **4 Máy Client (Node 1, 2, 3, 4):** Chạy script Python client. Mỗi máy sẽ biết địa chỉ IP LAN của máy Server.

### **2\. Kịch bản chạy thực tế (Execution Flow)**

**Bước 1: Khởi tạo và Giả lập sai lệch (Mô phỏng Clock Skew)**

* Khi chạy script trên 4 máy Client, script sẽ tự động sinh ra một số ngẫu nhiên để làm độ lệch ban đầu (ví dụ: Client 1 bị lệch \+5.2 giây, Client 2 bị lệch \-3.8 giây).  
* Lúc này, trên màn hình console của Client sẽ hiển thị log:  
  \[INFO\] Khởi động Client 1\. Thời gian OS: 21:36:10. Fake Offset: \+5.2s.  
  \[INFO\] Thời gian Client hiện tại (chưa đồng bộ): 21:36:15.200

**Bước 2: Thực thi thuật toán NTP**

* Bạn (người điều phối) hô bắt đầu, 4 máy client bấm phím Enter để kích hoạt quá trình ping lên Server. Quá trình trao đổi tin nhắn diễn ra như sau:  
  1. **Client:** Lấy thời gian $T\_1$, đóng gói vào request gửi cho Server.  
  2. **Server:** Nhận request, ghi nhận thời gian $T\_2$. Để kịch bản thêm thực tế và mô phỏng độ trễ xử lý, Server có thể time.sleep(0.05) (ngủ 50ms), sau đó lấy thời gian $T\_3$ và gửi gói tin phản hồi gồm (T\_2, T\_3) về cho Client.  
  3. **Client:** Nhận được phản hồi, ngay lập tức ghi nhận thời gian $T\_4$.

**Bước 3: Tính toán và Cập nhật**

* Client tiến hành tính toán ngay trên script Python:  
  * Tính độ trễ mạng: $\\delta \= \\frac{(T\_2-T\_1)+(T\_4-T\_3)}{2}$  
  * Tính độ lệch thời gian: $\\theta \= \\frac{(T\_2-T\_1)+(T\_3-T\_4)}{2}$  
* Client cộng giá trị $\\theta$ vào biến local\_offset của nó.

**Bước 4: Trình diễn Kết quả (Đánh giá theo yêu cầu 3 của đề bài)**

* Sau khi tính toán xong, màn hình console của Client sẽ in ra một bảng log tổng kết rất rõ ràng:  
  Plaintext  
  \--- KẾT QUẢ ĐỒNG BỘ NTP \---  
  \[+\] Thời gian gửi (T1): 21:36:20.000  
  \[+\] Thời gian Server nhận (T2): 21:36:14.850  
  \[+\] Thời gian Server gửi (T3): 21:36:14.900  
  \[+\] Thời gian nhận phản hồi (T4): 21:36:20.100  
  \---------------------------  
  \[\*\] Độ trễ mạng (Delay): 0.075s (75ms)  
  \[\*\] Độ lệch so với Server (Offset): \-5.175s  
  \---------------------------  
  \[SUCCESS\] Đã hiệu chỉnh lại đồng hồ nội bộ.  
  \[+\] Thời gian Client SAU đồng bộ: 21:36:14.925

* **Đánh giá:** Lúc này, bạn có thể cho các Client in ra thời gian (đã cộng offset) mỗi giây một lần. Nếu 4 máy client cùng hiển thị thời gian khớp với máy Server của bạn đến từng mili-giây, bản demo NTP đã thành công mỹ mãn.

---

Kịch bản này vừa đơn giản, trực quan lại bám sát 100% công thức từ giáo trình Tanenbaum. Bạn muốn sử dụng giao thức UDP (giống chuẩn NTP thực tế) hay TCP (đảm bảo không mất gói tin, dễ code hơn) cho các socket trong script Python này để mình phác thảo cấu trúc code luôn?