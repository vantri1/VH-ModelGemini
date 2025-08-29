# utils/filter.py
"""
Đây là module "bộ não" của hệ thống dịch thuật, chịu trách nhiệm phân tích,
làm sạch, và quyết định một chuỗi có nên được dịch hay không.

Quy trình hoạt động của hàm chính `should_translate`:
1.  Áp dụng các quy tắc loại bỏ nhanh và cứng (ví dụ: chuỗi chứa ký tự Châu Á,
    chuỗi đã là tiếng Việt, chuỗi chỉ có ký tự đặc biệt, chuỗi là biến/đường dẫn).
2.  Nếu chuỗi vượt qua các quy tắc trên, nó sẽ được đưa vào hệ thống chấm điểm
    để phân tích sâu hơn về mặt ngữ nghĩa và cấu trúc.
3.  Hệ thống chấm điểm sẽ trả về một quyết định cuối cùng dựa trên một ngưỡng điểm,
    giúp xử lý các trường hợp nhập nhằng một cách thông minh.
"""

import re
import logging
from typing import Dict, Tuple
import itertools
import threading

# Lấy logger đã được cấu hình ở file main để ghi lại các quyết định của bộ lọc.
logger = logging.getLogger("TranslatorLogger")

# --- BỘ ĐẾM TOÀN CỤC VÀ KHÓA AN TOÀN ---
# Tạo một bộ đếm duy nhất bắt đầu từ 0, dùng cho toàn bộ chương trình
placeholder_counter = itertools.count()
# Tạo một khóa để đảm bảo tại một thời điểm chỉ có một luồng được lấy số tiếp theo
counter_lock = threading.Lock()

# --- ĐỊNH NGHĨA PATTERN DÙNG CHUNG ---
# Định nghĩa pattern một lần để tái sử dụng, tăng hiệu quả và dễ quản lý.
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
# ==== CÁC HÀM TIỆN ÍCH VÀ KIỂM TRA ĐƠN LẺ (HELPER & CHECKER FUNCTIONS) ====
# ==============================================================================

def contains_asian_characters(text: str) -> bool:
    """
    Kiểm tra xem chuỗi có chứa bất kỳ ký tự Trung, Hàn, Nhật nào không.

    Args:
        text (str): Chuỗi cần kiểm tra.

    Returns:
        bool: True nếu chuỗi chứa ký tự Châu Á, ngược lại là False.
    """
    return bool(CJK_PATTERN.search(text))


def is_only_symbols_or_control(text: str) -> bool:
    """
    Kiểm tra xem chuỗi có TOÀN BỘ là ký tự không phải chữ cái hay không
    (bao gồm ký tự đặc biệt, số, khoảng trắng, ký tự điều khiển như NULL).

    Args:
        text (str): Chuỗi cần kiểm tra.

    Returns:
        bool: True nếu chuỗi không chứa bất kỳ chữ cái (a-z, A-Z) nào.
    """
    return not re.search(r'[a-zA-Z]', text)


def is_path_or_variable_style(text: str) -> bool:
    """
    Kiểm tra một chuỗi có phải là biến, hằng số, đường dẫn file,
    hay một chuỗi kỹ thuật khác không, với luồng logic được tối ưu hóa.
    """
    # Bước 1: Chuẩn hóa đầu vào
    cleaned_text = text.strip()
    if not cleaned_text:
        return False

    # Bước 2: Quy tắc cơ bản - Loại bỏ tất cả các cụm từ có nhiều hơn một "từ"
    # Nếu chuỗi có khoảng trắng ở giữa, nó chắc chắn không phải là một định danh kỹ thuật đơn lẻ.
    if ' ' in cleaned_text:
        return False

    # TỪ BƯỚC NÀY TRỞ ĐI, CHÚNG TA BIẾT CHẮC CHẮN `cleaned_text` LÀ MỘT "TỪ" DUY NHẤT

    # Bước 3: Kiểm tra các mẫu kỹ thuật trên "từ" đơn lẻ đó
    
    # Quy tắc ưu tiên 1: Nếu chứa ký tự đường dẫn, nó là đường dẫn.
    if '/' in cleaned_text or '\\' in cleaned_text:
        return True

    # Quy tắc ưu tiên 2: Nếu được phân tách bằng dấu chấm.
    dot_separated_pattern = r'^[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)+$'
    if re.fullmatch(dot_separated_pattern, cleaned_text):
        return True

    # Quy tắc ưu tiên 3: Kiểm tra các quy ước đặt tên biến phổ biến.
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
            
    # Nếu không khớp với bất kỳ mẫu nào ở trên, nó không phải là chuỗi kỹ thuật.
    return False

def is_patch_note_or_version(text: str) -> bool:
    """
    Kiểm tra một chuỗi có phải là câu phiên bản không
    """
    pattern = re.compile(r"(?i)^\[(?:[\d\.]+|Internal Test Version \d+)\s+Patch Notes\]$")
    return bool(pattern.fullmatch(text.strip()))


def is_code_like(text: str) -> bool:
    """
    Kiểm tra một chuỗi có chứa các dấu hiệu rõ ràng của một biểu thức code hay không.
    """
    # Các dấu hiệu mạnh của code: toán tử so sánh, lời gọi hàm phổ biến, keyword...
    code_patterns = [
        r'==|!=|<=|>=|&&|\|\|',  # Toán tử so sánh và logic
        r'\.\w+\(.*\)',          # Lời gọi hàm, ví dụ: .GetChild(i)
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
    NÂNG CẤP ĐẶC BIỆT: Bảo vệ placeholder cho game data với độ chính xác cao.
    
    Thứ tự ưu tiên bảo vệ:
    1. Game placeholders: {0}, {1}, {name|B}, {variable|modifier}
    2. Unity format strings: %s, %d, %f
    3. HTML/XML tags
    4. URLs
    5. Technical variables
    
    Args:
        text (str): Chuỗi đầu vào có thể chứa placeholder.

    Returns:
        tuple[str, Dict[str, str]]: Chuỗi đã được bảo vệ và dictionary ánh xạ.
    """
    replacements: Dict[str, str] = {}
    
    def replacer(match: re.Match) -> str:
        with counter_lock:
            counter_val = next(placeholder_counter)
        
        placeholder = f"__PROTECTED_{counter_val}__"
        replacements[placeholder] = match.group(0)
        return placeholder

    # GAME PLACEHOLDERS - Ưu tiên cao nhất
    game_patterns = [
        # Unity/Game engine format strings với số
        r'\{[\d]+\}',                           # {0}, {1}, {2}...
        
        # Game variables với modifiers
        r'\{[a-zA-Z_][a-zA-Z0-9_]*(?:\|[a-zA-Z_][a-zA-Z0-9_]*)*\}',  # {name|B}, {variable|modifier}
        
        # Unity percent format strings
        r'%[sdflb%]',                           # %s, %d, %f, %l, %b, %%
        
        # Color codes và special formatting
        r'<color=[^>]*>.*?</color>',            # <color=#FF0000>text</color>
        r'<size=[^>]*>.*?</size>',              # <size=14>text</size>
        r'<b>.*?</b>',                          # <b>bold</b>
        r'<i>.*?</i>',                          # <i>italic</i>
    ]
    
    # Áp dụng game patterns trước
    for pattern in game_patterns:
        text = re.sub(pattern, replacer, text, flags=re.DOTALL)
    
    # CÁC PATTERN KHÁC - Ưu tiên thấp hơn
    other_patterns = [
        r'<[^>]+>',                            # HTML/XML tags còn lại
        r'https?://[^\s/$.?#].[^\s]*',         # URLs  
        r'&[^&\s]+&',                          # &variable&
        r'\b#\w+\b',                           # #variable
        r'\b_\w+',                             # _variable
        r'\w+\.\w+',                           # object.property
    ]
    
    # Áp dụng các pattern khác
    for pattern in other_patterns:
        text = re.sub(pattern, replacer, text)

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
# ==== HỆ THỐNG CHẤM ĐIỂM THÔNG MINH (INTELLIGENT SCORING SYSTEM) ====
# ==============================================================================

def calculate_translation_score(text: str) -> int:
    """
    Phân tích một chuỗi và cho điểm dựa trên các đặc điểm của ngôn ngữ tự nhiên.
    Điểm càng cao, khả năng chuỗi đó là một câu văn cần dịch càng lớn.

    Args:
        text (str): Chuỗi cần được chấm điểm.

    Returns:
        int: Tổng điểm của chuỗi.
    """
    score = 0
    length = len(text)
    words = text.split()
    word_count = len(words)
    
    # --- Tín hiệu tiêu cực (trừ điểm cho các đặc điểm của chuỗi kỹ thuật) ---
    if length < 4: score -= 5 # Nếu một chuỗi có độ dài dưới 4 ký tự, hãy trừ 5 điểm khỏi "điểm dịch thuật" của nó.
    if word_count <= 1 and length > 15: score -= 10 # Từ đơn nhưng quá dài -> khả năng là mã
    if word_count <= 1: score -= 3  # Chuỗi chỉ chứa một từ duy nhất (hoặc không có từ nào)
    alpha_chars = len(re.findall(r'[a-zA-Z]', text))
    if length > 0 and (alpha_chars / length) < 0.7: score -= 4 # Tỷ lệ chữ cái thấp
    if re.search(r'[_/\\]', text): score -= 5 # Chứa ký tự lập trình
    if word_count > 1 and re.search(r'\b[a-z]+[A-Z]', text): score -= 10 # Chứa camelCase
    if re.search(r'\b(null|void|int|string|bool|var|let|const|true|false)\b', text, re.IGNORECASE):
        score -= 3

    # --- Tín hiệu tích cực (cộng điểm cho các đặc điểm của câu văn) ---
    if word_count > 2: score += 5 # Có nhiều từ
    if text.endswith(('.', '?', '!', '...')): score += 5 # Kết thúc bằng dấu câu
    if text and text[0].isupper(): score += 2 # Bắt đầu bằng chữ hoa
    common_words = {'the', 'is', 'you', 'are', 'to', 'in', 'of', 'for', 'with', 'on', 'at', 'a'}
    if any(word.lower() in common_words for word in words): score += 5 # Chứa từ tiếng Anh phổ thông

    return score


# ==============================================================================
# ==== HÀM QUYẾT ĐỊNH TỔNG HỢP (THE MASTER DECISION FUNCTION) ====
# ==============================================================================

def should_translate(text: str, threshold: int = 0) -> bool:
    """
    Hàm tổng hợp cuối cùng, kết hợp tất cả các bước một cách logic để đưa ra
    quyết định cuối cùng là CÓ hoặc KHÔNG dịch một chuỗi.

    Args:
        text (str): Chuỗi đầu vào cần quyết định.
        threshold (int): Ngưỡng điểm mà chuỗi cần vượt qua để được dịch.

    Returns:
        bool: True nếu chuỗi nên được dịch, ngược lại là False.
    """
    # BƯỚC 0: KIỂM TRA ĐẦU VÀO CƠ BẢN
    if not text or not isinstance(text, str): return False
    text = text.strip()
    if not text: return False

    # BƯỚC 1: ÁP DỤNG CÁC QUY TẮC LOẠI BỎ CỨNG (STRICT REJECTION RULES)
    # Đây là các quy tắc "một đi không trở lại", nếu vi phạm sẽ bị loại ngay.
    if is_patch_note_or_version(text): return False
    if is_code_like(text): return False
    if contains_asian_characters(text): return False
    if re.search(r"[\u00C0-\u1EF9]", text): return False # Đã là tiếng Việt
    if is_only_symbols_or_control(text): return False
    if is_path_or_variable_style(text): return False

    # BƯỚC 2: PHÂN TÍCH SÂU VỚI HỆ THỐNG CHẤM ĐIỂM
    # Chỉ những chuỗi vượt qua vòng 1 mới được vào vòng này.
    
    # Tách các placeholder ra khỏi nội dung có ý nghĩa.
    protected_text, _ = protect_placeholders(text)
    meaningful_text = re.sub(r'__PROTECTED_\d+__', '', protected_text).strip()
    
    # Nếu sau khi bỏ placeholder mà không còn nội dung thì cũng loại bỏ.
    if len(meaningful_text) < 2:
        return False
        
    # Tính điểm cho phần nội dung có ý nghĩa.
    score = calculate_translation_score(meaningful_text)
    
    # Ghi log để theo dõi quyết định của bộ lọc.
    log_msg = f"Điểm: {score} | Ngưỡng: {threshold} | Chuỗi: '{meaningful_text[:50]}'"
    
    # So sánh điểm với ngưỡng để đưa ra quyết định cuối cùng.
    if score >= threshold:
        logger.debug(f"[✅ DỊCH] {log_msg}")
        return True
    else:
        logger.debug(f"[❌ BỎ QUA] {log_msg}")
        return False