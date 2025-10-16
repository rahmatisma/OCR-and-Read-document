import re
from pprint import pprint


# ========== 1. PARSER UNTUK PERIZINAN & BIAYA KAWASAN ==========
def parse_perizinan_biaya_kawasan(text: str, labels: list[str]) -> dict:
    """Ekstrak bagian 'DATA PERIZINAN DAN BIAYA YANG TIMBUL DALAM KAWASAN'"""
    match_section = re.search(
        r"DATA\s*PERIZINAN\s*DAN\s*BIAYA\s*YANG\s*TIMBUL\s*DALAM\s*KAWASAN([\s\S]*?)(?=DATA\s*KAWASAN\s*UMUM|\Z)",
        text,
        re.IGNORECASE,
    )

    section_text = match_section.group(1) if match_section else text
    section_text = normalize_text(section_text)
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]

    data = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        matched_label = next(
            (lbl for lbl in labels if re.match(re.escape(lbl), line, re.IGNORECASE)),
            None,
        )

        if matched_label:
            key = normalize_key(matched_label)
            val = None

            # Cek horizontal
            horizontal_match = re.match(
                rf"{re.escape(matched_label)}\s*[:\-]?\s*(.+)", line, re.IGNORECASE
            )
            if horizontal_match and horizontal_match.group(1).strip():
                val = horizontal_match.group(1).strip()
            else:
                # Jika tidak, ambil baris berikutnya
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    is_next_label = any(
                        re.match(re.escape(l), next_line, re.IGNORECASE)
                        for l in labels
                    )
                    if not is_next_label and next_line:
                        val = next_line
                        i += 1

            data[key] = val
        i += 1

    return data

def parse_kawasan_umum(text: str, labels: list[str]) -> dict:
    """Ekstrak bagian 'DATA KAWASAN UMUM'"""
    match_section = re.search(
        r"DATA\s*KAWASAN\s*UMUM([\s\S]*?)(?=DATA\s*JALUR\s*KABEL|\Z)",
        text,
        re.IGNORECASE,
    )

    section_text = match_section.group(1) if match_section else text
    section_text = normalize_text(section_text)
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]

    data = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        matched_label = next(
            (lbl for lbl in labels if re.match(re.escape(lbl), line, re.IGNORECASE)),
            None,
        )

        if matched_label:
            key = normalize_key(matched_label)
            val = None

            horizontal_match = re.match(
                rf"{re.escape(matched_label)}\s*[:\-]?\s*(.+)", line, re.IGNORECASE
            )
            if horizontal_match and horizontal_match.group(1).strip():
                val = horizontal_match.group(1).strip()
            else:
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    is_next_label = any(
                        re.match(re.escape(l), next_line, re.IGNORECASE)
                        for l in labels
                    )
                    if not is_next_label and next_line:
                        val = next_line
                        i += 1
            data[key] = val
        i += 1

    return data


# ========== 3. NORMALISASI TEKS & LABEL ==========
def normalize_text(text: str) -> str:
    """Membersihkan teks agar lebih mudah diproses"""
    text = re.sub(r"[\r\t]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text


def normalize_key(label: str) -> str:
    """Ubah label jadi key aman untuk dict"""
    return (
        label.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
        .replace("-", "_")
    )


# ========== 4. DEBUGING UTAMA ==========
def debuging(all_text: str, page_number: int) -> dict:
    """Gabungkan parser kawasan private dan kawasan umum"""
    data = {
        "perizinan_biaya_kawasan": {},
        "kawasan_umum": {},
    }

    labels_perizinan_biaya_kawasan = [
        "Melewati kawasan private",
        "Nama Kawasan",
        "PIC Kawasan",
        "Kontak PIC Kawasan",
        "Panjang Kabel dalam Kawasan",
        "Pelaksana Penarikan Kabel dalam Kawasan",
        "Deposit Kerja",
        "Supervisi",
        "Biaya Penarikan Kabel dalam Kawasan",
        "Biaya Sewa",
        "Biaya lain…",
        "Info Lain - Lain (Jika Ada)",
    ]

    labels_kawasan_umum = [
        "Nama Kawasan Umum / PU yang dilewati",
        "Panjang Jalur Outdoor di Kawasan Umum",
    ]

    data["perizinan_biaya_kawasan"] = parse_perizinan_biaya_kawasan(
        all_text, labels_perizinan_biaya_kawasan
    )

    data["kawasan_umum"] = parse_kawasan_umum(all_text, labels_kawasan_umum)

    pprint(data)
    return data
