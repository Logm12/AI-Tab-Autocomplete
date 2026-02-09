# Phase 4: Deployment - Local Server & RAG

## 🎯 Mục Tiêu

Deploy model GGUF từ Phase 3 thành HTTP server với RAG context injection.

**Input**: `qwen-coder-code-completion-q4_k_m.gguf` (~400MB)  
**Output**: Local HTTP server tương thích OpenAI API + RAG system

## 📋 Phase 4 Gồm Những Gì?

### 1. **llama-server Setup**
- HTTP server tuân thủ chuẩn OpenAI API
- KV cache reusing (slot management)
- Giảm độ trễ khi gõ code liên tục
- Chạy trên CPU, không cần GPU

### 2. **RAG Context Injection**
- **Semantic Chunking**: Cắt code theo function/class
- **BM25 Search**: Keyword search cực nhanh
- **Smart Triggering**: Chỉ chạy RAG khi cần (`.`, `(`, etc.)
- Inject context vào prompt để model hiểu codebase

### 3. **Extension Integration**
- API endpoint tương thích VS Code extension
- Completion streaming
- Context management
- Error handling

## 🚀 Cách Chạy

### Option 1: Google Colab (Khuyến Nghị)

1. **Mở Google Colab** (CPU runtime)
2. **Copy `phase4_deployment.py`** vào cell
3. **Upload model GGUF** từ Phase 3
4. **Chạy cell**
5. **Server chạy tại** `http://localhost:8080`
6. **Test với API calls**

### Option 2: Local Machine

```bash
# 1. Cài llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp && make

# 2. Chạy server
./llama-server \
  -m qwen-coder-code-completion-q4_k_m.gguf \
  -c 2048 \
  --port 8080 \
  --slots 4 \
  --cont-batching

# 3. Test
curl http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "def hello():", "max_tokens": 64}'
```

## ⏱️ Thời Gian

| Bước | Thời gian | Mô tả |
|------|-----------|-------|
| Upload model | 2-3 min | Upload GGUF file |
| Setup llama.cpp | 5-10 min | Clone & compile |
| Start server | 10-20 sec | Load model vào RAM |
| Index codebase | 1-2 min | Chunking + BM25 index |
| **TOTAL** | **10-15 min** | |

## 📊 Kết Quả Mong Đợi

### Server Performance
```
Latency (cold):     100-200ms  (first request)
Latency (warm):     20-50ms    (with KV cache)
Throughput:         15-30 tok/s
RAM Usage:          800MB-1.2GB
```

### RAG Performance
```
Chunking:           ~1000 chunks/sec
BM25 Search:        <5ms per query
Context Injection:  <10ms overhead
```

## 📡 API Endpoints

### 1. `/v1/completions` - Code Completion
```bash
POST http://localhost:8080/v1/completions
Content-Type: application/json

{
  "prompt": "<PRE> def calculate_sum(a, b): <SUF> <MID>",
  "max_tokens": 64,
  "temperature": 0.2,
  "top_p": 0.95,
  "stop": ["
