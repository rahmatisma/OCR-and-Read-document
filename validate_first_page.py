# validate_first_page.py
"""
Validasi cepat halaman pertama PDF untuk deteksi jenis dokumen.
Digunakan sebelum full processing untuk menghindari pemrosesan dokumen yang salah.
"""

import fitz
from readers.ocr.processor import process_page_ocr
from dispatcher import detect_spk_type


def validate_first_page(pdf_path: str) -> dict:
    """
    Validasi halaman pertama PDF untuk deteksi jenis dokumen.
    
    Args:
        pdf_path: Path ke file PDF
        
    Returns:
        dict: {
            'success': bool,
            'document_type': str,  # spk_survey, checklist_wireless, unknown, dll
            'confidence': str,     # high, medium, low
            'message': str
        }
    """
    print(f"[INFO] 🔍 Validasi halaman pertama: {pdf_path}")
    
    try:
        # Buka PDF
        doc = fitz.open(pdf_path)
        
        if len(doc) == 0:
            doc.close()
            return {
                'success': False,
                'document_type': 'unknown',
                'confidence': 'none',
                'message': 'PDF tidak memiliki halaman'
            }
        
        # Ambil halaman pertama
        first_page = doc[0]
        
        # Coba ekstrak teks dari text layer dulu
        page_text = first_page.get_text("text").strip()
        
        # Jika kosong, gunakan OCR
        if not page_text:
            print(f"[INFO] Halaman 1 kosong, menjalankan OCR...")
            ocr_result = process_page_ocr(first_page, enhance=False, return_data=True)
            
            if isinstance(ocr_result, dict) and 'text' in ocr_result:
                page_text = ocr_result['text']
            elif isinstance(ocr_result, str):
                page_text = ocr_result
            else:
                page_text = ""
        
        doc.close()
        
        # Jika masih kosong setelah OCR
        if not page_text or len(page_text.strip()) < 10:
            return {
                'success': False,
                'document_type': 'unknown',
                'confidence': 'none',
                'message': 'Tidak dapat membaca teks dari halaman pertama. File mungkin rusak atau tidak dapat dibaca.'
            }
        
        print(f"[INFO] Teks halaman 1 berhasil diekstrak: {len(page_text)} karakter")
        
        # Deteksi jenis dokumen menggunakan dispatcher
        document_type = detect_spk_type(page_text)
        
        print(f"[INFO] ✅ Jenis dokumen terdeteksi: {document_type}")
        
        # Tentukan confidence level
        confidence = determine_confidence(page_text, document_type)
        
        # Build response
        if document_type == 'unknown':
            return {
                'success': False,
                'document_type': 'unknown',
                'confidence': 'none',
                'message': 'Jenis dokumen tidak dapat diidentifikasi. Pastikan file adalah SPK atau Form Checklist yang valid.'
            }
        else:
            return {
                'success': True,
                'document_type': document_type,
                'confidence': confidence,
                'message': f'Dokumen terdeteksi sebagai {document_type}'
            }
    
    except Exception as e:
        print(f"[ERROR] Validasi gagal: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'document_type': 'unknown',
            'confidence': 'none',
            'message': f'Error saat validasi: {str(e)}'
        }


def determine_confidence(text: str, doc_type: str) -> str:
    """
    Tentukan confidence level berdasarkan keyword matching.
    
    Returns:
        'high', 'medium', atau 'low'
    """
    text_lower = text.lower()
    
    # Keyword map untuk confidence check
    confidence_keywords = {
        'spk_survey': ['spk survey', 'survey report', 'surat perintah kerja'],
        'spk_instalasi': ['spk instalasi', 'instalasi report'],
        'spk_dismantle': ['spk dismantle', 'dismantle report'],
        'spk_aktivasi': ['spk aktivasi', 'aktivasi report'],
        'checklist_wireline': ['checklist', 'wireline', 'maintenance', 'form checklist'],
        'checklist_wireless': ['checklist', 'wireless', 'maintenance', 'form checklist'],
    }
    
    keywords = confidence_keywords.get(doc_type, [])
    
    # Hitung berapa banyak keyword yang ditemukan
    matches = sum(1 for keyword in keywords if keyword in text_lower)
    
    if matches >= 2:
        return 'high'
    elif matches == 1:
        return 'medium'
    else:
        return 'low'


# ============================================
# CLI TESTING (Optional)
# ============================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python validate_first_page.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    result = validate_first_page(pdf_path)
    
    print("\n" + "=" * 60)
    print("📋 HASIL VALIDASI")
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"Document Type: {result['document_type']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Message: {result['message']}")
    print("=" * 60)