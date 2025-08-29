# config.py

# ======================================================================================
# ==== CẤU HÌNH & HẰNG SỐ (CONFIGURATION & CONSTANTS) ====
# ======================================================================================
# Mọi tùy chỉnh đều nằm ở đây. Không cần sửa code ở các phần khác.
CONFIG = {
    # --- Cài đặt file ---
    "input_file": "string2.json",
    # "input_file": "classified_output/_1_safe_to_translate.json",
    # "input_file": "Strings.json",
    "output_file": "output.json",
    "temp_file": "temp_progress.json",
    "glossary_file": "glossary.json",

    # --- Cài đặt API ---
    # !!! THAY API KEY CỦA BẠN VÀO ĐÂY !!!
    "api_keys": [
        
        # Thêm bao nhiêu key tùy ý vào danh sách này
    ],
    "model_name": "gemini-2.5-flash",

    # --- Cài đặt dịch thuật ---
    # Thay đổi 'target_language' để dịch sang ngôn ngữ khác
    # Ví dụ: "Vietnamese", "English", "Japanese", "Korean"
    "target_language": "Vietnamese", 
    "source_language": "English",

    # --- Cài đặt xử lý Batch & Đa luồng ---
    "initial_batch_size": 50,         # Kích thước batch ban đầu
    "min_batch_size": 5,              # Kích thước batch tối thiểu khi có lỗi
    "max_batch_size": 200,            # Kích thước batch tối đa khi chạy ổn định
    "requests_per_minute_per_key": 10,# Giới hạn của Google API cho mỗi key
    
    # --- Cài đặt Retry & Timeout ---
    "max_api_retries": 3,             # Số lần thử lại tối đa cho một batch nếu gặp lỗi API
    "api_retry_delay": 5,             # Thời gian chờ (giây) giữa các lần thử lại

    # =========================================================================
    # ==== CÀI ĐẶT PHÂN LOẠI DỮ LIỆU ====
    # =========================================================================
    "classification_settings": {
        # Ngưỡng điểm để một chuỗi được coi là "An toàn để dịch".
        # - Tăng giá trị này (ví dụ: 10) để bộ lọc chặt chẽ hơn.
        # - Giảm giá trị này (ví dụ: 3) để bộ lọc "thoáng" hơn.
        "safe_translation_threshold": 5,

        # Ngưỡng điểm cơ bản để đưa vào diện "Cần xem lại".
        # Thường giữ giá trị này là 0.
        "base_translation_threshold": 0
    }
}