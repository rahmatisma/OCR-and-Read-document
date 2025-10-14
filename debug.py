import re
from pprint import pprint

all_teks = """INFORMASI GEDUNG PELANGGAN

Status Gedung

Milik Sendiri

Kondisi Gedung

Sudah Siap

Pemilik Bangunan

Alamat

JL. GRIYA ALAM SENTOSA,

Kontak Person

Bagian / Jabatan

Telpon / Fax

Email

Jumlah Lantai Gedung

Pelanggan bersedia dipasang perangkat

FO

Penempatan Antena

Tidak Perlu Izin

Sewa space antena

Ada

Sewa shaft kabel

Ada

Biaya IKG

Ada

Penanggungjawab pengurusan dan pembayaran sewa
Lintasarta
"""

def extract_field(label, text, next_labels):
    """
    Ambil isi setelah label sampai label berikutnya (atau akhir teks)
    """
    # Gabungkan label berikutnya jadi pola batas
    next_pattern = '|'.join(map(re.escape, next_labels)) if next_labels else '$'
    pattern = rf"{re.escape(label)}\s*([\s\S]*?)(?=\b(?:{next_pattern})\b)"
    
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    
    value = match.group(1).strip()
    # Bersihkan spasi & newline berlebih
    value = re.sub(r"\s+", " ", value)
    
    # Jika hasilnya kosong atau berisi label lain → kosong
    if not value or any(lbl.lower() in value.lower() for lbl in next_labels[:3]):
        return None
    
    return value.strip() or None


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

data = {"informasi_gedung": {}}

for i, label in enumerate(labels):
    next_labels = labels[i + 1:]
    key = (
        label.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("bersedia_dipasang_perangkat", "fo")
        .replace("penanggungjawab_pengurusan_dan_pembayaran_sewa", "penanggungjawab_sewa")
    )
    data["informasi_gedung"][key] = extract_field(label, all_teks, next_labels)

pprint(data)
