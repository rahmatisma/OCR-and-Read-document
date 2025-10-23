"""
Section Parsers - Parser untuk setiap bagian dokumen
Taruh file ini di: parsers/utils/section_parsers.py
"""
import re
from typing import Optional, Dict, List
from .text_utils import TextNormalizer, KeyNormalizer


class VendorParser:
    """Parser khusus untuk bagian VENDOR"""
    
    def __init__(self, text: str):
        self.text = TextNormalizer.normalize_dash(text)
        self.key_normalizer = KeyNormalizer()
    
    def parse(self) -> dict:
        """Parse semua data vendor"""
        return {
            "latitude": self._extract_latitude(),
            "longitude": self._extract_longitude(),
            "pic_pelanggan": self._extract_pic_pelanggan(),
            "kontak_pic_pelanggan": self._extract_kontak_pic(),
            "teknisi": self._extract_teknisi(),
            "nama_vendor": self._extract_nama_vendor(),
        }
    
    def _extract_latitude(self) -> Optional[str]:
        """Ambil latitude dari koordinat"""
        match = re.search(
            r"Koordinat\s*[\r\n\s]+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)",
            self.text,
            re.IGNORECASE
        )
        return match.group(1) if match else None
    
    def _extract_longitude(self) -> Optional[str]:
        """Ambil longitude dari koordinat"""
        match = re.search(
            r"Koordinat\s*[\r\n\s]+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)",
            self.text,
            re.IGNORECASE
        )
        return match.group(2) if match else None
    
    def _extract_pic_pelanggan(self) -> Optional[str]:
        """Ambil PIC pelanggan"""
        match = re.search(
            r"PIC\s+Pelanggan[^\n]*\n\s*(.*?)\s*\n\s*Kontak\s+PIC\s+Pelanggan",
            self.text,
            re.IGNORECASE | re.DOTALL
        )
        return match.group(1).strip() if match else None
    
    def _extract_kontak_pic(self) -> Optional[str]:
        """Ambil kontak PIC pelanggan"""
        match = re.search(
            r"Kontak\s+PIC\s+Pelanggan\s*[:\-]?\s*[\r\n\s]*([0-9\+\-\(\) ]+)",
            self.text,
            re.IGNORECASE
        )
        return match.group(1).strip() if match else None
    
    def _extract_nama_vendor(self) -> Optional[str]:
        """Ambil nama vendor dari berbagai jenis SPK."""
        # Pattern: kata "Vendor" diikuti whitespace/newline lalu nama vendor
        match = re.search(
            r'\bVendor\b\s+([A-Z][A-Z0-9\s]+?)(?=\s*\n\s*\n|\s*\n\s*(?:INFORMASI|HASIL|PEKERJAAN|Kontak))',
            self.text,
            re.DOTALL
        )

        if match:
            vendor_raw = match.group(1)
            vendor_raw = re.sub(r"\s+", " ", vendor_raw).strip()
            return vendor_raw
        return None


    def _extract_teknisi(self) -> Optional[str]:
        """Ambil nama teknisi dari berbagai jenis SPK."""
        # Cari vendor dulu untuk referensi
        vendor_name = self._extract_nama_vendor()
        
        # Pattern untuk teknisi: setelah "Pelaksana [JENIS] dari Tim Vendor" atau "Pelaksana"
        # sampai sebelum kata "Vendor"
        match = re.search(
            r'Pelaksana\s+(?:Survey|INSTALASI|AKTIVASI|DISMANTLE)?\s*(?:dari\s+Tim\s+Vendor)?\s+(.+?)\s+Vendor',
            self.text,
            re.IGNORECASE | re.DOTALL
        )

        if match:
            teknisi_raw = match.group(1)
            # Bersihkan whitespace berlebih dan newline
            teknisi_raw = re.sub(r'\s+', ' ', teknisi_raw).strip()
            
            # Hapus nama vendor dari teknisi jika ada
            if vendor_name:
                # Hapus vendor name lengkap (exact match)
                teknisi_raw = re.sub(
                    rf'\b{re.escape(vendor_name)}\b',
                    '',
                    teknisi_raw,
                    flags=re.IGNORECASE
                ).strip()
            
            return teknisi_raw if teknisi_raw else None
        
        return None
    
class PekerjaCabutParser:
    """Parser khusus untuk bagian VENDOR"""
    
    def __init__(self, text: str):
        self.text = TextNormalizer.normalize_dash(text)
        self.key_normalizer = KeyNormalizer()
    
    def parse(self) -> dict:
        """Parse semua data vendor"""
        return {
            "pic_pelanggan": self._extract_pic_pelanggan(),
            "kontak_pic_pelanggan": self._extract_kontak_pic(),
            "teknisi": self._extract_teknisi(),
            "nama_vendor": self._extract_nama_vendor(),
        }
    
    def _extract_latitude(self) -> Optional[str]:
        """Ambil latitude dari koordinat"""
        match = re.search(
            r"Koordinat\s*[\r\n\s]+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)",
            self.text,
            re.IGNORECASE
        )
        return match.group(1) if match else None
    
    def _extract_longitude(self) -> Optional[str]:
        """Ambil longitude dari koordinat"""
        match = re.search(
            r"Koordinat\s*[\r\n\s]+(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)",
            self.text,
            re.IGNORECASE
        )
        return match.group(2) if match else None
    
    def _extract_pic_pelanggan(self) -> Optional[str]:
        """Ambil PIC pelanggan"""
        match = re.search(
            r"PIC\s+Pelanggan[^\n]*\n\s*(.*?)\s*\n\s*Kontak\s+PIC\s+Pelanggan",
            self.text,
            re.IGNORECASE | re.DOTALL
        )
        return match.group(1).strip() if match else None
    
    def _extract_kontak_pic(self) -> Optional[str]:
        """Ambil kontak PIC pelanggan"""
        match = re.search(
            r"Kontak\s+PIC\s+Pelanggan\s*[:\-]?\s*[\r\n\s]*([0-9\+\-\(\) ]+)",
            self.text,
            re.IGNORECASE
        )
        return match.group(1).strip() if match else None
    
    def _extract_nama_vendor(self) -> Optional[str]:
        """Ambil nama vendor dari berbagai jenis SPK."""
        # Pattern: kata "Vendor" diikuti whitespace/newline lalu nama vendor
        match = re.search(
            r'\bVendor\b\s+([A-Z][A-Z0-9\s]+?)(?=\s*\n\s*\n|\s*\n\s*(?:INFORMASI|HASIL|PEKERJAAN|Kontak))',
            self.text,
            re.DOTALL
        )

        if match:
            vendor_raw = match.group(1)
            vendor_raw = re.sub(r"\s+", " ", vendor_raw).strip()
            return vendor_raw
        return None


    def _extract_teknisi(self) -> Optional[str]:
        """Ambil nama teknisi dari berbagai jenis SPK."""
        # Cari vendor dulu untuk referensi
        vendor_name = self._extract_nama_vendor()
        
        # Pattern untuk teknisi: setelah "Pelaksana [JENIS] dari Tim Vendor" atau "Pelaksana"
        # sampai sebelum kata "Vendor"
        match = re.search(
            r'Pelaksana\s+(?:Survey|INSTALASI|AKTIVASI|DISMANTLE)?\s*(?:dari\s+Tim\s+Vendor)?\s+(.+?)\s+Vendor',
            self.text,
            re.IGNORECASE | re.DOTALL
        )

        if match:
            teknisi_raw = match.group(1)
            # Bersihkan whitespace berlebih dan newline
            teknisi_raw = re.sub(r'\s+', ' ', teknisi_raw).strip()
            
            # Hapus nama vendor dari teknisi jika ada
            if vendor_name:
                # Hapus vendor name lengkap (exact match)
                teknisi_raw = re.sub(
                    rf'\b{re.escape(vendor_name)}\b',
                    '',
                    teknisi_raw,
                    flags=re.IGNORECASE
                ).strip()
            
            return teknisi_raw if teknisi_raw else None
        
        return None



class InformasiGedungParser:
    """Parser khusus untuk bagian INFORMASI GEDUNG"""
    
    def __init__(self, text: str, labels: List[str]):
        self.text = text
        self.labels = labels
        self.key_normalizer = KeyNormalizer()
    
    def parse(self) -> dict:
        """Parse semua data informasi gedung"""
        lines = [line.strip() for line in self.text.splitlines() if line.strip()]
        data = {}
        current_label = None
        
        for line in lines:
            # Cek apakah baris ini adalah label
            matched = False
            for lbl in self.labels:
                if re.fullmatch(lbl, line, re.IGNORECASE):
                    current_label = lbl
                    data[self.key_normalizer.normalize(current_label)] = None
                    matched = True
                    break
            
            # Jika bukan label dan ada current_label, ini adalah value
            if not matched and current_label:
                key = self.key_normalizer.normalize(current_label)
                
                # Jika label adalah email, pastikan nilainya benar-benar pola email
                if "email" in key:
                    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", line)
                    if email_match:
                        data[key] = email_match.group(0)
                    else:
                        data[key] = None  # kalau tidak ditemukan email valid
                else:
                    data[key] = line
                
                current_label = None

        
        return data


class SarpenParser:
    """Parser khusus untuk bagian SARPEN DAN RUANG SERVER"""
    
    def __init__(self, text: str, labels: List[str]):
        self.text = self._prepare_text(text)
        self.labels = labels
        self.key_normalizer = KeyNormalizer()
    
    def _prepare_text(self, text: str) -> str:
        """Persiapkan teks dengan normalisasi khusus untuk sarpen"""
        # Gabungkan baris label yang terpotong
        text = re.sub(r"\(PLN P-\s*\n\s*N\)", "(PLN P-N)", text)
        text = re.sub(r"\(PLN P-\s*\n\s*G\)", "(PLN P-G)", text)
        text = re.sub(r"\(PLN N-\s*\n\s*G\)", "(PLN N-G)", text)
        return TextNormalizer.clean(text)
    
    def parse(self) -> dict:
        """Parse semua data sarpen"""
        # Ekstrak section sarpen
        match_sarpen = re.search(
            r"INFORMASI SARPEN DAN RUANG SERVER PELANGGAN([\s\S]*?Perangkat Pelanggan[\s\S]*?)(?=$)",
            self.text, re.IGNORECASE
        )
        
        sarpen_text = match_sarpen.group(1) if match_sarpen else self.text
        lines = [line.strip() for line in sarpen_text.splitlines() if line.strip()]
        
        data = {}
        for label in self.labels:
            key = self.key_normalizer.normalize(label)
            value = self._extract_value(label, lines)
            data[key] = value
        
        return data
    
    def _extract_value(self, label: str, lines: List[str]) -> Optional[str]:
        """Extract value untuk label tertentu"""
        for i, line in enumerate(lines):
            # Pola 1: Label dan isi di satu baris
            pattern_inline = rf"^{re.escape(label)}\s*[:\-–=]\s*(.+)$"
            match = re.match(pattern_inline, line, re.IGNORECASE)
            if match:
                return match.group(1).strip()
            
            # Pola 2: Label di baris ini, isi di baris berikutnya
            if re.fullmatch(re.escape(label), line, re.IGNORECASE):
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Cegah ambil label lain
                    if not any(re.fullmatch(re.escape(l), next_line, re.IGNORECASE) for l in self.labels):
                        return next_line
                return None
        
        return None


class LokasiAntenaParser:
    """Parser khusus untuk bagian LOKASI ANTENA"""
    
    def __init__(self, text: str, labels: List[str]):
        self.text = self._extract_section(text)
        self.labels = labels
        self.key_normalizer = KeyNormalizer()
    
    def _extract_section(self, text: str) -> str:
        """Ekstrak section lokasi antena"""
        match = re.search(
            r"INFORMASI LOKASI ANTENA([\s\S]*?)(?=SURVEY REPORT|INFORMASI PERIZINAN|\Z)",
            text, re.IGNORECASE
        )
        section_text = match.group(1) if match else text
        return TextNormalizer.clean(section_text)
    
    def parse(self) -> dict:
        """Parse semua data lokasi antena"""
        lines = [line.strip() for line in self.text.splitlines() if line.strip()]
        
        # Hilangkan header jika ada
        if lines and "INFORMASI LOKASI ANTENA" in lines[0].upper():
            lines = lines[1:]
        
        data = {}
        i = 0
        
        while i < len(lines):
            line = lines[i]
            matched_label = self._find_matching_label(line)
            
            if matched_label:
                key = self.key_normalizer.normalize(matched_label)
                value = None
                
                # Ambil nilai dari baris berikutnya jika ada
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if not self._find_matching_label(next_line) and next_line:
                        value = next_line
                        i += 1
                
                data[key] = value
            
            i += 1
        
        return data
    
    def _find_matching_label(self, line: str) -> Optional[str]:
        """Cari label yang cocok dengan baris"""
        for lbl in self.labels:
            if re.fullmatch(re.escape(lbl), line, re.IGNORECASE):
                return lbl
        return None
"""
Section Parsers Part 2 - Tambahkan ini ke file section_parsers.py yang sudah ada
"""
import re
from typing import Optional, Dict, List
from .text_utils import TextNormalizer, KeyNormalizer


class PerizinanBiayaGedungParser:
    """Parser khusus untuk PERIZINAN DAN BIAYA GEDUNG"""
    
    def __init__(self, text: str, labels: List[str]):
        self.text = self._extract_section(text)
        self.labels = labels
        self.key_normalizer = KeyNormalizer()
    
    def _extract_section(self, text: str) -> str:
        """Ekstrak section perizinan biaya gedung"""
        match = re.search(
            r"DATA\s*PERIZINAN\s*DAN\s*BIAYA\s*YANG\s*TIMBUL\s*DALAM\s*GEDUNG([\s\S]*?)(?=INFORMASI SARPEN|DOKUMENTASI FOTO|\Z)",
            text, re.IGNORECASE
        )
        section_text = match.group(1) if match else text
        return TextNormalizer.clean(section_text)
    
    def parse(self) -> dict:
        """Parse data perizinan biaya gedung"""
        lines = [line.strip() for line in self.text.splitlines() if line.strip()]
        
        if lines and "DATA PERIZINAN" in lines[0].upper():
            lines = lines[1:]
        
        data = {}
        i = 0
        
        while i < len(lines):
            line = lines[i]
            matched_label = self._find_matching_label(line)
            
            if matched_label:
                key = self.key_normalizer.normalize(matched_label)
                
                # Skip jika label sudah ada (hindari duplikat)
                if key in data:
                    i += 1
                    continue
                
                value = None
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if not self._find_matching_label(next_line) and next_line:
                        value = next_line
                        i += 1
                
                data[key] = value
            
            i += 1
        
        return data
    
    def _find_matching_label(self, line: str) -> Optional[str]:
        for lbl in self.labels:
            if re.fullmatch(re.escape(lbl), line, re.IGNORECASE):
                return lbl
        return None


class PenempatanPerangkatParser:
    """Parser khusus untuk PENEMPATAN PERANGKAT"""
    
    def __init__(self, text: str, labels: List[str]):
        self.text = self._extract_section(text)
        self.labels = labels
        self.key_normalizer = KeyNormalizer()
    
    def _extract_section(self, text: str) -> str:
        """Ekstrak section penempatan perangkat"""
        match = re.search(
            r"DATA\s*PENEMPATAN\s*PERANGKAT\s*DI\s*LOKASI\s*PELANGGAN([\s\S]*?)(?=FOTO\s*PENEMPATAN|DOKUMENTASI|\Z)",
            text, re.IGNORECASE
        )
        section_text = match.group(1) if match else text
        return TextNormalizer.clean(section_text)
    
    def parse(self) -> dict:
        """Parse data penempatan perangkat"""
        lines = [line.strip() for line in self.text.splitlines() if line.strip()]
        
        if lines and "DATA PENEMPATAN" in lines[0].upper():
            lines = lines[1:]
        
        data = {}
        i = 0
        
        while i < len(lines):
            line = lines[i]
            matched_label = self._find_matching_label(line)
            
            if matched_label:
                key = self.key_normalizer.normalize(matched_label)
                
                if key in data:
                    i += 1
                    continue
                
                value = None
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if not self._find_matching_label(next_line) and next_line:
                        value = next_line
                        i += 1
                
                data[key] = value
            
            i += 1
        
        return data
    
    def _find_matching_label(self, line: str) -> Optional[str]:
        for lbl in self.labels:
            if re.fullmatch(re.escape(lbl), line, re.IGNORECASE):
                return lbl
        return None


class PerizinanBiayaKawasanParser:
    """Parser khusus untuk PERIZINAN BIAYA KAWASAN"""
    
    def __init__(self, text: str, labels: List[str]):
        self.text = self._extract_section(text)
        self.labels = labels
        self.key_normalizer = KeyNormalizer()
    
    def _extract_section(self, text: str) -> str:
        """Ekstrak section perizinan biaya kawasan"""
        match = re.search(
            r"DATA\s*PERIZINAN\s*DAN\s*BIAYA\s*YANG\s*TIMBUL\s*DALAM\s*KAWASAN([\s\S]*?)(?=DATA\s*KAWASAN\s*UMUM|\Z)",
            text, re.IGNORECASE
        )
        section_text = match.group(1) if match else text
        return TextNormalizer.clean(section_text)
    
    def parse(self) -> dict:
        """Parse data perizinan biaya kawasan"""
        lines = [line.strip() for line in self.text.splitlines() if line.strip()]
        data = {}
        i = 0
        
        while i < len(lines):
            line = lines[i]
            matched_label = self._find_matching_label(line)
            
            if matched_label:
                key = self.key_normalizer.normalize(matched_label)
                value = None
                
                # Cek horizontal (label dan value dalam 1 baris)
                horizontal_match = re.match(
                    rf"{re.escape(matched_label)}\s*[:\-]?\s*(.+)", 
                    line, 
                    re.IGNORECASE
                )
                
                if horizontal_match and horizontal_match.group(1).strip():
                    value = horizontal_match.group(1).strip()
                else:
                    # Ambil dari baris berikutnya
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if not self._find_matching_label(next_line) and next_line:
                            value = next_line
                            i += 1
                
                data[key] = value
            
            i += 1
        
        return data
    
    def _find_matching_label(self, line: str) -> Optional[str]:
        for lbl in self.labels:
            if re.match(re.escape(lbl), line, re.IGNORECASE):
                return lbl
        return None


class KawasanUmumParser:
    """Parser khusus untuk KAWASAN UMUM"""
    
    def __init__(self, text: str, labels: List[str]):
        self.text = self._extract_section(text)
        self.labels = labels
        self.key_normalizer = KeyNormalizer()
    
    def _extract_section(self, text: str) -> str:
        """Ekstrak section kawasan umum"""
        match = re.search(
            r"DATA\s*KAWASAN\s*UMUM([\s\S]*?)(?=DATA\s*JALUR\s*KABEL|\Z)",
            text, re.IGNORECASE
        )
        section_text = match.group(1) if match else text
        return TextNormalizer.clean(section_text)
    
    def parse(self) -> dict:
        """Parse data kawasan umum"""
        lines = [line.strip() for line in self.text.splitlines() if line.strip()]
        data = {}
        i = 0
        
        while i < len(lines):
            line = lines[i]
            matched_label = self._find_matching_label(line)
            
            if matched_label:
                key = self.key_normalizer.normalize(matched_label)
                value = None
                
                horizontal_match = re.match(
                    rf"{re.escape(matched_label)}\s*[:\-]?\s*(.+)", 
                    line, 
                    re.IGNORECASE
                )
                
                if horizontal_match and horizontal_match.group(1).strip():
                    value = horizontal_match.group(1).strip()
                else:
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if not self._find_matching_label(next_line) and next_line:
                            value = next_line
                            i += 1
                
                data[key] = value
            
            i += 1
        
        return data
    
    def _find_matching_label(self, line: str) -> Optional[str]:
        for lbl in self.labels:
            if re.match(re.escape(lbl), line, re.IGNORECASE):
                return lbl
        return None


class DataSplitterParser:
    """Parser khusus untuk DATA SPLITTER"""
    
    def __init__(self, text: str, labels: List[str]):
        self.text = self._extract_section(text)
        self.labels = labels
        self.key_normalizer = KeyNormalizer()
    
    def _extract_section(self, text: str) -> str:
        """Ekstrak section data splitter"""
        match = re.search(
            r"DATA\s*SPLITTER([\s\S]*?)(?=FOTO\s*SPLITTER|DATA\s*|DOKUMENTASI|\Z)",
            text, re.IGNORECASE
        )
        section_text = match.group(1) if match else text
        return TextNormalizer.clean(section_text)
    
    def parse(self) -> dict:
        """Parse data splitter"""
        lines = [line.strip() for line in self.text.splitlines() if line.strip()]
        data = {}
        i = 0
        
        while i < len(lines):
            line = lines[i]
            matched_label = self._find_matching_label(line)
            
            if matched_label:
                key = self.key_normalizer.normalize(matched_label)
                value = None
                
                # Coba ambil value di baris yang sama (horizontal)
                horizontal_match = re.match(
                    rf"{re.escape(matched_label)}\s*[:\-]?\s*(.+)", 
                    line, 
                    re.IGNORECASE
                )
                
                if horizontal_match and horizontal_match.group(1).strip():
                    value = horizontal_match.group(1).strip()
                else:
                    # Ambil dari baris berikutnya (vertikal)
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if not self._find_matching_label(next_line) and next_line:
                            value = next_line
                            i += 1
                
                data[key] = value
            
            i += 1
        
        return data
    
    def _find_matching_label(self, line: str) -> Optional[str]:
        for lbl in self.labels:
            if re.match(re.escape(lbl), line, re.IGNORECASE):
                return lbl
        return None


class DataHHParser:
    """Parser khusus untuk DATA HH (Eksisting dan Baru)"""
    
    def __init__(self, text: str, tipe: str):
        """
        Args:
            text: Full text dokumen
            tipe: 'eksisting' atau 'baru'
        """
        self.text = self._extract_section(text, tipe)
        self.tipe = tipe
        self.key_normalizer = KeyNormalizer()
    
    def _extract_section(self, text: str, tipe: str) -> str:
        """Ekstrak section data HH"""
        if tipe == "eksisting":
            pattern = r"DATA\s*HH\s*EKSISTING\s*YANG\s*DIPAKAI([\s\S]*?)(?=SURVEY REPORT FO|\Z)"
        else:
            pattern = r"DATA\s*HH\s*BARU([\s\S]*?)(?=FOTO LOKASI HH BARU|\Z)"
        
        match = re.search(pattern, text, re.IGNORECASE)
        section_text = match.group(1).strip() if match else ""
        
        # Normalisasi
        section_text = re.sub(r"[\r\t]+", " ", section_text)
        section_text = re.sub(r" {2,}", " ", section_text)
        section_text = re.sub(r"\n+", "\n", section_text)
        
        return section_text
    
    def parse(self) -> dict:
        """Parse data HH"""
        if not self.text:
            return {}
        
        lines = [line.strip() for line in self.text.splitlines() if line.strip()]
        data = {}
        current_hh = None
        
        # Label pattern
        label_pattern = re.compile(
            r"^(Kondisi HH-\d+|Lokasi HH-\d+|Longitude dan Latitude HH-\d+|"
            r"Ketersediaan Closure-\d+|Kapasitas Closure-\d+|Kondisi Closure-\d+|"
            r"Kebutuhan penambahan Closure-\d+)$",
            re.IGNORECASE
        )
        
        for i, line in enumerate(lines):
            # Deteksi header HH baru
            match_hh = re.match(r"Data\s*HH\s*(\d+)", line, re.IGNORECASE)
            if match_hh:
                current_hh = f"hh_{match_hh.group(1)}"
                data[current_hh] = {}
                continue
            
            if not current_hh:
                continue
            
            # Deteksi label
            if label_pattern.match(line):
                key = self.key_normalizer.normalize(line)
                value = None
                
                # Cek apakah baris berikutnya adalah nilai
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if not label_pattern.match(next_line) and not re.match(r"Data\s*HH", next_line, re.IGNORECASE):
                        value = next_line
                
                data[current_hh][key] = value
        
        return data