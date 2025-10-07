# ocr utama
from paddleocr import PaddleOCR
import numpy as np
from PIL import Image

# Inisialisasi model OCR sekali saja
ocr_model = PaddleOCR(use_angle_cls=True, lang='en')

def extract_texts_and_scores(result):
    """Ekstraksi teks dan skor dari output PaddleOCR"""
    texts, scores = [], []
    if not result:
        return texts, scores

    first = result[0]
    if isinstance(first, dict):
        if 'rec_texts' in first:
            return first.get('rec_texts', []), first.get('rec_scores', [])
        if 'rec_res' in first:
            for item in first['rec_res']:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    texts.append(item[0])
                    scores.append(item[1])
            return texts, scores

    # fallback jika struktur berbeda
    page_data = first if isinstance(first, (list, tuple)) else result

    def find_str(obj):
        if isinstance(obj, str):
            return obj
        if isinstance(obj, (list, tuple)):
            for e in obj:
                s = find_str(e)
                if s:
                    return s
        if isinstance(obj, dict):
            for v in obj.values():
                s = find_str(v)
                if s:
                    return s
        return None

    def find_num(obj):
        if isinstance(obj, (float, int)):
            return float(obj)
        if isinstance(obj, (list, tuple)):
            for e in obj:
                n = find_num(e)
                if n is not None:
                    return n
        if isinstance(obj, dict):
            for v in obj.values():
                n = find_num(v)
                if n is not None:
                    return n
        return None

    for line in page_data:
        text = find_str(line)
        score = find_num(line)
        texts.append(text or "")
        scores.append(score or 0.0)

    return texts, scores


def run_ocr(image_input) -> str:
    """
    Jalankan OCR pada gambar (numpy array atau path).
    - image_input: bisa berupa numpy array atau path ke file gambar
    - return: string gabungan teks hasil OCR
    """
    all_texts = []

    try:
        # Deteksi tipe input: path atau numpy array
        if isinstance(image_input, str):
            img = Image.open(image_input).convert("RGB")
            img_np = np.array(img)
        elif isinstance(image_input, np.ndarray):
            img_np = image_input
        else:
            raise ValueError("Input harus berupa path string atau numpy array.")

        # Jalankan OCR
        result = ocr_model.ocr(img_np)
        texts, scores = extract_texts_and_scores(result)
        all_texts.extend(texts)

    except Exception as e:
        print(f"[ERROR] OCR gagal: {e}")

    return " ".join(all_texts)

