"""
PM Dispatcher - IMPROVED VERSION
 Unified output format dengan main dispatcher
"""

from typing import Dict, Optional
import re


# Mapping judul form ke document type
FORM_PM_TITLES = {
    "Preventive Maintenance 1 Phase UPS": "form_pm_1phase_ups",
    "Preventive Maintenance 3 Phase UPS": "form_pm_3phase_ups",
    "Preventive Maintenance AC": "form_pm_ac",
    "Permohonan Tindak Lanjut Preventive Maintenance": "form_pm_permohonan_tindak_lanjut",
    "Tindak Lanjut Preventive Maintenance": "form_pm_tindak_lanjut",
    "Preventive Maintenance Genset": "form_pm_genset",
    "Jadwal Preventive Maintenance Sentral": "form_pm_jadwal_sentral",
    "Preventive Maintenance Inverter -48VDC": "form_pm_inverter",
    "Preventive Maintenance Inverter -48VDC/220VAC": "form_pm_inverter",
    "Preventive Maintenance Shelter Room": "form_pm_ruang_shelter",
    "Preventive Maintenance Ruang Shelter": "form_pm_ruang_shelter",
    "Preventive Maintenance Rectifier": "form_pm_rectifier",
    "Preventive Maintenance Lightning Protection": "form_pm_petir_grounding",
    "Preventive Maintenance Petir dan Grounding": "form_pm_petir_grounding",
    "Preventive Cable Installation": "form_pm_instalasi_kabel",
    "Preventive Maintenance Instalasi Kabel": "form_pm_instalasi_kabel",
    "Preventive Maintenance Battery": "form_pm_battery",
    "Preventive Maintenance Pole": "form_pm_pole_tower",
    "Preventive Maintenance Tower": "form_pm_pole_tower",
    "Preventive Maintenance Inventory Device": "form_pm_dokumentasi_perangkat",
    "Dokumentasi dan Pendataan Perangkat": "form_pm_dokumentasi_perangkat",
}


def detect_pm_form_type(text: str) -> Optional[str]:
    """
    Deteksi jenis form PM dari teks dokumen
    
    Detection priority:
    1. Document code (FM-LAP-D2-SOP-003-XXX) - most reliable
    2. Form title keyword matching
    
    Args:
        text: Teks dokumen (biasanya all_text)
    
    Returns:
        document_type string atau None jika tidak terdeteksi
    """
    text_lower = text.lower()
    
    #  PRIORITY 1: Cek kode dokumen FM-LAP-D2-SOP-003-XXX (PALING RELIABLE)
    # NOTE: Handle spasi di "FM-LAP- D2" (ada spasi setelah LAP-)
    kode_match = re.search(r"FM-LAP-?\s*D2-SOP-003-(\d{3})", text)
    if kode_match:
        kode = kode_match.group(1)
        print(f"[PM Dispatcher] Terdeteksi kode form: FM-LAP-D2-SOP-003-{kode}")
        
        # Mapping kode ke document type
        kode_mapping = {
            "001": "form_pm_1phase_ups",              # 1 Phase UPS
            "002": "form_pm_3phase_ups",              # 3 Phase UPS  
            "003": "form_pm_genset",                  # Genset
            "004": "form_pm_ac",                      # AC
            "005": "form_pm_inverter",                # Inverter -48VDC/220VAC 
            "006": "form_pm_ruang_shelter",           # Shelter Room / ODC
            "007": "form_pm_rectifier",               # Rectifier
            "008": "form_pm_petir_grounding",         # Lightning Protection & Grounding
            "009": "form_pm_instalasi_kabel",         # Cable Installation & Distribution Panel
            "010": "form_pm_battery",                 # Battery
            "011": "form_pm_pole_tower",              # Pole / Tower
            "012": "form_pm_dokumentasi_perangkat",   # Inventory Device
            "013": "form_pm_permohonan_tindak_lanjut", # Permohonan Tindak Lanjut
            "014": "form_pm_tindak_lanjut",           # Tindak Lanjut
            "015": "form_pm_jadwal_sentral",          # Jadwal PM Sentral
        }
        
        detected = kode_mapping.get(kode)
        if detected:
            print(f"[PM Dispatcher]  Mapped to: {detected}")
            return detected
        else:
            print(f"[PM Dispatcher] ⚠️ Kode {kode} tidak dikenali dalam mapping")
    
    #  PRIORITY 2: Fallback ke title matching
    for title, doc_type in FORM_PM_TITLES.items():
        if title.lower() in text_lower:
            print(f"[PM Dispatcher]  Terdeteksi dari title: {doc_type}")
            return doc_type
    
    return None


def dispatch_pm_parser(all_text: str, page_texts: list, ocr_data: list = None) -> dict:
    """
    Dispatch ke parser PM yang sesuai berdasarkan jenis form
    
     UNIFIED OUTPUT FORMAT:
    {
        "document_type": "form_pm_inverter",
        "parsed": { ... semua data parsing ... },
        "metadata": {
            "parser_used": "PMInverterParser",
            "detection_method": "document_code",
            "ocr_data_available": true/false,
            "parsing_status": "success" | "failed" | "not_implemented"
        }
    }
    
    Args:
        all_text: Full text dari dokumen
        page_texts: List text per halaman
        ocr_data: Data OCR (opsional)
    
    Returns:
        Dictionary hasil parsing dengan format unified
    """
    # Deteksi jenis form
    doc_type = detect_pm_form_type(all_text)
    
    if not doc_type:
        return {
            "document_type": "unknown",
            "parsed": {},
            "metadata": {
                "parser_used": None,
                "detection_method": None,
                "ocr_data_available": bool(ocr_data),
                "parsing_status": "detection_failed",
                "error": "Form PM tidak terdeteksi",
                "text_sample": all_text[:500]
            }
        }
    
    #  IMPORT DAN JALANKAN PARSER
    try:
        parser_instance = None
        parser_name = None
        
        #  PM INVERTER (ACTIVE)
        if doc_type == "form_pm_inverter":
            from .pm_inverter_parser import PMInverterParser
            parser_name = "PMInverterParser"
            parser_instance = PMInverterParser(all_text, page_texts, ocr_data)

        elif doc_type == "form_pm_ruang_shelter":
            from .pm_ruang_shelter_parser import PMRuangShelterParser
            parser_name = "PMRuangShelterParser"
            parser_instance = PMRuangShelterParser(all_text, page_texts, ocr_data)
        
        elif doc_type == "form_pm_rectifier":
            from .pm_rectifier_parser import PMRectifierParser
            parser_name = "PMRectifierParser"
            parser_instance = PMRectifierParser(all_text, page_texts, ocr_data)

        elif doc_type == "form_pm_petir_grounding":
            from .pm_petir_grounding_parser import PMLightningGroundingParser
            parser_name = "PMLightningGroundingParser"
            parser_instance = PMLightningGroundingParser(all_text, page_texts, ocr_data)
        
        elif doc_type == "form_pm_instalasi_kabel":
            from .pm_instalasi_kabel_panel_distribusi_parser import PMInstalasiKabelPanelDistribusiParser
            parser_name = "PMInstalasiKabelPanelDistribusiParser"
            parser_instance = PMInstalasiKabelPanelDistribusiParser(all_text, page_texts, ocr_data)
        
        elif doc_type == "form_pm_battery":
            from .pm_battery_parser import PMBatteryParser
            parser_name = "PMBatteryParser"
            parser_instance = PMBatteryParser(all_text, page_texts, ocr_data)

        elif doc_type == "form_pm_pole_tower":
            from .pm_pole_tower_parser import PMPoleTowerParser
            parser_name = "PMPoleTowerParser"
            parser_instance = PMPoleTowerParser(all_text, page_texts, ocr_data)

        elif doc_type == "form_pm_dokumentasi_perangkat":
            from .pm_dokumentasi_pendataan_perangkat_parser import PMDokumentasiPendataanPerangkatParser
            parser_name = "PMDokumentasiPendataanPerangkatParser"
            parser_instance = PMDokumentasiPendataanPerangkatParser(all_text, page_texts, ocr_data)

        elif doc_type == "form_pm_ac":
            from .pm_ac_parser import PMACParser
            parser_name = "PMACParser"
            parser_instance = PMACParser(all_text, page_texts, ocr_data)

        # 🚧 Parser lainnya (belum dibuat)
        elif doc_type == "form_pm_1phase_ups":
            from .pm_1phase_ups_parser import PM1PhaseUPSParser
            parser_name = "PM1PhaseUPSParser"
            parser_instance = PM1PhaseUPSParser(all_text, page_texts, ocr_data)
            
        elif doc_type == "form_pm_3phase_ups":
            from .pm_3phase_ups_parser import PM3PhaseUPSParser
            parser_name = "PM3PhaseUPSParser"
            parser_instance = PM3PhaseUPSParser(all_text, page_texts, ocr_data)
            
        
        
        else:
            # Parser belum dibuat
            return {
                "document_type": doc_type,
                "parsed": {},
                "metadata": {
                    "parser_used": None,
                    "detection_method": "document_code",
                    "ocr_data_available": bool(ocr_data),
                    "parsing_status": "not_implemented",
                    "error": f"Parser untuk {doc_type} belum dibuat",
                    "note": "Silakan buat parser berdasarkan template pm_inverter_parser.py"
                }
            }
        
        # Jalankan parser
        print(f"[PM Dispatcher]  Using {parser_name}")
        parsed_data = parser_instance.parse()
        
        # Extract document code dari text (bukan dari parser result)
        doc_code_match = re.search(r"(FM-LAP-?\s*D2-SOP-003-\d{3})", all_text)
        doc_code = doc_code_match.group(1) if doc_code_match else None
        
        #  UNIFIED OUTPUT FORMAT
        result = {
            "document_type": doc_type,
            "parsed": parsed_data,
            "metadata": {
                "parser_used": parser_name,
                "detection_method": "document_code",
                "document_code": doc_code,
                "ocr_data_available": bool(ocr_data),
                "parsing_status": "success"
            }
        }
        
        return result
        
    except ImportError as e:
        print(f"[PM Dispatcher]  Import Error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "document_type": doc_type,
            "parsed": {},
            "metadata": {
                "parser_used": None,
                "detection_method": "document_code",
                "ocr_data_available": bool(ocr_data),
                "parsing_status": "not_implemented",
                "error": f"Parser belum dibuat: {str(e)}",
                "traceback": traceback.format_exc()
            }
        }
        
    except Exception as e:
        print(f"[PM Dispatcher]  Parsing Error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "document_type": doc_type,
            "parsed": {},
            "metadata": {
                "parser_used": parser_name,
                "detection_method": "document_code",
                "ocr_data_available": bool(ocr_data),
                "parsing_status": "failed",
                "error": f"Error saat parsing: {str(e)}",
                "traceback": traceback.format_exc()
            }
        }