## Stella Payment Bot

Discord bot tích hợp PayOS, FastAPI webhook và MongoDB để tạo QR thanh toán, nhận callback và ghi nhận giao dịch.

### Tính năng chính
- Slash commands: `/payment`, `/cancelpayment`, `/status`, `/list`.
- Tạo QR/link PayOS và theo dõi hóa đơn đang chờ.
- Nhận webhook PayOS qua FastAPI (`POST /api/payos`).
- Lưu giao dịch vào MongoDB, phân trang danh sách khách hàng theo tổng chi tiêu.

### Yêu cầu hệ thống
- Python 3.10+
- MongoDB (MongoDB Atlas hoặc self-host)
- Token Discord Bot
- Tài khoản PayOS (Client ID, API Key, Checksum Key)

### Cài đặt
bash
pip install -r requirements.txt


### Cấu hình môi trường (.env)
Tạo file `.env` tại thư mục gốc dự án (hoặc dùng mẫu `.env` kèm theo) với các biến sau:

DISCORD_TOKEN=your_discord_bot_token
MONGO_URI=mongodb+srv://user:pass@cluster/dbname?retryWrites=true&w=majority

PAYOS_CLIENT_ID=your_payos_client_id
PAYOS_API_KEY=your_payos_api_key
PAYOS_CHECKSUM_KEY=your_payos_checksum_key


Tùy chọn (khuyến nghị đưa vào ENV thay vì hardcode):

# Gợi ý nếu muốn cấu hình qua ENV (code hiện đang hardcode)
# GUILD_ID=123456789012345678
# LOG_CHANNEL_ID=123456789012345678
# CUSTOMER_ROLE_ID=123456789012345678


### Chạy ứng dụng
bash
python main.py

Bot sẽ chạy cùng FastAPI trên `0.0.0.0:19131`.

### Cấu hình Webhook PayOS
- URL: `http(s)://<domain_or_ip>:19131/api/payos`
- Phương thức: POST
- Đảm bảo cổng 19131 được mở ra internet hoặc dùng reverse proxy.
- Nên cấu hình xác minh chữ ký (chưa bật trong code mẫu này).

### Sử dụng lệnh
- `/payment user amount`: tạo QR cho người dùng chỉ định, gửi embed vào kênh hiện tại.
- `/cancelpayment order_code`: huỷ hóa đơn đang chờ theo mã đơn.
- `/status`: xem ping, RAM, uptime.
- `/list`: liệt kê top khách hàng theo tổng chi tiêu.

### Lệnh thống kê & top
- `/top <ngày|tuần|tháng> [limit]`:
  - Hiển thị top 5-10 người donate nhiều nhất trong khoảng thời gian.
  - Có huy hiệu vui: 🥇🥈🥉 cho top 1-3.
- `/history <ngày|tuần|tháng>`:
  - Lịch sử donate của chính bạn (ephemeral), gồm tổng số tiền và đến 20 giao dịch gần nhất.
- `/myrank`:
  - Xem thứ hạng donate của bạn trong tháng hiện tại.
- `/daily`:
  - Tổng donate (server) trong hôm nay.
- `/serverstats <ngày|tuần|tháng>`:
  - Tổng doanh thu và số giao dịch trong kỳ.
- `/compare @user <ngày|tuần|tháng>`:
  - So sánh donate giữa bạn và người khác trong kỳ.

### Lệnh quản trị
- `/resetstats <ngày|tuần|tháng>`: Reset thống kê trong kỳ (xóa giao dịch của kỳ đó).
- `/check @user`: Xem tổng donate và lịch sử gần nhất của một người dùng.
- `/export <tháng> [năm]`: Xuất file CSV lịch sử giao dịch của tháng.

### Bảo mật & riêng tư
- Không lưu thông tin thẻ/tài khoản PayOS. DB chỉ lưu `user_id` (Discord), `amount`, `timestamp`.
- Hạn chế chia sẻ token. Nếu lộ, hãy regenerate trên Discord Developer Portal.
- Dịch vụ `pastes.dev` hiện dùng để chứa `inuser_id payer_id channel_id`. Cân nhắc thay bằng DB nội bộ hoặc ký/ mã hoá nội dung mô tả.

### Khắc phục sự cố
- Kiểm tra biến môi trường: `echo $Env:DISCORD_TOKEN` (PowerShell)
- Kiểm tra kết nối MongoDB và URI.
- Xem log trong kênh log Discord (ID được cấu hình trong code) và console.

### Tác giả & Đóng góp
- Tác giả bot Discord: `\_karisan\_`
- Người hỗ trợ thêm tính năng: `Saly`

### License
MIT (nếu không có yêu cầu khác).
