"""
Base PM Parser - FIXED VERSION V2
 FIXED V2: Better pelaksana extraction (handle multiple whitespace patterns)
 FIXED V2: More robust regex patterns
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Tuple
import re


class BasePMParser(ABC):
    """
    Base class untuk semua parser Form PM POP
    Support untuk text-based dan OCR-based PDF
    """

    # Invalid values (labels bukan value)
    INVALID_VALUES = {
        "date / time", "date", "time",
        "reg. number", "reg number", "reg.number",
        "brand / type", "brand", "type",
        "s/n", "sn", "serial number",
        "kapasitas", "capacity",
        "no.", "no",
        "location", "lokasi",
        "department", "dept",
        "sub department", "sub dept"
    }

    def __init__(self, all_text: str, page_texts: list, ocr_data: list = None):
        self.all_text = all_text or ""
        self.page_texts = page_texts or []
        self.ocr_data = ocr_data or []

    # ======================================================
    # ABSTRACT METHOD
    # ======================================================
    @abstractmethod
    def parse(self) -> dict:
        """Must be implemented by child classes"""
        pass

    # ======================================================
    # HEADER EXTRACTION (REGEX-BASED)
    # ======================================================
    def extract_header(self) -> dict:
        """
        Extract header dengan regex yang table-aware
        
        Format di PDF:
        No. Dok. : FM-LAP-D2-SOP-003-005    Formulir              Versi : 1.0
        Preventive Maintenance              Hal : 1 dari 1
        Inverter -48VDC/220VAC              Label : Internal
        """
        return {
            "no_dok": self._extract_field_value("No\\.\\s*Dok\\.?\\s*:", "Formulir"),
            "judul": self._extract_judul_formulir(),
            "versi": self._extract_field_value("Versi\\s*:", "Hal"),
            "halaman": self._extract_field_value("Hal\\s*:", "Label"),
            "label": self._extract_field_value("Label\\s*:", "Location|HakCipta|$")
        }

    def _extract_field_value(self, field_pattern: str, stop_pattern: str) -> str:
        """
        Extract value antara field_pattern dan stop_pattern
        
        Args:
            field_pattern: Regex pattern untuk field label (e.g., "No\\.\\s*Dok\\.?\\s*:")
            stop_pattern: Pattern untuk berhenti (e.g., "Formulir")
            
        Returns:
            Extracted value (cleaned)
        """
        # Pattern: "Field : VALUE (stop sebelum stop_pattern)"
        pattern = rf"{field_pattern}\s*([^\n]+?)(?=\s*{stop_pattern}|\n|$)"
        match = re.search(pattern, self.all_text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            # Clean common artifacts
            value = re.sub(r'\s{2,}', ' ', value)  # Multiple spaces
            value = value.strip(' :：')
            
            # Validate bukan label lain
            if value.lower() not in self.INVALID_VALUES and len(value) > 0:
                return value
        
        return ""

    def _extract_judul_formulir(self) -> str:
        """
        Extract judul formulir (biasanya multi-line)
        
        Contoh:
        Formulir
        Preventive Maintenance 
        Inverter -48VDC/220VAC
        """
        # Try to find text between "Formulir" and "Versi"
        pattern = r"Formulir\s*(.*?)\s*Versi\s*:"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            judul = match.group(1).strip()
            # Clean newlines and multiple spaces
            judul = re.sub(r'\s*\n\s*', ' ', judul)
            judul = re.sub(r'\s{2,}', ' ', judul)
            return judul
        
        return "Preventive Maintenance"

    # ======================================================
    # INFORMASI UMUM EXTRACTION
    # ======================================================
    def extract_informasi_umum(self) -> dict:
        """
        Extract informasi umum dengan field-by-field regex
        
        Format:
        Location        : Grand Mall Bekasi
        Date / time     : Sabtu, 31 Januari 2025
        Brand / Type    : Matrik
        Reg. Number     : -
        S/N             : 126721651256
        """
        return {
            "location": self._extract_simple_field(r"Location\s*:", r"Date|Brand|Reg|S/N|\n\n"),
            "date_time": self._extract_simple_field(r"Date\s*/?\s*time\s*:", r"Brand|Reg|S/N|Type|\n\n"),
            "brand_type": self._extract_simple_field(r"Brand\s*/?\s*Type\s*:", r"Reg|S/N|Kapasitas|\n\n"),
            "reg_number": self._extract_simple_field(r"Reg\.?\s*Number\s*:", r"S/N|Brand|Type|\n\n"),
            "serial_number": self._extract_simple_field(r"S\s*/?\s*N\s*:", r"No\.|Result|Descriptions|\n\n"),
        }

    def _extract_simple_field(self, label_pattern: str, stop_pattern: str) -> str:
        """
        Extract simple field dengan regex
        
        Args:
            label_pattern: Pattern untuk label (e.g., r"Location\\s*:")
            stop_pattern: Pattern untuk berhenti (e.g., r"Date|Brand")
        """
        pattern = rf"{label_pattern}\s*([^\n]+?)(?=\s*(?:{stop_pattern})|\n\s*\n|$)"
        match = re.search(pattern, self.all_text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            value = value.strip(' :：-')
            
            # Validate
            if value and value.lower() not in self.INVALID_VALUES:
                return value
        
        return ""

    # ======================================================
    # NOTES EXTRACTION
    # ======================================================
    def extract_notes(self) -> Optional[str]:
        """
        Extract notes/additional information
        
        Pattern: "Notes / additional informations : VALUE"
        Stop before: Executor/Pelaksana section
        """
        pattern = r"Notes\s*/\s*additional\s+informations?\s*:\s*(.*?)(?=Executor|Pelaksana|Verifikator|$)"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            return None
        
        notes = match.group(1).strip()
        
        # Clean multiple newlines and spaces
        notes = re.sub(r'\n\s*\n', '\n', notes)
        notes = re.sub(r'\s{2,}', ' ', notes)
        
        return notes if notes else None

    # ======================================================
    # PELAKSANA EXTRACTION - FIXED V2
    # ======================================================
    def extract_pelaksana(self) -> dict:
        """
        Extract pelaksana dari section Executor.
        Handles VERTICAL format (tiap field di baris terpisah)
        dan HORIZONTAL format (satu baris) sebagai fallback.
        """
        print("[PM POLE TOWER] Extracting pelaksana...")

        pelaksana = {
            "executor": [],
            "verifikator": None,
            "head_of_sub_department": None,
        }

        # Cari section setelah header tabel "No Nama Mitra / Internal Signature"
        section_match = re.search(
            r"No\s+Nama\s+Mitra\s*/\s*Internal\s+Signature\s*(.*?)$",
            self.all_text,
            re.IGNORECASE | re.DOTALL,
        )

        if not section_match:
            print("[PM POLE TOWER]   ⚠️ Pelaksana section tidak ditemukan")
            return pelaksana

        lines = [
            line.strip()
            for line in section_match.group(1).split("\n")
            if line.strip()
        ]

        i = 0
        while i < len(lines):
            line = lines[i]

            # Skip signature separators dan placeholders
            if "___" in line or re.match(r"^\(\s*_+", line):
                i += 1
                continue

            # --- VERTICAL format: line hanya angka (= "no" executor) ---
            # Scan lines berikutnya untuk nama + mitra sampai angka baru
            if re.match(r"^\d+$", line):
                no = line
                nama = ""
                mitra = ""

                j = i + 1
                collected = []
                while j < len(lines):
                    next_line = lines[j]
                    # Stop: angka baru = executor berikutnya
                    if re.match(r"^\d+$", next_line):
                        break
                    # Stop: placeholder signature
                    if "___" in next_line or re.match(r"^\(\s*_+", next_line):
                        break
                    collected.append(next_line)
                    j += 1

                # collected[0] = nama, collected[1] = mitra
                if len(collected) >= 1:
                    nama = collected[0]
                if len(collected) >= 2:
                    mitra = collected[1]

                # Tambahkan hanya kalau ada nama
                if nama:
                    pelaksana["executor"].append(
                        {
                            "no": no,
                            "Nama": nama,
                            "Mitra / internal": mitra,
                        }
                    )
                    print(
                        f"[PM POLE TOWER]   ✓ Executor #{no}: {nama}"
                    )

                i = j  # jump past collected lines
                continue

            # --- HORIZONTAL format fallback: "1 Azki IMS" ---
            parts = line.split()
            if len(parts) >= 2 and parts[0].isdigit():
                if not parts[1].startswith("("):
                    pelaksana["executor"].append(
                        {
                            "no": parts[0],
                            "Nama": parts[1],
                            "Mitra / internal": (
                                parts[2] if len(parts) > 2 else ""
                            ),
                        }
                    )
                    print(
                        f"[PM POLE TOWER]   ✓ Executor #{parts[0]}: {parts[1]}"
                    )

            i += 1

        return pelaksana

    # ======================================================
    # MULTI-OPTION FIELD EXTRACTION (untuk Capacity Selection)
    # ======================================================
    def extract_multi_option_field(self, field_no: str, description: str, 
                                   options: List[Tuple[str, str]], 
                                   result_value: str) -> Dict:
        """
        Extract multi-option field dengan deteksi opsi yang dipilih
        
        Args:
            field_no: Nomor field (e.g., "2.b")
            description: Deskripsi field (e.g., "DC Current Input")
            options: List of (capacity, standard) tuples
            result_value: Nilai result (e.g., "1,01")
        
        Returns:
            Multi-option field dict
        """
        # Build capacity_options array
        capacity_options = [
            {"capacity": cap, "standard": std}
            for cap, std in options
        ]
        
        # Detect which capacity is selected
        capacity_detected = self._detect_selected_capacity(description, options, result_value)
        
        # Find the standard for selected capacity
        standard_selected = ""
        for cap, std in options:
            if cap == capacity_detected:
                standard_selected = f"{std} ({cap})"
                break
        
        # Extract status
        status = self._extract_status_for_field(description)
        
        return {
            "no": field_no,
            "description": description,
            "result": result_value,
            "capacity_options": capacity_options,
            "capacity_detected": capacity_detected,
            "standard_selected": standard_selected,
            "status": status
        }

    def _detect_selected_capacity(self, description: str, options: List[Tuple[str, str]], 
                                  result_value: str) -> str:
        """
        Detect which capacity option is selected
        
        Methods:
        1. Symbol detection
        2. Proximity detection
        3. Value matching
        """
        # Method 1: Symbol detection
        for capacity, standard in options:
            symbol_pattern = rf"[≤☑✓✔√⊠xX\*]\s*{re.escape(standard)}\s*\(\s*{re.escape(capacity)}\s*\)"
            if re.search(symbol_pattern, self.all_text, re.IGNORECASE):
                return capacity
        
        # Method 2: Proximity detection
        desc_pattern = re.escape(description)
        section_match = re.search(rf"{desc_pattern}.*?{result_value}.*?(?=\n\s*[a-z]\.|Notes|Executor|$)", 
                                 self.all_text, re.IGNORECASE | re.DOTALL)
        
        if section_match:
            section_text = section_match.group(0)
            for capacity, standard in options:
                if re.search(rf"{re.escape(standard)}.*?\(\s*{re.escape(capacity)}\s*\)", section_text, re.IGNORECASE):
                    return capacity
        
        # Method 3: Value matching (fallback)
        try:
            result_float = float(result_value.replace(",", ".").replace("-", "0"))
            
            min_diff = float('inf')
            closest_capacity = options[0][0] if options else ""
            
            for capacity, standard in options:
                std_match = re.search(r'(\d+[\.,]?\d*)', standard)
                if std_match:
                    std_value = float(std_match.group(1).replace(",", "."))
                    diff = abs(result_float - std_value)
                    if diff < min_diff:
                        min_diff = diff
                        closest_capacity = capacity
            
            return closest_capacity
        except (ValueError, IndexError):
            pass
        
        return options[0][0] if options else ""

    def _extract_status_for_field(self, description: str) -> str:
        """Extract status (OK/NOK) for a specific field"""
        pattern = rf"{re.escape(description)}.*?(OK|NOK)"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            return match.group(1)
        
        return ""