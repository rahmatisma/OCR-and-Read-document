"""
Konfigurasi semua label untuk parsing dokumen SPK Survey
Taruh file ini di: parsers/config/labels.py
"""

# Label untuk Informasi Gedung
INFORMASI_GEDUNG_LABELS = [
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

# Label untuk Sarpen Ruang Server
SARPEN_LABELS = [
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

# Label untuk Lokasi Antena
LOKASI_ANTENA_LABELS = [
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

# Label untuk Perizinan & Biaya Gedung
PERIZINAN_BIAYA_GEDUNG_LABELS = [
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

# Label untuk Penempatan Perangkat
PENEMPATAN_PERANGKAT_LABELS = [
    "Lokasi Penempatan Modem dan Router",
    "Kesiapan Ruang Server",
    "Ketersedian Rak Server",
    "Space Modem dan Router",
    "Diizinkan Foto Ruang Server Pelanggan"
]

# Label untuk Perizinan Biaya Kawasan
PERIZINAN_BIAYA_KAWASAN_LABELS = [
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

# Label untuk Kawasan Umum
KAWASAN_UMUM_LABELS = [
    "Nama Kawasan Umum / PU yang dilewati",
    "Panjang Jalur Outdoor di Kawasan Umum",
]

# Label untuk Data Splitter
DATA_SPLITTER_LABELS = [
    "Lokasi Splitter",
    "ID Splitter",
    "Kapasitas Splitter",
    "Jumlah Port Kosong",
    "List Port Kosong dan Redaman",
    "Nama Node (Jika tidak ada Splitter)",
    "List port kosong",
    "Arah Akses",
]