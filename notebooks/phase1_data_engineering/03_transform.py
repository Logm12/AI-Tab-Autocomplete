import os
import re
import argparse
import random
import tokenize
import io
from pathlib import Path
from tqdm import tqdm
import logging
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CodeTransformer:
    def __init__(self, import_dropout_rate=0.3):
        self.import_dropout_rate = import_dropout_rate

    def remove_comments_python(self, source):
        """
        Remove comments from Python code using tokenize.
        """
        try:
            io_obj = io.StringIO(source)
            out_tokens = []
            for tok in tokenize.generate_tokens(io_obj.readline):
                if tok.type == tokenize.COMMENT:
                    continue
                out_tokens.append(tok)
            return tokenize.untokenize(out_tokens)
        except tokenize.TokenError:
            return source
        except Exception as e:
            return source

    def remove_comments_cpp_java(self, source):
        def replacer(match):
            s = match.group(0)
            if s.startswith('/'):
                return " "
            else:
                return s

        pattern = re.compile(
            r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
            re.DOTALL | re.MULTILINE
        )
        return re.sub(pattern, replacer, source)

    def import_dropout(self, source, lang):
        lines = source.splitlines()
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            is_import = False
            
            if lang == 'Python':
                if stripped.startswith('import ') or stripped.startswith('from '):
                    is_import = True
            elif lang == 'Java':
                if stripped.startswith('import '):
                    is_import = True
            elif lang in ['C++', 'C']:
                if stripped.startswith('#include'):
                    is_import = True
            
            if is_import:
                if random.random() > self.import_dropout_rate:
                    new_lines.append(line)
            else:
                new_lines.append(line)
                
        return "\n".join(new_lines)

    def transform(self, content, filename):
        ext = Path(filename).suffix
        lang = 'Unknown'
        
        if ext == '.py':
            lang = 'Python'
            content = self.remove_comments_python(content)
        elif ext in ['.java', '.cpp', '.h', '.cc', '.cxx', '.hpp']:
            lang = 'Java' if ext == '.java' else 'C++'
            content = self.remove_comments_cpp_java(content)
            
        if lang in ['Python', 'Java', 'C++']:
            content = self.import_dropout(content, lang)
            
        return content

def process_file(args_tuple):
    input_path, output_path, dropout_rate = args_tuple
    try:
        # LOGGING: Input - file to transform
        # logger.debug(f"[process_file] Input: Transforming {input_path}")
        
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        transformer = CodeTransformer(import_dropout_rate=dropout_rate)
        transformed_content = transformer.transform(content, input_path.name)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(transformed_content)
        
        # LOGGING: Output - transformed file
        # logger.debug(f"[process_file] Output: Transformed {input_path} -> {output_path} (Size: {len(transformed_content)})")
        return True
    except Exception as e:
        logger.error(f"Error processing {input_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Transform code: Remove comments and Import Dropout (Optimized)")
    parser.add_argument("--input_dir", type=str, default="scrubbed_data", help="Directory containing scrubbed files")
    parser.add_argument("--output_dir", type=str, default="transformed_data", help="Directory to save transformed files")
    parser.add_argument("--dropout_rate", type=float, default=0.3, help="Rate of import dropout (0.0 to 1.0)")
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
        file_pairs.append((file_path, dest_path, args.dropout_rate))
    
    # Process in parallel
    count = 0
    # OPTIMIZATION: Chunksize calculation
    chunk_size = max(1, len(file_pairs) // (workers * 4))
    logger.info(f"Using chunksize: {chunk_size}")

    with ProcessPoolExecutor(max_workers=workers) as executor:
        # OPTIMIZATION: Added chunksize argument
        results = list(tqdm(executor.map(process_file, file_pairs, chunksize=chunk_size), total=len(file_pairs)))
        count = sum(results)
            
    logger.info(f"Transformation completed. Processed {count} files.")

if __name__ == "__main__":
    main()
