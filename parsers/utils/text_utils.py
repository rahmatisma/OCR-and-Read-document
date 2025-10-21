"""
Utility functions untuk text processing
Taruh file ini di: parsers/utils/text_utils.py
"""
import re
from typing import Optional


class TextNormalizer:
    """Class untuk normalisasi teks"""
    
    @staticmethod
    def normalize(raw_text: str) -> str:
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
    
    @staticmethod
    def clean(text: str) -> str:
        """Membersihkan teks agar lebih mudah diproses"""
        text = re.sub(r"[\r\t]+", " ", text)
        text = re.sub(r" {2,}", " ", text)
        text = re.sub(r"\n+", "\n", text)
        return text
    
    @staticmethod
    def normalize_dash(text: str) -> str:
        """Normalisasi berbagai jenis dash jadi dash standar"""
        return text.replace("−", "-").replace("–", "-").replace("—", "-").replace("―", "-")


class RegexSearcher:
    """Class untuk pencarian regex yang robust"""
    
    @staticmethod
    def search(pattern: str, text: str, allow_multiline: bool = False) -> Optional[str]:
        """
        Fungsi pencarian regex yang lebih tangguh untuk hasil OCR PDF.
        
        Args:
            pattern: Regex pattern untuk search
            text: Text yang akan di-search
            allow_multiline: Jika True, newline dianggap spasi
            
        Returns:
            Hasil match atau None
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


class KeyNormalizer:
    """Class untuk normalisasi key JSON"""
    
    @staticmethod
    def normalize(label: str) -> str:
        """
        Normalisasi label jadi snake_case untuk key JSON
        
        Example:
            "Status Gedung" -> "status_gedung"
            "PIC BM" -> "pic_bm"
        """
        key = (
            label.lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace(".", "")
            .replace("(", "")
            .replace(")", "")
            .replace("-", "_")
        )
        
        # Special replacements
        key = key.replace("bersedia_dipasang_perangkat", "fo")
        key = key.replace("penanggungjawab_pengurusan_dan_pembayaran_sewa", "penanggungjawab_sewa")
        
        return key


class SectionExtractor:
    """Class untuk ekstraksi section tertentu dari teks"""
    
    @staticmethod
    def extract_between(text: str, start_pattern: str, end_pattern: str) -> str:
        """
        Ekstrak teks antara dua pattern
        
        Args:
            text: Text lengkap
            start_pattern: Pattern awal section
            end_pattern: Pattern akhir section
            
        Returns:
            Text section yang di-extract
        """
        pattern = rf"{start_pattern}([\s\S]*?)(?={end_pattern}|\Z)"
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else ""