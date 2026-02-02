# OCR and Read Document - Python Backend

**Intelligent OCR & Document Processing Backend for Website Read PDF**

Backend service untuk memproses dokumen PDF menggunakan OCR (Optical Character Recognition), parsing otomatis, dan ekstraksi data terstruktur. Sistem ini menggunakan PaddleOCR untuk ekstraksi teks dan parser khusus untuk berbagai jenis dokumen.

---

## Frontend Repository

**Laravel Frontend**: [https://github.com/rahmatisma/Website-Read-PDF](https://github.com/rahmatisma/Website-Read-PDF)

Repository ini adalah backend yang harus dijalankan secara terpisah dari frontend Laravel.

---

## Tech Stack

### Core Technologies
- **Python**: 3.10.6
- **Flask**: 3.1.2 (Web framework)
- **PaddleOCR**: 2.7.0.3 (OCR engine)
- **PaddlePaddle**: 2.6.2 (Deep learning framework)
- **PyMuPDF**: 1.20.2 (PDF processing)

### Image Processing
- **OpenCV**: 4.6.0.66 (Computer vision)
- **Pillow**: 12.1.0 (Image manipulation)
- **scikit-image**: 0.25.2 (Image processing algorithms)
- **imgaug**: 0.4.0 (Image augmentation)

### Data Processing
- **NumPy**: 1.26.4
- **Pandas**: 2.3.3
- **scikit-learn**: 1.7.2
- **SciPy**: 1.15.3

### Document Processing
- **python-docx**: 1.2.0 (Word documents)
- **openpyxl**: 3.1.5 (Excel files)
- **pdf2docx**: 0.5.8 (PDF to DOCX conversion)

### Utilities
- **requests**: 2.32.5 (HTTP client)
- **beautifulsoup4**: 4.14.3 (HTML parsing)
- **lxml**: 6.0.2 (XML processing)

---

## System Requirements

### Required Software

1. **Python** 3.10.6 (exact version recommended)
   - Download: https://www.python.org/downloads/release/python-3106/

2. **Git**

3. **Visual C++ Redistributable** (Windows only - untuk PaddlePaddle)
   - Download: https://aka.ms/vs/17/release/vc_redist.x64.exe

### Optional (Recommended)

- **CUDA Toolkit** (for GPU acceleration with PaddlePaddle)
  - Only if you have NVIDIA GPU
  - Download: https://developer.nvidia.com/cuda-downloads

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/rahmatisma/OCR-and-Read-document.git
cd OCR-and-Read-document
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Pastikan virtual environment aktif (akan ada `(venv)` di terminal).

### Step 3: Upgrade pip

```bash
python -m pip install --upgrade pip
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: Jika file `requirements.txt` belum ada, buat file tersebut dengan isi:

```txt
Flask==3.1.2
paddleocr==2.7.0.3
paddlepaddle==2.6.2
PyMuPDF==1.20.2
opencv-python==4.6.0.66
opencv-contrib-python==4.6.0.66
Pillow==12.1.0
numpy==1.26.4
pandas==2.3.3
scikit-learn==1.7.2
scikit-image==0.25.2
scipy==1.15.3
requests==2.32.5
python-docx==1.2.0
openpyxl==3.1.5
pdf2docx==0.5.8
beautifulsoup4==4.14.3
lxml==6.0.2
imgaug==0.4.0
matplotlib==3.10.8
```

### Step 5: Verify Installation

```bash
# Check Python version
python --version
# Should show: Python 3.10.6

# Check pip packages
pip list

# Check if PaddleOCR installed correctly
python -c "from paddleocr import PaddleOCR; print('PaddleOCR OK')"
```

### Step 6: Download PaddleOCR Models (First Run)

PaddleOCR akan otomatis download model saat pertama kali dijalankan. Ini akan memakan waktu beberapa menit tergantung koneksi internet.

Model yang akan didownload:
- Detection model (~3MB)
- Recognition model (~10MB)  
- Angle classification model (~1MB)

### Step 7: Test OCR

Buat file test sederhana:

```python
# test_ocr.py
from paddleocr import PaddleOCR

print("Initializing PaddleOCR...")
print("First run will download models (this may take a few minutes)...")

ocr = PaddleOCR(use_angle_cls=True, lang='en')
print("\nPaddleOCR initialized successfully!")
print("Models downloaded and loaded!")
print("System ready!")
```

Jalankan:
```bash
python test_ocr.py
```

**Note**: Pertama kali run akan download model files (~15MB total). Ini hanya sekali saja.

---

## Configuration

### Environment Variables (Optional)

Buat file `.env` jika diperlukan:

```env
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=True

# Server Configuration
HOST=0.0.0.0
PORT=5000

# OCR Configuration
OCR_LANGUAGE=en
USE_ANGLE_CLASSIFICATION=True
USE_GPU=False

# File Upload
MAX_CONTENT_LENGTH=100000000
UPLOAD_FOLDER=./input/pdf
OUTPUT_FOLDER=./output

# Logging
LOG_LEVEL=INFO
```

### PaddleOCR Configuration

Update konfigurasi OCR di `app.py` atau file konfigurasi sesuai kebutuhan:

```python
from paddleocr import PaddleOCR

# Konfigurasi PaddleOCR
ocr = PaddleOCR(
    use_angle_cls=True,      # Gunakan angle classification
    lang='en',               # Language (en, ch, etc)
    use_gpu=False,           # Set True jika ada GPU
    show_log=False,          # Hide verbose logs
    det_db_thresh=0.3,       # Detection threshold
    det_db_box_thresh=0.5,   # Box threshold
    rec_batch_num=6          # Batch size untuk recognition
)
```

### GPU Acceleration (Optional)

Jika punya NVIDIA GPU dan sudah install CUDA:

```python
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en',
    use_gpu=True,           # Enable GPU
    gpu_mem=500             # GPU memory (MB)
)
```

---

## Running the Application

### Development Mode

**Start Flask Server:**

```bash
# Activate virtual environment first
# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate

# Run Flask app
python app.py
```

Server akan berjalan di: `http://localhost:5000`

### Production Mode

Untuk production, gunakan WSGI server seperti **Gunicorn** (Linux/Mac) atau **Waitress** (Windows):

**Install Gunicorn (Linux/Mac):**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

**Install Waitress (Windows):**
```bash
pip install waitress
waitress-serve --listen=0.0.0.0:5000 app:app
```

---

## API Endpoints

### 1. Process PDF

Process PDF document dengan OCR dan parsing otomatis.

**Endpoint:** `POST /process-pdf`

**Form Data:**
- `file`: PDF file (required)
- `laravel_storage_path`: Path ke Laravel storage (optional)

**Example Request:**
```bash
curl -X POST http://localhost:5000/process-pdf \
  -F "file=@document.pdf" \
  -F "laravel_storage_path=/path/to/laravel/storage/app/public"
```

**Example Response:**
```json
{
  "message": "processed ok",
  "filename": "uuid.json",
  "data": {
    "dokumentasi": [
      {
        "jenis": "Foto Lokasi",
        "patch_foto": "output/extracted/spk/survey/survey_20260202_101530/images/foto_1.jpg"
      }
    ],
    "parsed": {
      "document_type": "spk_survey",
      "data": {
        "header": {...},
        "informasi_umum": {...}
      }
    }
  }
}
```

### 2. Validate First Page

Quick validation untuk mendeteksi jenis dokumen dari halaman pertama.

**Endpoint:** `POST /validate-first-page`

**Form Data:**
- `file`: PDF file (required)
- `expected_category`: 'spk', 'checklist', atau 'pmpop' (optional)

**Example Request:**
```bash
curl -X POST http://localhost:5000/validate-first-page \
  -F "file=@document.pdf" \
  -F "expected_category=spk"
```

**Example Response:**
```json
{
  "success": true,
  "document_type": "spk_survey",
  "confidence": "high",
  "message": "Dokumen terdeteksi sebagai SPK Survey",
  "is_valid_for_category": true
}
```

### 3. Health Check

Check status server dan dependencies.

**Endpoint:** `GET /health`

**Example Response:**
```json
{
  "status": "online",
  "python_version": "3.10.6",
  "flask_version": "3.1.2",
  "paddleocr_available": true,
  "paddlepaddle_version": "2.6.2"
}
```

---

## Project Structure

```
OCR-and-Read-document/
├── config/
│   ├── __init__.py
│   └── document_rules.py        # Rules untuk deteksi jenis dokumen
├── parsers/
│   ├── Form_PM_POP/             # Parser untuk Form PM POP
│   │   ├── pm_battery_parser.py
│   │   ├── pm_inverter_parser.py
│   │   └── ... (parser lainnya)
│   ├── config/
│   │   └── pm_labels.py         # Label definitions
│   ├── utils/
│   │   ├── datetime_utils.py
│   │   ├── spatial_utils.py
│   │   └── text_utils.py
│   ├── base_parser.py
│   ├── spk_survey_parser.py     # Parser SPK Survey
│   ├── spk_instalasi_parser.py  # Parser SPK Instalasi
│   ├── spk_dismantle_parser.py  # Parser SPK Dismantle
│   ├── spk_aktivasi_parser.py   # Parser SPK Aktivasi
│   ├── checklist_wireless_parser.py
│   └── checklist_wireline_parser.py
├── readers/
│   ├── ocr/
│   │   ├── image_extractor.py   # Extract images dari PDF
│   │   ├── processor.py         # OCR processing
│   │   └── text_reader.py       # Text extraction
│   ├── pdf_reader.py            # PDF reader utama
│   └── doc_reader.py
├── input/
│   ├── img/                     # Test images
│   └── pdf/                     # Test PDFs
├── output/                      # Hasil processing
│   └── extracted/
│       ├── spk/
│       │   ├── survey/
│       │   ├── instalasi/
│       │   ├── dismantle/
│       │   └── aktivasi/
│       ├── checklist/
│       │   ├── wireline/
│       │   └── wireless/
│       └── form_pm/
│           ├── battery/
│           ├── inverter/
│           └── ... (lainnya)
├── app.py                       # Flask application
├── main.py                      # CLI interface
├── dispatcher.py                # Document type dispatcher
├── validate_first_page.py       # Quick validation
├── requirements.txt             # Python dependencies
└── README.md
```

---

## Supported Document Types

### SPK (Surat Perintah Kerja)
- SPK Survey
- SPK Instalasi
- SPK Dismantle
- SPK Aktivasi

### Form Checklist
- Checklist Wireline
- Checklist Wireless

### Form PM POP (Preventive Maintenance)
- PM 1 Phase UPS
- PM 3 Phase UPS
- PM AC
- PM Inverter
- PM Ruang Shelter
- PM Rectifier
- PM Petir & Grounding
- PM Instalasi Kabel & Panel Distribusi
- PM Battery
- PM Pole Tower
- PM Dokumentasi Perangkat
- PM Genset

---

## Testing

### Test dengan CLI (main.py)

```bash
python main.py
```

Akan muncul menu interaktif untuk memilih dokumen test.

### Test dengan Flask API

```bash
# Start server
python app.py

# Test dengan curl (terminal lain)
curl -X POST http://localhost:5000/process-pdf \
  -F "file=@input/pdf/Survey 1.pdf"
```

### Test Individual Parser

```python
# test_parser.py
from parsers.spk_survey_parser import SpkSurveyParser

parser = SpkSurveyParser()
result = parser.parse(ocr_data)
print(result)
```

---

## Troubleshooting

### Common Issues

**1. ModuleNotFoundError: No module named 'paddleocr'**
```bash
pip install paddleocr==2.7.0.3
```

**2. PaddlePaddle installation failed**

Untuk CPU only:
```bash
pip install paddlepaddle==2.6.2 -i https://mirror.baidu.com/pypi/simple
```

Untuk GPU (dengan CUDA):
```bash
pip install paddlepaddle-gpu==2.6.2
```

**3. DLL load failed (Windows)**

Install Visual C++ Redistributable:
https://aka.ms/vs/17/release/vc_redist.x64.exe

**4. ImportError: numpy.core.multiarray**

```bash
pip uninstall numpy
pip install numpy==1.26.4
```

**5. PaddleOCR model download failed**

Model akan auto-download saat pertama kali run. Jika gagal:
- Check koneksi internet
- Coba manual download dari: https://paddleocr.bj.bcebos.com/
- Atau gunakan mirror China: 
```python
ocr = PaddleOCR(use_angle_cls=True, lang='en', 
                det_model_dir='./models/det',
                rec_model_dir='./models/rec')
```

**6. Out of memory saat processing PDF besar**

Reduce batch size atau process per halaman:
```python
# Di config
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en',
    rec_batch_num=1,  # Reduce batch size
    max_text_length=512
)
```

**7. Flask port already in use**

```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:5000 | xargs kill -9
```

---

## Performance Optimization

### 1. Use GPU (if available)

Install CUDA dan PaddlePaddle GPU version:
```bash
pip install paddlepaddle-gpu==2.6.2
```

Update di code:
```python
ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True)
```

### 2. Batch Processing

Process multiple PDFs secara parallel:
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    results = executor.map(process_pdf, pdf_files)
```

### 3. Cache OCR Results

Simpan hasil OCR untuk dokumen yang sama:
```python
import hashlib
import json

def get_file_hash(file_path):
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

# Cache hasil
cache_file = f"cache/{file_hash}.json"
```

---

## Integration with Laravel Frontend

### 1. Start Backend Server

```bash
cd OCR-and-Read-document
venv\Scripts\activate  # Windows
python app.py
```

### 2. Configure Laravel

Update `.env` di Laravel project:
```env
PYTHON_API_URL=http://localhost:5000
```

### 3. Test Integration

Upload PDF dari Laravel frontend, backend akan otomatis process.

---

## Development

### Add New Document Parser

1. Buat file parser baru di `parsers/`:
```python
# parsers/my_new_parser.py
from parsers.base_parser import BaseParser

class MyNewParser(BaseParser):
    def parse(self, ocr_data):
        # Your parsing logic
        return parsed_data
```

2. Register di `dispatcher.py`:
```python
from parsers.my_new_parser import MyNewParser

PARSER_MAP = {
    'my_new_type': MyNewParser,
    # ... existing parsers
}
```

3. Add detection rule di `validate_first_page.py`

### Run Tests

```bash
# Install pytest
pip install pytest

# Run tests
pytest tests/
```

---

## Deployment

### Using Docker (Recommended)

```dockerfile
FROM python:3.10.6-slim

WORKDIR /app

# Install system dependencies untuk OpenCV dan PaddlePaddle
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app", "--timeout", "300"]
```

Build and run:
```bash
docker build -t ocr-backend .
docker run -p 5000:5000 ocr-backend
```

### Using systemd (Linux)

Create service file `/etc/systemd/system/ocr-backend.service`:
```ini
[Unit]
Description=OCR Backend Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/OCR-and-Read-document
Environment="PATH=/path/to/OCR-and-Read-document/venv/bin"
ExecStart=/path/to/OCR-and-Read-document/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl start ocr-backend
sudo systemctl enable ocr-backend
```

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License.

---

## Support

For issues or questions:
- Open an issue on [GitHub Issues](https://github.com/rahmatisma/OCR-and-Read-document/issues)
- For frontend issues: [Laravel Frontend Issues](https://github.com/rahmatisma/Website-Read-PDF/issues)

---

## Author

**Rahmat Isma**
- GitHub: [@rahmatisma](https://github.com/rahmatisma)

---

## Acknowledgments

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - Powerful OCR engine by Baidu
- [PaddlePaddle](https://github.com/PaddlePaddle/Paddle) - Deep learning framework
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF processing library
- [OpenCV](https://opencv.org/) - Computer vision library

---

## Related Repositories

**Laravel Frontend**: [Website-Read-PDF](https://github.com/rahmatisma/Website-Read-PDF)
