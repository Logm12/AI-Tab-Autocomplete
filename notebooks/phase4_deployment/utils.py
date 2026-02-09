import re
import difflib
from typing import List

def get_stop_tokens() -> List[str]:
    """Returns the standard stop tokens for the model."""
    return [
        "<|im_end|>", "<|im_start|>", 
        "<|fim_prefix|>", "<|fim_suffix|>", "<|fim_middle|>", 
        "<|endoftext|>"
    ]

STOP_SPECIAL = get_stop_tokens()

def detect_language(code: str) -> str:
    """
    Heuristically detects the programming language of a code snippet.
    """
    if not code:
        return "unknown"
        
    # Check only the last few lines for context
    lines = code.strip().split('\n')[-5:]
    text = '\n'.join(lines).lower()
    
    # Python indicators
    if 'def ' in text or 'import ' in text or 'from ' in text:
        if ':' in text or 'import ' in text:
            return "python"
            
    # C++ indicators
    if '#include' in text or 'std::' in text or 'cout' in text or 'using namespace' in text:
        return "cpp"
        
    # Java indicators
    if 'public class' in text or 'public static' in text or 'system.out' in text or '@override' in text:
        return "java"
    
    # JavaScript/TypeScript indicators
    if 'const ' in text or 'let ' in text or 'function ' in text or '=>' in text:
        return "javascript"
        
    return "unknown"

def get_stop_for_lang(lang: str, is_block: bool) -> List[str]:
    """
    Returns language-specific stop tokens to prevent runaway generation.
    """
    stops = STOP_SPECIAL.copy()
    
    if is_block:
        if lang == "python":
            stops.extend(["\n\n", "\ndef ", "\nclass ", "\n@"])
        elif lang == "cpp":
            stops.extend(["\n\n", "\nint ", "\nvoid ", "\nclass ", "};"])
        elif lang == "java":
            stops.extend(["\n\n", "\npublic ", "\nprivate ", "\nclass ", "};"])
        else:
            stops.extend(["\n\n", "\ndef ", "\nclass "])
    else:
        # Inline completion typically stops at the end of the line
        stops.extend(["\n", "\r"])
        if lang in ("cpp", "java", "javascript"):
             stops.extend([";", "{"])
             
    return stops

def filter_sensitive_output(text: str) -> str:
    """
    Filters out potential sensitive information using regex.
    """
    # Pattern for common secrets (simplified for performance)
    # Matches strings that look like API keys or passwords
    forbidden_pattern = re.compile(
        r"(sk-[a-zA-Z0-9]{20,}|password\s*[:=]|api[_-]?key|secret[_-]?key)", 
        re.IGNORECASE
    )
    
    if forbidden_pattern.search(text):
        return ""
    return text

class MetricsCalculator:
    """
    Utilities for calculating code completion metrics.
    """
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r'\S+', text)
    
    @staticmethod
    def edit_similarity(pred: str, expected: str) -> float:
        if not pred and not expected:
            return 1.0
        matcher = difflib.SequenceMatcher(None, pred, expected)
        return matcher.ratio()
    
    @staticmethod
    def exact_match(pred: str, expected: str) -> float:
        return 1.0 if pred.strip() == expected.strip() else 0.0
    
    @staticmethod
    def perfect_line(pred: str, expected: str) -> float:
        # Compare first lines only
        p_line = pred.strip().split('\n')[0] if pred else ""
        e_line = expected.strip().split('\n')[0] if expected else ""
        return 1.0 if p_line == e_line else 0.0
