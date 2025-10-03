from parsers.spk_survey_parser import parse_spk_survey
from parsers.spk_instalasi_parser import parse_spk_instalasi
from parsers.spk_dismantle_parser import parse_spk_dismantle

def detect_spk_type(all_text: str) -> str:
    """
    Deteksi jenis SPK berdasarkan kata kunci di teks.
    Return salah satu: survey / instalasi / dismantle / unknown
    """
    lower_text = all_text.lower()

    if "spk survey" in lower_text:
        return "survey"
    elif "spk instalasi" in lower_text:
        return "instalasi"
    elif "spk dismantle" in lower_text:
        return "dismantle"
    elif "spk aktivasi" in lower_text:
        return "aktivasi"
    elif "wireline" in lower_text:
        return "wireline"
    elif "maintenace remote wireless" in lower_text:
        return "maintenace remote wireless"
    else:
        return "unknown"


def dispatch_parser(all_text: str, page_texts: list[dict]) -> dict:
    """
    Dispatcher untuk arahkan teks ke parser sesuai jenis SPK.
    """
    spk_type = detect_spk_type(all_text)

    if spk_type == "survey":
        return parse_spk_survey(all_text, page_texts)
    elif spk_type == "instalasi":
        return parse_spk_instalasi(all_text, page_texts)
    elif spk_type == "dismantle":
        return parse_spk_dismantle(all_text, page_texts)
    else:
        return {
            "jenis_spk": "unknown",
            "data": {},
            "note": "Jenis SPK tidak terdeteksi. Perlu cek manual."
        }
