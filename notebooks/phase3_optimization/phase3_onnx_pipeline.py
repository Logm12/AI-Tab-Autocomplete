import os
import shutil
import subprocess
import sys
from pathlib import Path

# --- Configuration ---
BASE_MODEL_ID = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
ADAPTER_PATH = "/kaggle/input/modell/final_model" # Adjust based on Kaggle input structure
OUTPUT_DIR = "qwen2.5-coder-0.5b-onnx"
QUANTIZED_OUTPUT = "qwen2.5-coder-0.5b-onnx-int8"

def install_dependencies():
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "optimum[onnxruntime]", "onnx", "onnxruntime", "peft", "transformers", "accelerate", "protobuf==3.20.3"])

def main():
    install_dependencies()
    
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    from optimum.exporters.onnx import main_export
    from onnxruntime.quantization import quantize_dynamic, QuantType

    # 1. Load and Merge Model
    print("Loading Base Model...")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID,
        torch_dtype=torch.float32, # CPU friendly
        device_map="cpu"
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)

    print(f"Loading Adapter from {ADAPTER_PATH}...")
    # Handle case where adapter is inside a subdir or zip (simplified for script)
    # In Kaggle, usually inputs are unzipped. 
    # If ADAPTER_PATH doesn't exist, try to find it
    adapter_final_path = ADAPTER_PATH
    if not os.path.exists(ADAPTER_PATH):
        for root, dirs, files in os.walk("/kaggle/input"):
            if "adapter_config.json" in files:
                adapter_final_path = root
                break
    
    print(f"Found adapter at: {adapter_final_path}")
    model = PeftModel.from_pretrained(base_model, adapter_final_path)
    
    print("Merging model...")
    model = model.merge_and_unload()
    
    # Save merged model temporarily for ONNX export
    merged_dir = "merged_model"
    model.save_pretrained(merged_dir)
    tokenizer.save_pretrained(merged_dir)
    
    # 2. Export to ONNX
    print("Exporting to ONNX...")
    # We use optimum's main_export for simplicity and robustness
    # optimum-cli export onnx --model merged_model --task text-generation-with-past qwen2.5-coder-0.5b-onnx
    
    subprocess.run([
        "optimum-cli", "export", "onnx",
        "--model", merged_dir,
        "--task", "text-generation-with-past",
        OUTPUT_DIR
    ], check=True)
    
    # 3. Quantize to INT8
    print("Quantizing to INT8 (Dynamic)...")
    onnx_model_path = os.path.join(OUTPUT_DIR, "model.onnx")
    quantized_model_path = os.path.join(QUANTIZED_OUTPUT, "model_int8.onnx")
    
    os.makedirs(QUANTIZED_OUTPUT, exist_ok=True)
    
    # Copy other necessary files (tokenizer, config, etc.)
    for file in os.listdir(OUTPUT_DIR):
        if file != "model.onnx" and not file.endswith(".onnx_data"):
            shutil.copy(os.path.join(OUTPUT_DIR, file), QUANTIZED_OUTPUT)
            
    quantize_dynamic(
        model_input=onnx_model_path,
        model_output=quantized_model_path,
        weight_type=QuantType.QUInt8
    )
    
    print(f"Quantization complete! Model saved to {QUANTIZED_OUTPUT}")
    print("Files in output:")
    print(os.listdir(QUANTIZED_OUTPUT))

if __name__ == "__main__":
    main()
