# MediAssist Inference API

## 1\. Tên dự án & Mục tiêu

**Tên dự án:** MediAssist Inference API

**Mục tiêu:** Xây dựng một REST API service cho phép người dùng nhập triệu chứng bằng tiếng Việt tự nhiên. Hệ thống phân tích nguy cơ tiềm ẩn từ triệu chứng, phân loại mức độ khẩn cấp (triage), sau đó đề xuất lộ trình khám cụ thể — bác sĩ nào, khoa nào, xét nghiệm gì cần làm trước — dựa trên dữ liệu thật của bệnh viện lưu trong DB. Kết quả không phải do LLM tự bịa mà kết hợp giữa LLM phân tích ngôn ngữ và rule engine \+ DB bệnh viện để đảm bảo độ tin cậy.

> **Disclaimer:** Hệ thống chỉ mang tính chất gợi ý tham khảo, không thay thế chẩn đoán y tế từ bác sĩ.

---

## 2\. Công nghệ sử dụng

### Application Layer

| Công nghệ | Vai trò |
| :---- | :---- |
| Python 3.11 | Ngôn ngữ chính |
| FastAPI | REST API framework — nhận request, validate, route |
| Uvicorn \+ Gunicorn | ASGI server chạy FastAPI trên EC2 |
| Docker | Đóng gói service thành container, dễ deploy |
| LangChain | Orchestrate LLM call \+ prompt template |
| OpenAI / Claude API | LLM phân tích triệu chứng, nhận diện nguy cơ |
| Sentence Transformers | Tạo embedding vector để semantic cache |

### AWS Infrastructure

| AWS Service | Vai trò |
| :---- | :---- |
| VPC (10.0.0.0/16) | Mạng riêng biệt, cô lập toàn bộ hệ thống |
| EC2 (t3.small) | Chạy FastAPI service — Public Subnet |
| AWS API Gateway | Entry point HTTPS duy nhất, rate limiting, throttling |
| ElastiCache (Redis) | Semantic cache kết quả LLM — Private Subnet |
| RDS PostgreSQL | Dữ liệu bệnh viện: bác sĩ, xét nghiệm, rule engine — Private Subnet |
| S3 | Lưu request/response log, medical document PDF |
| Internet Gateway | Cho phép EC2 kết nối Internet để gọi LLM API |
| VPC Endpoint (S3) | EC2 truy cập S3 nội bộ, không qua Internet |
| Security Group | Firewall: chỉ EC2 mới được kết nối Redis và RDS |
| AWS Secrets Manager | Lưu LLM API key an toàn, không hardcode |

---

## 3\. Luồng xử lý nghiệp vụ

### Tổng quan

Bệnh nhân nhập triệu chứng

         │

         ▼

\[Bước 1\] Semantic Cache check (Redis)

  Cache hit ──────────────────────────────► Trả về ngay

  Cache miss

         │

         ▼

\[Bước 2\] Risk Assessment (LLM)

  Phân tích triệu chứng → danh sách nguy cơ tiềm ẩn \+ xác suất

         │

         ▼

\[Bước 3\] Triage Classification (Rule Engine \+ DB)

  EMERGENCY → URGENT → GENERAL → SPECIALIST

         │

         ▼

\[Bước 4\] Lộ trình khám (DB bệnh viện)

  Bác sĩ nào → Xét nghiệm gì → Chuyên khoa tiếp theo nếu cần

         │

         ▼

\[Bước 5\] Lưu cache \+ log → Trả response

### Phân loại triage

| Mức | Điều kiện | Hành động |
| :---- | :---- | :---- |
| `EMERGENCY` | Triệu chứng nguy hiểm tính mạng (đau ngực dữ dội, liệt đột ngột, khó thở nặng) | Cảnh báo đỏ, gọi 115 ngay — không gợi ý bác sĩ |
| `URGENT` | Nguy cơ cao, cần khám trong 24h (sốt cao \+ cứng cổ, đau bụng dữ dội) | Gợi ý bác sĩ \+ slot sớm nhất có sẵn |
| `GENERAL` | Triệu chứng mơ hồ, chồng chéo nhiều nguy cơ | Khám tổng quát trước \+ xét nghiệm sàng lọc |
| `SPECIALIST` | Triệu chứng rõ ràng, chỉ định được chuyên khoa | Gợi ý thẳng bác sĩ chuyên khoa phù hợp |

### Ví dụ response đầy đủ

Input: `"mệt mỏi 2 tuần, sụt 4kg, ra mồ hôi đêm, ho khan"`

{

  "symptoms\_analyzed": \["mệt mỏi kéo dài", "sụt cân", "ra mồ hôi đêm", "ho khan"\],

  "risk\_assessment": \[

    { "condition": "Lao phổi",          "risk\_level": "high",   "probability": 0.68 },

    { "condition": "U lympho Hodgkin",  "risk\_level": "medium", "probability": 0.31 },

    { "condition": "Tiểu đường type 2", "risk\_level": "medium", "probability": 0.28 },

    { "condition": "Cường giáp",        "risk\_level": "low",    "probability": 0.15 }

  \],

  "triage": "urgent",

  "examination\_pathway": {

    "step\_1": {

      "label": "Khám tổng quát trước",

      "reason": "Triệu chứng chồng chéo nhiều nguy cơ — cần bác sĩ Nội tổng hợp sàng lọc ban đầu",

      "doctor": {

        "name": "BS. Nguyễn Văn A",

        "department": "Nội tổng hợp",

        "hospital": "Bệnh viện Bạch Mai",

        "next\_available": "2026-09-28 08:00",

        "available\_slots": 3

      }

    },

    "step\_2": {

      "label": "Xét nghiệm cơ bản song song",

      "tests": \[

        { "name": "Công thức máu (CBC)",      "reason": "Phát hiện thiếu máu, nhiễm trùng, u lympho" },

        { "name": "X-quang ngực thẳng",       "reason": "Sàng lọc Lao phổi, u phổi" },

        { "name": "Test Xpert MTB/RIF",       "reason": "Xác nhận Lao phổi nếu X-quang nghi ngờ" },

        { "name": "Đường huyết lúc đói",      "reason": "Loại trừ Tiểu đường" },

        { "name": "TSH, FT4",                 "reason": "Loại trừ Cường giáp" }

      \]

    },

    "step\_3": {

      "label": "Chuyển chuyên khoa sau khi có kết quả",

      "note": "Bác sĩ Nội tổng hợp đọc kết quả và route đến đúng chuyên khoa",

      "possible\_routes": \[

        { "if": "X-quang nghi Lao",   "then": "Hô hấp / Lao" },

        { "if": "CBC bất thường",      "then": "Huyết học" },

        { "if": "Đường huyết cao",     "then": "Nội tiết" },

        { "if": "TSH bất thường",      "then": "Nội tiết" }

      \]

    }

  },

  "cached": false,

  "latency\_ms": 3800,

  "disclaimer": "Đây là gợi ý tham khảo dựa trên triệu chứng. Bác sĩ sẽ quyết định lộ trình khám chính xác."

}

---

## 4\. Schema Database (RDS PostgreSQL)

\-- Bệnh viện

hospitals (

  id, name, address, phone

)

\-- Chuyên khoa

specialties (

  id, name, description

)

\-- Bác sĩ

doctors (

  id, name, specialty\_id, hospital\_id,

  experience\_years, bio

)

\-- Lịch làm việc và slot

doctor\_schedules (

  id, doctor\_id, date,

  time\_slot, is\_available

)

\-- Danh mục xét nghiệm của từng bệnh viện

hospital\_tests (

  id, hospital\_id, test\_name,

  test\_code, price, turnaround\_hours

)

\-- Rule engine: nguy cơ → xét nghiệm gợi ý

risk\_test\_mapping (

  id, condition\_name, test\_code, priority

)

\-- Rule engine: nguy cơ → chuyên khoa tiếp theo

risk\_specialty\_mapping (

  id, condition\_name, specialty\_id,

  route\_condition

)

\-- Lịch sử request (audit trail)

analysis\_logs (

  id, symptoms\_text, triage\_result,

  risk\_json, pathway\_json, created\_at

)

> **Nguyên tắc quan trọng:** `risk_test_mapping` và `risk_specialty_mapping` là rule engine cứng từ DB — không để LLM tự quyết định xét nghiệm hay chuyên khoa. LLM chỉ làm nhiệm vụ phân tích ngôn ngữ và nhận diện nguy cơ, phần routing luôn dựa trên dữ liệu có kiểm soát.

---

## 5\. API Endpoints

| Method | Endpoint | Mô tả |
| :---- | :---- | :---- |
| `POST` | `/api/v1/analyze` | Phân tích triệu chứng → risk assessment \+ triage \+ lộ trình khám |
| `GET` | `/api/v1/doctors` | Danh sách bác sĩ theo chuyên khoa và bệnh viện |
| `GET` | `/api/v1/doctors/:id/slots` | Lịch slot còn trống của bác sĩ |
| `GET` | `/api/v1/specialties` | Danh sách chuyên khoa |
| `GET` | `/api/v1/tests` | Danh mục xét nghiệm theo bệnh viện |
| `GET` | `/health` | Health check — API Gateway dùng để monitor |

---

## 6\. Kiến trúc mạng VPC

Internet

    │

    ▼

AWS API Gateway (HTTPS)

    │

    ▼  \[chỉ mở port 8000 từ API Gateway\]

┌─────────────────────────────────────────────────┐

│                VPC (10.0.0.0/16)                │

│                                                 │

│  ┌──────────────────────┐                       │

│  │  Public Subnet       │                       │

│  │  (10.0.1.0/24)       │                       │

│  │                      │                       │

│  │  EC2 — FastAPI       │◄── Internet Gateway   │

│  │  (Docker container)  │    (gọi LLM API)      │

│  └──────────┬───────────┘                       │

│             │  \[Security Group: chỉ từ EC2\]     │

│  ┌──────────▼───────────┐                       │

│  │  Private Subnet      │                       │

│  │  (10.0.2.0/24)       │                       │

│  │                      │                       │

│  │  ElastiCache Redis   │  ← Semantic cache     │

│  │  RDS PostgreSQL      │  ← Hospital data      │

│  └──────────────────────┘                       │

│                                                 │

└─────────────────────────────────────────────────┘

    │

    ▼  \[VPC Endpoint — không qua Internet\]

AWS S3 (log \+ documents)

### Tương tác với VPC — tóm tắt

| Component | Subnet | Lý do |
| :---- | :---- | :---- |
| EC2 (FastAPI) | Public | Cần nhận traffic từ API Gateway và gọi LLM API ra Internet |
| ElastiCache Redis | Private | Data layer, không cần Internet, chỉ EC2 được kết nối |
| RDS PostgreSQL | Private | Chứa dữ liệu bệnh viện nhạy cảm, chỉ EC2 được kết nối |
| S3 | Ngoài VPC | Truy cập qua VPC Endpoint, không đi qua Internet |
| LLM API (OpenAI/Claude) | External | EC2 gọi ra qua Internet Gateway, key lưu trong Secrets Manager |

---

## 7\. Ghi chú thiết kế — Trade-off EC2 Subnet

EC2 được đặt ở **Public Subnet** thay vì Private Subnet. Đây là quyết định có chủ ý:

**Cách 1 — Public Subnet \+ Internet Gateway** *(thiết kế hiện tại)*

| Ưu điểm | Nhược điểm |
| :---- | :---- |
| Đơn giản, không cần thêm component | EC2 có Public IP, bị expose ra Internet |
| Không phát sinh chi phí thêm | Tăng attack surface, không đúng chuẩn production |

**Cách 2 — Private Subnet \+ NAT Gateway** *(production chuẩn)*

| Ưu điểm | Nhược điểm |
| :---- | :---- |
| EC2 không có Public IP, không thể tấn công trực tiếp | Chi phí cố định \~\$32–\$45/tháng cho NAT Gateway |
| Đúng chuẩn bảo mật production | Thêm component trung gian, tăng độ phức tạp |
| Tuân thủ principle of least privilege | NAT Gateway là điểm hỏng tiềm ẩn cho toàn bộ outbound Private Subnet |
| Dễ kiểm soát và audit outbound traffic | Cần cấu hình thêm route table |

> **Quyết định:** Dùng Cách 1 vì chi phí NAT Gateway (\~\$32/tháng) không hợp lý cho bài tập. Rủi ro giảm thiểu bằng Security Group chỉ mở inbound từ API Gateway và API key lưu trong Secrets Manager.  
>   
> **Production thật:** dùng Private Subnet \+ NAT Gateway theo AWS Well-Architected Framework.

---

## 8\. Điểm nghẽn tiềm ẩn & Hướng giải quyết

| \# | Điểm nghẽn | Hậu quả | Giải pháp | Ghi chú |
| :---- | :---- | :---- | :---- | :---- |
| 1 | `t3.small` (2GB RAM) load Sentence Transformers (\~400MB–1GB) cùng FastAPI | OOM Killer ngắt container đột ngột | Nâng lên `t3.medium`, hoặc dùng **Amazon Bedrock Embeddings API** thay self-host | ⚠️ Chấp nhận cho bài tập — chi phí instance cao hơn không phù hợp scope |
| 2 | Single EC2, không có Load Balancer | SPOF — EC2 chết là toàn bộ API ngừng | **ALB \+ Auto Scaling Group**, tối thiểu 2 instance trên 2 AZ | ⚠️ Chấp nhận cho bài tập — ALB phát sinh chi phí và độ phức tạp không cần thiết |
| 3 | Embedding chạy đồng bộ (blocking) trong FastAPI async | Event loop nghẽn, request đồng thời bị delay | Dùng `run_in_executor` offload sang thread pool, hoặc tách embedding thành service riêng | Có thể fix ngay trong code, không tốn chi phí thêm |
| 4 | EC2 ở Public Subnet, outbound qua Internet Gateway | Attack surface lớn, không chuẩn production | Chuyển EC2 sang Private Subnet \+ **NAT Gateway** | ⚠️ Chấp nhận cho bài tập — NAT Gateway \~\$32/tháng không hợp lý cho scope học tập |
| 5 | Data transfer cost khi gọi LLM API qua Internet Gateway | Egress fee \$0.09/GB tăng khi scale | Dùng **Amazon Bedrock** thay OpenAI/Claude external — gọi nội bộ AWS, không egress cost | Không đáng kể ở quy mô bài tập, chỉ ảnh hưởng khi scale hàng triệu request |

