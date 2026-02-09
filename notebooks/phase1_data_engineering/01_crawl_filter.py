import os
import argparse
from datasets import load_dataset
from pathlib import Path
from tqdm import tqdm
import logging
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024
MIN_LINE_COUNT = 5
ALLOWED_EXTENSIONS = {'.py', '.java', '.cpp', '.h', '.cc', '.cxx', '.hpp'}
EXCLUDED_DIRS = {'node_modules', 'venv', '__pycache__', 'target', 'dist', 'build', 'bin', 'obj', 'test', 'tests', 'vendor'}
BATCH_SIZE = 500
# OPTIMIZATION: Increased max workers to utilize more I/O bandwidth
MAX_WORKERS = min(os.cpu_count() * 4, 32) if os.cpu_count() else 8

DATASET_NAME = "bigcode/the-stack"
LANG_MAP = {
    'Python': 'data/python',
    'Java': 'data/java',
    'C++': 'data/c++'
}

DEFAULT_TARGETS = {
    'Python': 100000,
    'Java': 100000,
    'C++': 100000
}


def is_valid_file(content, filename):
    # LOGGING: Input - processing file validation
    # logger.debug(f"[is_valid_file] Input: {filename}, Size: {len(content)} bytes")
    
    if not content or not filename:
        logger.debug(f"[is_valid_file] Skipping: Empty content or filename")
        return False
    
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.debug(f"[is_valid_file] Skipping: Invalid extension {ext} for {filename}")
        return False

    path_parts = filename.replace('\\', '/').split('/')
    if any(part in EXCLUDED_DIRS for part in path_parts):
        return False

    lines = content.count('\n') + 1
    if lines < MIN_LINE_COUNT:
        return False

    try:
        if len(content.encode('utf-8')) > MAX_FILE_SIZE_BYTES:
            return False
    except:
        return False

    # LOGGING: Output - valid file found
    # logger.debug(f"[is_valid_file] Output: VALID - {filename}")
    return True


def save_file_batch(batch_data, output_dir):
    # LOGGING: Input - batch to save
    logger.info(f"[save_file_batch] Input: Batch of {len(batch_data)} files to {output_dir}")
    
    saved_count = 0
    for content, filename, lang in batch_data:
        try:
            lang_dir = output_dir / lang
            lang_dir.mkdir(parents=True, exist_ok=True)
            
            safe_filename = filename.replace('\\', '/').lstrip('/')
            safe_filename = safe_filename.replace('/', '_')
            
            unique_name = f"{saved_count}_{safe_filename}"
            file_path = lang_dir / unique_name
            
            with open(file_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(content)
            saved_count += 1
        except Exception as e:
            logger.debug(f"Failed to save {filename}: {e}")
            
    # LOGGING: Output - save result
    logger.info(f"[save_file_batch] Output: Successfully saved {saved_count}/{len(batch_data)} files")
    return saved_count


def process_language(lang_name, data_dir, output_path, target_samples, hf_token, workers):
    logger.info(f"========== START process_language: {lang_name} ==========")
    logger.info(f"Input: data_dir={data_dir}, target={target_samples}, workers={workers}")
    
    max_retries = 10
    base_delay = 10
    
    for attempt in range(max_retries):
        try:
            ds = load_dataset(
                DATASET_NAME,
                data_dir=data_dir,
                split="train",
                streaming=True,
                token=hf_token
            )
            
            count = 0
            batch = []
            pbar = tqdm(total=target_samples, desc=f"Downloading {lang_name}", unit="files")
            
            ds_iter = iter(ds)
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = []
                
                while count < target_samples:
                    try:
                        sample = None
                        iter_retries = 10
                        
                        for i in range(iter_retries):
                            try:
                                sample = next(ds_iter)
                                break
                            except StopIteration:
                                break
                            except Exception as e:
                                if "429" in str(e) or "Too Many Requests" in str(e) or "ConnectionError" in str(e):
                                    wait_time = base_delay * (1.5 ** i) + random.uniform(1, 5)
                                    logger.warning(f"Rate limited. Waiting {wait_time:.2f}s... (Attempt {i+1}/{iter_retries})")
                                    time.sleep(wait_time)
                                else:
                                    logger.warning(f"Error fetching sample: {e}. Retrying...")
                                    time.sleep(1)
                        
                        if sample is None:
                            break
                        
                        content = sample.get('content', '')
                        filename = sample.get('max_stars_repo_path', sample.get('path', f'unknown_{count}.txt'))
                        
                        if is_valid_file(content, filename):
                            batch.append((content, filename, lang_name))
                            
                            if len(batch) >= BATCH_SIZE:
                                future = executor.submit(save_file_batch, batch.copy(), output_path)
                                futures.append(future)
                                batch.clear()
                                
                                for f in list(futures):
                                    if f.done():
                                        saved = f.result()
                                        count += saved
                                        pbar.update(saved)
                                        futures.remove(f)
                                
                    except StopIteration:
                        break
                    except Exception as e:
                        logger.debug(f"Error in processing loop: {e}")
                        continue
                
                if batch:
                    future = executor.submit(save_file_batch, batch.copy(), output_path)
                    futures.append(future)
                
                for future in as_completed(futures):
                    saved = future.result()
                    count += saved
                    pbar.update(saved)
            
            pbar.close()
            logger.info(f"========== END process_language: {lang_name} ==========")
            logger.info(f"Output: {count} files saved")
            return count

        except Exception as e:
            wait_time = base_delay * (2 ** attempt) + random.uniform(1, 5)
            logger.error(f"Error loading {lang_name}: {e}. Retrying in {wait_time:.2f}s... (Attempt {attempt+1}/{max_retries})")
            time.sleep(wait_time)
    
    logger.error(f"Max retries reached for {lang_name}. Skipping.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Crawl code data from The Stack dataset")
    parser.add_argument("--output_dir", type=str, default="raw_data", help="Output directory")
    parser.add_argument("--max_samples", type=int, default=None, help="Max samples per language (overrides individual settings)")
    parser.add_argument("--max_samples_python", type=int, default=DEFAULT_TARGETS['Python'], help="Max Python samples")
    parser.add_argument("--max_samples_java", type=int, default=DEFAULT_TARGETS['Java'], help="Max Java samples")
    parser.add_argument("--max_samples_cpp", type=int, default=DEFAULT_TARGETS['C++'], help="Max C++ samples")
    parser.add_argument("--hf_token", type=str, default=None, help="HuggingFace API Token")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help="Number of parallel workers")
    
    args = parser.parse_args()
    
    targets = {
        'Python': args.max_samples if args.max_samples else args.max_samples_python,
        'Java': args.max_samples if args.max_samples else args.max_samples_java,
        'C++': args.max_samples if args.max_samples else args.max_samples_cpp
    }
    
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    total_target = sum(targets.values())
    logger.info(f"Starting crawl from {DATASET_NAME}")
    logger.info(f"Target: {total_target} total samples ({targets})")
    logger.info(f"Workers: {args.workers}, Batch size: {BATCH_SIZE}")
    
    total_downloaded = 0
    
    for lang_name, data_dir in LANG_MAP.items():
        target = targets[lang_name]
        count = process_language(lang_name, data_dir, output_path, target, args.hf_token, args.workers)
        total_downloaded += count
    
    logger.info(f"Download completed. Total files: {total_downloaded}")


if __name__ == "__main__":
    main()
