from paddleocr import PaddleOCR
import numpy as np
from PIL import Image
import os

# Inisialisasi model OCR sekali
ocr_model = PaddleOCR(use_angle_cls=True, lang='en')


def extract_texts_and_scores(result):
    """Ekstraksi teks dan skor dari output PaddleOCR"""
    texts = []
    scores = []
    if not result:
        return texts, scores

    first = result[0]
    if isinstance(first, dict):
        if 'rec_texts' in first:
            texts = first.get('rec_texts', [])
            scores = first.get('rec_scores', [0.0] * len(texts))
            return texts, scores
        if 'rec_res' in first:
            for item in first['rec_res']:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    texts.append(item[0])
                    scores.append(item[1] if len(item) > 1 else 0.0)
            return texts, scores

    # fallback
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
        texts.append(text if text is not None else "")
        scores.append(score if score is not None else 0.0)

    return texts, scores


def read_image(img_path: str) -> str:
    """
    OCR gambar → hasil teks string
    NOTE: Tidak lagi meng-handle PDF (itu sudah ditangani read_pdf)
    """
    all_texts = []

    try:
        img = Image.open(img_path).convert("RGB")
        img_np = np.array(img)
        result = ocr_model.ocr(img_np)
        texts, scores = extract_texts_and_scores(result)
        all_texts.extend(texts)

    except Exception as e:
        print(f"[ERROR] OCR gagal di {img_path}: {e}")

    return " ".join(all_texts)
