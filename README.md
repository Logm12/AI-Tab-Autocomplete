# Local Code Completion System

**Edge-optimized code completion system powered by Qwen2.5-Coder**

Run code completion locally on local CPU with low latency. This system eliminates the need for cloud dependencies, GPUs, or external API keys, ensuring code remains private.

---

## Features

- **Privacy Focused**: All inference runs locally; no code is transmitted to external servers.
- **Low Latency**: Achieves 20-50ms latency on standard CPUs.
- **Efficient**: Uses a quantized (Q4_K_M) model (~400MB).
- **Compatible**: Drop-in replacement for OpenAI API endpoints, compatible with VS Code extensions like Continue.
- **Docker Support**: Deployment via Docker Compose.
- **Multi-Language**: Supports Python, Java, C++, and JavaScript.

## Performance Metrics

| Metric | Value |
|--------|-------|
| Model Size | ~400MB (GGUF Q4_K_M) |
| Cold Start Latency | 100-200ms |
| Warm Latency (Inline) | **20-50ms** |
| Warm Latency (Block) | 50-100ms |
| RAM Usage | 800MB - 1.2GB |
| GPU Required | No |

## Architecture

The system follows a streamlined four-phase pipeline designed for efficiency and privacy:

1.  **Data Engineering**: Collection, scrubbing, and transformation of training data (from BigCode The Stack).
2.  **Model Training**: Fine-tuning Qwen2.5-Coder using QLoRA and DPO (Direct Preference Optimization).
3.  **Optimization**: Merging adapters and converting/quantizing to GGUF format for edge deployment.
4.  **Deployment**: Serving the model via a FastAPI server using `llama.cpp` for inference.
The following diagram illustrates the complete workflow, from data processing to ensuring the model runs efficiently on consumer hardware.

<div align="center">
  <img src="assets/Viettel_data_pipeline.png" alt="System Architecture Diagram" width="100%">
</div>

## Quick Start

### Option 1: Docker (Recommended)

1.  Clone the repository and navigating to the notebooks directory.
2.  Start the inference server:
    ```bash
    docker-compose up inference
    ```
3.  The server will be available at `http://localhost:8000`.

### Option 2: Local Installation

1.  **Environment Setup**:
    ```bash
    python -m venv venv
    source venv/bin/activate 
    # or: .\venv\Scripts\activate 
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r notebooks/phase4_deployment/requirements.txt
    ```

3.  **Configuration**:
    Create a `.env` file in `notebooks/phase4_deployment/` based on `.env.example`. Ensure `MODEL_PATH` points to your GGUF model.

4.  **Run Server**:
    ```bash
    cd notebooks/phase4_deployment
    python server_gguf.py
    ```

### Testing the API

**Health Check**:
```bash
curl http://localhost:8000/health
```

**Code Completion Request**:
```bash
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "import pandas as",
    "max_tokens": 16
  }'
```

**Expected Response**: `" pd"`

## Project Structure

```
AI-Auto-Complete/
├── notebooks/
│   ├── phase1_data_engineering/     # Data collection & processing scripts
│   ├── phase2_training/             # Model training notebooks (SFT, DPO)
│   ├── phase3_optimization/         # Model optimization and quantization
│   ├── phase4_deployment/           # Production server and testing
│   │   ├── server_gguf.py           # FastAPI inference server code
│   │   ├── utils.py                 # Shared utility functions
│   │   └── test_client_gguf.py      # Client verification script
│   ├── docker-compose.yml           # Container orchestration
│   └── Dockerfile.training          # Training environment definition
│
├── models/                          # Quantized model files (*.gguf)
└── PROJECT_REPORT.md                # Detailed technical documentation
```

## API Reference

The server provides OpenAI-compatible endpoints:

-   `GET /health`: Server status check.
-   `GET /v1/models`: List available models.
-   `POST /v1/completions`: Single prompt code completion.
-   `POST /v1/chat/completions`: Chat-based interaction.

## Integration with IDEs

This server works with the **Continue** extension for VS Code and JetBrains.

**Configuration (`~/.continue/config.yaml`)**:

```yaml
name: Local Qwen
version: 1.0.0
models:
  - name: Qwen Autocomplete
    provider: openai
    model: qwen2.5-coder
    apiBase: http://127.0.0.1:8000/v1
    apiKey: empty
    roles:
      - autocomplete
    autocompleteOptions:
      debounceDelay: 50
      maxPromptTokens: 1024
      transform: false
```

## Offline Environment Setup

For environments without internet access, you can pre-download all necessary Python packages (wheels) using the provided Docker configuration.

1.  **Build the Downloader Image**:
    ```bash
    docker build -f Dockerfile.wheels -t offline-wheels .
    ```

2.  **Extract Wheels**:
    Copy the downloaded packages from the container to your local machine:
    ```bash
    docker create --name temp-container offline-wheels
    docker cp temp-container:/wheels ./offline_packages
    docker rm temp-container
    ```

3.  **Install on Offline Machine**:
    Transfer the `offline_packages` directory to your target machine and install:
    ```bash
    pip install --no-index --find-links=./offline_packages -r phase4_deployment/requirements.txt
    ```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
