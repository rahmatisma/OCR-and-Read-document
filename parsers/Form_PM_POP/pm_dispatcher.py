"""
PM Dispatcher - Deteksi dan routing untuk 14 Form PM POP
Taruh file ini di: parsers/Form_PM_POP/pm_dispatcher.py
"""

from typing import Dict, Optional


# Mapping judul form ke document type
FORM_PM_TITLES = {
    "Preventive Maintenance 1 Phase UPS": "form_pm_1phase_ups",
    "Preventive Maintenance 3 Phase UPS": "form_pm_3phase_ups",
    "Preventive Maintenance AC": "form_pm_ac",
    "Permohonan Tindak Lanjut Preventive Maintenance": "form_pm_permohonan_tindak_lanjut",
    "Tindak Lanjut Preventive Maintenance": "form_pm_tindak_lanjut",
    "Preventive Maintenance Genset": "form_pm_genset",
    "Jadwal Preventive Maintenance Sentral": "form_pm_jadwal_sentral",
    "Preventive Maintenance Inverter -48VDC-220VAC": "form_pm_inverter",
    "Preventive Maintenance Ruang Shelter": "form_pm_ruang_shelter",
    "Preventive Maintenance Rectifier": "form_pm_rectifier",
    "Preventive Maintenance Petir dan Grounding": "form_pm_petir_grounding",
    "Preventive Maintenance Instalasi Kabel dan Panel Distribusi": "form_pm_instalasi_kabel",
    "Preventive Maintenance Battery": "form_pm_battery",
    "Dokumentasi dan Pendataan Perangkat": "form_pm_dokumentasi_perangkat",
}


def detect_pm_form_type(text: str) -> Optional[str]:
    """
    Deteksi jenis form PM dari teks dokumen
    
    Args:
        text: Teks dokumen (biasanya all_text)
    
    Returns:
        document_type string atau None jika tidak terdeteksi
    
    Contoh:
        >>> detect_pm_form_type("Formulir Preventive Maintenance 1 Phase UPS")
        'form_pm_1phase_ups'
    """
    text_lower = text.lower()
    
    # Cari pattern "Formulir [Judul Form]"
    for title, doc_type in FORM_PM_TITLES.items():
        if title.lower() in text_lower:
            print(f"[PM Dispatcher] Terdeteksi: {doc_type}")
            return doc_type
    
    # Fallback: cek apakah ada kode dokumen FM-LAP-D2-SOP-003-XXX
    import re
    kode_match = re.search(r"FM-LAP-D2-SOP-003-(\d{3})", text)
    if kode_match:
        kode = kode_match.group(1)
        print(f"[PM Dispatcher] Terdeteksi kode form: FM-LAP-D2-SOP-003-{kode}")
        
        # Mapping kode ke document type
        kode_mapping = {
            "001": "form_pm_1phase_ups",
            "002": "form_pm_3phase_ups",
            "003": "form_pm_ac",
            "004": "form_pm_permohonan_tindak_lanjut",
            "005": "form_pm_tindak_lanjut",
            "006": "form_pm_genset",
            "007": "form_pm_jadwal_sentral",
            "008": "form_pm_inverter",
            "009": "form_pm_ruang_shelter",
            "010": "form_pm_rectifier",
            "011": "form_pm_petir_grounding",
            "012": "form_pm_instalasi_kabel",
            "013": "form_pm_battery",
            "014": "form_pm_dokumentasi_perangkat",
        }
        return kode_mapping.get(kode)
    
    return None


def dispatch_pm_parser(all_text: str, page_texts: list, ocr_data: list = None) -> dict:
    """
    Dispatch ke parser PM yang sesuai berdasarkan jenis form
    
    Args:
        all_text: Full text dari dokumen
        page_texts: List text per halaman
        ocr_data: Data OCR (opsional)
    
    Returns:
        Dictionary hasil parsing dengan key 'document_type' dan data lainnya
    """
    # Deteksi jenis form
    doc_type = detect_pm_form_type(all_text)
    
    if not doc_type:
        return {
            "document_type": "unknown",
            "error": "Form PM tidak terdeteksi",
            "raw_text": all_text[:500]  # Sample untuk debugging
        }
    
    # Import parser yang sesuai
    try:
        if doc_type == "form_pm_1phase_ups":
            from .pm_1phase_ups_parser import PM1PhaseUPSParser
            parser = PM1PhaseUPSParser(all_text, page_texts, ocr_data)
            result = parser.parse()
            
        elif doc_type == "form_pm_3phase_ups":
            from .pm_3phase_ups_parser import PM3PhaseUPSParser
            parser = PM3PhaseUPSParser(all_text, page_texts, ocr_data)
            result = parser.parse()
            
        elif doc_type == "form_pm_ac":
            from .pm_ac_parser import PMACParser
            parser = PMACParser(all_text, page_texts, ocr_data)
            result = parser.parse()
            
        # TODO: Tambahkan elif untuk 11 form PM lainnya
        # elif doc_type == "form_pm_permohonan_tindak_lanjut":
        #     from .pm_permohonan_tindak_lanjut_parser import PMPermohonanTindakLanjutParser
        #     ...
        
        else:
            # Parser belum dibuat
            return {
                "document_type": doc_type,
                "error": f"Parser untuk {doc_type} belum dibuat",
                "status": "pending_implementation"
            }
        
        # Tambahkan document_type ke result
        result["document_type"] = doc_type
        return result
        
    except ImportError as e:
        return {
            "document_type": doc_type,
            "error": f"Parser belum dibuat: {str(e)}",
            "status": "pending_implementation"
        }
    except Exception as e:
        return {
            "document_type": doc_type,
            "error": f"Error saat parsing: {str(e)}",
            "status": "parsing_error"
        }