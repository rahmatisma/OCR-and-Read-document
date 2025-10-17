import re
from pprint import pprint

def normalize_text(raw_text: str) -> str:
    """
    Bersihkan teks hasil OCR, ubah semua jenis minus ke ASCII '-'
    """
    # Ganti semua bentuk dash atau minus Unicode ke tanda minus biasa
    raw_text = raw_text.replace("−", "-").replace("–", "-").replace("—", "-").replace("―", "-")
    return raw_text

def parse_spk_survey(all_text: str):
    all_text = normalize_text(all_text)

    data = {
        "vendor": {
            "teknisi": None,
            "nama_vendor": None,
            "pic_pelanggan": None,
            "kontak_pic_pelanggan": None,
            "latitude": None,
            "longitude": None
        }
    }

    # 🔹 Ambil koordinat
    match = re.search(
        r"Koordinat\s*[\r\n\s]+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)",
        all_text,
        re.IGNORECASE
    )
    if match:
        data["vendor"]["latitude"] = match.group(1)
        data["vendor"]["longitude"] = match.group(2)

    # 🔹 Ambil PIC pelanggan
    match = re.search(
        r"PIC\s+Pelanggan[^\n]*\n\s*(.*?)\s*\n\s*Kontak\s+PIC\s+Pelanggan",
        all_text,
        re.IGNORECASE | re.DOTALL
    )
    if match:
        data["vendor"]["pic_pelanggan"] = match.group(1).strip()

    # 🔹 Ambil kontak PIC
    match = re.search(
        r"Kontak\s+PIC\s+Pelanggan\s*[:\-]?\s*[\r\n\s]*([0-9\+\-\(\) ]+)",
        all_text,
        re.IGNORECASE
    )
    if match:
        data["vendor"]["kontak_pic_pelanggan"] = match.group(1).strip()

    # 🔹 Ambil pelaksana dan vendor
    match = re.search(
        r"Pelaksana\s+Survey\s+dari\s+Tim\s+Vendor\s*[:\-]?\s*[\r\n\s]*(.+?)\s+Vendor\s*[:\-]?\s*[\r\n\s]*([A-Za-z0-9\s]+?)(?=\s*\n\s*INFORMASI|$)",
        all_text,
        re.IGNORECASE | re.DOTALL
    )
    if match:
        teknisi_raw = match.group(1).strip()
        vendor_raw = match.group(2).strip()

        if vendor_raw and teknisi_raw.upper().endswith(vendor_raw.upper()):
            teknisi_raw = teknisi_raw[: -len(vendor_raw)].strip()

        data["vendor"]["teknisi"] = teknisi_raw
        data["vendor"]["nama_vendor"] = vendor_raw

    return data
def debuging(all_text: str, page_number: int):
    # print (all_text)
    # exit()
    data = {}
    data["vendor_info"] = parse_spk_survey(all_text)
    print(f"\n📄 Hasil Parsing Halaman {page_number}")
    pprint(data)
    return data