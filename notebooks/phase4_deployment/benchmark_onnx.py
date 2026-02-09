import os
import time
import torch
from optimum.onnxruntime import ORTModelForCausalLM
from transformers import AutoTokenizer
import onnxruntime as ort
import numpy as np

# Robust Path Resolution
# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Resolve model path relative to the script, not the current working directory
MODEL_PATH = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "phase3_optimization", "qwen2.5-coder-0.5b-onnx-int8"))

PROMPT = "import pandas as"

def benchmark(threads):
    print(f"\n--- Benchmarking with intra_op_num_threads={threads} ---")
    print(f"Target Model Path: {MODEL_PATH}")
    
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model path does not exist: {MODEL_PATH}")
        return

    sess_options = ort.SessionOptions()
    sess_options.intra_op_num_threads = threads
    sess_options.inter_op_num_threads = 1
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    
    print("Loading model...")
    start_load = time.time()
    try:
        model = ORTModelForCausalLM.from_pretrained(
            MODEL_PATH,
            file_name="model_int8.onnx",
            use_cache=True,
            use_io_binding=False,
            session_options=sess_options,
            provider="CPUExecutionProvider"
        )
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    print(f"Model loaded in {time.time() - start_load:.2f}s")
    
    inputs = tokenizer(PROMPT, return_tensors="pt")
    
    # Warmup
    print("Warming up...")
    model.generate(**inputs, max_new_tokens=1)
    
    # Run Inference
    print("Running inference...")
    start_infer = time.time()
    outputs = model.generate(
        **inputs, 
        max_new_tokens=5, 
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id
    )
    end_infer = time.time()
    
    latency = (end_infer - start_infer) * 1000
    print(f"Total Latency (5 tokens): {latency:.2f}ms")
    print(f"Average per token: {latency/5:.2f}ms")
    
    decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"Output: {decoded}")

if __name__ == "__main__":
    # Test with different thread counts
    for t in [1, 2, 4]:
        benchmark(t)
