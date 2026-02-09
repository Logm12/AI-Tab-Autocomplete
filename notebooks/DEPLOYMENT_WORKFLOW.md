# AI Auto-Complete: Quy Trình Triển Khai Đầy Đủ

## Tổng Quan Luồng Công Việc

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  LAPTOP CÁ NHÂN │───▶│   DOCKER HUB    │───▶│  MÁY TẬP ĐOÀN   │
│  (Có mạng)      │    │  (Cloud)        │    │  (Server mạnh)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        ▲                                              │
        │              SYNC MODEL                      │
        └──────────────────────────────────────────────┘
```

---

## PHẦN A: TRÊN LAPTOP CÁ NHÂN (Chuẩn bị & Push)

### A1. Cài đặt Docker Hub Account
```bash
# Đăng ký tại: https://hub.docker.com
# Ghi nhớ: USERNAME và PASSWORD
```

### A2. Sửa file cấu hình
Mở `docker_push_registry.bat`, sửa:
```batch
set USERNAME=your-dockerhub-username
```

### A3. Build và Push Image lên Docker Hub
```bash
cd notebooks
docker_push_registry.bat
```
→ Image sẽ được push lên `docker.io/USERNAME/ai-autocomplete:latest`

### A4. Push Code lên Git (nếu cần)
```bash
git add .
git commit -m "Docker deployment setup"
git push origin main
```

---

## PHẦN B: TRÊN MÁY TẬP ĐOÀN (Pull, Train, Deploy)

### B1. Pull Docker Image
```bash
docker login
docker pull docker.io/USERNAME/ai-autocomplete:latest
```

### B2. Tạo Thư Mục Làm Việc
```bash
mkdir -p ~/ai-autocomplete/data
mkdir -p ~/ai-autocomplete/models
cd ~/ai-autocomplete
```

### B3. Chạy Phase 1: Tạo Dataset
```bash
# Clone repo hoặc copy scripts
git clone https://github.com/YOUR_REPO/AI-Auto-Complete.git
cd AI-Auto-Complete/notebooks

# Chạy crawl data
python phase1_data_engineering/01_crawl_filter.py
python phase1_data_engineering/02_scrubbing.py
python phase1_data_engineering/03_transform.py
python phase1_data_engineering/04_fim_gen.py

# Output: data/train.jsonl, data/val.jsonl
```

### B4. Chạy Phase 2: Training (Cần GPU)
```bash
# Nếu máy tập đoàn có GPU:
python -m pip install unsloth transformers peft accelerate
python phase2_training/train.py

# Hoặc chạy notebook:
jupyter notebook phase2_training/02_training.ipynb

# Output: final_model/ (LoRA adapter)
```

### B5. Chạy Phase 3: Convert sang GGUF
```bash
# Cài llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp && make -j$(nproc)
cd ..

# Convert model
python phase3_optimization/phase3_gguf_pipeline.py

# Output: qwen2.5-coder-0.5b-q4_k_m.gguf
```

### B6. Chạy Phase 4: Deploy Server
```bash
# Copy model vào thư mục
cp qwen2.5-coder-0.5b-q4_k_m.gguf ~/ai-autocomplete/models/

# Chạy Docker container
docker run -d \
    --name ai-server \
    -p 8000:8000 \
    -v ~/ai-autocomplete/models:/app/models:ro \
    docker.io/USERNAME/ai-autocomplete:latest

# Test
curl http://localhost:8000/health
```

---

## PHẦN C: ĐỒNG BỘ MODEL VỀ LAPTOP CÁ NHÂN

### Cách 1: Qua Docker Hub (Khuyên dùng)

**Trên máy tập đoàn:**
```bash
# Tạo image mới chứa model đã train
docker build -t USERNAME/ai-autocomplete:trained -f- . <<EOF
FROM docker.io/USERNAME/ai-autocomplete:latest
COPY qwen2.5-coder-0.5b-q4_k_m.gguf /app/models/
EOF

# Push lên Docker Hub
docker push USERNAME/ai-autocomplete:trained
```

**Trên laptop cá nhân:**
```bash
docker pull USERNAME/ai-autocomplete:trained
docker run -d -p 8000:8000 USERNAME/ai-autocomplete:trained
```

### Cách 2: Download trực tiếp file GGUF

**Trên máy tập đoàn:**
```bash
# Nén model
zip model_trained.zip qwen2.5-coder-0.5b-q4_k_m.gguf

# Upload lên cloud storage hoặc server file
# VD: Google Drive, OneDrive, hoặc server nội bộ
```

**Trên laptop cá nhân:**
```bash
# Download và giải nén
unzip model_trained.zip -d notebooks/phase3_optimization/gguf_model/

# Chạy server
cd notebooks
docker_pull_run.bat
```

---

## PHẦN D: CÁC LỆNH HỮU ÍCH

### Quản lý Docker
```bash
# Xem logs
docker logs -f ai-server

# Dừng server
docker stop ai-server

# Xóa container
docker rm ai-server

# Xem tất cả images
docker images

# Xóa image
docker rmi USERNAME/ai-autocomplete:latest
```

### Test API
```bash
# Health check
curl http://localhost:8000/health

# Inline completion
curl -X POST http://localhost:8000/v1/inline \
  -H "Content-Type: application/json" \
  -d '{"prompt": "import pandas as", "max_tokens": 16}'

# Block completion
curl -X POST http://localhost:8000/v1/block \
  -H "Content-Type: application/json" \
  -d '{"prompt": "def fibonacci(n):", "max_tokens": 64}'
```

---

## TÓM TẮT NHANH

| Bước | Vị trí | Lệnh chính |
|------|--------|------------|
| 1 | Laptop | `docker_push_registry.bat` |
| 2 | Server | `docker pull USERNAME/ai-autocomplete` |
| 3 | Server | `python phase1-4 scripts` |
| 4 | Server | `docker push USERNAME/ai-autocomplete:trained` |
| 5 | Laptop | `docker pull USERNAME/ai-autocomplete:trained` |
