import os
import argparse
import random
import json
from pathlib import Path
from tqdm import tqdm
import logging
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_CONTEXT_LINES = 64      
MAX_CHARS_PER_PART = 2048  

def get_limited_context(lines, is_prefix=True):

    if is_prefix:
        selected_lines = lines[-MAX_CONTEXT_LINES:]
    else:
        selected_lines = lines[:MAX_CONTEXT_LINES]
        
    content = "".join(selected_lines)
    
    if len(content) > MAX_CHARS_PER_PART:
        if is_prefix:
            content = content[-MAX_CHARS_PER_PART:] 
        else:
            content = content[:MAX_CHARS_PER_PART]
            
    return content

def create_fim_sample(content):
    lines = content.splitlines(keepends=True)
    if len(lines) < 3:
        return None
        
    n_lines = len(lines)
    
    is_inline_mode = random.random() < 0.7
    
    if is_inline_mode:
        candidate_lines = [(i, line) for i, line in enumerate(lines) if len(line.strip()) > 20]
        if not candidate_lines:
            is_inline_mode = False
        else:
            line_idx, line = random.choice(candidate_lines)
            
            line_no_newline = line.rstrip('\n\r')
            
            min_split = max(1, len(line_no_newline) // 4)
            max_split = max(min_split + 1, len(line_no_newline) - 5)
            
            if max_split <= min_split:
                is_inline_mode = False
            else:
                split_pos = random.randint(min_split, max_split)
                
                prefix_part = line_no_newline[:split_pos]
                middle_part = line_no_newline[split_pos:]
                
                prefix_lines = lines[:line_idx]
                suffix_lines = lines[line_idx + 1:]
                
                prefix_context = get_limited_context(prefix_lines, is_prefix=True)
                suffix_context = get_limited_context(suffix_lines, is_prefix=False)
                
                # Combine
                prefix = prefix_context + prefix_part
                middle = middle_part + "\n" # Stop at EOL
                suffix = suffix_context
                
                fim_string = f"<PRE> {prefix} <SUF> {suffix} <MID> {middle}"
                
                return {"text": fim_string, "metadata": {"type": "FIM_INLINE"}}
    
    if not is_inline_mode:
        start_idx = random.randint(0, max(0, n_lines - 4))
        block_size = random.randint(2, min(10, n_lines - start_idx))
        end_idx = start_idx + block_size
        
        prefix_lines = lines[:start_idx]
        middle_lines = lines[start_idx:end_idx]
        suffix_lines = lines[end_idx:]
        
        prefix = get_limited_context(prefix_lines, is_prefix=True)
        suffix = get_limited_context(suffix_lines, is_prefix=False)
        
        middle = "".join(middle_lines).rstrip('\n\r')
        middle_with_stop = middle + "<|im_end|>"
        
        fim_string = f"<PRE> {prefix} <SUF> {suffix} <MID> {middle_with_stop}"
        
        return {"text": fim_string, "metadata": {"type": "FIM_BLOCK"}}

def process_file(file_path):
    try:
        # LOGGING: Input - file to FIM
        # logger.debug(f"[process_file] Input: FIM gen for {file_path}")
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if not content.strip():
            return None
            
        sample = create_fim_sample(content)
        
        if sample:
             # LOGGING: Output - created sample
             # logger.debug(f"[process_file] Output: Created FIM sample for {file_path} (Type: {sample['metadata']['type']})")
             pass
             
        return sample
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate FIM Dataset (Optimized for Latency)")
    parser.add_argument("--input_dir", type=str, default="transformed_data", help="Directory containing transformed files")
    parser.add_argument("--output_file", type=str, default="fim_dataset.jsonl", help="Output JSONL file")
    parser.add_argument("--workers", type=int, default=None, help="Number of parallel workers")
    
    args = parser.parse_args()
    
    workers = args.workers or cpu_count()
    input_path = Path(args.input_dir)
    
    if not input_path.exists():
        logger.error(f"Input directory {input_path} does not exist.")
        return

    files = list(input_path.rglob('*'))
    files = [f for f in files if f.is_file()]
    
    logger.info(f"Found {len(files)} files to process.")
    logger.info(f"Using {workers} parallel workers.")
    logger.info(f"Context Limits: {MAX_CONTEXT_LINES} lines / {MAX_CHARS_PER_PART} chars per side.")
    
    count = 0
    # OPTIMIZATION: Chunksize calculation
    chunk_size = max(1, len(files) // (workers * 4))
    logger.info(f"Using chunksize: {chunk_size}")

    with open(args.output_file, 'w', encoding='utf-8') as outfile:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # OPTIMIZATION: Added chunksize argument
            for sample in tqdm(executor.map(process_file, files, chunksize=chunk_size), total=len(files)):
                if sample:
                    json.dump(sample, outfile, ensure_ascii=False)
                    outfile.write('\n')
                    count += 1
                
    logger.info(f"FIM Generation completed. Generated {count} samples.")

if __name__ == "__main__":
    main()
