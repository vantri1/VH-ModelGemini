# utils/filter.py (Phiên bản cải thiện cho game data)
"""
Đây là module "bộ não" của hệ thống dịch thuật, chịu trách nhiệm phân tích,
làm sạch, và quyết định một chuỗi có nên được dịch hay không.

NÂNG CẤP ĐẶC BIỆT CHO GAME DATA:
- Bảo vệ tốt hơn các placeholder game như {0}, {name|B}, {variable}
- Đảm bảo khôi phục chính xác 100% khoảng trắng và format
- Xử lý các trường hợp đặc biệt của Unity game engine
"""

import re
import logging
from typing import Dict, Tuple
import itertools
import threading

logger = logging.getLogger("TranslatorLogger")

# --- BỘ ĐẾM TOÀN CỤC VÀ KHÓA AN TOÀN ---
placeholder_counter = itertools.count()
counter_lock = threading.Lock()

# --- ĐỊNH NGHĨA PATTERN DÙNG CHUNG ---
CJK_PATTERN = re.compile(
    "["
    "\u4e00-\u9fff"  # Ký tự CJK hợp nhất (chính)
    "\u3400-\u4dbf"  # Ký tự CJK hợp nhất - Mở rộng A
    "\u3040-\u309f"  # Hiragana (Nhật)
    "\u30a0-\u30ff"  # Katakana (Nhật)
    "\uff00-\uffef"  # Ký tự half-width và full-width
    "\uac00-\ud7af"  # Hangul (Hàn)
    "]"
)

# ==============================================================================
# ==== CÁC HÀM TIỆN ÍCH VÀ KIỂM TRA ĐƠN LẺ ====
# ==============================================================================

def contains_asian_characters(text: str) -> bool:
    """Kiểm tra xem chuỗi có chứa bất kỳ ký tự Trung, Hàn, Nhật nào không."""
    return bool(CJK_PATTERN.search(text))

def is_only_symbols_or_control(text: str) -> bool:
    """Kiểm tra xem chuỗi có TOÀN BỘ là ký tự không phải chữ cái hay không."""
    return not re.search(r'[a-zA-Z]', text)

def is_path_or_variable_style(text: str) -> bool:
    """Kiểm tra một chuỗi có phải là biến, hằng số, đường dẫn file hay không."""
    cleaned_text = text.strip()
    if not cleaned_text or ' ' in cleaned_text:
        return False

    # Quy tắc ưu tiên 1: Đường dẫn
    if '/' in cleaned_text or '\\' in cleaned_text:
        return True

    # Quy tắc ưu tiên 2: Phân tách bằng dấu chấm
    dot_separated_pattern = r'^[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)+$'
    if re.fullmatch(dot_separated_pattern, cleaned_text):
        return True

    # Quy tắc ưu tiên 3: Các quy ước đặt tên biến
    variable_patterns = [
        r'^[a-z]+[A-Z][a-zA-Z0-9]*$',   # camelCase
        r'^[A-Z][a-zA-Z0-9]+$',         # PascalCase
        r'^[a-z0-9]+(-[a-z0-9]+)+$',   # kebab-case
        r'^[a-z0-9_]+(?:_[a-z0-9]+)+$',# snake_case
        r'^[A-Z_]+[A-Z0-9_]*[A-Z_]+$'   # ALL_CAPS_SNAKE_CASE
    ]
    for pattern in variable_patterns:
        if re.fullmatch(pattern, cleaned_text):
            return True
            
    return False

def is_patch_note_or_version(text: str) -> bool:
    """Kiểm tra một chuỗi có phải là câu phiên bản không."""
    pattern = re.compile(r"(?i)^\[(?:[\d\.]+|Internal Test Version \d+)\s+Patch Notes\]$")
    return bool(pattern.fullmatch(text.strip()))

def is_code_like(text: str) -> bool:
    """Kiểm tra một chuỗi có chứa các dấu hiệu rõ ràng của một biểu thức code hay không."""
    code_patterns = [
        r'==|!=|<=|>=|&&|\|\|',  # Toán tử so sánh và logic
        r'\.\w+\(.*\)',          # Lời gọi hàm
    ]
    
    for pattern in code_patterns:
        if re.search(pattern, text):
            return True
            
    return False

# ==============================================================================
# ==== HỆ THỐNG BẢO VỆ PLACEHOLDER NÂNG CẤP CHO GAME ====
# ==============================================================================

def protect_placeholders(text: str) -> Tuple[str, Dict[str, str]]:
    """
    CRITICAL: Bảo vệ placeholder cho global-metadata.dat với độ chính xác tuyệt đối.
    
    MỌI SAI SÓT CÓ THỂ CRASH GAME!
    
    Thứ tự bảo vệ theo mức độ nguy hiểm:
    1. Unity string formatting: {0}, {1}, %s, %d
    2. Game logic variables: {name|B}, {variable|modifier}  
    3. C# code elements: namespaces, methods, properties
    4. Unity markup: <color>, <size>, <b>, <i>
    5. File paths và URLs
    6. Assembly references
    
    Args:
        text (str): Chuỗi từ global-metadata.dat

    Returns:
        tuple[str, Dict[str, str]]: Chuỗi bảo vệ và ánh xạ khôi phục
    """
    replacements: Dict[str, str] = {}
    
    def replacer(match: re.Match) -> str:
        with counter_lock:
            counter_val = next(placeholder_counter)
        
        placeholder = f"__PROTECTED_{counter_val}__"
        replacements[placeholder] = match.group(0)
        return placeholder

    # === LEVEL 1: UNITY ENGINE CRITICAL PATTERNS ===
    critical_unity_patterns = [
        # Unity string formatting - CỰC KỲ QUAN TRỌNG
        r'\{[\d]+\}',                           # {0}, {1}, {2}...
        r'\{[\d]+:[^}]+\}',                     # {0:F2}, {1:D3}
        
        # Unity/C# format specifiers  
        r'%[sdflbxXeEgGc%]',                    # %s, %d, %f, %l, %b, %x, %X, %e, %E, %g, %G, %c, %%
        
        # Game scripting variables
        r'\{[a-zA-Z_][a-zA-Z0-9_]*(?:\|[a-zA-Z_][a-zA-Z0-9_]*)*\}',  # {name|B}, {variable|modifier}
    ]
    
    # === LEVEL 2: C# CODE ELEMENTS ===
    csharp_patterns = [
        # Namespaces và assembly qualified names
        r'\b[A-Z][a-zA-Z0-9]*(?:\.[A-Z][a-zA-Z0-9]*)+\b',  # System.Collections.Generic
        
        # Method calls với parameters
        r'\b\w+\([^)]*\)',                     # Method(), GetChild(0)
        
        # Properties và fields
        r'\b\w+\.\w+(?:\.\w+)*',               # transform.position.x
        
        # Generics
        r'<[A-Z][a-zA-Z0-9,\s]*>',            # <T>, <string, int>
    ]
    
    # === LEVEL 3: UNITY MARKUP ===
    unity_markup_patterns = [
        # Rich Text markup - PHẢI BẢO VỆ TOÀN BỘ
        r'<color=[^>]*>.*?</color>',            # <color=#FF0000>text</color>
        r'<size=[^>]*>.*?</size>',              # <size=14>text</size>
        r'<material=[^>]*>.*?</material>',      # <material=shader>text</material>
        r'<quad[^>]*>',                         # <quad material=1 size=20 x=0.1 y=0.1 width=0.5 height=0.5>
        r'<sprite[^>]*>',                       # <sprite name="icon" index=0>
        
        # Basic formatting
        r'</?(?:b|i|u|sub|sup|mark|s)>',       # <b>, </b>, <i>, </i>, etc.
        r'<(?:br|BR)\s*/?>', # <br>, <BR>, <br/>, <BR/>
        
        # Custom Unity tags
        r'<nobr>.*?</nobr>',                    # <nobr>no break</nobr>
        r'<indent=[^>]*>.*?</indent>',          # <indent=10%>text</indent>
        r'<line-height=[^>]*>.*?</line-height>', # <line-height=50%>text</line-height>
    ]
    
    # === LEVEL 4: FILE SYSTEM & NETWORK ===
    filesystem_patterns = [
        # File paths - Windows & Unix
        r'[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*',  # C:\Path\File.ext
        r'/(?:[^/\s]+/)*[^/\s]*',               # /path/to/file
        
        # URLs
        r'https?://[^\s/$.?#].[^\s]*',          # http://example.com
        r'ftp://[^\s/$.?#].[^\s]*',             # ftp://example.com
        
        # Unity asset paths
        r'Assets/[^\s]*',                       # Assets/Scripts/Player.cs
        r'Resources/[^\s]*',                    # Resources/Textures/icon.png
    ]
    
    # === LEVEL 5: PROGRAMMING CONSTRUCTS ===
    programming_patterns = [
        # Hex colors
        r'#[0-9A-Fa-f]{6,8}',                  # #FF0000, #FF0000FF
        
        # GUIDs
        r'\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}',
        
        # Version numbers
        r'\b\d+\.\d+(?:\.\d+)*(?:-[a-zA-Z0-9]+)*\b', # 1.0.0, 2.1.3-beta
        
        # Special variables
        r'&[^&\s]+&',                          # &variable&
        r'\$[a-zA-Z_][a-zA-Z0-9_]*',           # $variable
        r'@[a-zA-Z_][a-zA-Z0-9_]*',            # @parameter
    ]
    
    # === LEVEL 6: REMAINING TAGS ===
    remaining_patterns = [
        r'<[^>]+>',                            # Bất kỳ tag nào còn lại
    ]
    
    # ÁP DỤNG THEO THỨ TỰ ƯU TIÊN
    all_pattern_groups = [
        critical_unity_patterns,
        csharp_patterns, 
        unity_markup_patterns,
        filesystem_patterns,
        programming_patterns,
        remaining_patterns
    ]
    
    for pattern_group in all_pattern_groups:
        for pattern in pattern_group:
            text = re.sub(pattern, replacer, text, flags=re.DOTALL)

    return text, replacements

def restore_placeholders(text: str, replacements: Dict[str, str]) -> str:
    """
    NÂNG CẤP: Khôi phục placeholder với đảm bảo chính xác 100%.
    
    Args:
        text (str): Chuỗi đã dịch chứa các mã __PROTECTED_X__.
        replacements (Dict[str, str]): Dictionary ánh xạ từ mã về giá trị gốc.
    
    Returns:
        str: Chuỗi đã được khôi phục placeholder.
    """
    if not replacements:
        return text

    # Khôi phục theo thứ tự từ số lớn đến nhỏ để tránh xung đột
    # Ví dụ: __PROTECTED_10__ phải được thay trước __PROTECTED_1__
    sorted_keys = sorted(replacements.keys(), 
                        key=lambda x: int(re.search(r'(\d+)', x).group(1)), 
                        reverse=True)
    
    for placeholder in sorted_keys:
        original_value = replacements[placeholder]
        # Thay thế chính xác placeholder
        text = text.replace(placeholder, original_value)
    
    return text

# ==============================================================================
# ==== HỆ THỐNG CHẤM ĐIỂM THÔNG MINH ====
# ==============================================================================

def calculate_translation_score(text: str) -> int:
    """Phân tích một chuỗi và cho điểm dựa trên các đặc điểm của ngôn ngữ tự nhiên."""
    score = 0
    length = len(text)
    words = text.split()
    word_count = len(words)
    
    # Tín hiệu tiêu cực
    if length < 4: score -= 5
    if word_count <= 1 and length > 15: score -= 10
    if word_count <= 1: score -= 3
    alpha_chars = len(re.findall(r'[a-zA-Z]', text))
    if length > 0 and (alpha_chars / length) < 0.7: score -= 4
    if re.search(r'[_/\\]', text): score -= 5
    if word_count > 1 and re.search(r'\b[a-z]+[A-Z]', text): score -= 10
    if re.search(r'\b(null|void|int|string|bool|var|let|const|true|false)\b', text, re.IGNORECASE):
        score -= 3

    # Tín hiệu tích cực
    if word_count > 2: score += 5
    if text.endswith(('.', '?', '!', '...')): score += 5
    if text and text[0].isupper(): score += 2
    common_words = {'the', 'is', 'you', 'are', 'to', 'in', 'of', 'for', 'with', 'on', 'at', 'a'}
    if any(word.lower() in common_words for word in words): score += 5

    return score

# ==============================================================================
# ==== HÀM QUYẾT ĐỊNH TỔNG HỢP ====
# ==============================================================================

def should_translate(text: str, threshold: int = 0) -> bool:
    """
    Hàm tổng hợp cuối cùng để quyết định có dịch một chuỗi hay không.
    """
    # BƯỚC 0: KIỂM TRA ĐẦU VÀO CƠ BẢN
    if not text or not isinstance(text, str): return False
    text = text.strip()
    if not text: return False

    # BƯỚC 1: ÁP DỤNG CÁC QUY TẮC LOẠI BỎ CỨNG
    if is_patch_note_or_version(text): return False
    if is_code_like(text): return False
    if contains_asian_characters(text): return False
    if re.search(r"[\u00C0-\u1EF9]", text): return False # Đã là tiếng Việt
    if is_only_symbols_or_control(text): return False
    if is_path_or_variable_style(text): return False

    # BƯỚC 2: PHÂN TÍCH SÂU VỚI HỆ THỐNG CHẤM ĐIỂM
    protected_text, _ = protect_placeholders(text)
    meaningful_text = re.sub(r'__PROTECTED_\d+__', '', protected_text).strip()
    
    if len(meaningful_text) < 2:
        return False
        
    score = calculate_translation_score(meaningful_text)
    
    log_msg = f"Điểm: {score} | Ngưỡng: {threshold} | Chuỗi: '{meaningful_text[:50]}'"
    
    if score >= threshold:
        logger.debug(f"[✅ DỊCH] {log_msg}")
        return True
    else:
        logger.debug(f"[❌ BỎ QUA] {log_msg}")
        return False