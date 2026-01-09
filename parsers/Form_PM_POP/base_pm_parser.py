"""
Base PM Parser - Parent class untuk semua Form PM POP parser
Taruh file ini di: parsers/Form_PM_POP/base_pm_parser.py
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict
import re


class BasePMParser(ABC):
    """
    Base class untuk semua parser Form PM POP
    Aman untuk template kosong dan dokumen terisi
    """

    # Label yang TIDAK BOLEH dianggap sebagai value
    INVALID_VALUES = {
        "date / time",
        "reg. number",
        "brand / type",
        "s/n",
        "kapasitas",
        "no.",
        "location",
        "department",
        "sub department"
    }

    def __init__(self, all_text: str, page_texts: list, ocr_data: list = None):
        self.all_text = all_text or ""
        self.page_texts = page_texts or []
        self.ocr_data = ocr_data or []

    # ======================================================
    # ABSTRACT
    # ======================================================
    @abstractmethod
    def parse(self) -> dict:
        pass

    # ======================================================
    # INIT STRUCTURE
    # ======================================================
    def _init_pm_structure(self) -> dict:
        return {
            "header": {
                "no_dok": None,
                "judul_formulir": None,
                "versi": None,
                "halaman": None,
                "label": None
            },
            "informasi_umum": {
                "location": None,
                "date_time": None,
                "reg_number": None,
                "brand_type": None,
                "serial_number": None,
                "kapasitas": None
            },
            "checklist_items": [],
            "notes": None,
            "pelaksana": []
        }

    # ======================================================
    # HEADER
    # ======================================================
    def extract_header(self) -> dict:
        return {
        "no_dok": self.find_nearest_value("No.Dok"),
        "judul_formulir": "Preventive Maintenance",
        "versi": self.find_nearest_value("Versi"),
        "halaman": self.find_nearest_value("Hal"),
        "label": self.find_nearest_value("Label"),
    }

    # ======================================================
    # INFORMASI UMUM (AMAN UNTUK TEMPLATE)
    # ======================================================
    def extract_informasi_umum(self) -> dict:
        return {
        "location": self.find_nearest_value("Location"),
        "date_time": self.find_nearest_value("Date"),
        "reg_number": self.find_nearest_value("Reg"),
        "brand_type": self.find_nearest_value("Brand"),
        "serial_number": self.find_nearest_value("S/N"),
        "kapasitas": self.find_nearest_value("Kapasitas"),
    }

    def _extract_field(self, label: str) -> Optional[str]:
        """
        Extract field HANYA jika benar-benar ada isinya.
        Label ≠ value.
        """
        pattern = rf"{re.escape(label)}\s*:\s*(.+)"
        match = re.search(pattern, self.all_text, re.IGNORECASE)

        if not match:
            return None

        value = match.group(1).strip()
        value_clean = value.lower()

        if not value:
            return None

        if value_clean in self.INVALID_VALUES:
            return None

        return value

    # ======================================================
    # NOTES
    # ======================================================
    def extract_notes(self) -> Optional[str]:
        match = re.search(
            r"Notes\s*/\s*additional\s+informations?\s*:\s*(.*)",
            self.all_text,
            re.IGNORECASE | re.DOTALL
        )

        if not match:
            return None

        value = match.group(1).strip()

        # Jika yang ketangkap justru footer
        if "Pelaksana" in value or "Mengetahui" in value:
            return None

        return value if value else None

    # ======================================================
    # PELAKSANA
    # ======================================================
    def extract_pelaksana(self) -> List[Dict]:
        pelaksana = []

        section = re.search(
            r"Pelaksana\s+Mengetahui(.*?)(?=\Z)",
            self.all_text,
            re.IGNORECASE | re.DOTALL
        )

        if not section:
            return pelaksana

        lines = section.group(1).splitlines()

        for line in lines:
            line = line.strip()
            if not line or "Nama" in line or "(" in line:
                continue

            parts = re.split(r"\s{2,}|\|", line)
            parts = [p.strip() for p in parts if p.strip()]

            if len(parts) >= 2:
                pelaksana.append({
                    "nama": parts[1] if len(parts) > 1 else None,
                    "department": parts[2] if len(parts) > 2 else None,
                    "sub_department": parts[3] if len(parts) > 3 else None
                })

        return pelaksana

    # ======================================================
    # UTIL
    # ======================================================
    def search_regex(self, pattern: str, text: str = None, multiline: bool = False) -> Optional[str]:
        if text is None:
            text = self.all_text

        if multiline:
            text = re.sub(r"\s+", " ", text)

        flags = re.IGNORECASE | (re.DOTALL if multiline else 0)
        match = re.search(pattern, text, flags)

        if not match:
            return None

        return match.group(1).strip() if match.lastindex else match.group(0).strip()

    def _safe_value(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None

        val = value.strip()
        if val.lower() in self.INVALID_VALUES:
            return None

        return val
    
    def find_value_after_label(self, label: str, max_distance=80):
        """
        Cari nilai di OCR data setelah label tertentu (layout-aware)
        """
        if not self.ocr_data:
            return ""

        # flatten OCR
        flat = [item for page in self.ocr_data for item in page]

        for i, item in enumerate(flat):
            if label.lower() in item["text"].lower():
                y_label = item["position"][0]

                # cari teks di kanan / bawah label
                candidates = []
                for other in flat:
                    if abs(other["position"][0] - y_label) < max_distance:
                        if other["position"][1] > item["position"][1]:
                            candidates.append(other)

                if candidates:
                    candidates.sort(key=lambda x: x["position"][1])
                    return candidates[0]["text"]

        return ""
    
    def find_nearest_value(self, label: str, y_tolerance=25, x_min_offset=10):
        """
        Cari nilai terdekat dari label berdasarkan posisi OCR (KANAN atau BAWAH)
        """
        if not self.ocr_data:
            return ""

        flat = [item for page in self.ocr_data for item in page]

        label_item = None
        for item in flat:
            if label.lower() in item["text"].lower():
                label_item = item
                break

        if not label_item:
            return ""

        lx, ly = label_item["position"][1], label_item["position"][0]

        candidates = []
        for item in flat:
            ix, iy = item["position"][1], item["position"][0]

            # 1️⃣ kanan satu baris
            if abs(iy - ly) <= y_tolerance and ix > lx + x_min_offset:
                candidates.append((abs(ix - lx), item))

            # 2️⃣ tepat di bawah
            elif iy > ly and abs(ix - lx) <= 60:
                candidates.append((abs(iy - ly), item))

        if not candidates:
            return ""

        # ambil yang paling dekat
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]["text"]


