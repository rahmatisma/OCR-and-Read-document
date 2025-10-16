import re

def normalize_text(raw_text: str) -> str:
    """
    Normalisasi teks supaya 'Key\\n:\\nValue' jadi 'Key: Value'
    dan jika kosong tetap 'Key:'.
    """
    # Gabungkan pola "Key\n:\nValue" atau "Key\n: Value" jadi satu baris
    text = re.sub(r"([A-Za-z0-9\.\s]+)\n\s*:\s*\n\s*", r"\1: ", raw_text)
    text = re.sub(r"([A-Za-z0-9\.\s]+)\n\s*:\s*", r"\1: ", text)
    # Hapus spasi berlebih di awal/akhir tiap baris
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines)


def parse_spk_survey(all_text: str, page_texts: list[str], ttd_results: dict = None, doc_results: dict = None) -> dict:
    all_text = normalize_text(all_text)
    ttd_results = ttd_results or {}
    doc_results = doc_results or {}

    # print(all_text)
    # exit()
    
    data = {
        "spk": {},
        "pelanggan": {},
        "jaringan": {},
        "pelaksanaan": {},
        "tanda_tangan": [],  # list of {peran, nama, path_ttd}
        "vendor": {},
        "informasi_gedung": {},
        "sarpen_ruang_server": {},
        "lokasi_antena": {},
        "perizinan_biaya_gedung": {},
        "penempatan_perangkat": {},
        "perizinan_biaya_kawasan": {},
        "kawasan_umum": {},
        "data_splitter": {},
        "data_hh": [],
        "plan_jalur_dalam_gedung": None,
        "dokumentasi": [],   # list of {jenis, path_foto, keterangan}
        "time_frame_pekerja": {},
        "berita_acara": {},

    }

    # === PARSING TEKS ===
    data["spk"]["judul_spk"] = search_regex(r"(BERITA\s+ACARA|SURAT\s+PERINTAH(?:\s+KERJA)?)", all_text)
    data["spk"]["tipe_spk"] = "spk survey"
    data["spk"]["no_spk"] = search_regex(r"Nomor\s*:\s*([^\n]*)", all_text)
    data["spk"]["tanggal_spk"] = search_regex(r"Tanggal\s*:\s*([^\n]*)", all_text)
    data["spk"]["no_fps"] = search_regex(r"No\.?\s*FPS\s*:\s*([^\n]*)", all_text)

    data["pelanggan"]["nama_pelanggan"] = search_regex(r"Nama\s*Pelanggan\s*:\s*([^\n]*)", all_text)
    data["pelanggan"]["lokasi_pelanggan"] = search_regex(r"Lokasi\s*Pelanggan\s*:\s*([^\n]*)", all_text)
    data["pelanggan"]["kontak_person"] = search_regex(r"Kontak\s*Person\s*:\s*([^\n]*)", all_text)
    data["pelanggan"]["telepon"] = search_regex(r"Telepon\s*:\s*([0-9]+)", all_text)

    data["jaringan"]["no_jaringan"] = search_regex(r"No\.?\s*Jaringan\s*:\s*([^\n]*)", all_text)
    data["jaringan"]["jasa"] = search_regex(r"Jasa\s*:\s*([^\n]*)", all_text)
    data["jaringan"]["manage_router"] = search_regex(r"Manage\s*Router\s*:\s*([^\n]*)", all_text)
    data["jaringan"]["opsi_router"] = search_regex(r"Opsi\s*Router\s*(?:1|2|3)\s*:\s*([^\n]*)", all_text)
    data["jaringan"]["ip_lan"] = search_regex(r"IP\s*LAN\s*:\s*([^\n]*)", all_text)
    data["jaringan"]["tgl_rfs_la"] = search_regex(r"Tgl\.RFS LA\s*:\s*([^\n]*)", all_text)
    data["jaringan"]["tgl_rfs_plg"] = search_regex(r"Tgl\.RFS PLG\s*:\s*([^\n]*)", all_text)
    data["jaringan"]["media_akses"] = search_regex(r"Media\s*Akses\s*:\s*([^\n]*)", all_text)
    data["jaringan"]["pop"] = search_regex(r"POP\s*:\s*(.*?)(?=\n[A-Z][A-Za-z ]*?:)", all_text, allow_multiline=True)
    data["jaringan"]["kecepatan"] = search_regex(r"Kecepatan\s*:\s*([^\n]*)", all_text)

    waktu_matches = re.findall(r"\d{2}/[A-Za-z]{3}/\d{4}\s+\d{2}:\d{2}", all_text)
    data["pelaksanaan"] = {
        "permintaan_pelanggan": waktu_matches[0] if len(waktu_matches) > 0 else "",
        "datang": waktu_matches[1] if len(waktu_matches) > 1 else "",
        "selesai": waktu_matches[2] if len(waktu_matches) > 2 else "",
    }

    data["vendor"]["teknisi"] = search_regex(r"Pelaksana\s+Survey\s+dari\s+Tim\s+Vendor\s*:?\s*(.*?)(?=\n[A-Z][A-Za-z ]*?:|\nVendor|\Z)", all_text)
    data["vendor"]["nama_vendor"] = search_regex(r"^[ \t]*Vendor\s*:?\s*(?:\n\s*)?([^\n]+)", all_text)

    labels = [
        "Status Gedung",
        "Kondisi Gedung",
        "Pemilik Bangunan",
        "Alamat",
        "Kontak Person",
        "Bagian / Jabatan",
        "Telpon / Fax",
        "Email",
        "Jumlah Lantai Gedung",
        "Pelanggan bersedia dipasang perangkat",
        "Penempatan Antena",
        "Sewa space antena",
        "Sewa shaft kabel",
        "Biaya IKG",
        "Penanggungjawab pengurusan dan pembayaran sewa"
    ]

    result = parse_informasi_gedung(all_text, labels)

    # Format hasil ke bentuk snake_case untuk key JSON
    for k, v in result.items():
        key = (normalize_key(k))
            
        data["informasi_gedung"][key] = v

    # laber sarpen
    labels_sarpen = [
        "Power Line / Listrik",
        "Ketersediaan Power Outlet untuk OTB, Modem, dan Router",
        "Info Kelistrikan (PLN P-N)",
        "Info Kelistrikan (PLN P-G)",
        "Info Kelistrikan (PLN N-G)",
        "Grounding Listrik",
        "UPS",
        "Ruangan Ber AC",
        "Suhu Ruangan",
        "1. Lantai",
        "2. Ruang",
        "Perangkat Pelanggan"
    ]
    match_sarpen = re.search(
        r"INFORMASI SARPEN DAN RUANG SERVER PELANGGAN([\s\S]*?Perangkat Pelanggan[\s\S]*?)(?=$)",
        all_text, re.IGNORECASE
    )

    for lbl in labels_sarpen:
        key = normalize_key(lbl)
        val = parse_sarpen(all_text, labels_sarpen, lbl, match_sarpen)
        data["sarpen_ruang_server"][key] = val

    # Lokasi Antena
    labels_lokasi = [
        "Lokasi Antena",
        "Detail Lokasi Antena",
        "Space Tersedia",
        "Akses di lokasi perlu alat bantu",
        "Penangkal Petir",
        "Tinggi Penangkal Petir",
        "Jarak ke lokasi antena",
        "Tindak Lanjut",
        "Tower / Pole",
        "Pemilik Tower / Pole"
    ]
    data["lokasi_antena"] = parse_lokasi_antena(all_text, labels_lokasi)

    # Perizinan & Biaya Gedung
    labels_perizinan_biaya = [
        "PIC BM",
        "Kontak PIC BM",
        "Material dan Infrastruktur",
        "Panjang Kabel dalam Gedung",
        "Pelaksana Penarikan Kabel dalam Gedung",
        "Waktu Pelaksanaan Penarikan Kabel",
        "Supervisi",
        "Deposit Kerja",
        "IKG (Instalasi Kabel Gedung)",
        "Biaya Sewa",
        "Biaya lain…",
        "Info Lain - Lain (Jika Ada)"
    ]
    data["perizinan_biaya_gedung"] = parse_perizinan_biaya_gedung(all_text, labels_perizinan_biaya)

    # Penempatan Perangkat
    labels_penempatan_perangkat = [
        "Lokasi Penempatan Modem dan Router",
        "Kesiapan Ruang Server",
        "Ketersedian Rak Server",
        "Space Modem dan Router",
        "Diizinkan Foto Ruang Server Pelanggan"
    ]
    
    data["penempatan_perangkat"] = parse_penempatan_perangkat(all_text, labels_penempatan_perangkat)

    # Perizinan Biaya Kawasan
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
    data["perizinan_biaya_kawasan"] = parse_perizinan_biaya_kawasan(all_text, labels_perizinan_biaya_kawasan)

    # Perizinan Biaya Kawasan - tambahan
    labels_kawasan_umum = [
        "Nama Kawasan Umum / PU yang dilewati",
        "Panjang Jalur Outdoor di Kawasan Umum",
    ]

    data["kawasan_umum"] = parse_kawasan_umum(all_text, labels_kawasan_umum)

    # Data Splitter
    labels_splitter = [
        "Lokasi Splitter",
        "ID Splitter",
        "Kapasitas Splitter",
        "Jumlah Port Kosong",
        "List Port Kosong dan Redaman",
        "Nama Node (Jika tidak ada Splitter)",
        "List port kosong",
        "Arah Akses",
    ]

    data["data_splitter"] = parse_data_splitter(all_text, labels_splitter)

    data["data_hh"] = parse_multiple_hh(all_text)

    if "PLAN JALUR DALAM GEDUNG" in all_text:
        data["plan_jalur_dalam_gedung"] = "Tersedia (lihat halaman terkait)"

    data["berita_acara"]["judul_spk"] = "BERITA ACARA"
    data["berita_acara"]["tipe_spk"] = "survey"
    data["berita_acara"]["nomor_spk"] = search_regex(r"Nomor\s*SPK\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["tanggal"] = search_regex(r"Tanggal\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["nama_pelanggan"] = search_regex(r"Nama\s*Pelanggan\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["no_jaringan"] = search_regex(r"No\.?\s*Jaringan\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["no_fps"] = search_regex(r"No\.?\s*FPS\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["jasa"] = search_regex(r"Jasa\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["manage_router"] = search_regex(r"Manage\s*Router\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["opsi_router"] = search_regex(r"Opsi\s*Router\s*1/2/3\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["ip_lan"] = search_regex(r"IP\s*LAN\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["tgl_rfs_la"] = search_regex(r"Tgl\.?RFS\s*LA\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["tgl_rfs_pelanggan"] = search_regex(r"Tgl\.?RFS\s*PLG\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["lokasi_pelanggan"] = search_regex(r"Lokasi\s*Pelanggan\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["jenis_survey"] = search_regex(r"Jenis\s*Survey\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["media_akses"] = search_regex(r"Media\s*Akses\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["pop"] = search_regex(r"POP\s*:\s*(.*?)(?=\n[A-Z][A-Za-z ]*?:)", all_text, allow_multiline=True)
    data["berita_acara"]["kecepatan"] = search_regex(r"Kecepatan\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["kontak_person"] = search_regex(r"Kontak\s*Person\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["telepon"] = search_regex(r"Telepon\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["waktu_pelaksanaan_perm_pelanggan"] = search_regex(r"Permintaan\s*Pelanggan\s*([^\n]*)", all_text)
    data["berita_acara"]["waktu_pelaksanaan_datang"] = search_regex(r"Datang\s*([^\n]*)", all_text)
    data["berita_acara"]["waktu_pelaksanaan_selesai"] = search_regex(r"Selesai\s*([^\n]*)", all_text)

    data["dokumentasi"] = parse_dokumentasi(doc_results)


    return data


def parse_dokumentasi(doc_results):
    """
    Mengubah hasil deteksi dokumentasi menjadi format seragam.
    Input doc_results: list hasil processor, misal [{'jenis': 'foto lokasi', 'path_foto': '...', 'keterangan': '...'}]
    """
    hasil = []
    for doc in doc_results.get("dokumentasi", []):
        hasil.append({
            "jenis": doc.get("jenis"),
            "path_foto": doc.get("path_foto"),
            "keterangan": doc.get("keterangan")
        })
    return hasil

def search_regex(pattern, text, allow_multiline=False):
    """
    Fungsi pencarian regex yang lebih tangguh untuk hasil OCR PDF.
    
    Fitur:
    - Jika allow_multiline=True, maka newline dianggap spasi (untuk teks panjang seperti alamat).
    - Jika hasil regex kosong, otomatis mencari nilai di baris berikutnya.
    - Jika value berisi label lain (mengandung ':' di awal), hasil dianggap tidak valid.
    """

    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if not match:
        return None

    value = match.group(1).strip()

    # Jika hasil kosong → coba ambil dari baris berikutnya
    if not value:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if re.search(pattern, line, re.IGNORECASE):
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Jangan ambil label baru (biasanya diakhiri ':')
                    if next_line and not re.match(r"^[A-Za-z ]+:?$", next_line):
                        return next_line
        return None

    # Kalau multiline tidak diizinkan → hasil dengan newline dianggap tidak valid
    if not allow_multiline and "\n" in value:
        return None

    # Jika multiline diizinkan → ubah newline jadi spasi
    if allow_multiline:
        value = re.sub(r"\s*\n\s*", " ", value).strip()

    # Hindari hasil yang sebenarnya label baru
    if ":" in value and not allow_multiline:
        return None

    return value


def parse_multiple_hh(text: str):
    """
    Parsing data HH (handhole) yang bisa muncul berulang di dokumen.
    Contoh pola teks yang didukung:
    Data HH 1
    Lokasi HH-1 Jl. Contoh No. 123
    Longitude 106.12345
    Latitude -6.12345
    """
    hh_list = []
    # Pola diperbaiki agar lebih toleran terhadap spasi, newline, dan urutan teks
    pattern = (
        r"Data\s*HH\s*(\d+).*?"           # Tangkap nomor HH
        r"Lokasi\s*HH-?\1\s*([^\n\r]*)"   # Tangkap lokasi
        r".*?Longitude[^0-9\-]*([0-9\.\-]+)"  # Tangkap longitude
        r".*?Latitude[^0-9\-]*([0-9\.\-]+)"   # Tangkap latitude
    )

    for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
        hh_list.append({
            "nama_hh": f"HH-{match.group(1)}",
            "lokasi_hh": match.group(2).strip(),
            "longitude": match.group(3),
            "latitude": match.group(4)
        })

    return hh_list

def normalize_key(label: str) -> str:
    return (
        label.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
        .replace("-", "_")
        .replace("bersedia_dipasang_perangkat", "fo")
        .replace("penanggungjawab_pengurusan_dan_pembayaran_sewa", "penanggungjawab_sewa")
    )

def parse_informasi_gedung(text: str, labels: list[str]) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    data = {}

    current_label = None
    for line in lines:
        # Kalau baris ini cocok dengan label
        for lbl in labels:
            if re.fullmatch(lbl, line, re.IGNORECASE):
                current_label = lbl
                data[current_label] = None  # Siapkan tempatnya
                break
        else:
            # Kalau ini isi dari label sebelumnya
            if current_label:
                data[current_label] = line
                current_label = None  # Reset, supaya isi tidak nempel ke label lain

    return data

def parse_sarpen(all_text: str, labels_sarpen: list[str], current_label: str, match_sarpen) -> str | None:
    # Ambil teks bagian sarpen saja
    sarpen_text = match_sarpen.group(1) if match_sarpen else all_text

    # Normalisasi teks
    sarpen_text = re.sub(r"[\r\t]+", " ", sarpen_text)
    sarpen_text = re.sub(r" {2,}", " ", sarpen_text)
    sarpen_text = re.sub(r"\n+", "\n", sarpen_text)

    # Gabungkan baris label yang terpotong
    sarpen_text = re.sub(r"\(PLN P-\s*\n\s*N\)", "(PLN P-N)", sarpen_text)
    sarpen_text = re.sub(r"\(PLN P-\s*\n\s*G\)", "(PLN P-G)", sarpen_text)
    sarpen_text = re.sub(r"\(PLN N-\s*\n\s*G\)", "(PLN N-G)", sarpen_text)

    # Split ke baris
    lines = [line.strip() for line in sarpen_text.splitlines() if line.strip()]
    val = None

    for i, line in enumerate(lines):
        # Pola 1 → Label dan isi di satu baris (dengan : atau -)
        pattern_inline = rf"^{re.escape(current_label)}\s*[:\-–=]\s*(.+)$"
        match = re.match(pattern_inline, line, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            break

        # Pola 2 → Label di baris ini, isi di baris berikutnya
        if re.fullmatch(re.escape(current_label), line, re.IGNORECASE):
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Cegah supaya tidak salah baca label lain
                if not any(re.fullmatch(re.escape(l), next_line, re.IGNORECASE) for l in labels_sarpen):
                    val = next_line
            break

    return val
        
def parse_lokasi_antena(text: str, labels: list[str]) -> dict:
    """
    Ekstrak informasi dari bagian 'INFORMASI LOKASI ANTENA'.
    Mengembalikan dict {key: value} tanpa nesting.
    """
    match_lokasi = re.search(
        r"INFORMASI LOKASI ANTENA([\s\S]*?)(?=SURVEY REPORT|INFORMASI PERIZINAN|\Z)",
        text, re.IGNORECASE
    )

    section_text = match_lokasi.group(1) if match_lokasi else text
    section_text = pembersihan_data(section_text)
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]

    # Hilangkan header jika ada
    if lines and "INFORMASI LOKASI ANTENA" in lines[0].upper():
        lines = lines[1:]

    data = {}

    # Parsing vertikal
    i = 0
    while i < len(lines):
        line = lines[i]
        matched_label = next((lbl for lbl in labels if re.fullmatch(re.escape(lbl), line, re.IGNORECASE)), None)

        if matched_label:
            key = normalize_key(matched_label)
            val = None

            # Ambil nilai berikutnya jika bukan label baru
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                is_next_label = any(re.fullmatch(re.escape(l), next_line, re.IGNORECASE) for l in labels)

                if not is_next_label and next_line:
                    val = next_line
                    i += 1

            data[key] = val

        i += 1

    return data

def parse_perizinan_biaya_gedung(text: str, labels: list[str]) -> dict:
    """
    Ekstrak informasi dari bagian 'DATA PERIZINAN DAN BIAYA YANG TIMBUL DALAM GEDUNG'.
    Mengembalikan dict {key: value} tanpa nesting.
    """
    # Ambil bagian teks yang sesuai
    match_section = re.search(
        r"DATA\s*PERIZINAN\s*DAN\s*BIAYA\s*YANG\s*TIMBUL\s*DALAM\s*GEDUNG([\s\S]*?)(?=INFORMASI SARPEN|DOKUMENTASI FOTO|\Z)",
        text,
        re.IGNORECASE
    )

    section_text = match_section.group(1) if match_section else text
    section_text = pembersihan_data(section_text)
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]

    # Hilangkan header jika ada
    if lines and "DATA PERIZINAN" in lines[0].upper():
        lines = lines[1:]

    data = {}
    i = 0

    # Parsing vertikal per baris
    while i < len(lines):
        line = lines[i]
        matched_label = next(
            (lbl for lbl in labels if re.fullmatch(re.escape(lbl), line, re.IGNORECASE)), None
        )

        if matched_label:
            key = normalize_key(matched_label)

            # Jika label sudah pernah muncul, skip (contohnya Supervisi kedua)
            if key in data:
                i += 1
                continue

            val = None

            # Ambil baris berikutnya jika bukan label baru
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                is_next_label = any(
                    re.fullmatch(re.escape(l), next_line, re.IGNORECASE) for l in labels
                )

                if not is_next_label and next_line:
                    val = next_line
                    i += 1

            data[key] = val

        i += 1

    return data

def parse_penempatan_perangkat(text: str, labels: list[str]) -> dict:
    """
    Ekstrak informasi dari bagian 'DATA PENEMPATAN PERANGKAT DI LOKASI PELANGGAN'.
    Mengembalikan dict {key: value} tanpa nesting.
    """
    # Ambil bagian teks yang sesuai
    match_section = re.search(
        r"DATA\s*PENEMPATAN\s*PERANGKAT\s*DI\s*LOKASI\s*PELANGGAN([\s\S]*?)(?=FOTO\s*PENEMPATAN|DOKUMENTASI|\Z)",
        text,
        re.IGNORECASE
    )

    section_text = match_section.group(1) if match_section else text
    section_text = pembersihan_data(section_text)
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]

    # Hilangkan header jika ada
    if lines and "DATA PENEMPATAN" in lines[0].upper():
        lines = lines[1:]

    data = {}
    i = 0

    # Parsing vertikal per baris
    while i < len(lines):
        line = lines[i]
        matched_label = next(
            (lbl for lbl in labels if re.fullmatch(re.escape(lbl), line, re.IGNORECASE)), None
        )

        if matched_label:
            key = normalize_key(matched_label)

            # Jika label sudah pernah muncul, skip (hindari duplikat)
            if key in data:
                i += 1
                continue

            val = None

            # Ambil baris berikutnya jika bukan label baru
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                is_next_label = any(
                    re.fullmatch(re.escape(l), next_line, re.IGNORECASE) for l in labels
                )

                if not is_next_label and next_line:
                    val = next_line
                    i += 1

            data[key] = val

        i += 1

    return data

def parse_perizinan_biaya_kawasan(text: str, labels: list[str]) -> dict:
    """Ekstrak bagian 'DATA PERIZINAN DAN BIAYA YANG TIMBUL DALAM KAWASAN'"""
    match_section = re.search(
        r"DATA\s*PERIZINAN\s*DAN\s*BIAYA\s*YANG\s*TIMBUL\s*DALAM\s*KAWASAN([\s\S]*?)(?=DATA\s*KAWASAN\s*UMUM|\Z)",
        text,
        re.IGNORECASE,
    )

    section_text = match_section.group(1) if match_section else text
    section_text = pembersihan_data(section_text)
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
    section_text = pembersihan_data(section_text)
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

def parse_data_splitter(text: str, labels: list[str]) -> dict:
    """
    Ekstrak informasi dari bagian 'DATA SPLITTER'.
    Mengembalikan dict {key: value}.
    """
    match_section = re.search(
        r"DATA\s*SPLITTER([\s\S]*?)(?=FOTO\s*SPLITTER|DATA\s*|DOKUMENTASI|\Z)",
        text,
        re.IGNORECASE,
    )

    section_text = match_section.group(1) if match_section else text
    section_text = pembersihan_data(section_text)

    # Pisahkan per baris
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

            # Coba ambil value di baris yang sama (horizontal)
            horizontal_match = re.match(
                rf"{re.escape(matched_label)}\s*[:\-]?\s*(.+)", line, re.IGNORECASE
            )
            if horizontal_match and horizontal_match.group(1).strip():
                val = horizontal_match.group(1).strip()
            else:
                # Jika tidak ada, ambil dari baris berikutnya (vertikal)
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

def pembersihan_data(text: str) -> str:
    """Membersihkan teks agar lebih mudah diproses"""
    text = re.sub(r"[\r\t]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text


