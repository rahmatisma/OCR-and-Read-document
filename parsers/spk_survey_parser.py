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


def parse_spk_survey(all_text: str, page_texts: list[str]) -> dict:
    all_text = normalize_text(all_text)
    # print(all_text)
    # exit()
    data = {
        "spk": {},
        "pelanggan": {},
        "jaringan": {},
        "pelaksanaan": {},
        "tanda_tangan": [],
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
        "dokumentasi": [],
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

    data["informasi_gedung"]["status_gedung"] = search_regex(r"Status\s*Gedung\s*([^\n]*)", all_text)
    data["informasi_gedung"]["kondisi_gedung"] = search_regex(r"Kondisi\s*Gedung\s*([^\n]*)", all_text)
    data["informasi_gedung"]["pemilik_bangunan"] = search_regex(r"^[ \t]*Pemilik\s*Bangunan\s*:?[ \t]*(?P<val>[^\r\n]*)", all_text)
    
    data["informasi_gedung"]["kontak_person"] = search_regex(r"Kontak\s*Person\s*([^\n]*)", all_text)
    data["informasi_gedung"]["bagian_jabatan"] = search_regex(r"Bagian\s*/\s*Jabatan\s*([^\n]*)", all_text)
    data["informasi_gedung"]["telpon_fax"] = search_regex(r"Telpon\s*/\s*Fax\s*([^\n]*)", all_text)
    data["informasi_gedung"]["email"] = search_regex(r"Email\s*([^\n]*)", all_text)
    data["informasi_gedung"]["jumlah_lantai_gedung"] = search_regex(r"Jumlah\s*Lantai\s*Gedung\s*([^\n]*)", all_text)
    data["informasi_gedung"]["pelanggan_fo"] = search_regex(r"Pelanggan\s*bersedia\s*dipasang\s*perangkat\s*([^\n]*)", all_text)
    data["informasi_gedung"]["penempatan_antena"] = search_regex(r"Penempatan\s*Antena\s*([^\n]*)", all_text)
    data["informasi_gedung"]["sewa_space_antena"] = search_regex(r"Sewa\s*space\s*antena\s*([^\n]*)", all_text)
    data["informasi_gedung"]["sewa_shaft_kabel"] = search_regex(r"Sewa\s*shaft\s*kabel\s*([^\n]*)", all_text)
    data["informasi_gedung"]["biaya_ikg"] = search_regex(r"Biaya\s*IKG\s*([^\n]*)", all_text)
    data["informasi_gedung"]["penanggungjawab_sewa"] = search_regex(r"Penanggungjawab\s*pengurusan\s*dan\s*pembayaran\s*sewa\s*([^\n]*)", all_text)

    data["sarpen_ruang_server"]["grounding_listrik"] = "Ada" in all_text
    data["sarpen_ruang_server"]["ups"] = "UPS Tersedia" in all_text or "Tersedia/Ada" in all_text
    data["sarpen_ruang_server"]["ruangan_ber_ac"] = "Ruangan Ber AC Ada" in all_text or "Ruangan Ber AC" in all_text
    data["sarpen_ruang_server"]["power_line"] = search_regex(r"Power\s*Line\s*/\s*Listrik\s*([^\n]*)", all_text)
    data["sarpen_ruang_server"]["power_outlet"] = search_regex(r"Ketersediaan\s*Power\s*Outlet.*([^\n]*)", all_text)
    data["sarpen_ruang_server"]["info_kelistrikan_pln_pn"] = search_regex(r"Info\s*Kelistrikan\s*\(PLN\s*P-N\)\s*([^\n]*)", all_text)
    data["sarpen_ruang_server"]["info_kelistrikan_pln_pg"] = search_regex(r"Info\s*Kelistrikan\s*\(PLN\s*P-G\)\s*([^\n]*)", all_text)
    data["sarpen_ruang_server"]["info_kelistrikan_pln_ng"] = search_regex(r"Info\s*Kelistrikan\s*\(PLN\s*N-G\)\s*([^\n]*)", all_text)
    data["sarpen_ruang_server"]["suhu_ruangan"] = search_regex(r"Suhu\s*Ruangan\s*([^\n]*)", all_text)
    data["sarpen_ruang_server"]["penempatan_modem"] = search_regex(r"Penempatan\s*Modem\s*([^\n]*)", all_text)
    data["sarpen_ruang_server"]["penempatan_modem_lantai"] = search_regex(r"1\.\s*Lantai\s*([^\n]*)", all_text)
    data["sarpen_ruang_server"]["penempatan_modem_ruang"] = search_regex(r"2\.\s*Ruang\s*([^\n]*)", all_text)
    data["sarpen_ruang_server"]["perangkat_pelanggan"] = search_regex(r"Perangkat\s*Pelanggan\s*([^\n]*)", all_text)

    # Lokasi Antena
    data["lokasi_antena"]["lokasi_antena"] = search_regex(r"Lokasi\s*Antena\s*([^\n]*)", all_text)
    data["lokasi_antena"]["detail_lokasi_antena"] = search_regex(r"Detail\s*Lokasi\s*Antena\s*([^\n]*)", all_text)
    data["lokasi_antena"]["space_tersedia"] = search_regex(r"Space\s*Tersedia\s*([^\n]*)", all_text)
    data["lokasi_antena"]["akses_perlu_alat_bantu"] = search_regex(r"Akses\s*di\s*lokasi\s*perlu\s*alat\s*bantu\s*([^\n]*)", all_text)
    data["lokasi_antena"]["penangkal_petir"] = search_regex(r"Penangkal\s*Petir\s*([^\n]*)", all_text)
    data["lokasi_antena"]["tinggi_penangkal_petir"] = search_regex(r"Tinggi\s*Penangkal\s*Petir\s*([^\n]*)", all_text)
    data["lokasi_antena"]["jarak_lokasi_antena"] = search_regex(r"Jarak\s*ke\s*lokasi\s*antena\s*([^\n]*)", all_text)
    data["lokasi_antena"]["tindak_lanjut"] = search_regex(r"Tindak\s*Lanjut\s*([^\n]*)", all_text)
    data["lokasi_antena"]["tower_pole"] = search_regex(r"Tower\s*/\s*Pole\s*([^\n]*)", all_text)
    data["lokasi_antena"]["pemilik_tower_pole"] = search_regex(r"Pemilik\s*Tower\s*/\s*Pole\s*([^\n]*)", all_text)

    # Perizinan & Biaya Gedung
    data["perizinan_biaya_gedung"]["pic_bm"] = search_regex(r"PIC\s*BM\s*([^\n]*)", all_text)
    data["perizinan_biaya_gedung"]["kontak_pic_bm"] = search_regex(r"Kontak\s*PIC\s*BM\s*([^\n]*)", all_text)
    data["perizinan_biaya_gedung"]["material_infrastruktur"] = search_regex(r"Material\s*dan\s*Infrastruktur\s*([^\n]*)", all_text)
    data["perizinan_biaya_gedung"]["panjang_kabel"] = search_regex(r"Panjang\s*Kabel\s*dalam\s*Gedung\s*([^\n]*)", all_text)
    data["perizinan_biaya_gedung"]["pelaksana_penarikan_kabel"] = search_regex(r"Pelaksana\s*Penarikan\s*Kabel\s*dalam\s*Gedung\s*([^\n]*)", all_text)
    data["perizinan_biaya_gedung"]["waktu_pelaksanaan_penarikan"] = search_regex(r"Waktu\s*Pelaksanaan\s*Penarikan\s*Kabel\s*([^\n]*)", all_text)
    data["perizinan_biaya_gedung"]["supervisi"] = search_regex(r"Supervisi\s*([^\n]*)", all_text)
    data["perizinan_biaya_gedung"]["deposit_kerja"] = search_regex(r"Deposit\s*Kerja\s*([^\n]*)", all_text)
    data["perizinan_biaya_gedung"]["ikg"] = search_regex(r"IKG\s*\(Instalasi\s*Kabel\s*Gedung\)\s*([^\n]*)", all_text)
    data["perizinan_biaya_gedung"]["biaya_sewa"] = search_regex(r"Biaya\s*Sewa\s*([^\n]*)", all_text)
    data["perizinan_biaya_gedung"]["biaya_lain"] = search_regex(r"Biaya\s*lain.*?([^\n]*)", all_text)
    data["perizinan_biaya_gedung"]["info_lain"] = search_regex(r"Info\s*Lain\s*-\s*Lain.*?([^\n]*)", all_text)

    # Perizinan Biaya Kawasan
    data["perizinan_biaya_kawasan"]["melewati_kawasan_private"] = search_regex(r"Melewati\s*kawasan\s*private\s*([^\n]*)", all_text)
    data["perizinan_biaya_kawasan"]["nama_kawasan"] = search_regex(r"Nama\s*Kawasan\s*([^\n]*)", all_text)
    data["perizinan_biaya_kawasan"]["pic_kawasan"] = search_regex(r"PIC\s*Kawasan\s*([^\n]*)", all_text)
    data["perizinan_biaya_kawasan"]["kontak_pic_kawasan"] = search_regex(r"Kontak\s*PIC\s*Kawasan\s*([^\n]*)", all_text)
    data["perizinan_biaya_kawasan"]["panjang_kabel"] = search_regex(r"Panjang\s*Kabel\s*dalam\s*Kawasan\s*([^\n]*)", all_text)
    data["perizinan_biaya_kawasan"]["pelaksana_penarikan_kabel"] = search_regex(r"Pelaksana\s*Penarikan\s*Kabel.*?([^\n]*)", all_text)
    data["perizinan_biaya_kawasan"]["deposit_kerja"] = search_regex(r"Deposit\s*Kerja\s*([^\n]*)", all_text)
    data["perizinan_biaya_kawasan"]["supervisi"] = search_regex(r"Supervisi\s*([^\n]*)", all_text)
    data["perizinan_biaya_kawasan"]["biaya_penarikan_kabel"] = search_regex(r"Biaya\s*Penarikan\s*Kabel.*?([^\n]*)", all_text)
    data["perizinan_biaya_kawasan"]["biaya_sewa"] = search_regex(r"Biaya\s*Sewa\s*([^\n]*)", all_text)
    data["perizinan_biaya_kawasan"]["biaya_lain"] = search_regex(r"Biaya\s*lain.*?([^\n]*)", all_text)
    data["perizinan_biaya_kawasan"]["info_lain"] = search_regex(r"Info\s*Lain.*?([^\n]*)", all_text)

    # Perizinan Biaya Kawasan - tambahan
    data["kawasan_umum"]["nama_kawasan_umum"] = search_regex(r"Nama\s*Kawasan\s*Umum.*?([^\n]*)", all_text)
    data["kawasan_umum"]["panjang_jalur_outdoor"] = search_regex(r"Panjang\s*Jalur\s*Outdoor.*?([^\n]*)", all_text)

    # Data Splitter
    data["data_splitter"]["lokasi_splitter"] = search_regex(r"Lokasi\s*Splitter\s*([^\n]*)", all_text)
    data["data_splitter"]["splitter_id"] = search_regex(r"ID\s*Splitter\s*([^\n]*)", all_text)
    data["data_splitter"]["kapasitas_splitter"] = search_regex(r"Kapasitas\s*Splitter\s*([^\n]*)", all_text)
    data["data_splitter"]["jumlah_port_kosong"] = search_regex(r"Jumlah\s*Port\s*Kosong\s*([^\n]*)", all_text)
    data["data_splitter"]["list_port_kosong_redaman"] = search_regex(r"List\s*Port\s*K(osong)?\s*dan\s*Redaman\s*([^\n]*)", all_text)
    data["data_splitter"]["nama_node"] = search_regex(r"Nama\s*Node.*?([^\n]*)", all_text)
    data["data_splitter"]["list_port_kosong"] = search_regex(r"List\s*port\s*kosong\s*([^\n]*)", all_text)
    data["data_splitter"]["arah_akses"] = search_regex(r"Arah\s*Akses\s*([^\n]*)", all_text)

    data["data_hh"] = parse_multiple_hh(all_text)

    # Penempatan Perangkat
    data["penempatan_perangkat"]["lokasi_penempatan"] = search_regex(r"Lokasi\s*Penempatan\s*Modem.*?([^\n]*)", all_text)
    data["penempatan_perangkat"]["kesiapan_ruang_server"] = search_regex(r"Kesiapan\s*Ruang\s*Server\s*([^\n]*)", all_text)
    data["penempatan_perangkat"]["ketersediaan_rak_server"] = search_regex(r"Ketersedia[n|an]\s*Rak\s*Server\s*([^\n]*)", all_text)
    data["penempatan_perangkat"]["space_modem_router"] = search_regex(r"Space\s*Modem\s*dan\s*Router\s*([^\n]*)", all_text)
    data["penempatan_perangkat"]["izin_foto_ruang_server"] = search_regex(r"Diizinkan\s*Foto\s*Ruang\s*Server\s*Pelanggan\s*([^\n]*)", all_text)

    if "PLAN JALUR DALAM GEDUNG" in all_text:
        data["plan_jalur_dalam_gedung"] = "Tersedia (lihat halaman terkait)"

    # Judul SPK
    data["berita_acara"]["judul_spk"] = "BERITA ACARA"
    data["berita_acara"]["tipe_spk"] = "survey"

    # Informasi SPK
    data["berita_acara"]["nomor_spk"] = search_regex(r"Nomor\s*SPK\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["tanggal"] = search_regex(r"Tanggal\s*:\s*([^\n]*)", all_text)

    # Informasi Pelanggan
    data["berita_acara"]["nama_pelanggan"] = search_regex(r"Nama\s*Pelanggan\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["no_jaringan"] = search_regex(r"No\.?\s*Jaringan\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["no_fps"] = search_regex(r"No\.?\s*FPS\s*:\s*([^\n]*)", all_text)

    # Informasi Jasa
    data["berita_acara"]["jasa"] = search_regex(r"Jasa\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["manage_router"] = search_regex(r"Manage\s*Router\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["opsi_router"] = search_regex(r"Opsi\s*Router\s*1/2/3\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["ip_lan"] = search_regex(r"IP\s*LAN\s*:\s*([^\n]*)", all_text)

    # Tanggal RFS
    data["berita_acara"]["tgl_rfs_la"] = search_regex(r"Tgl\.?RFS\s*LA\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["tgl_rfs_pelanggan"] = search_regex(r"Tgl\.?RFS\s*PLG\s*:\s*([^\n]*)", all_text)

    # Lokasi
    data["berita_acara"]["lokasi_pelanggan"] = search_regex(r"Lokasi\s*Pelanggan\s*:\s*([^\n]*)", all_text)

    # Jenis Survey
    data["berita_acara"]["jenis_survey"] = search_regex(r"Jenis\s*Survey\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["media_akses"] = search_regex(r"Media\s*Akses\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["pop"] = search_regex(r"POP\s*:\s*(.*?)(?=\n[A-Z][A-Za-z ]*?:)", all_text, allow_multiline=True)

    # Kecepatan
    data["berita_acara"]["kecepatan"] = search_regex(r"Kecepatan\s*:\s*([^\n]*)", all_text)

    # Kontak Person
    data["berita_acara"]["kontak_person"] = search_regex(r"Kontak\s*Person\s*:\s*([^\n]*)", all_text)
    data["berita_acara"]["telepon"] = search_regex(r"Telepon\s*:\s*([^\n]*)", all_text)

    # Waktu Pelaksanaan
    data["berita_acara"]["waktu_pelaksanaan_perm_pelanggan"] = search_regex(r"Permintaan\s*Pelanggan\s*([^\n]*)", all_text)
    data["berita_acara"]["waktu_pelaksanaan_datang"] = search_regex(r"Datang\s*([^\n]*)", all_text)
    data["berita_acara"]["waktu_pelaksanaan_selesai"] = search_regex(r"Selesai\s*([^\n]*)", all_text)


    data["tanda_tangan"].append({
        "peran": "Yang Memerintahkan",
        "nama": search_regex(r"Yang Memerintahkan.*?([A-Za-z ]+)", all_text),
        "path_ttd": None
    })

    return data


def search_regex(pattern, text, allow_multiline=False):
    """
    Fungsi pencarian regex yang aman dan sederhana.
    - Jika allow_multiline=True, newline diizinkan dan akan dirapikan jadi spasi
    - Jika value ternyata berisi label lain (ada ':'), dianggap kosong
    """
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if match:
        value = match.group(1).strip()

        if not value:
            return None

        if not allow_multiline:
            if '\n' in value:
                return None
        else:
            # rapikan newline → spasi
            value = re.sub(r"\s*\n\s*", " ", value).strip()

        if ':' in value and not allow_multiline:
            return None

        return value
    return None

def parse_multiple_hh(text: str):
    hh_list = []
    matches = re.finditer(
        r"Data HH\s*(\d+).*?Lokasi HH-\1\s*(.+?)\s*Longitude.*?([0-9\.\-]+).*?Latitude.*?([0-9\.\-]+)",
        text, re.S
    )
    for match in matches:
        hh_list.append({
            "nama_hh": f"HH-{match.group(1)}",
            "lokasi_hh": match.group(2),
            "longitude": match.group(3),
            "latitude": match.group(4)
        })
    return hh_list
