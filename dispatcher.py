# dispatcher.py
"""
Dispatcher untuk mendeteksi jenis dokumen dan mengarahkan ke parser yang sesuai
"""

from parsers.spk_survey_parser import parse_spk_survey
from parsers.spk_instalasi_parser import parse_spk_instalasi
from parsers.spk_dismantle_parser import parse_spk_dismantle
from parsers.spk_aktivasi_parser import parse_spk_aktivasi
from parsers.checklist_wireless_parser import parse_checklist_wireless
from parsers.checklist_wireline_parser import parse_checklist_wireline


def detect_spk_type(all_text: str) -> str:
    """
    Deteksi jenis SPK berdasarkan kata kunci di teks.
    
    Args:
        all_text: Teks lengkap dari PDF
        
    Returns:
        String jenis SPK: "spk_survey" | "spk_instalasi" | "spk_dismantle" | 
                        "spk_aktivasi" | "checklist_wireline" | 
                        "maintenance_remote_wireless" | "unknown"
    """
    lower_text = all_text.lower()

    # Deteksi berdasarkan kata kunci (urutan penting: yang lebih spesifik di atas)
    if "spk survey" in lower_text:
        return "spk_survey"
    elif "spk instalasi" in lower_text:
        return "spk_instalasi"
    elif "spk dismantle" in lower_text:
        return "spk_dismantle"
    elif "spk aktivasi" in lower_text:
        return "spk_aktivasi"
    elif "checklist" in lower_text and "wireline" in lower_text:
        return "checklist_wireline"
    elif "checklist" in lower_text and "wireless" in lower_text:
        return "checklist_wireless"
    elif "maintenance remote wireless" in lower_text:
        return "maintenance_remote_wireless"
    else:
        print("[WARNING] Jenis SPK tidak terdeteksi dari teks")
        return "unknown"


# ========== UPDATE FUNCTION INI ==========
def dispatch_parser(all_text: str, page_texts: list, ocr_data: list = None) -> dict:
    """
    Dispatcher untuk mengarahkan teks ke parser sesuai jenis SPK.
    
    Args:
        all_text: Teks lengkap dari PDF
        page_texts: List teks per halaman (legacy, untuk backward compatibility)
        ocr_data: List of OCR data dengan bbox/position (BARU)
        
    Returns:
        Dictionary dengan format:
        {
            "document_type": "spk_survey",  # ← PENTING: untuk image_extractor
            "jenis_spk": "survey",           # ← untuk backward compatibility
            "data": { ... parsed data ... },
            "metadata": { ... }
        }
    """
    # Deteksi jenis SPK
    spk_type = detect_spk_type(all_text)
    print(f"[INFO] Dispatcher: Jenis dokumen terdeteksi = {spk_type}")
    
    # ========== DEBUG OCR DATA ==========
    if ocr_data:
        print(f"[INFO] Dispatcher: OCR data tersedia ({len(ocr_data)} items)")
    else:
        print(f"[WARNING] Dispatcher: OCR data KOSONG atau None")
    # ====================================

    # Mapping jenis SPK ke parser
    parser_map = {
        "spk_survey": parse_spk_survey,
        "spk_instalasi": parse_spk_instalasi,
        "spk_dismantle": parse_spk_dismantle,
        "spk_aktivasi": parse_spk_aktivasi,
        "checklist_wireless": parse_checklist_wireless,
        "checklist_wireline": parse_checklist_wireline,
    }

    # Ambil parser yang sesuai
    parser_func = parser_map.get(spk_type)

    if parser_func:
        try:
            # ========== PASS OCR DATA KE PARSER ==========
            # Cek apakah parser support ocr_data parameter
            import inspect
            sig = inspect.signature(parser_func)
            
            if 'ocr_data' in sig.parameters:
                # Parser support ocr_data
                print(f"[INFO] Calling parser dengan OCR data")
                parsed_data = parser_func(all_text, page_texts, ocr_data=ocr_data)
            else:
                # Parser belum support ocr_data (backward compatibility)
                print(f"[WARNING] Parser {parser_func.__name__} belum support ocr_data")
                parsed_data = parser_func(all_text, page_texts)
            # =============================================
            
            # Tambahkan document_type ke hasil
            result = {
                "document_type": spk_type,  # ← untuk image_extractor
                "jenis_spk": spk_type.replace("spk_", ""),  # backward compatibility
                "data": parsed_data,
                "metadata": {
                    "parser_used": parser_func.__name__,
                    "detection_confidence": "high",
                    "ocr_data_available": bool(ocr_data)  # ← TAMBAHKAN INFO INI
                }
            }
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Parser gagal: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "document_type": spk_type,
                "jenis_spk": spk_type.replace("spk_", ""),
                "data": {},
                "metadata": {
                    "error": str(e),
                    "note": "Parser gagal, perlu cek manual."
                }
            }
    else:
        # Jenis SPK tidak dikenali atau belum ada parsernya
        return {
            "document_type": "unknown",
            "jenis_spk": "unknown",
            "data": {},
            "metadata": {
                "detected_type": spk_type,
                "note": "Jenis SPK tidak terdeteksi atau parser belum tersedia. Perlu cek manual."
            }
        }


# ========== HELPER FUNCTIONS (OPSIONAL) ==========

def get_available_spk_types() -> list:
    """
    Mendapatkan daftar jenis SPK yang didukung.
    
    Returns:
        List string jenis SPK
    """
    return [
        "spk_survey",
        "spk_instalasi",
        "spk_dismantle",
        "spk_aktivasi",
        "checklist_wireline",
        "checklist_wireless",
        "maintenance_remote_wireless"
    ]


def validate_spk_type(spk_type: str) -> bool:
    """
    Validasi apakah jenis SPK didukung.
    
    Args:
        spk_type: Jenis SPK yang ingin divalidasi
        
    Returns:
        True jika didukung, False jika tidak
    """
    return spk_type in get_available_spk_types()