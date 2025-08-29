# main.py (Phiên bản cuối cùng, xử lý Ctrl+C và file tạm)
import json
import os
from queue import Queue
from tqdm import tqdm
import sys
import time
import re

# Import các thành phần từ các module đã tạo
from config import CONFIG
from utils.logger import setup_logger
from utils.filter import should_translate
from translator.worker import TranslatorWorker

# --- CHỨC NĂNG 1: PHÂN LOẠI DỮ LIỆU ---
def classify_data():
    # ... (Hàm này giữ nguyên như cũ, không cần thay đổi)
    logger = setup_logger()
    logger.info("🚀 Bắt đầu GIAI ĐOẠN 1: PHÂN LOẠI DỮ LIỆU...")
    try:
        with open(CONFIG["input_file"], "r", encoding="utf-8") as f:
            original_data = json.load(f)
        logger.info(f"📖 Đã đọc {len(original_data)} mục từ '{CONFIG['input_file']}'.")
    except Exception as e:
        logger.error(f"❌ Không thể đọc file input '{CONFIG['input_file']}': {e}"); return
    safe_to_translate, needs_review, skipped_technical = [], [], []
    SAFE_THRESHOLD = CONFIG["classification_settings"]["safe_translation_threshold"]
    BASE_THRESHOLD = CONFIG["classification_settings"]["base_translation_threshold"]
    logger.info(f"⚙️  Áp dụng ngưỡng an toàn: {SAFE_THRESHOLD}, ngưỡng cơ bản: {BASE_THRESHOLD}")
    for i, item in enumerate(original_data):
        if 'index' not in item: item['index'] = i
    for item in tqdm(original_data, desc="Đang phân loại"):
        original_text = item.get("value", "")
        if should_translate(original_text, threshold=SAFE_THRESHOLD):
            safe_to_translate.append(item)
        elif should_translate(original_text, threshold=BASE_THRESHOLD):
            needs_review.append(item)
        else:
            skipped_technical.append(item)
    logger.info("📊 Phân loại hoàn tất!")
    logger.info(f"  - ✅ An toàn để dịch: {len(safe_to_translate)} mục")
    logger.info(f"  - ⚠️ Cần xem lại: {len(needs_review)} mục")
    logger.info(f"  - ❌ Bỏ qua (kỹ thuật): {len(skipped_technical)} mục")
    output_dir = "classified_output"
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "_1_safe_to_translate.json"), "w", encoding="utf-8") as f:
        json.dump(safe_to_translate, f, ensure_ascii=False, indent=2)
    with open(os.path.join(output_dir, "_2_needs_review.json"), "w", encoding="utf-8") as f:
        json.dump(needs_review, f, ensure_ascii=False, indent=2)
    with open(os.path.join(output_dir, "_3_skipped_technical.json"), "w", encoding="utf-8") as f:
        json.dump(skipped_technical, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 Đã lưu kết quả phân loại vào thư mục '{output_dir}'.")

# --- CHỨC NĂNG 2: DỊCH THUẬT ĐA LUỒNG (ĐÃ NÂNG CẤP) ---
def run_translation():
    logger = setup_logger()
    logger.info("🚀 Bắt đầu GIAI ĐOẠN 2: DỊCH THUẬT ĐA LUỒNG...")
    
    try:
        with open(CONFIG["input_file"], "r", encoding="utf-8") as f:
            data_to_translate = json.load(f)
        if not data_to_translate:
            logger.warning("⚠️ File input rỗng, không có gì để dịch."); return
        logger.info(f"📖 Đã đọc {len(data_to_translate)} mục từ '{CONFIG['input_file']}' để dịch.")
    except Exception as e:
        logger.error(f"❌ Lỗi đọc file input: {e}"); return

    glossary = {}
    try:
        with open(CONFIG["glossary_file"], "r", encoding="utf-8") as f:
            glossary = json.load(f)
    except FileNotFoundError: pass

    final_data = data_to_translate.copy()

    # [THÊM MỚI] Lọc lại danh sách để chỉ dịch các mục chưa có tiếng Việt
    logger.info("🔍 Lọc lần cuối: Chỉ dịch các mục có ít hơn 3 ký tự tiếng Việt...")
    vietnamese_pattern = re.compile(r"[\u00C0-\u1EF9]")
    
    items_to_batch = [
        item for item in data_to_translate
        if len(re.findall(vietnamese_pattern, str(item.get('value', '')))) < 2
    ]
    
    if not items_to_batch:
        logger.info("🎉 Không còn mục nào cần dịch. Mọi thứ đã hoàn tất!")
        # Vẫn lưu lại file output cuối cùng để hoàn tất quy trình
        with open(CONFIG["output_file"], "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Kết quả cuối cùng đã được lưu tại '{CONFIG['output_file']}'.")
        if os.path.exists(CONFIG["temp_file"]):
            os.remove(CONFIG["temp_file"])
        return

    logger.info(f"📊 Tìm thấy {len(items_to_batch)} mục cần dịch tiếp.")

    api_keys = [key for key in CONFIG["api_keys"] if "YOUR_" not in key]
    if not api_keys: logger.error("❌ API Keys không hợp lệ."); return
    
    work_queue = Queue()
    results_queue = Queue()
    
    batch_size = CONFIG.get('initial_batch_size', 50)
    batch_id_counter = 0

    for i in range(0, len(items_to_batch), batch_size):
        work_queue.put({'batch_id': batch_id_counter, 'data': items_to_batch[i:i+batch_size]})
        batch_id_counter += 1
        
    threads = []
    for i, key in enumerate(api_keys):
        # Đặt luồng là daemon, chúng sẽ tự động thoát khi chương trình chính kết thúc
        worker = TranslatorWorker(i + 1, key, work_queue, results_queue, glossary)
        worker.daemon = True 
        worker.start()
        threads.append(worker)

    index_to_position = {item['index']: pos for pos, item in enumerate(final_data)}
    
    # [NÂNG CẤP] Bọc vòng lặp chính trong try...except để xử lý Ctrl+C
    try:
        with tqdm(total=batch_id_counter, desc="Đang dịch", unit="batch") as pbar:
            completed_batches = 0
            while completed_batches < batch_id_counter:
                try:
                    result_batch = results_queue.get(timeout=1) # Giảm timeout để kiểm tra thường xuyên hơn
                    
                    # Cập nhật kết quả
                    for result_item in result_batch['results']:
                        original_index = result_item['index']
                        if original_index in index_to_position:
                            position = index_to_position[original_index]
                            final_data[position]['value'] = result_item['value']
                    
                    completed_batches += 1
                    pbar.update(1)

                    # [NÂNG CẤP] Lưu file tạm sau mỗi 5 batch
                    if completed_batches % 5 == 0:
                        with open(CONFIG["temp_file"], "w", encoding="utf-8") as f:
                            json.dump(final_data, f, ensure_ascii=False, indent=2)
                            logger.info(f"💾 Đã lưu tiến độ tạm thời vào '{CONFIG['temp_file']}'.")

                except Exception:
                    # Bỏ qua lỗi timeout của queue.get() để vòng lặp tiếp tục
                    # và kiểm tra xem có luồng nào còn sống không
                    if not any(t.is_alive() for t in threads):
                        logger.error("❌ Tất cả các luồng đã dừng đột ngột!")
                        break
                    continue
        
        # Nếu hoàn thành mà không bị ngắt
        logger.info("✅ Dịch thuật hoàn tất!")
        with open(CONFIG["output_file"], "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Kết quả cuối cùng đã được lưu tại '{CONFIG['output_file']}'.")
        
        # Xóa file tạm khi thành công
        if os.path.exists(CONFIG["temp_file"]):
            os.remove(CONFIG["temp_file"])
            logger.info(f"🧹 Đã xóa file tiến độ tạm '{CONFIG['temp_file']}'.")

    except KeyboardInterrupt:
        # Xử lý khi người dùng nhấn Ctrl+C
        logger.warning("\n🛑 Người dùng đã yêu cầu dừng chương trình.")
        logger.info(f"💾 Tiến độ đã được lưu trong file '{CONFIG['temp_file']}'. Chạy lại script để tiếp tục.")
        # Lưu lần cuối trước khi thoát
        with open(CONFIG["temp_file"], "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        sys.exit(0)


# --- ĐIỂM KHỞI CHẠY CHƯƠNG TRÌNH ---
if __name__ == "__main__":
    # --- CÔNG TẮC ĐIỀU KHIỂN ---
    
    # GIAI ĐOẠN 1: Chạy dòng này trước.
    # classify_data()
    
    # GIAI ĐOẠN 2: Sau đó, comment dòng trên và bỏ comment dòng dưới.
    run_translation()