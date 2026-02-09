"""
Phase 3: GGUF Conversion Pipeline (Kaggle)
==========================================
This script converts a fine-tuned LoRA model to GGUF Q4_K_M format for fast CPU inference.

Target: ~80-100ms/token on CPU using llama-cpp-python.

Usage on Kaggle:
1. Upload your fine-tuned model (from Phase 2) to Kaggle as a Dataset.
2. Create a new Kaggle Notebook with GPU T4 x2 accelerator.
3. Copy this script into the notebook and run.
4. Download the output GGUF file.
"""

# ============================================================
# CELL 1: Install Dependencies
# ============================================================
# !pip install -q transformers peft accelerate bitsandbytes sentencepiece protobuf
# !pip install -q huggingface_hub

# Build llama.cpp from source (required for convert scripts)
# !git clone https://github.com/ggerganov/llama.cpp.git
# !cd llama.cpp && make -j$(nproc)

# Install Python requirements for conversion
# !pip install -q -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt

print("Dependencies installed!")

# ============================================================
# CELL 2: Configuration
# ============================================================
import os
import torch

# === MODIFY THESE PATHS ===
# Path to your fine-tuned LoRA adapter (uploaded as Kaggle Dataset)
LORA_ADAPTER_PATH = "/kaggle/input/your-lora-adapter/final_model"

# Base model (the original model you fine-tuned from)
BASE_MODEL_NAME = "Qwen/Qwen2.5-Coder-0.5B-Instruct"

# Output paths
MERGED_MODEL_PATH = "/kaggle/working/merged_model"
GGUF_OUTPUT_PATH = "/kaggle/working/qwen2.5-coder-0.5b-q4_k_m.gguf"

print(f"LoRA Adapter: {LORA_ADAPTER_PATH}")
print(f"Base Model: {BASE_MODEL_NAME}")
print(f"Output GGUF: {GGUF_OUTPUT_PATH}")

# ============================================================
# CELL 3: Merge LoRA with Base Model
# ============================================================
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

print("\n=== Step 1: Loading Base Model ===")
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL_NAME,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME, trust_remote_code=True)

print("\n=== Step 2: Loading LoRA Adapter ===")
model = PeftModel.from_pretrained(base_model, LORA_ADAPTER_PATH)

print("\n=== Step 3: Merging LoRA into Base Model ===")
model = model.merge_and_unload()

print("\n=== Step 4: Saving Merged Model ===")
model.save_pretrained(MERGED_MODEL_PATH, safe_serialization=True)
tokenizer.save_pretrained(MERGED_MODEL_PATH)
print(f"Merged model saved to: {MERGED_MODEL_PATH}")

# ============================================================
# CELL 4: Convert to GGUF Format
# ============================================================
import subprocess

print("\n=== Step 5: Converting to GGUF (F16) ===")
# First convert to F16 GGUF
f16_gguf_path = "/kaggle/working/qwen2.5-coder-0.5b-f16.gguf"

convert_cmd = [
    "python", "llama.cpp/convert_hf_to_gguf.py",
    MERGED_MODEL_PATH,
    "--outfile", f16_gguf_path,
    "--outtype", "f16"
]

result = subprocess.run(convert_cmd, capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print(f"Error: {result.stderr}")
else:
    print(f"F16 GGUF created: {f16_gguf_path}")

# ============================================================
# CELL 5: Quantize to Q4_K_M
# ============================================================
print("\n=== Step 6: Quantizing to Q4_K_M ===")

quantize_cmd = [
    "./llama.cpp/llama-quantize",
    f16_gguf_path,
    GGUF_OUTPUT_PATH,
    "Q4_K_M"
]

result = subprocess.run(quantize_cmd, capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print(f"Error: {result.stderr}")
else:
    print(f"Quantized GGUF created: {GGUF_OUTPUT_PATH}")

# ============================================================
# CELL 6: Verify Output
# ============================================================
print("\n=== Step 7: Verification ===")

if os.path.exists(GGUF_OUTPUT_PATH):
    size_mb = os.path.getsize(GGUF_OUTPUT_PATH) / (1024 * 1024)
    print(f"✅ GGUF file created successfully!")
    print(f"   Path: {GGUF_OUTPUT_PATH}")
    print(f"   Size: {size_mb:.2f} MB")
    
    # Expected size for Q4_K_M of 0.5B model: ~300-400MB
    if 200 < size_mb < 500:
        print("   Size looks correct for Q4_K_M quantization.")
    else:
        print("   ⚠️ Size seems unusual, please verify the model.")
else:
    print("❌ GGUF file not found. Check error messages above.")

# ============================================================
# CELL 7: Quick Test with llama-cpp-python
# ============================================================
print("\n=== Step 8: Quick Inference Test ===")

# Install llama-cpp-python for testing
# !pip install -q llama-cpp-python

try:
    from llama_cpp import Llama
    
    llm = Llama(
        model_path=GGUF_OUTPUT_PATH,
        n_ctx=2048,
        n_threads=4,
        verbose=False
    )
    
    # Test prompt
    prompt = "import pandas as"
    
    import time
    start = time.time()
    output = llm(prompt, max_tokens=10, stop=["\n"], echo=False)
    latency = (time.time() - start) * 1000
    
    generated_text = output["choices"][0]["text"]
    tokens_generated = output["usage"]["completion_tokens"]
    ms_per_token = latency / tokens_generated if tokens_generated > 0 else 0
    
    print(f"Prompt: {prompt}")
    print(f"Generated: {generated_text}")
    print(f"Latency: {latency:.2f}ms ({ms_per_token:.2f}ms/token)")
    print(f"\n✅ Model is working! Ready for deployment.")
    
except Exception as e:
    print(f"Test skipped or failed: {e}")
    print("You can test the model locally after downloading.")

# ============================================================
# CELL 8: Download Instructions
# ============================================================
print("\n" + "="*60)
print("🎉 GGUF CONVERSION COMPLETE!")
print("="*60)
print(f"""
Next Steps:
1. Download the GGUF file from Kaggle Output:
   {GGUF_OUTPUT_PATH}

2. Place it in your local project:
   notebooks/phase3_optimization/gguf_model/qwen2.5-coder-0.5b-q4_k_m.gguf

3. Update Phase 4 server to use llama-cpp-python instead of ONNX Runtime.

Expected Performance:
- CPU (4 threads): ~80-100ms/token
- This is 1.5-2x faster than ONNX INT8!
""")
