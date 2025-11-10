# readers/ocr/processor.py
"""
Processor OCR untuk ekstraksi teks dan gambar dari PDF
Fixed: Return structured OCR data untuk coordinate-based parsing
"""

import os
import numpy as np
from PIL import Image
import fitz
from readers.ocr.text_reader import run_ocr
from readers.ocr.image_extractor import extract_and_classify_images


def ensure_dir(path):
    """Pastikan direktori ada sebelum digunakan."""
    if not os.path.exists(path):
        os.makedirs(path)


def process_page_ocr(page, enhance=False, return_structured=False, return_data=False, max_dimension=1920):
    """
    Proses OCR pada satu halaman PDF dengan opsi structured output.
    
    Args:
        page: PyMuPDF page object
        enhance: Apply preprocessing (False = lebih cepat untuk form jelas)
        return_structured: Return tuple (text, lines) - DEPRECATED, gunakan return_data
        return_data: Return dict {'text': str, 'data': list} untuk parser (RECOMMENDED)
        max_dimension: Maksimum dimensi gambar untuk speed optimization
    
    Returns:
        - String: teks saja (default)
        - Tuple: (text, ocr_lines) (jika return_structured=True) - DEPRECATED
        - Dict: {'text': str, 'data': list} (jika return_data=True) - RECOMMENDED
            data format: [{'text': str, 'score': float, 'bbox': [x1,y1,x2,y2], 'position': (y,x)}, ...]
    """
    try:
        # 1. Render dengan DPI optimal (150 untuk balance speed/quality)
        pix = page.get_pixmap(dpi=150)
        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        
        # 2. Resize jika terlalu besar (speed optimization)
        width, height = img.size
        if max(width, height) > max_dimension:
            ratio = max_dimension / max(width, height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            print(f"[INFO] Resize gambar: {width}x{height} → {new_size[0]}x{new_size[1]}")
        
        img_np = np.array(img)
        
        # 3. Jalankan OCR
        if return_data or return_structured:
            # Return structured data untuk coordinate-based parsing
            result = run_ocr(img_np, enhance_image=enhance, return_structured=True)
            
            print(f"[DEBUG] OCR returned {len(result['lines'])} items")
            
            # Print sample untuk debugging
            if result['lines']:
                print(f"[DEBUG] Sample OCR items (first 5):")
                for i, item in enumerate(result['lines'][:5]):
                    text_preview = item['text'][:50] + "..." if len(item['text']) > 50 else item['text']
                    print(f"  [{i}] '{text_preview}' (score={item['score']:.2f}, bbox={item.get('bbox', 'N/A')})")
            
            # ========== NEW: Return format untuk parser ==========
            if return_data:
                return {
                    'text': result['text'],
                    'data': result['lines']  # lines sudah ada bbox dan position
                }
            # =====================================================
            
            # Backward compatibility untuk return_structured
            return result['text'], result['lines']
        else:
            # Return text only (backward compatible)
            text = run_ocr(img_np, enhance_image=enhance)
            return text.strip()

    except Exception as e:
        print(f"[ERROR] Gagal OCR halaman: {e}")
        import traceback
        traceback.print_exc()
        
        if return_data:
            return {'text': '', 'data': []}
        if return_structured:
            return "", []
        return ""


def process_pdf_with_images(pdf_path, doc_type, output_dir="output/images"):
    """
    Jalankan pipeline lengkap ekstraksi gambar dokumentasi.
    
    Args:
        pdf_path: Path ke file PDF
        doc_type: Tipe dokumen dari dispatcher (contoh: "spk_survey", "spk_instalasi")
        output_dir: Direktori output untuk gambar
        
    Returns:
        List dictionary dengan format:
        [
            {"jenis": "Dokumentasi foto", "patch_foto": "output/images/..."},
            ...
        ]
    """
    print(f"[INFO] Mengekstrak gambar dari PDF: {pdf_path}")
    print(f"[INFO] Tipe dokumen: {doc_type}")

    try:
        ensure_dir(output_dir)
        
        # Ekstrak gambar berdasarkan label sesuai doc_type
        results = extract_and_classify_images(
            pdf_path=pdf_path, 
            doc_type=doc_type, 
            output_dir=output_dir
        )
        
        return results

    except Exception as e:
        print(f"[ERROR] Gagal mengekstrak gambar PDF: {e}")
        return []


# ===== UTILITY FUNCTIONS =====

def extract_page_text_with_ocr(page, use_ocr_always=False, enhance=False):
    """
    Extract teks dari halaman PDF dengan fallback ke OCR.
    
    Args:
        page: PyMuPDF page object
        use_ocr_always: Force OCR meskipun ada text layer
        enhance: Apply preprocessing untuk OCR
    
    Returns:
        Tuple: (text, ocr_lines)
            - text: string teks
            - ocr_lines: list OCR data (empty jika tidak pakai OCR)
    """
    # Cek apakah halaman punya text layer
    page_text = page.get_text("text").strip()
    
    if page_text and not use_ocr_always:
        # Ada text layer, tidak perlu OCR
        print(f"[INFO] Halaman {page.number + 1}: Menggunakan text layer")
        return page_text, []
    else:
        # Tidak ada text layer atau force OCR
        print(f"[INFO] Halaman {page.number + 1}: Menjalankan OCR...")
        return process_page_ocr(page, enhance=enhance, return_structured=True)


def process_pdf_pages_with_ocr(pdf_path, use_ocr_always=False, enhance=False):
    """
    Process semua halaman PDF dengan OCR support.
    
    Args:
        pdf_path: Path ke file PDF
        use_ocr_always: Force OCR untuk semua halaman
        enhance: Apply preprocessing
    
    Returns:
        Dict dengan format:
        {
            'all_text': str,           # Gabungan semua text
            'page_texts': [str, ...],  # Text per halaman
            'ocr_data': [[{}, ...], ...] # OCR data per halaman (bisa kosong)
        }
    """
    try:
        doc = fitz.open(pdf_path)
        all_text_parts = []
        page_texts = []
        all_ocr_data = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract text dengan OCR support
            page_text, ocr_lines = extract_page_text_with_ocr(
                page, 
                use_ocr_always=use_ocr_always, 
                enhance=enhance
            )
            
            all_text_parts.append(page_text)
            page_texts.append(page_text)
            all_ocr_data.append(ocr_lines)
        
        doc.close()
        
        return {
            'all_text': "\n\n".join(all_text_parts),
            'page_texts': page_texts,
            'ocr_data': all_ocr_data
        }
    
    except Exception as e:
        print(f"[ERROR] Gagal memproses PDF: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'all_text': "",
            'page_texts': [],
            'ocr_data': []
        }