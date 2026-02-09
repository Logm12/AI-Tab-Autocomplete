import requests
import time
import json
import difflib
import re
import statistics

BASE_URL = "http://127.0.0.1:8000"

class MetricsCalculator:
    @staticmethod
    def tokenize(text):
        return re.findall(r'\S+', text)

    @staticmethod
    def exact_match(pred, expected):
        return 1.0 if pred.strip() == expected.strip() else 0.0

    @staticmethod
    def edit_similarity(pred, expected):
        if not pred and not expected: return 1.0
        matcher = difflib.SequenceMatcher(None, pred, expected)
        return matcher.ratio()

    @staticmethod
    def perfect_line(pred, expected):
        pred_line = pred.strip().split('\n')[0]
        exp_line = expected.strip().split('\n')[0]
        return 1.0 if pred_line == exp_line else 0.0

    @staticmethod
    def matched_ratio(pred, expected):
        p_tokens = MetricsCalculator.tokenize(pred)
        e_tokens = MetricsCalculator.tokenize(expected)
        if not e_tokens: return 0.0
        
        matches = 0
        for p, e in zip(p_tokens, e_tokens):
            if p == e: matches += 1
            else: break
        return matches / len(e_tokens)

    @staticmethod
    def ratio_of_completed_code(prompt, generated):
        total_len = len(prompt) + len(generated)
        return len(generated) / total_len if total_len > 0 else 0

    @staticmethod
    def persistence_rate(pred, expected):
        matcher = difflib.SequenceMatcher(None, pred, expected)
        match_len = sum(block.size for block in matcher.get_matching_blocks())
        return match_len / len(pred) if len(pred) > 0 else 0


def run_test_case(mode, test_cases):
    print(f"\n{'='*20} Testing {mode.upper()} Completion {'='*20}")
    
    results = {
        "latency": [], "es": [], "em": [], "pl": [], "mr": [], "rocc": [], "pr": []
    }
    
    print(f"[run_test_case] Started batch: {len(test_cases)} cases")

    for case in test_cases:
        prompt = case["prompt"]
        expected = case["expected"]
        
        endpoint = "/v1/completions"
        max_tokens = 24 if mode == "inline" else 64
        
        try:
            start = time.time()
            response = requests.post(
                f"{BASE_URL}{endpoint}",
                json={
                    "prompt": prompt, 
                    "max_tokens": max_tokens,
                    "stop": case.get("stop", None) 
                }
            )
            print(f"[run_test_case] Request sent. Status: {response.status_code}")
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                generated = data["choices"][0]["text"]
                
                em = MetricsCalculator.exact_match(generated, expected)
                es = MetricsCalculator.edit_similarity(generated, expected)
                pl = MetricsCalculator.perfect_line(generated, expected)
                mr = MetricsCalculator.matched_ratio(generated, expected)
                rocc = MetricsCalculator.ratio_of_completed_code(prompt, generated)
                pr = MetricsCalculator.persistence_rate(generated, expected)
                
                results["latency"].append(latency)
                results["es"].append(es)
                results["em"].append(em)
                results["pl"].append(pl)
                results["mr"].append(mr)
                results["rocc"].append(rocc)
                results["pr"].append(pr)

                print(f"[{mode.upper()}] Prompt: {prompt[:40]}...")
                print(f"   Actual:   {repr(generated)}")
                print(f"   Expected: {repr(expected)}")
                print(f"   Metrics:  TTS={latency:.0f}ms | PL={pl:.0f} | ES={es:.2f} | PR={pr:.2f}")
                print("-" * 60)
            else:
                print(f"Error {response.status_code}: {response.text}")

        except Exception as e:
            print(f"Connection Error: {e}")

    if results["latency"]:
        print(f"\nSUMMARY REPORT ({mode.upper()})")
        print("-" * 40)
        print(f"   Samples Evaluated:          {len(results['latency'])}")
        print(f"   Avg Time to Show (Latency): {statistics.mean(results['latency']):.2f} ms")
        print(f"   Exact Match (EM):           {statistics.mean(results['em'])*100:.1f}%")
        print(f"   Perfect Line (PL):          {statistics.mean(results['pl'])*100:.1f}%")
        print(f"   Edit Similarity (ES):       {statistics.mean(results['es'])*100:.1f}%")
        print(f"   Matched Ratio (MR):         {statistics.mean(results['mr'])*100:.1f}%")
        print(f"   Persistence Rate (PR):      {statistics.mean(results['pr'])*100:.1f}%")
        print("="*60)

def test_health():
    print("Checking Server Status...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print(f"Server Online: {response.json().get('model')}")
        else:
            print(f"Server Error: {response.status_code}")
            exit()
    except:
        print("Could not connect to server. Is 'server_gguf.py' running?")
        exit()

def main():
    test_health()
    
    inline_cases = [
        {"prompt": "import pandas as", "expected": " pd"},
        {"prompt": "import numpy as", "expected": " np"},
        {"prompt": "from fastapi import", "expected": " FastAPI"},
        {"prompt": "def add(a, b): return", "expected": " a + b"},
        {"prompt": "if __name__ == ", "expected": "'__main__':"},
        {"prompt": "print('Hello ", "expected": "World')"}
    ]
    run_test_case("inline", inline_cases)

    block_cases = [
        {
            "prompt": "def fibonacci(n):", 
            "expected": "\n    if n <= 1:\n        return n\n    else:\n        return fibonacci(n-1) + fibonacci(n-2)"
        },
        {
            "prompt": "def square(x):", 
            "expected": "\n    return x * x"
        },
        {
            "prompt": "class Dog:",
            "expected": "\n    def __init__(self, name):\n        self.name = name"
        }
    ]
    run_test_case("block", block_cases)

if __name__ == "__main__":
    main()