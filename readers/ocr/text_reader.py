# readers/ocr/text_reader.py
"""
OCR Reader dengan Layout-Aware Processing
Compatible dengan PaddleOCR v3+ (PaddleX API)
"""

from paddleocr import PaddleOCR
import numpy as np
from PIL import Image
import cv2

# Inisialisasi model OCR dengan API baru
print("[INFO] Menggunakan PaddleOCR v3+ (PaddleX API)")
ocr_model = PaddleOCR(
    use_textline_orientation=True,  # Ganti use_angle_cls (deprecated)
    lang='en'
)


def preprocess_image(image_np, enhance=True):
    """Pre-processing image untuk meningkatkan akurasi OCR"""
    if not enhance:
        return image_np
    
    try:
        # Convert ke RGB jika RGBA
        if len(image_np.shape) == 3 and image_np.shape[2] == 4:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGBA2RGB)
        
        # Convert ke grayscale
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        
        # Adaptive threshold
        thresh = cv2.adaptiveThreshold(
            denoised, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Convert kembali ke RGB
        processed = cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
        return processed
    
    except Exception as e:
        print(f"[WARNING] Preprocessing gagal: {e}")
        return image_np


def extract_from_paddlev3_result(result):
    """
    Ekstraksi dari PaddleOCR v3+ result format
    
    Format PaddleX OCRResult object dengan attributes:
    - rec_texts: list of strings
    - rec_scores: list of floats
    - dt_polys atau rec_polys: list of numpy arrays (bounding boxes)
    
    Returns:
        list of dict: [{'text': str, 'score': float, 'bbox': list, 'position': tuple}, ...]
    """
    items = []
    
    try:
        if not result or len(result) == 0:
            return items
        
        # Ambil prediksi pertama (single image)
        prediction = result[0] if isinstance(result, list) else result
        
        # Cek apakah object punya attribute (PaddleX OCRResult)
        if hasattr(prediction, 'rec_texts'):
            rec_texts = getattr(prediction, 'rec_texts', [])
            rec_scores = getattr(prediction, 'rec_scores', [])
            # Coba dt_polys dulu, fallback ke rec_polys
            dt_polys = getattr(prediction, 'dt_polys', None)
            if dt_polys is None:
                dt_polys = getattr(prediction, 'rec_polys', [])
            
            # Proses setiap deteksi
            for i in range(len(rec_texts)):
                try:
                    text = rec_texts[i] if i < len(rec_texts) else ""
                    score = rec_scores[i] if i < len(rec_scores) else 1.0
                    bbox = dt_polys[i] if i < len(dt_polys) else None
                    
                    if text and bbox is not None:
                        # Konversi numpy array ke list jika perlu
                        if hasattr(bbox, 'tolist'):
                            bbox = bbox.tolist()
                        
                        # Hitung posisi center untuk sorting
                        if len(bbox) >= 4:
                            # bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                            y_center = (bbox[0][1] + bbox[2][1]) / 2
                            x_left = bbox[0][0]
                            
                            items.append({
                                'text': str(text),
                                'score': float(score),
                                'bbox': bbox,
                                'position': (y_center, x_left)
                            })
                except Exception as e:
                    print(f"[WARNING] Skip item {i}: {e}")
                    continue
        
        # Fallback: coba format dict (backward compatibility)
        elif isinstance(prediction, dict):
            rec_texts = prediction.get('rec_texts', prediction.get('rec_text', []))
            rec_scores = prediction.get('rec_scores', prediction.get('rec_score', []))
            dt_polys = prediction.get('dt_polys', prediction.get('rec_polys', []))
            
            for i in range(len(rec_texts)):
                try:
                    text = rec_texts[i] if i < len(rec_texts) else ""
                    score = rec_scores[i] if i < len(rec_scores) else 1.0
                    bbox = dt_polys[i] if i < len(dt_polys) else None
                    
                    if text and bbox is not None:
                        if hasattr(bbox, 'tolist'):
                            bbox = bbox.tolist()
                        
                        if len(bbox) >= 4:
                            y_center = (bbox[0][1] + bbox[2][1]) / 2
                            x_left = bbox[0][0]
                            
                            items.append({
                                'text': str(text),
                                'score': float(score),
                                'bbox': bbox,
                                'position': (y_center, x_left)
                            })
                except Exception as e:
                    print(f"[WARNING] Skip item {i}: {e}")
                    continue
        
        # Fallback: format list lama (very old version)
        elif isinstance(prediction, (list, tuple)):
            for line in prediction:
                try:
                    if len(line) >= 2:
                        bbox = line[0]
                        text_info = line[1]
                        
                        if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                            text = text_info[0]
                            score = text_info[1]
                        else:
                            text = str(text_info)
                            score = 1.0
                        
                        if hasattr(bbox, 'tolist'):
                            bbox = bbox.tolist()
                        
                        if isinstance(bbox, list) and len(bbox) >= 4:
                            y_center = (bbox[0][1] + bbox[2][1]) / 2
                            x_left = bbox[0][0]
                            
                            items.append({
                                'text': str(text),
                                'score': float(score),
                                'bbox': bbox,
                                'position': (y_center, x_left)
                            })
                except Exception as e:
                    print(f"[WARNING] Skip line: {e}")
                    continue
    
    except Exception as e:
        print(f"[ERROR] Ekstraksi gagal: {e}")
        import traceback
        traceback.print_exc()
    
    return items


def sort_by_reading_order(items, line_threshold=20):
    """Urutkan teks berdasarkan reading order"""
    if not items:
        return items
    
    sorted_items = sorted(
        items, 
        key=lambda item: (
            round(item['position'][0] / line_threshold) * line_threshold,
            item['position'][1]
        )
    )
    return sorted_items


def run_ocr(image_input, enhance_image=False, return_structured=False):
    """
    Jalankan OCR pada gambar (numpy array atau path)
    Compatible dengan PaddleOCR v3+
    
    Args:
        image_input: numpy array atau path ke file gambar
        enhance_image: preprocessing (default: False)
        return_structured: return dict detail atau string (default: False)
    
    Returns:
        - String: gabungan teks (jika return_structured=False)
        - Dict: {'text': str, 'lines': list} (jika return_structured=True)
    """
    all_texts = []
    structured_data = []

    try:
        # Load image
        if isinstance(image_input, str):
            img = Image.open(image_input).convert("RGB")
            img_np = np.array(img)
        elif isinstance(image_input, np.ndarray):
            img_np = image_input
        else:
            raise ValueError("Input harus path string atau numpy array")

        # Preprocessing (optional)
        if enhance_image:
            img_np = preprocess_image(img_np, enhance=True)

        # Jalankan OCR dengan API baru (predict)
        result = ocr_model.predict(img_np)
        
        # Debug: print struktur result
        # print(f"[DEBUG] Result type: {type(result)}")
        # if result:
        #     print(f"[DEBUG] Result[0] type: {type(result[0])}")
        #     if isinstance(result[0], dict):
        #         print(f"[DEBUG] Result[0] keys: {result[0].keys()}")
        
        # Ekstrak teks dari result format baru
        items = extract_from_paddlev3_result(result)
        
        # Sort by reading order
        sorted_items = sort_by_reading_order(items)
        
        # Compile texts
        all_texts = [item['text'] for item in sorted_items]
        structured_data = sorted_items

    except Exception as e:
        print(f"[ERROR] OCR gagal: {e}")
        import traceback
        traceback.print_exc()
        
        if return_structured:
            return {'text': '', 'lines': []}
        return ""

    # Return
    if return_structured:
        return {
            'text': " ".join(all_texts),
            'lines': structured_data
        }
    else:
        return " ".join(all_texts)


def run_ocr_with_confidence_filter(image_input, min_score=0.5, enhance_image=False):
    """OCR dengan filtering berdasarkan confidence score"""
    try:
        result = run_ocr(image_input, enhance_image=enhance_image, return_structured=True)
        
        filtered_texts = [
            item['text'] 
            for item in result['lines'] 
            if item['score'] >= min_score
        ]
        
        return " ".join(filtered_texts)
    
    except Exception as e:
        print(f"[ERROR] OCR filter gagal: {e}")
        return ""


# Backward compatibility: keep old function name
def extract_texts_and_scores(result):
    """
    Legacy function untuk backward compatibility
    Sekarang wrapper untuk extract_from_paddlev3_result
    """
    items = extract_from_paddlev3_result(result)
    sorted_items = sort_by_reading_order(items)
    
    texts = [item['text'] for item in sorted_items]
    scores = [item['score'] for item in sorted_items]
    
    return texts, scores