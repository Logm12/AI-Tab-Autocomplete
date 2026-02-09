import os
import time
import logging
import multiprocessing
import json
from contextlib import asynccontextmanager
from typing import List, Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from llama_cpp import Llama
from dotenv import load_dotenv

import utils

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"), 
    format='%(asctime)s | %(levelname)s | %(message)s', 
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global model state
model_state = {"llm": None}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for the application lifespan.
    Handles model loading and unloading.
    """
    model_path = os.getenv("MODEL_PATH")
    if not model_path:
        logger.error("MODEL_PATH environment variable not set.")
        model_state["llm"] = None
    elif not os.path.exists(model_path):
        logger.error(f"Model file not found at: {model_path}")
        model_state["llm"] = None
    else:
        try:
            logger.info(f"Loading model from: {model_path}")
            n_threads = max(1, multiprocessing.cpu_count() - 2) # Leave some cores for the OS
            
            model_state["llm"] = Llama(
                model_path=model_path,
                n_ctx=512,
                n_threads=n_threads,
                n_batch=512,
                n_gpu_layers=0, # CPU only
                verbose=False,
                use_mmap=True,
                use_mlock=False
            )
            logger.info(f"Model loaded successfully! Threads: {n_threads}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            model_state["llm"] = None
    
    yield
    
    # Cleanup
    if model_state["llm"]:
        del model_state["llm"]
        logger.info("Model unloaded.")

app = FastAPI(title="Edge AI Code Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# Request Models
class CompletionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra='ignore')
    model: str = "qwen2.5-coder"
    prompt: str
    suffix: Optional[str] = None
    max_tokens: Optional[int] = Field(default=24, alias="maxTokens")
    temperature: Optional[float] = 0.0
    top_p: Optional[float] = Field(default=0.95, alias="topP")
    stop: Optional[Union[str, List[str]]] = None
    stream: Optional[bool] = False

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra='ignore')
    model: str = "qwen2.5-coder"
    messages: List[ChatMessage]
    max_tokens: Optional[int] = Field(default=512, alias="maxTokens")
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = Field(default=0.95, alias="topP")
    stop: Optional[Union[str, List[str]]] = None
    stream: Optional[bool] = False

def token_heal(llm: Llama, prompt: str) -> tuple[str, str]:
    """
    Fixes tokenization artifacts at the boundary of the prompt.
    """
    if not llm:
        return prompt, ""
    try:
        tokens = llm.tokenize(prompt.encode('utf-8'))
        if not tokens:
            return prompt, ""
        decoded = llm.detokenize(tokens).decode('utf-8', errors='ignore')
        if len(decoded) < len(prompt):
            lost = prompt[len(decoded):]
            return decoded, lost
    except Exception:
        pass
    return prompt, ""

@app.get("/health")
def health_check():
    status = "ok" if model_state["llm"] else "error"
    return {"status": status, "model": os.path.basename(os.getenv("MODEL_PATH", "unknown"))}

@app.get("/v1/models")
def list_models():
    return {
        "object": "list", 
        "data": [{"id": "qwen2.5-coder", "object": "model", "owned_by": "local"}]
    }

@app.post("/v1/completions")
async def completions(request: CompletionRequest):
    llm = model_state["llm"]
    if not llm:
        raise HTTPException(status_code=503, detail="Model not initialized")

    start_time = time.time()
    
    # Pre-process prompt
    code = request.prompt
    # Remove special tokens if present in prompt to avoid confusion, though usually they aren't
    # (Simplified logic compared to original which did manual stripping of FIM tokens)
    
    lang = utils.detect_language(code)
    
    # Determine mode (Inline vs Block)
    lines = [l for l in code.split("\n") if not l.strip().startswith("// ")]
    last_line = lines[-1].strip() if lines else ""
    is_block = last_line.endswith(":") or last_line.endswith("{") or code.strip().endswith("\n")
    
    # Dynamic parameter adjustment
    max_tok = min(request.max_tokens or (16 if is_block else 8), 64) # Cap at 64 for safety
    temp = request.temperature if request.temperature is not None else (0.1 if is_block else 0.0)
    
    # Stop tokens
    stops = utils.get_stop_for_lang(lang, is_block)
    if request.stop:
        stops.extend(request.stop if isinstance(request.stop, list) else [request.stop])

    req_id = int(time.time() * 1000) % 10000
    logger.info(f"[{req_id}] CMPL | {lang} | {'BLOCK' if is_block else 'INLINE'} | Prompt len: {len(code)}")

    try:
        healed_prompt, prefix_loss = token_heal(llm, request.prompt)
        
        output = llm(
            prompt=healed_prompt,
            suffix=request.suffix,
            max_tokens=max_tok,
            stop=stops,
            temperature=temp,
            top_p=request.top_p,
            echo=False
        )
        
        generated_text = prefix_loss + output["choices"][0]["text"]
        generated_text = utils.filter_sensitive_output(generated_text)
        
        usage = output["usage"]
        latency_ms = (time.time() - start_time) * 1000
        
        logger.info(f"[{req_id}] DONE | {usage['completion_tokens']} toks | {latency_ms:.0f}ms")

        response = {
            "id": f"cmpl-{req_id}",
            "object": "text_completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "text": generated_text, 
                "index": 0, 
                "logprobs": None, 
                "finish_reason": "stop"
            }],
            "usage": usage
        }

        if request.stream:
            def stream_generator():
                yield f"data: {json.dumps(response)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
            
        return response

    except Exception as e:
        logger.error(f"[{req_id}] ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    llm = model_state["llm"]
    if not llm:
        raise HTTPException(status_code=503, detail="Model not initialized")
        
    start_time = time.time()
    
    # Format prompt for ChatML
    prompt_parts = []
    for msg in request.messages:
        role = msg.role
        content = msg.content
        prompt_parts.append(f"<|im_start|>{role}\n{content}<|im_end|>\n")
    
    prompt_parts.append("<|im_start|>assistant\n")
    full_prompt = "".join(prompt_parts)
    
    stops = ["<|im_end|>", "<|im_start|>"]
    if request.stop:
        stops.extend(request.stop if isinstance(request.stop, list) else [request.stop])
        
    try:
        output = llm(
            prompt=full_prompt,
            max_tokens=request.max_tokens or 512,
            stop=stops,
            temperature=request.temperature or 0.7,
            top_p=request.top_p,
            echo=False
        )
        
        generated_text = output["choices"][0]["text"].strip()
        generated_text = utils.filter_sensitive_output(generated_text)
        
        usage = output["usage"]
        latency_ms = (time.time() - start_time) * 1000
        
        logger.info(f"CHAT | {usage['completion_tokens']} toks | {latency_ms:.0f}ms")

        response = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "index": 0, 
                "message": {"role": "assistant", "content": generated_text}, 
                "finish_reason": "stop"
            }],
            "usage": usage
        }

        if request.stream:
            def stream_generator():
                chunk = {
                    "id": response["id"], 
                    "object": "chat.completion.chunk", 
                    "created": response["created"], 
                    "model": request.model, 
                    "choices": [{
                        "index": 0, 
                        "delta": {"content": generated_text}, 
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                
                chunk["choices"][0] = {"index": 0, "delta": {}, "finish_reason": "stop"}
                yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(stream_generator(), media_type="text/event-stream")
            
        return response

    except Exception as e:
        logger.error(f"CHAT ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("server_gguf:app", host=host, port=port, reload=True)
