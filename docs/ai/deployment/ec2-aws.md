# Chạy Refs Dashboard trên AWS EC2

Hướng dẫn triển khai stack **Docker Compose** (frontend + backend) trên một máy **EC2**, kết nối **MongoDB Atlas**.

## Yêu cầu

- Tài khoản AWS + VPC mặc định
- Cluster **MongoDB Atlas** và connection string `mongodb+srv://...`
- (Tuỳ chọn) Tên miền trỏ A-record về IP public của EC2 — để dùng HTTPS với Nginx + Let’s Encrypt

## 1. Tạo EC2 instance

| Gợi ý | Giá trị |
|--------|---------|
| AMI | **Amazon Linux 2023** hoặc **Ubuntu 22.04 LTS** |
| Loại instance | `t3.small` trở lên (Next.js build + FastAPI) |
| Ổ đĩa | ≥ 20 GiB gp3 |
| Key pair | Tạo/mới và lưu file `.pem` để SSH |

## 2. Security Group (firewall)

Mở các cổng tối thiểu:

| Hướng | Port | Nguồn | Mục đích |
|--------|------|--------|-----------|
| Inbound | **22** | IP của bạn (`x.x.x.x/32`) | SSH |
| Inbound | **3000** | `0.0.0.0/0` hoặc IP cố định | Frontend Next.js (tạm thời; production nên dùng 80/443 + reverse proxy) |
| Inbound | **4000** | **Không mở public** nếu chỉ dùng proxy `/api` qua Next | Backend chỉ cần nội bộ Docker |

**Khuyến nghị production:** chỉ mở **80** và **443**, đặt **Nginx** (hoặc ALB) phía trước; không expose `:4000` ra Internet.

## 3. MongoDB Atlas

1. **Database Access** — user/password có quyền đọc/ghi DB `refs_dashboard` (hoặc DB trong URI).
2. **Network Access** → **Add IP Address**:
   - Cách nhanh (dev): `0.0.0.0/0`
   - An toàn hơn: thêm **Elastic IP** của EC2 (`x.x.x.x/32`), hoặc dùng **VPC Peering / Private Endpoint** nếu cluster chỉ cho private network.

Connection string ví dụ:

```text
mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/refs_dashboard?retryWrites=true&w=majority
```

Nếu mật khẩu có ký tự đặc biệt, **URL-encode** (ví dụ `@` → `%40`).

## 4. Cài Docker trên EC2

### Amazon Linux 2023

```bash
sudo dnf update -y
sudo dnf install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
# đăng xuất / SSH lại để nhóm docker có hiệu lực
```

Plugin Compose (nếu chưa có):

```bash
DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
mkdir -p $DOCKER_CONFIG/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
docker compose version
```

### Ubuntu 22.04

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu
```

## 5. Lấy code và cấu hình `.env`

```bash
git clone <YOUR_REPO_URL> refs-dashboard
cd refs-dashboard
cp backend/.env.example backend/.env
nano backend/.env   # hoặc vim
```

Bắt buộc chỉnh tối thiểu:

| Biến | Ý nghĩa trên EC2 |
|------|-------------------|
| `MONGODB_URI` | URI Atlas (`mongodb+srv://...`) |
| `JWT_SECRET` | Chuỗi ngẫu nhiên dài (không dùng giá trị mặc định) |
| `FRONTEND_URL` | **URL mà trình duyệt dùng để mở dashboard** — ví dụ `http://EC2_PUBLIC_IP:3000` hoặc `https://dashboard.example.com`. Backend dùng cho **CORS**; sai giá trị sẽ lỗi gọi API từ browser nếu gọi thẳng backend. |

Cấu hình API các sàn (BingX, Exness, …) theo nhu cầu.

**Quan trọng:** đặt `FRONTEND_URL` trong `backend/.env` đúng với URL người dùng truy cập (local hoặc IP/domain EC2) — biến này dùng cho **CORS**. Không cần ghi đè trong `docker-compose.yml`.

### `docker-compose.yml`

Compose **không** set `FRONTEND_URL` — chỉ dùng `backend/.env`.

## 6. Build và chạy

```bash
cd ~/refs-dashboard
docker compose build --no-cache
docker compose up -d
docker compose ps
docker compose logs -f backend   # kiểm tra lỗi kết nối Mongo / seed
```

- Frontend: `http://EC2_PUBLIC_IP:3000`
- Backend Swagger (chỉ mở port 4000 khi cần debug): `http://EC2_PUBLIC_IP:4000/docs`

Ứng dụng **tự seed** admin khi backend khởi động (nếu DB trống). Mặc định (theo code seed): `admin` / `admin123` — đổi ngay sau lần đăng nhập đầu.

## 7. Elastic IP (tuỳ chọn)

Gán **Elastic IP** cho instance để IP public không đổi sau reboot — cập nhật lại rule Atlas và `FRONTEND_URL` cho khớp.

## 8. Production: Nginx + HTTPS (khuyến nghị)

Luồng: Internet → **443** → Nginx → proxy `localhost:3000` (Next) và có thể proxy `/api` → `localhost:4000` hoặc giữ Next rewrite như hiện tại.

1. Cài Nginx + Certbot (Let’s Encrypt).
2. `server_name dashboard.example.com;`
3. `proxy_pass http://127.0.0.1:3000;`
4. Sau khi có HTTPS: đặt `FRONTEND_URL=https://dashboard.example.com` và rebuild/restart stack.

Chi tiết Certbot theo distro: [certbot.eff.org](https://certbot.eff.org/).

## 9. Vận hành

```bash
# Xem log
docker compose logs -f

# Restart sau khi đổi .env
docker compose up -d --build

# Backup: dữ liệu nằm trên Atlas — backup theo chính sách Atlas
```

## 10. Xử lý sự cố thường gặp

| Hiện tượng | Hướng xử lý |
|------------|-------------|
| Backend không kết nối được Mongo | Kiểm tra Atlas **Network Access**, URI, user/password, DB name trong URI |
| Browser báo CORS / API lỗi | Đảm bảo `FRONTEND_URL` **trùng** scheme + host + port mà user mở trang |
| Port 3000 không vào được | Security Group inbound + kiểm tra `docker compose ps` |
| Hết RAM khi build frontend | Dùng instance lớn hơn (`t3.medium` tạm thời) hoặc tăng swap; hoặc build image trên CI rồi `docker pull` trên EC2 |
| `npm ci` / build frontend fail | Commit `frontend/package-lock.json` và `git pull` trên EC2. Dockerfile đã đổi sang `node:20-bookworm-slim` và fallback `npm install` nếu không có lockfile. Log chi tiết: `docker compose build --progress=plain frontend` |

---

Tài liệu liên quan trong repo: `README.md`, `docker-compose.yml`, `backend/.env.example`.
