# translator/worker.py
import threading
import time
import json
import re
import logging
from queue import Queue
from typing import Dict, List

import google.generativeai as genai

# Import các thành phần cần thiết từ các file khác
from config import CONFIG
from utils.filter import protect_placeholders, restore_placeholders

logger = logging.getLogger("TranslatorLogger")

class TranslatorWorker(threading.Thread):
    def __init__(self, thread_id: int, api_key: str, work_queue: Queue, results_queue: Queue, glossary: Dict[str, str]):
        super().__init__()
        self.thread_id = thread_id
        self.api_key = api_key
        self.work_queue = work_queue
        self.results_queue = results_queue
        self.glossary = glossary
        self.model = None
        self.last_request_time = 0
        self.rate_limit_seconds = 60.0 / CONFIG["requests_per_minute_per_key"]
        self.name = f"Worker-{self.thread_id}" # Đặt tên cho luồng để log dễ đọc hơn

    def _configure_model(self):
        """Cấu hình mô hình GenerativeAI cho luồng này."""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(CONFIG["model_name"])
            logger.info(f"Đã cấu hình model thành công với Key #{self.thread_id}.")
            return True
        except Exception as e:
            logger.error(f"LỖI NGHIÊM TRỌNG khi cấu hình Key #{self.thread_id}: {e}")
            return False


    def _build_prompt(self, batch_to_translate: List[Dict]) -> str:
        """
        NÂNG CẤP: Xây dựng prompt chuyên sâu, được tối ưu hóa cho game Quỷ Cốc Bát Hoang.
        """
        # input_block và glossary_str giữ nguyên cách tạo
        input_block = ",\n".join([
            f'{{"index": {item["index"]}, "value": {json.dumps(item["value"])}}}'
            for item in batch_to_translate
        ])
        glossary_str = "\n".join([f"- {en}: {vi}" for en, vi in self.glossary.items()]) or "Không có thuật ngữ nào được cung cấp."
    
        # --- ĐÂY LÀ PHẦN PROMPT MỚI, CHI TIẾT VÀ BÁ ĐẠO HƠN ---
        prompt = f"""
        Bạn là một Đại Lão Tu Tiên đã chơi Quỷ Cốc Bát Hoang hàng vạn giờ, am hiểu sâu sắc từng thuật ngữ, bối cảnh và văn phong của game. Vai trò của bạn là một API JSON, dịch các chuỗi text từ {CONFIG['source_language']} sang {CONFIG['target_language']} với sự chính xác và "cái hồn" của một người trong giới tu tiên.
    
        ---
        ## BỐI CẢNH GAME (BẮT BUỘC GHI NHỚ)
        - **Tên Game**: Quỷ Cốc Bát Hoang (Tale of Immortal).
        - **Thể loại**: Tu tiên, huyền huyễn, thế giới mở.
        - **Yếu tố chính**: Tu luyện cảnh giới, độ kiếp, linh căn, công pháp, tâm pháp, pháp bảo, đan dược, tông môn, đạo hữu, kỳ ngộ, thần thú, yêu thú...
    
        ---
        ## BẢNG THUẬT NGỮ (TUÂN THỦ TUYỆT ĐỐI)
        {glossary_str}
    
        ---
        ## QUY TẮC VĂN PHONG (QUAN TRỌNG)
        1.  **Sử dụng từ Hán Việt**: Ưu tiên các từ Hán Việt phù hợp với không khí tu tiên (ví dụ: "Linh Khí", "Công Pháp", "Đan Dược", "Tâm Ma", "Độ Kiếp").
        2.  **Xưng hô**: Dịch "You" một cách linh hoạt tùy ngữ cảnh: "Ngươi" (khi nói với đối thủ, người vai vế thấp hơn), "Ta" (khi nhân vật tự xưng), "Đạo hữu" (khi giao tiếp với người tu tiên khác), "Tại hạ", "Tiền bối", "Hậu bối"...
        3.  **Giọng văn**: Duy trì giọng văn trang trọng, cổ phong, mang hơi hướng truyện kiếm hiệp, tiên hiệp. TUYỆT ĐỐI không dùng từ ngữ hiện đại, "teen code" hay văn nói suồng sã.
    
        ---
        ## QUY TẮC KỸ THUẬT (SAI SÓT SẼ GÂY LỖI GAME)
        1.  **BẢO TOÀN PLACEHOLDER**: TUYỆT ĐỐI không dịch hay thay đổi các mã định danh như `__PROTECTED_0__`, `__PROTECTED_1__`. Giữ nguyên 100%.
        2.  **ĐỊNH DẠNG OUTPUT**: BẮT BUỘC chỉ trả về một JSON array hợp lệ. Mỗi object phải có dạng `{{"index": <số>, "translation": "<bản dịch>"}}`. Số lượng object phải là {len(batch_to_translate)}. Không thêm bất kỳ giải thích hay markdown nào khác.
        3.  **BẢO TOÀN KHOẢNG TRẮNG**: Giữ nguyên mọi khoảng trắng và ký tự xuống dòng (\\n) ở đầu và cuối chuỗi dịch. KHÔNG được tự động xóa chúng.
        4.  **BẢO TOÀN CÁC BIẾN, THẺ, ĐƯỜNG DẪN**: TUYỆT ĐỐI 100% KHÔNG DỊCH HAY SỬA CÁC TỪ CÓ DẤU HIỆU LÀ BIẾN, THẺ, ĐƯỜNG DẪN VÀ CÁC DẤU HIỆU LẠ KHÁC.
        ---
        ## VÍ DỤ MẪU (HỌC THEO)
        - **Ví dụ 1 (Đột phá cảnh giới):**
          INPUT: `{{ "index": 999, "text": "You have broken through to the Foundation Establishment Realm." }}`
          OUTPUT: `{{ "index": 999, "translation": "Ngươi đã đột phá đến cảnh giới Trúc Cơ." }}`
        - **Ví dụ 2 (Đối thoại):**
          INPUT: `{{ "index": 998, "text": "Fellow Daoist, this __PROTECTED_0__ is a rare treasure." }}`
          OUTPUT: `{{ "index": 998, "translation": "Đạo hữu, món __PROTECTED_0__ này quả là một kỳ trân dị bảo." }}`
        - **Ví dụ 3 (Mô tả vật phẩm):**
          INPUT: `{{ "index": 997, "text": "A pill that increases Qi absorption speed by __PROTECTED_0__%." }}`
          OUTPUT: `{{ "index": 997, "translation": "Một viên đan dược giúp tăng tốc độ hấp thu Linh Khí thêm __PROTECTED_0__%." }}`
    
        ---
        ## DỮ LIỆU CẦN DỊCH:
        [
        {input_block}
        ]
    
        ## JSON OUTPUT:
        """
        return prompt

    def _rate_limit(self):
        """Đảm bảo không vượt quá giới hạn request mỗi phút."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_seconds:
            wait_time = self.rate_limit_seconds - elapsed
            logger.info(f"Rate limiting. Chờ {wait_time:.2f} giây...")
            time.sleep(wait_time)
        self.last_request_time = time.time()

    def run(self):
        """Vòng lặp chính của worker."""
        if not self._configure_model():
            return

        while True:
            try:
                batch = self.work_queue.get()
                if batch is None:
                    logger.info("Nhận được tín hiệu dừng. Kết thúc.")
                    break

                logger.info(f"Đang xử lý batch #{batch['batch_id']} ({len(batch['data'])} mục).")
                self._rate_limit()

                translated_batch = None
                for attempt in range(CONFIG["max_api_retries"]):
                    try:
                        protected_data = []
                        for item in batch['data']:
                            original_value = item.get('value', '')
                            protected_text, replacements = protect_placeholders(original_value)
                            protected_data.append({"index": item['index'], "value": protected_text, "replacements": replacements})

                        prompt = self._build_prompt(protected_data)
                        response = self.model.generate_content(prompt)
                        raw_output = response.text.strip()
                        
                        json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)
                        if not json_match:
                            raise ValueError("Không tìm thấy JSON array trong response từ AI.")
                        
                        api_results = json.loads(json_match.group(0))

                        # 4. Kiểm tra số lượng mục trả về
                        if len(api_results) != len(protected_data):
                            raise ValueError(f"AI trả về sai số lượng! Gửi đi: {len(protected_data)}, Nhận về: {len(api_results)}")
                        
                        final_results = []
                        results_map = {res['index']: res['translation'] for res in api_results}
                        
                        for item in protected_data:
                            original_index = item['index']
                            translated_protected_text = results_map.get(original_index)
                            
                            if translated_protected_text:
                                restored_text = restore_placeholders(translated_protected_text, item['replacements'])
                                final_results.append({'index': original_index, 'value': restored_text})
                        
                        translated_batch = {'batch_id': batch['batch_id'], 'results': final_results}
                        break

                    except Exception as e:
                        logger.warning(f"Lỗi khi dịch batch #{batch['batch_id']} (lần {attempt + 1}): {e}")
                        if attempt < CONFIG["max_api_retries"] - 1:
                            time.sleep(CONFIG["api_retry_delay"])
                        else:
                            logger.error(f"BỎ QUA batch #{batch['batch_id']} sau {CONFIG['max_api_retries']} lần thử thất bại.")

                if translated_batch:
                    self.results_queue.put(translated_batch)
                
                self.work_queue.task_done()

            except Exception as e:
                logger.error(f"Lỗi không xác định trong vòng lặp chính: {e}")
                self.work_queue.task_done()