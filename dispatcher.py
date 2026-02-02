# dispatcher.py - FIXED VERSION
"""
 FIXED: Checklist priority lebih tinggi dari SPK
"""

from parsers.spk_survey_parser import parse_spk_survey
from parsers.spk_instalasi_parser import parse_spk_instalasi
from parsers.spk_dismantle_parser import parse_spk_dismantle
from parsers.spk_aktivasi_parser import parse_spk_aktivasi
from parsers.checklist_wireless_parser import parse_checklist_wireless
from parsers.checklist_wireline_parser import parse_checklist_wireline
from parsers.Form_PM_POP.pm_dispatcher import dispatch_pm_parser, detect_pm_form_type


def detect_spk_type(all_text: str) -> str:
    """
    Deteksi jenis SPK/dokumen berdasarkan kata kunci di teks.
    
    🔧 FIXED Priority Order:
    1. Form PM POP (paling spesifik - ada kode FM-LAP-D2-SOP-003-XXX)
    2. Checklist (lebih spesifik dari SPK - ada kata "CHECKLIST")  ← DIPINDAH KE ATAS!
    3. SPK (lebih umum)
    
    Args:
        all_text: Teks lengkap dari PDF
        
    Returns:
        String jenis dokumen atau "unknown"
    """
    lower_text = all_text.lower()

    # ============================================
    # PRIORITY 1: CEK FORM PM POP DULU
    # ============================================
    pm_form_type = detect_pm_form_type(all_text)
    if pm_form_type:
        print(f"[DISPATCHER]  Terdeteksi sebagai Form PM: {pm_form_type}")
        return pm_form_type

    # ============================================
    # PRIORITY 2: CEK CHECKLIST (DIPINDAH KE ATAS!) 
    # Kenapa? Karena "FORM CHECKLIST MAINTENANCE REMOTE WIRELESS" 
    # juga mengandung kata "wireless" dan "aktivasi" yang bisa ke-trigger SPK
    # ============================================
    if "checklist" in lower_text and "wireline" in lower_text:
        print(f"[DISPATCHER]  Terdeteksi sebagai Checklist Wireline")
        return "checklist_wireline"
    
    elif "checklist" in lower_text and "wireless" in lower_text:
        print(f"[DISPATCHER]  Terdeteksi sebagai Checklist Wireless")
        return "checklist_wireless"
    
    # ============================================
    # PRIORITY 3: CEK SPK (prioritas lebih rendah)
    # ============================================
    elif "spk survey" in lower_text or ("survey" in lower_text and "spk" in lower_text):
        print(f"[DISPATCHER]  Terdeteksi sebagai SPK Survey")
        return "spk_survey"
    
    elif "spk instalasi" in lower_text or ("instalasi" in lower_text and "spk" in lower_text):
        print(f"[DISPATCHER]  Terdeteksi sebagai SPK Instalasi")
        return "spk_instalasi"
    
    elif "spk dismantle" in lower_text or ("dismantle" in lower_text and "spk" in lower_text):
        print(f"[DISPATCHER]  Terdeteksi sebagai SPK Dismantle")
        return "spk_dismantle"
    
    elif "spk aktivasi" in lower_text or ("aktivasi" in lower_text and "spk" in lower_text):
        print(f"[DISPATCHER]  Terdeteksi sebagai SPK Aktivasi")
        return "spk_aktivasi"
    
    else:
        print("[DISPATCHER] ⚠️ Jenis dokumen tidak terdeteksi dari teks")
        return "unknown"


# ============================================
# REST OF THE FILE (UNCHANGED)
# ============================================

def dispatch_parser(all_text: str, page_texts: list, ocr_data: list = None) -> dict:
    """Dispatcher utama - route dokumen ke parser yang sesuai."""
    print("\n" + "="*70)
    print(" DISPATCHER - Starting document detection...")
    print("="*70)
    
    if ocr_data:
        total_items = sum(len(page) for page in ocr_data) if isinstance(ocr_data, list) else 0
        print(f"[INFO] OCR data tersedia: {len(ocr_data)} halaman, {total_items} items total")
    else:
        print(f"[WARNING] OCR data tidak tersedia")

    doc_type = detect_spk_type(all_text)
    print(f"\n[RESULT] Document type detected: {doc_type}")
    
    # ROUTE 1: FORM PM POP
    if doc_type and doc_type.startswith("form_pm_"):
        print(f"\n[ROUTING] → PM Dispatcher")
        print(f"[INFO] Processing as Form PM POP...")
        
        try:
            pm_result = dispatch_pm_parser(all_text, page_texts, ocr_data)
            
            if "parsed" not in pm_result:
                normalized = {
                    "document_type": pm_result.get("document_type", doc_type),
                    "parsed": pm_result,
                    "metadata": {
                        "parser_used": "PMDispatcher",
                        "detection_method": "document_code",
                        "ocr_data_available": bool(ocr_data),
                        "parsing_status": pm_result.get("status", "success")
                    }
                }
                
                if "document_type" in normalized["parsed"]:
                    del normalized["parsed"]["document_type"]
                if "status" in normalized["parsed"]:
                    del normalized["parsed"]["status"]
                
                return normalized
            else:
                return pm_result
                
        except Exception as e:
            print(f"[ERROR] PM Parser failed: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "document_type": doc_type,
                "parsed": {},
                "metadata": {
                    "parser_used": "PMDispatcher",
                    "detection_method": "document_code",
                    "ocr_data_available": bool(ocr_data),
                    "parsing_status": "failed",
                    "error": str(e)
                }
            }

    # ROUTE 2: SPK & CHECKLIST
    parser_map = {
        "spk_survey": ("SPKSurveyParser", parse_spk_survey),
        "spk_instalasi": ("SPKInstalasiParser", parse_spk_instalasi),
        "spk_dismantle": ("SPKDismantleParser", parse_spk_dismantle),
        "spk_aktivasi": ("SPKAktivasiParser", parse_spk_aktivasi),
        "checklist_wireless": ("ChecklistWirelessParser", parse_checklist_wireless),
        "checklist_wireline": ("ChecklistWirelineParser", parse_checklist_wireline),
    }

    if doc_type in parser_map:
        parser_name, parser_func = parser_map[doc_type]
        print(f"\n[ROUTING] → {parser_name}")
        print(f"[INFO] Processing as {doc_type}...")
        
        try:
            import inspect
            sig = inspect.signature(parser_func)
            
            if 'ocr_data' in sig.parameters:
                print(f"[INFO] Calling {parser_name} dengan OCR data")
                parsed_data = parser_func(all_text, page_texts, ocr_data=ocr_data)
            else:
                print(f"[WARNING] {parser_name} belum support OCR data parameter")
                parsed_data = parser_func(all_text, page_texts)
            
            result = {
                "document_type": doc_type,
                "parsed": parsed_data,
                "metadata": {
                    "parser_used": parser_name,
                    "detection_method": "keyword",
                    "ocr_data_available": bool(ocr_data),
                    "parsing_status": "success"
                }
            }
            
            print(f"[SUCCESS]  Parsing completed!")
            return result
            
        except Exception as e:
            print(f"[ERROR]  Parser failed: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "document_type": doc_type,
                "parsed": {},
                "metadata": {
                    "parser_used": parser_name,
                    "detection_method": "keyword",
                    "ocr_data_available": bool(ocr_data),
                    "parsing_status": "failed",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
            }
    
    # ROUTE 3: UNKNOWN
    else:
        print(f"\n[WARNING] ⚠️ Document type not recognized or parser not available")
        return {
            "document_type": "unknown",
            "parsed": {},
            "metadata": {
                "parser_used": None,
                "detection_method": None,
                "ocr_data_available": bool(ocr_data),
                "parsing_status": "unknown_document_type",
                "detected_type": doc_type,
                "note": "Jenis dokumen tidak terdeteksi atau parser belum tersedia.",
                "text_sample": all_text[:500] + "..." if len(all_text) > 500 else all_text
            }
        }


def get_available_document_types() -> dict:
    """Daftar jenis dokumen yang didukung"""
    return {
        "spk": [
            "spk_survey",
            "spk_instalasi",
            "spk_dismantle",
            "spk_aktivasi"
        ],
        "checklist": [
            "checklist_wireline",
            "checklist_wireless"
        ],
        "form_pm": [
            "form_pm_1phase_ups",
            "form_pm_3phase_ups",
            "form_pm_genset",
            "form_pm_ac",
            "form_pm_inverter",
            "form_pm_ruang_shelter",
            "form_pm_rectifier",
            "form_pm_petir_grounding",
            "form_pm_instalasi_kabel",
            "form_pm_battery",
            "form_pm_pole_tower",
            "form_pm_dokumentasi_perangkat",
            "form_pm_permohonan_tindak_lanjut",
            "form_pm_tindak_lanjut",
            "form_pm_jadwal_sentral",
        ]
    }


def get_all_supported_types() -> list:
    """Flat list semua document types"""
    all_types = []
    for category, types in get_available_document_types().items():
        all_types.extend(types)
    return all_types


def validate_document_type(doc_type: str) -> bool:
    """Validasi apakah jenis dokumen didukung"""
    return doc_type in get_all_supported_types()


def get_parser_status(doc_type: str) -> dict:
    """Get status implementasi parser"""
    implemented = {
        "spk_survey": {"status": "active", "version": "1.0"},
        "spk_instalasi": {"status": "active", "version": "1.0"},
        "spk_dismantle": {"status": "active", "version": "1.0"},
        "spk_aktivasi": {"status": "active", "version": "1.0"},
        "checklist_wireless": {"status": "active", "version": "1.0"},
        "checklist_wireline": {"status": "active", "version": "1.0"},
        "form_pm_inverter": {"status": "active", "version": "1.0"},
    }
    
    if doc_type in implemented:
        return {
            "document_type": doc_type,
            **implemented[doc_type],
            "available": True
        }
    elif doc_type in get_all_supported_types():
        return {
            "document_type": doc_type,
            "status": "planned",
            "version": None,
            "available": False,
            "note": "Parser belum diimplementasi"
        }
    else:
        return {
            "document_type": doc_type,
            "status": "unknown",
            "version": None,
            "available": False,
            "note": "Document type tidak dikenali"
        }


def print_supported_documents():
    """Print daftar dokumen yang didukung"""
    print("\n" + "="*70)
    print("📋 SUPPORTED DOCUMENT TYPES")
    print("="*70)
    
    doc_types = get_available_document_types()
    
    for category, types in doc_types.items():
        print(f"\n {category.upper()}:")
        for doc_type in types:
            status_info = get_parser_status(doc_type)
            status_icon = "" if status_info["available"] else "🚧"
            print(f"   {status_icon} {doc_type}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    print_supported_documents()