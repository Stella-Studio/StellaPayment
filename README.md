## Stella Payment Bot
Discord bot tích hợp PayOS, FastAPI webhook và MongoDB để tạo QR thanh toán, nhận callback và ghi nhận giao dịch.

### Tính năng chính
- Tạo QR/link PayOS và theo dõi hóa đơn đang chờ.
- Lưu giao dịch vào MongoDB, phân trang danh sách khách hàng theo tổng chi tiêu.

### Yêu cầu hệ thống
- Python 3.10+
- MongoDB (MongoDB Atlas hoặc self-host)
- Tài khoản PayOS (Client ID, API Key, Checksum Key)

### Cài đặt
`pip install -r requirements.txt`


### Cấu hình môi trường (.env)
DISCORD_TOKEN=your_discord_bot_token
MONGO_URI=mongodb+srv://user:pass@cluster/dbname?retryWrites=true&w=majority

PAYOS_CLIENT_ID=your_payos_client_id
PAYOS_API_KEY=your_payos_api_key
PAYOS_CHECKSUM_KEY=your_payos_checksum_key

### Chạy ứng dụng
`python main.py`

### Cấu hình Webhook PayOS
- Kênh thanh toán -> Chọn kênh -> Cài đặt -> Chỉnh sửa thông tin -> Webhook Url: 
  - http(s)://<ip:port>/api/payos
  - Đảm bảo port được mở hoặc dùng reverse proxy (ngrok, devtunnel, cloudflare tunnel,...).

### Sử dụng lệnh
- `/payment <user> <amount>`: tạo QR cho người dùng chỉ định, gửi embed vào kênh hiện tại.
- `/cancelpayment <order_code>`: huỷ hóa đơn đang chờ theo mã đơn.
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
- `/compare <user> <ngày|tuần|tháng>`:
  - So sánh donate giữa bạn và người khác trong kỳ.

### Lệnh quản trị
- `/resetstats <ngày|tuần|tháng>`: Reset thống kê trong kỳ (xóa giao dịch của kỳ đó).
- `/check <user>`: Xem tổng donate và lịch sử gần nhất của một người dùng.
- `/export <tháng> [năm]`: Xuất file CSV lịch sử giao dịch của tháng.

### Bảo mật & riêng tư
- Không lưu thông tin thẻ/tài khoản PayOS. DB chỉ lưu `user_id` (Discord), `amount`, `timestamp`.
- Hạn chế chia sẻ token. Nếu lộ, hãy regenerate trên Discord Developer Portal.

### Tác giả & Đóng góp
- Tác giả bot Discord: `_karisan_`

- Người hỗ trợ thêm tính năng: `Saly`
