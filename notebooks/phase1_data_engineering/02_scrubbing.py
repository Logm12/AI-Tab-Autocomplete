import os
import re
import argparse
from pathlib import Path
from tqdm import tqdm
import logging
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecretScrubber:
    def __init__(self):
        self.patterns = [
            # AWS Access Key ID
            (r'(?<![A-Z0-9])[A-Z0-9]{20}(?![A-Z0-9])', '<SECRET_TOKEN>'),
            # AWS Secret Access Key
            (r'(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])', '<SECRET_TOKEN>'),
            # Google API Key
            (r'AIza[0-9A-Za-z-_]{35}', '<SECRET_TOKEN>'),
            # Generic API Key assignments 
            (r'(?i)(api_key|apikey|secret_key|access_token)\s*=\s*["\']([a-zA-Z0-9_\-]{20,})["\']', r'\1 = "<SECRET_TOKEN>"'),
            # IPv4 Private Addresses (10.x.x.x, 172.16-31.x.x, 192.168.x.x)
            (r'(?<!\d)(10\.\d{1,3}\.\d{1,3}\.\d{1,3})(?!\d)', '<SECRET_TOKEN>'),
            (r'(?<!\d)(172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(?!\d)', '<SECRET_TOKEN>'),
            (r'(?<!\d)(192\.168\.\d{1,3}\.\d{1,3})(?!\d)', '<SECRET_TOKEN>'),
            # Password assignments 
            (r'(?i)(password|passwd|pwd)\s*=\s*["\']([^"\']{6,})["\']', r'\1 = "<SECRET_TOKEN>"'),
            # Connection strings (Postgres, MySQL, etc.)
            (r'postgres://[^:]+:[^@]+@', 'postgres://<USER>:<SECRET_TOKEN>@'),
            (r'mysql://[^:]+:[^@]+@', 'mysql://<USER>:<SECRET_TOKEN>@'),
        ]
        self.compiled_patterns = [(re.compile(p), r) for p, r in self.patterns]

    def scrub(self, content):
        scrubbed_content = content
        for pattern, replacement in self.compiled_patterns:
            scrubbed_content = pattern.sub(replacement, scrubbed_content)
        return scrubbed_content

def process_file(args_tuple):
    input_path, output_path = args_tuple
    try:
        # LOGGING: Input - file to scrub
        # logger.debug(f"[process_file] Input: Scrubbing {input_path}")
        
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        scrubber = SecretScrubber()
        scrubbed_content = scrubber.scrub(content)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(scrubbed_content)
            
        # LOGGING: Output - scrubbed file
        # logger.debug(f"[process_file] Output: Scrubbed {input_path} -> {output_path} (Size: {len(scrubbed_content)})")
        return True
    except Exception as e:
        logger.error(f"Error processing {input_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Scrub secrets from code files (Optimized)")
    parser.add_argument("--input_dir", type=str, default="raw_data", help="Directory containing raw code files")
    parser.add_argument("--output_dir", type=str, default="scrubbed_data", help="Directory to save scrubbed files")
    parser.add_argument("--workers", type=int, default=None, help="Number of parallel workers (default: CPU count)")
    
    args = parser.parse_args()
    
    workers = args.workers or cpu_count()
    
    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)
    
    if not input_path.exists():
        logger.error(f"Input directory {input_path} does not exist.")
        return

    files = list(input_path.rglob('*'))
    files = [f for f in files if f.is_file()]
    
    logger.info(f"Found {len(files)} files to process.")
    logger.info(f"Using {workers} parallel workers.")
    
    # Prepare file pairs
    file_pairs = []
    for file_path in files:
        rel_path = file_path.relative_to(input_path)
        dest_path = output_path / rel_path
        file_pairs.append((file_path, dest_path))
    
    # Process in parallel
    count = 0
    # OPTIMIZATION: Chunksize calculation
    chunk_size = max(1, len(file_pairs) // (workers * 4))
    logger.info(f"Using chunksize: {chunk_size}")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        # OPTIMIZATION: Added chunksize argument
        results = list(tqdm(executor.map(process_file, file_pairs, chunksize=chunk_size), total=len(file_pairs)))
        count = sum(results)
            
    logger.info(f"Scrubbing completed. Processed {count} files.")

if __name__ == "__main__":
    main()
