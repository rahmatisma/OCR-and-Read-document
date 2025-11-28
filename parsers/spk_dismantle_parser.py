"""
SPK Survey Parser - Parser utama untuk dokumen SPK Survey
Taruh file ini di: parsers/spk_survey_parser.py

File ini adalah ORCHESTRATOR yang mengkoordinasi semua section parser
"""
import re
from typing import Dict, List
from .base_parser import BaseParser
from parsers.utils.section_parsers import (
    PekerjaCabutParser,
)

def parse_spk_dismantle(all_text: str, page_texts: list[str], ttd_results: dict = None, doc_results: dict = None) -> dict:
    """
    Fungsi wrapper untuk kompatibilitas dengan kode lama
    
    Args:
        all_text: Full text dari dokumen
        page_texts: List text per halaman
        ttd_results: Hasil deteksi TTD (opsional)
        doc_results: Hasil dokumen (opsional)
    
    Returns:
        Dictionary berisi hasil parsing
    """
    parser = SPKDismantleParser(all_text, page_texts, ttd_results, doc_results)
    return parser.parse()


class SPKDismantleParser(BaseParser):
    """
    Parser utama untuk SPK Survey
    Tugasnya: mengkoordinasi semua section parser
    """
    
    def __init__(self, all_text: str, page_texts: list[str], ttd_results: dict = None, doc_results: dict = None):
        super().__init__(all_text, page_texts)
        self.ttd_results = ttd_results or {}
        self.doc_results = doc_results or {}

        if "BERITA ACARA" in all_text:
            parts = all_text.split("BERITA ACARA", 1)
            self.spk_text = parts[0].strip()
            self.berita_text = parts[1].strip()  # JANGAN tambahkan "BERITA ACARA" lagi
            
            # Buat marker untuk validasi
            self.has_berita_acara = True
        else:
            # Jika tidak ada BERITA ACARA, semua adalah SPK
            self.spk_text = all_text.strip()
            self.berita_text = ""
            self.has_berita_acara = False
    
    def parse(self) -> dict:
        """
        Entry point untuk parsing SPK Survey
        Method ini mengkoordinasi semua section parser
        """
        # 1. Inisialisasi struktur data
        data = self._init_data_structure_spk_dismantel()
        
        # 2. Parse bagian-bagian sederhana (langsung di sini)
        self._parse_spk_section(data)
        self._parse_pelanggan_section(data)
        self._parse_jaringan_section(data)
        self._parse_pelaksanaan_section(data)
        self._parse_list_section(data)
        self._parse_berita_acara_section(data)
        
        # 3. Parse bagian kompleks menggunakan section parser
        data["pekerja_cabut"] = PekerjaCabutParser(self.all_text).parse()
        
        return data
    
    def _parse_spk_section(self, data: dict):
        """Parse bagian SPK (header dokumen)"""
        spk = data["spk"]
        spk["judul_spk"] = self.search_regex(
            r"(BERITA\s+ACARA|SURAT\s+PERINTAH(?:\s+KERJA)?)",
            self.all_text
        )
        spk["tipe_spk"] = "spk dismantle"
        spk["no_spk"] = self.search_regex(r"Nomor\s*:\s*([^\n]*)", self.all_text)
        spk["tanggal_spk"] = self.search_regex(r"Tanggal\s*:\s*([^\n]*)", self.all_text)
        spk["no_mr"] = self.search_regex(
            r"No\.\s*MR\s*:\s*([^\n]*)",
            self.all_text
        )

    
    def _parse_pelanggan_section(self, data: dict):
        """Parse bagian data pelanggan"""
        pelanggan = data["pelanggan"]
        pelanggan["nama_pelanggan"] = self.search_regex(
            r"Nama\s*Pelanggan\s*:\s*([^\n]*)",
            self.all_text
        )
        pelanggan["lokasi_pelanggan"] = self.search_regex(
            r"Lokasi\s*Pelanggan\s*:\s*([^\n]*)",
            self.all_text
        )
        pelanggan["kontak_person"] = self.search_regex(
            r"Kontak\s*Person\s*:\s*([^\n]*)",
            self.all_text
        )
        pelanggan["telepon"] = self.search_regex(
            r"Telepon\s*:\s*([0-9]+)",
            self.all_text
        )
    
    def _parse_jaringan_section(self, data: dict):
        """Parse bagian data jaringan"""
        jaringan = data["jaringan"]
        jaringan["no_jaringan"] = self.search_regex(
            r"No\.?\s*Jaringan\s*:\s*([^\n]*)",
            self.all_text
        )
        jaringan["jasa"] = self.search_regex(r"Jasa\s*:\s*([^\n]*)", self.all_text)
        jaringan["tgl_rfs_la"] = self.search_regex(
            r"Tgl\.RFS LA\s*:\s*([^\n]*)",
            self.all_text
        )
        jaringan["tgl_rfs_plg"] = self.search_regex(
            r"Tgl\.RFS PLG\s*:\s*([^\n]*)",
            self.all_text
        )
        
        jaringan["kecepatan"] = self.search_regex(
            r"Kecepatan\s*:\s*([^\n]*)",
            self.all_text
        )
    import re

    def _parse_list_section(self, data: dict):
        """
        Parse bagian 'List Item' dan ambil semua item yang diawali dengan tanda '-'.
        Bisa menangani jumlah item yang dinamis dan format baris tidak seragam.
        """
        text = self.all_text

        # 1️⃣ Tangkap blok teks dari "List Item" sampai sebelum section berikutnya
        section_match = re.search(
            r"List\s*Item\s*:([\s\S]*?)(?=\n[A-Z][A-Za-z ]*?:|\Z)", 
            text, 
            re.IGNORECASE
        )

        if not section_match:
            data["list_item"] = None
            return data

        section_text = section_match.group(1)

        # 2️⃣ Tangkap semua baris list dengan awalan '-'
        # Format contoh: "- B2WN0262020HA1346 , FORTIGATE-50E HW AND WARRANTY"
        item_pattern = re.compile(
            r"-\s*([A-Z0-9\-\/]+)\s*,?\s*(.+?)(?=\n\s*-\s*[A-Z0-9\-\/]+|$)",
            re.MULTILINE | re.DOTALL
        )

        items = []
        for match in item_pattern.finditer(section_text):
            kode = match.group(1).strip()
            deskripsi = match.group(2).strip().replace("\n", " ")
            items.append({
                "kode": kode,
                "deskripsi": deskripsi
            })

        # 3️⃣ Simpan hasil ke dictionary utama
        data["list_item"] = items if items else None
        return data

    
    def _parse_pelaksanaan_section(self, data: dict):
        """Parse bagian waktu pelaksanaan"""
        waktu_matches = re.findall(r"\d{2}/[A-Za-z]{3}/\d{4}\s+\d{2}:\d{2}", self.all_text)
        data["pelaksanaan"] = {
            "permintaan_pelanggan": waktu_matches[0] if len(waktu_matches) > 0 else "",
            "datang": waktu_matches[1] if len(waktu_matches) > 1 else "",
            "selesai": waktu_matches[2] if len(waktu_matches) > 2 else "",
        }
    
    def _parse_berita_acara_section(self, data: dict):
        """Parse bagian berita acara"""
        berita_acara = data["berita_acara"]
        berita_acara["judul_spk"] = "BERITA ACARA"
        berita_acara["tipe_spk"] = "dismantle"
        berita_acara["nomor_spk"] = self.search_regex(
            r"Nomor\s*SPK\s*:\s*([^\n]*)",
            self.all_text
        )
        berita_acara["tanggal"] = self.search_regex(
            r"Tanggal\s*:\s*([^\n]*)",
            self.all_text
        )
        berita_acara["nama_pelanggan"] = self.search_regex(
            r"Nama\s*Pelanggan\s*:\s*([^\n]*)",
            self.all_text
        )
        berita_acara["no_jaringan"] = self.search_regex(
            r"No\.?\s*Jaringan\s*:\s*([^\n]*)",
            self.all_text
        )
        berita_acara["no_fps"] = self.search_regex(
            r"No\.?\s*FPS\s*:\s*([^\n]*)",
            self.all_text
        )
        berita_acara["jasa"] = self.search_regex(r"Jasa\s*:\s*([^\n]*)", self.all_text)
        berita_acara["tgl_rfs_la"] = self.search_regex(
            r"Tgl\.?RFS\s*LA\s*:\s*([^\n]*)",
            self.all_text
        )
        berita_acara["tgl_rfs_pelanggan"] = self.search_regex(
            r"Tgl\.?RFS\s*PLG\s*:\s*([^\n]*)",
            self.all_text
        )
        berita_acara["lokasi_pelanggan"] = self.search_regex(
            r"Lokasi\s*Pelanggan\s*:\s*([^\n]*)",
            self.all_text
        )
        berita_acara["media_akses"] = self.search_regex(
            r"Media\s*Akses\s*:\s*([^\n]*)",
            self.all_text
        )
        berita_acara["kecepatan"] = self.search_regex(
            r"Kecepatan\s*:\s*([^\n]*)",
            self.all_text
        )
        berita_acara["kontak_person"] = self.search_regex(
            r"Kontak\s*Person\s*:\s*([^\n]*)",
            self.berita_text
        )
        berita_acara["telepon"] = self.search_regex(
            r"Telepon\s*:\s*([^\n]*)",
            self.berita_text
        )
        
        # Waktu pelaksanaan berita acara
        waktu_matches = re.findall(r"\d{2}/[A-Za-z]{3}/\d{4}\s+\d{2}:\d{2}", self.all_text)
        data["pelaksanan_berita_acara"] = {
            "permintaan_pelanggan": waktu_matches[0] if len(waktu_matches) > 0 else "",
            "datang": waktu_matches[1] if len(waktu_matches) > 1 else "",
            "selesai": waktu_matches[2] if len(waktu_matches) > 2 else "",
        }