# merge_files.py (Phiên bản đã sửa lỗi)
import json
import os
import logging

# --- CẤU HÌNH ---
# Điền đúng tên các file của bạn vào đây
ORIGINAL_FILE = "strings.json" # File gốc ban đầu
TRANSLATED_FILE = "output.json" # File chứa kết quả dịch từ Giai đoạn 2
FINAL_OUTPUT_FILE = "FINAL_GAME_DATA.json" # Tên file cuối cùng sau khi gộp

# Thiết lập logger đơn giản
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def merge_data():
    """
    Gộp dữ liệu đã dịch vào file gốc để tạo ra file cuối cùng,
    đảm bảo giữ nguyên thứ tự và số lượng.
    """
    logging.info("🚀 Bắt đầu GIAI ĐOẠN 3: Gộp dữ liệu...")

    # ======================================================================
    # ==== SỬA LỖI TẠI ĐÂY ====
    # ======================================================================
    # Bước 1: Đọc file gốc vào biến original_data để làm cơ sở so sánh
    try:
        with open(ORIGINAL_FILE, "r", encoding="utf-8") as f:
            original_data = json.load(f)
        
        # Tạo một bản sao để làm việc, đây sẽ là dữ liệu cuối cùng của chúng ta
        final_data = original_data.copy()
        logging.info(f"📖 Đã đọc {len(original_data)} mục từ file gốc '{ORIGINAL_FILE}'.")
    except FileNotFoundError:
        logging.error(f"❌ Lỗi: Không tìm thấy file gốc '{ORIGINAL_FILE}'. Vui lòng kiểm tra lại cấu hình.")
        return

    # Bước 2: Đọc file đã dịch
    try:
        with open(TRANSLATED_FILE, "r", encoding="utf-8") as f:
            translated_data = json.load(f)
        logging.info(f"📖 Đã đọc {len(translated_data)} mục đã được dịch từ '{TRANSLATED_FILE}'.")
    except FileNotFoundError:
        logging.error(f"❌ Lỗi: Không tìm thấy file đã dịch '{TRANSLATED_FILE}'. Bạn đã chạy Giai đoạn 2 chưa?")
        return

    # Bước 3: Tạo một "từ điển" từ dữ liệu đã dịch để tra cứu nhanh
    logging.info("⚙️  Tạo bản đồ tra cứu từ dữ liệu đã dịch...")
    translated_map = {item['index']: item['value'] for item in translated_data}

    # Bước 4: Cập nhật file gốc với các bản dịch
    update_count = 0
    index_to_position = {item['index']: pos for pos, item in enumerate(final_data)}

    logging.info("🔄 Bắt đầu cập nhật file gốc với các bản dịch...")
    for original_index, translated_value in translated_map.items():
        if original_index in index_to_position:
            position = index_to_position[original_index]
            final_data[position]['value'] = translated_value
            update_count += 1

    logging.info(f"✅ Đã cập nhật thành công {update_count} mục.")

    # Bước 5: Kiểm tra lại lần cuối (Bây giờ sẽ hoạt động)
    if len(final_data) != len(original_data):
        logging.error("❌ LỖI NGHIÊM TRỌNG: Số lượng mục trong file cuối cùng không khớp với file gốc!")
        return

    logging.info("🛡️  Kiểm tra tính toàn vẹn thành công. Số lượng mục khớp.")

    # Bước 6: Lưu file cuối cùng
    with open(FINAL_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    logging.info(f"🎉 Hoàn tất! File cuối cùng đã được lưu tại: '{FINAL_OUTPUT_FILE}'")
    logging.info("File này đã sẵn sàng để bạn chuyển đổi lại thành global-metadata.dat.")


if __name__ == "__main__":
    merge_data()