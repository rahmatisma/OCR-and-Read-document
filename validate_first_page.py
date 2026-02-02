# validate_first_page.py
"""
Validasi cepat halaman pertama PDF untuk deteksi jenis dokumen.
 UPDATED: Support Form PM POP dengan validasi kategori
"""

import fitz
import re
from readers.ocr.processor import process_page_ocr
from dispatcher import detect_spk_type


#  MAPPING KATEGORI (harus sync dengan Laravel)
CATEGORY_MAPPING = {
    'spk': ['spk_survey', 'spk_instalasi', 'spk_dismantle', 'spk_aktivasi'],
    'checklist': ['checklist_wireline', 'checklist_wireless'],
    'pmpop': [
        'form_pm_1phase_ups',
        'form_pm_3phase_ups',
        'form_pm_ac',
        'form_pm_inverter',
        'form_pm_ruang_shelter',
        'form_pm_rectifier',
        'form_pm_petir_grounding',
        'form_pm_instalasi_kabel',
        'form_pm_battery',
        'form_pm_pole_tower',
        'form_pm_dokumentasi_perangkat',
        'form_pm_genset',
        'form_pm_permohonan_tindak_lanjut',
        'form_pm_tindak_lanjut',
        'form_pm_jadwal_sentral',
    ],
}


def validate_first_page(pdf_path: str, expected_category: str = None) -> dict:
    """
    Validasi halaman pertama PDF untuk deteksi jenis dokumen.
    
    Args:
        pdf_path: Path ke file PDF
        expected_category: Kategori yang diharapkan ('spk', 'checklist', 'pmpop')
        
    Returns:
        dict: {
            'success': bool,
            'document_type': str,
            'confidence': str,
            'message': str,
            'is_valid_for_category': bool  #  NEW
        }
    """
    print(f"[INFO]  Validasi halaman pertama: {pdf_path}")
    if expected_category:
        print(f"[INFO] Expected category: {expected_category}")
    
    try:
        # Buka PDF
        doc = fitz.open(pdf_path)
        
        if len(doc) == 0:
            doc.close()
            return {
                'success': False,
                'document_type': 'unknown',
                'confidence': 'none',
                'message': 'PDF tidak memiliki halaman',
                'is_valid_for_category': False
            }
        
        # Ambil halaman pertama
        first_page = doc[0]
        
        # Coba ekstrak teks dari text layer dulu
        page_text = first_page.get_text("text").strip()
        
        #  UNTUK FILE SCAN: Jika kosong atau sangat pendek, gunakan OCR
        if not page_text or len(page_text.strip()) < 20:
            print(f"[INFO] Halaman 1 kosong/pendek ({len(page_text)} chars), menjalankan OCR...")
            ocr_result = process_page_ocr(first_page, enhance=True, return_data=True)
            
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
                'message': 'Tidak dapat membaca teks dari halaman pertama. File mungkin rusak atau tidak dapat dibaca.',
                'is_valid_for_category': False
            }
        
        print(f"[INFO] Teks halaman 1 berhasil diekstrak: {len(page_text)} karakter")
        print(f"[DEBUG] Preview teks (150 char): {page_text[:150]}")
        
        #  DETEKSI JENIS DOKUMEN
        document_type = detect_spk_type(page_text)
        
        if document_type == 'unknown':
            print("[WARNING] Jenis dokumen tidak terdeteksi dari teks")
        
        print(f"[INFO]  Jenis dokumen terdeteksi: {document_type}")
        
        #  VALIDASI KATEGORI (jika expected_category diberikan)
        is_valid_for_category = True
        category_message = ""
        
        if expected_category and document_type != 'unknown':
            allowed_types = CATEGORY_MAPPING.get(expected_category, [])
            is_valid_for_category = document_type in allowed_types
            
            if not is_valid_for_category:
                # Cari kategori yang sebenarnya
                actual_category = None
                for cat, types in CATEGORY_MAPPING.items():
                    if document_type in types:
                        actual_category = cat
                        break
                
                category_message = f" Dokumen ini seharusnya diupload di kategori '{actual_category}', bukan '{expected_category}'."
        
        # Tentukan confidence level
        confidence = determine_confidence(page_text, document_type)
        
        # Build response
        if document_type == 'unknown':
            result = {
                'success': False,
                'document_type': 'unknown',
                'confidence': 'none',
                'message': 'Jenis dokumen tidak dapat diidentifikasi. Pastikan file adalah SPK, Form Checklist, atau Form PM POP yang valid.',
                'is_valid_for_category': False
            }
        else:
            # Build friendly message
            if document_type.startswith('form_pm_'):
                doc_name = document_type.replace('form_pm_', '').replace('_', ' ').title()
                message = f'Dokumen terdeteksi sebagai Form PM: {doc_name}'
            elif document_type.startswith('spk_'):
                doc_name = document_type.replace('spk_', '').upper()
                message = f'Dokumen terdeteksi sebagai SPK {doc_name}'
            elif document_type.startswith('checklist_'):
                doc_name = document_type.replace('checklist_', '').title()
                message = f'Dokumen terdeteksi sebagai Form Checklist {doc_name}'
            else:
                message = f'Dokumen terdeteksi sebagai {document_type}'
            
            # Tambahkan category warning jika ada
            if category_message:
                message += category_message
            
            result = {
                'success': True,
                'document_type': document_type,
                'confidence': confidence,
                'message': message,
                'is_valid_for_category': is_valid_for_category  #  NEW
            }
        
        print(f"[INFO]  Validation result: {result}")
        return result
    
    except Exception as e:
        print(f"[ERROR] Validasi gagal: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'document_type': 'unknown',
            'confidence': 'none',
            'message': f'Error saat validasi: {str(e)}',
            'is_valid_for_category': False
        }


def determine_confidence(text: str, doc_type: str) -> str:
    """
    Tentukan confidence level berdasarkan keyword matching.
    
    Returns:
        'high', 'medium', atau 'low'
    """
    text_lower = text.lower()
    text_normalized = re.sub(r'\s+', ' ', text_lower.strip())
    
    # ============================================
    # CONFIDENCE UNTUK FORM PM POP
    # ============================================
    if doc_type.startswith('form_pm_'):
        score = 0
        
        # Check strong indicators
        strong_patterns = [
            r'preventive\s*maintenance',
            r'pemeliharaan\s*preventif',
            r'formulir',
            r'form\s*pm',
            r'FM-LAP-D2-SOP-003',  # Kode dokumen PM (PALING KUAT)
        ]
        
        for pattern in strong_patterns:
            if re.search(pattern, text_normalized):
                score += 2
        
        # Check supporting keywords
        supporting = ['maintenance', 'perawatan', 'berkala', 'rutin', 'checklist']
        for keyword in supporting:
            if keyword in text_normalized:
                score += 1
        
        #  Jika ada kode FM-LAP-D2-SOP-003-XXX, confidence PASTI high
        # NOTE: Handle spasi di "FM-LAP- D2"
        if re.search(r'FM-LAP-?\s*D2-SOP-003-\d{3}', text_normalized):
            return 'high'
        
        if score >= 6:
            return 'high'
        elif score >= 3:
            return 'medium'
        else:
            return 'low'
    
    # ============================================
    # CONFIDENCE UNTUK SPK & CHECKLIST
    # ============================================
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
    
    if matches >= 3:
        return 'high'
    elif matches >= 2:
        return 'medium'
    else:
        return 'low'


# ============================================
# CLI TESTING (Optional)
# ============================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python validate_first_page.py <pdf_path> [expected_category]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    expected_category = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = validate_first_page(pdf_path, expected_category)
    
    print("\n" + "=" * 60)
    print("📋 HASIL VALIDASI")
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"Document Type: {result['document_type']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Valid for Category: {result['is_valid_for_category']}")
    print(f"Message: {result['message']}")
    print("=" * 60)