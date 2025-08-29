# 🚀 Tool Dịch Thuật Game Đa Luồng Sử Dụng API Google Gemini

Công cụ này được thiết kế để tự động hóa quá trình dịch thuật các file text (JSON) của game, đặc biệt là các file dữ liệu lớn và phức tạp. Nó được xây dựng với các tính năng an toàn để đảm bảo tính toàn vẹn của dữ liệu game, bảo vệ các biến và mã nguồn, đồng thời sử dụng AI để dịch văn bản một cách tự nhiên.

Hoạt động tốt với file String.json được tạo ra từ **global-metadata.dat** bằng công cụ **il2cpp-stringliteral-patcher-master**

## ✨ Các tính năng chính

* **Dịch thuật đa luồng**: Tận dụng nhiều API key của Google Gemini để tăng tốc độ dịch một cách đáng kể.
* **Bộ lọc thông minh**: Sử dụng hệ thống phân tích và chấm điểm để tự động phân biệt giữa văn bản cần dịch và các chuỗi kỹ thuật (tên biến, đường dẫn file, patch notes...).
* **Bảo vệ Placeholder tuyệt đối**: Tự động nhận diện và bảo vệ tất cả các loại biến (`{...}`, `<...>`, `&...`, `#...`) để đảm bảo chúng không bị dịch sai, tránh gây lỗi game.
* **Quy trình 3 giai đoạn an toàn**: Tách biệt việc **Phân loại**, **Dịch thuật** và **Gộp kết quả** để người dùng có thể kiểm soát hoàn toàn dữ liệu.
* **Hỗ trợ Bảng thuật ngữ (Glossary)**: Đảm bảo các thuật ngữ chuyên ngành của game được dịch một cách nhất quán.
* **Tự động gộp kết quả**: Cung cấp script để gộp file đã dịch và file chưa dịch lại với nhau, bảo toàn 100% thứ tự và số lượng mục gốc.

---
## 📁 Cấu trúc thư mục
Đảm bảo dự án của bạn có đầy đủ các file và thư mục như sau:
```bash
translator_project/
├── main.py                 # Script chính để chạy Phân loại và Dịch thuật
├── merge_files.py          # Script để gộp kết quả cuối cùng
├── config.py               # File cấu hình trung tâm
├── requirements.txt        # Danh sách các thư viện cần thiết
│
├── translator/
│   ├── init.py
│   └── worker.py           # Logic của từng luồng dịch
│
└── utils/
    ├── init.py
    ├── filter.py           # "Bộ não" của hệ thống lọc
    └── logger.py           # Cấu hình logger
```

*Lưu ý: Các file `__init__.py` là file trống, dùng để đánh dấu thư mục là một Python package.*

---
## ⚙️ Cài đặt

Thực hiện các bước sau trong cửa sổ dòng lệnh (Terminal, PowerShell, CMD).

1.  **Yêu cầu**: Đảm bảo bạn đã cài đặt **Python 3.8** trở lên.

2.  **Tải mã nguồn**: Tải hoặc sao chép tất cả các file trên vào thư mục dự án của bạn.

3.  **Di chuyển vào thư mục dự án**:
    ```bash
    cd path/to/translator_project
    ```

4.  **Tạo môi trường ảo** (khuyến khích):
    ```bash
    python -m venv venv
    ```

5.  **Kích hoạt môi trường ảo**:
    * Trên **Windows** (PowerShell, CMD):
        ```powershell
        .\venv\Scripts\activate
        ```
    * Trên **Windows** (Git Bash):
        ```bash
        source venv/Scripts/activate
        ```
    * Trên **macOS/Linux**:
        ```bash
        source venv/bin/activate
        ```
    *Sau khi kích hoạt, bạn sẽ thấy `(venv)` ở đầu dòng lệnh.*

6.  **Cài đặt các thư viện**:
    ```bash
    pip install -r requirements.txt
    ```
Cài đặt đã hoàn tất!

---
## 🚀 Hướng dẫn Sử dụng (Quy trình 3 Giai đoạn)

Đây là quy trình làm việc được đề xuất để đảm bảo an toàn và chất lượng cao nhất.

### Bước 0: Chuẩn bị Dữ liệu và Cấu hình

1.  **Chuẩn bị dữ liệu**:
    * Đặt file dữ liệu game cần dịch của bạn vào thư mục dự án và đảm bảo tên của nó khớp với `input_file` trong `config.py` (mặc định là `input.json`).
    * Tạo file `glossary.json` và thêm các thuật ngữ của game vào đó.
2.  **Cấu hình**: Mở file `config.py`:
    * **Quan trọng nhất**: Dán các **API Key** của bạn vào danh sách `api_keys`.
    * Kiểm tra lại các tên file (`input_file`, `output_file`...) xem đã đúng ý bạn chưa.

### Bước 1: Chạy Giai đoạn 1 - Phân loại dữ liệu

Mục đích của giai đoạn này là để bộ lọc thông minh đọc qua toàn bộ dữ liệu gốc và tách chúng ra thành các file nhỏ hơn.

1.  **Kiểm tra `main.py`**: Mở file `main.py` và đảm bảo "công tắc" ở cuối đang bật chế độ `classify_data`:
    ```python
    if __name__ == "__main__":
        # GIAI ĐOẠN 1: Chạy dòng này trước.
        classify_data()
        
        # GIAI ĐOẠN 2: ...
        # run_translation()
    ```
2.  **Chạy lệnh**:
    ```bash
    python main.py
    ```
3.  **Kết quả**: Một thư mục mới `classified_output` sẽ được tạo ra, chứa 3 file JSON.

### Bước 2: Chạy Giai đoạn 2 - Dịch thuật

Bây giờ chúng ta sẽ dịch file an toàn đã được lọc ra.

1.  **(Tùy chọn)** Mở file `classified_output/_2_needs_review.json`. Nếu có mục nào bạn muốn dịch, hãy copy chúng và dán vào file `classified_output/_1_safe_to_translate.json`.
2.  **Cập nhật `config.py`**: Mở `config.py` và sửa `input_file` để trỏ đến file an toàn:
    ```python
    "input_file": "classified_output/_1_safe_to_translate.json",
    ```
3.  **Đổi "công tắc" trong `main.py`**: Mở lại `main.py` và thay đổi phần cuối file:
    ```python
    if __name__ == "__main__":
        # GIAI ĐOẠN 1: Đã chạy xong.
        # classify_data()
        
        # GIAI ĐOẠN 2: Bắt đầu chạy dịch thuật.
        run_translation()
    ```
4.  **Chạy lệnh**:
    ```bash
    python main.py
    ```
5.  **Kết quả**: Quá trình dịch đa luồng sẽ bắt đầu. Sau khi hoàn tất, một file dịch (ví dụ: `output_translated.json`) sẽ được tạo ra.

### Bước 3: Chạy Giai đoạn 3 - Gộp kết quả

Đây là bước cuối cùng để tạo ra file game hoàn chỉnh.

1.  **Kiểm tra `merge_files.py`**: Mở file `merge_files.py` và chắc chắn rằng các tên file trong phần `CẤU HÌNH` là chính xác.
2.  **Chạy lệnh**:
    ```bash
    python merge_files.py
    ```
3.  **Kết quả cuối cùng**: Một file `FINAL_GAME_DATA.json` sẽ được tạo ra. File này có số lượng và thứ tự **giống hệt** file `input.json` gốc, với các phần đã được dịch được cập nhật. Đây là file bạn sẽ dùng cho các bước mod game tiếp theo.

---
### ## 💡 Tùy chỉnh Nâng cao

Bạn có thể tinh chỉnh độ nhạy của bộ lọc bằng cách thay đổi các giá trị trong `classification_settings` ở file `config.py`. Tăng `safe_translation_threshold` sẽ làm bộ lọc chặt chẽ hơn, giảm sẽ làm bộ lọc thoáng hơn.