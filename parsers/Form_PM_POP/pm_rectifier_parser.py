"""
Parser untuk Form PM Rectifier - SIMPLIFIED VERSION
Document Code: FM-LAP-D2-SOP-003-007

 Simplified - inherit dari BasePMParser
 Multi-capacity support dengan logic yang benar
 Item 1.d: "Installed" ada di description
 Item 2.b: Tidak ada capacity_detected jika result kosong

Struktur Dokumen:
1. Header
2. Informasi Umum (Location, Date/time, Brand/Type, Reg, S/N, Kap.Power Module)
3. Physical Check (5 items: a-e)
4. Performance and Capacity Check (5 items: a-e)
5. Backup Tests (2 items: 3-4)
6. Notes
7. Pelaksana
"""

from parsers.Form_PM_POP.base_pm_parser import BasePMParser
from typing import Dict, List, Tuple
import re


class PMRectifierParser(BasePMParser):
    """Parser untuk Form Preventive Maintenance Rectifier"""
    
    def __init__(self, all_text: str, page_texts: list, ocr_data: list = None):
        super().__init__(all_text, page_texts, ocr_data)
        
        # AC Current Input options (2.b)
        self.AC_CURRENT_OPTIONS = [
            ("Single Power Module", "5.5 A"),
            ("Dual Power Module", "11 A"),
            ("Three Power Module", "16.5 A")
        ]
        
        # DC Current Output options (2.c)
        self.DC_CURRENT_OPTIONS = [
            ("Single Power Module", "25 A"),
            ("Dual Power Module", "50 A"),
            ("Three Power Module", "75 A")
        ]
    
    def parse(self) -> dict:
        """Parse dokumen Form PM Rectifier"""
        print("\n[PM RECTIFIER] Memulai parsing...")
        
        result = {
            "header": self.extract_header(),
            "informasi_umum": self.extract_informasi_umum_rectifier(),
            "physical_check": self.extract_physical_check(),
            "performance_capacity_check": self.extract_performance_capacity_check(),
            "backup_tests": self.extract_backup_tests(),
            "notes": self.extract_notes(),
            "pelaksana": self.extract_pelaksana_rectifier()
        }
        
        print("[PM RECTIFIER]  Parsing selesai!")
        return result
    
    # ================================================================
    # INFORMASI UMUM
    # ================================================================
    def extract_informasi_umum_rectifier(self) -> dict:
        """Extract informasi umum dengan field Kap.Power Module"""
        print("[PM RECTIFIER] Parsing Informasi Umum...")
        
        info = {
            "location": self._extract_simple_field(r"Location\s*:", r"Date|Brand|Reg|\n\n"),
            "date_time": self._extract_simple_field(r"Date\s*/?\s*time\s*:", r"Reg|Brand|S/N|\n\n"),
            "brand_type": self._extract_simple_field(r"Brand\s*/?\s*Type\s*:", r"S/N|Reg|Kap\.|\n\n"),
            "reg_number": self._extract_simple_field(r"Reg\.?\s*Number\s*:", r"Brand|S/N|Type|\n\n"),
            "serial_number": self._extract_simple_field(r"S\s*/?\s*N\s*:", r"Kap\.|No\.|Descriptions|\n\n"),
            "kap_power_module": self._extract_capacity_power_module()
        }
        
        return info
    
    def _extract_capacity_power_module(self) -> str:
        """Extract Kap.Power Module (Single/Dual/Three)"""
        pattern = r"Kap\.?\s*Power\s+Module\s*:\s*(Single|Dual|Three)"
        match = re.search(pattern, self.all_text, re.IGNORECASE)
        return match.group(1).strip() if match else ""
    
    # ================================================================
    # PHYSICAL CHECK (Section 1)
    # ================================================================
    def extract_physical_check(self) -> List[Dict]:
        """Extract Physical Check items"""
        print("[PM RECTIFIER] Parsing Physical Check...")
        
        items = []
        
        # Find section
        section_pattern = r"1\.\s*Physical\s+Check\s*(.*?)(?=2\.?\s*Performance|Notes|$)"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            return items
        
        section_text = section_match.group(1)
        
        # 1.a - Environment Condition
        a_item = self._extract_standard_item(section_text, "a", "Environment Condition", 
                                              r"a\.\s*Environment\s+Condition\s+(\w+)\s+(.*?)\s+(OK|NOK)",
                                              "Clean, No dust")
        if a_item:
            items.append(a_item)
        
        # 1.b - LED / display
        b_item = self._extract_standard_item(section_text, "b", "LED / display",
                                              r"b\.\s*LED\s*/\s*display\s+(\w+)\s+(.*?)\s+(OK|NOK)",
                                              "Normal")
        if b_item:
            items.append(b_item)
        
        # 1.c - Battery Connection
        c_item = self._extract_standard_item(section_text, "c", "Battery Connection",
                                              r"c\.\s*Battery\s+Connection\s+(\w+)\s+(.*?)\s+(OK|NOK)",
                                              "Tighten, No Corrosion")
        if c_item:
            items.append(c_item)
        
        # 1.d - Rectifier Module Installed (SPECIAL CASE)
        # "Installed" ada di description, bukan di result/standard
        if re.search(r"d\.\s*Rectifier\s+Module\s+Installed", section_text, re.IGNORECASE):
            items.append({
                "no": "1.d",
                "description": "Rectifier Module Installed",
                "result": None,
                "standard": None,
                "status": None
            })
            print(f"[PM RECTIFIER]   ✓ 1.d: Rectifier Module Installed")
        
        # 1.e - Alarm Modul Rectifier
        e_item = self._extract_standard_item(section_text, "e", "Alarm Modul Rectifier",
                                              r"e\.\s*Alarm\s+Modul\s+Rectifier\s+(\w+)\s+(.*?)\s+(OK|NOK)",
                                              "Normal = Green, Alarm = Red")
        if e_item:
            items.append(e_item)
        
        return items
    
    def _extract_standard_item(self, section_text: str, letter: str, description: str,
                               pattern: str, standard: str, section_no: str = "1") -> Dict:
        """Helper untuk extract item standard (result, standard, status)"""
        match = re.search(pattern, section_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            print(f"[PM RECTIFIER]   ✓ {section_no}.{letter}: {match.group(1)}")
            return {
                "no": f"{section_no}.{letter}",
                "description": description,
                "result": match.group(1).strip(),
                "standard": standard,
                "status": match.group(3).strip()
            }
        
        return None
    
    # ================================================================
    # PERFORMANCE AND CAPACITY CHECK (Section 2)
    # ================================================================
    def extract_performance_capacity_check(self) -> List[Dict]:
        """Extract Performance and Capacity Check items"""
        print("[PM RECTIFIER] Parsing Performance and Capacity Check...")
        
        items = []
        
        # Find section
        section_pattern = r"2\.?\s*Performance\s+and\s+Capacity\s+Check\s*(.*?)(?=Backup\s+Tests|3\.|Notes|$)"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            return items
        
        section_text = section_match.group(1)
        
        # 2.a - AC Input Voltage (standard item)
        a_item = self._extract_standard_item(section_text, "a", "AC Input Voltage",
                                              r"a\.\s*AC\s+Input\s+Voltage\s+([\d,\.]+)\s+(.*?)\s+(OK|NOK)",
                                              "180-240 VAC", "2")
        if a_item:
            items.append(a_item)
        
        # 2.b - AC Current Input (multi-capacity, result kosong)
        b_item = self._extract_ac_current_input(section_text)
        if b_item:
            items.append(b_item)
        
        # 2.c - DC Current Output (multi-capacity, result ada nilai)
        c_item = self._extract_dc_current_output(section_text)
        if c_item:
            items.append(c_item)
        
        # 2.d - Charging Voltage DC (standard item)
        d_item = self._extract_standard_item(section_text, "d", "Charging Voltage DC",
                                              r"d\.\s*Charging\s+Voltage\s+DC\s+([\d,\.]+)\s+(.*?)\s+(OK|NOK)",
                                              "48 – 55,3 VDC", "2")
        if d_item:
            items.append(d_item)
        
        # 2.e - Charging Current DC (standard item)
        e_item = self._extract_standard_item(section_text, "e", "Charging Current DC",
                                              r"e\.\s*Charging\s+Current\s+DC\s+([\d,\.]+)\s+(.*?)\s+(OK|NOK)",
                                              "Max 10% Battery Capacity ( AH )", "2")
        if e_item:
            items.append(e_item)
        
        return items
    
    def _extract_ac_current_input(self, section_text: str) -> Dict:
        """
        Extract 2.b - AC Current Input
        
        Result: "-" (kosong)
        Logic: Karena result kosong, TIDAK perlu capacity_detected
        """
        print("[PM RECTIFIER] Extracting AC Current Input...")
        
        # Extract result
        result_pattern = r"b\.\s*AC\s+Current\s+Input\s+([\d,\.\-]+)"
        result_match = re.search(result_pattern, section_text, re.IGNORECASE)
        result = result_match.group(1).strip() if result_match else "-"
        
        # Build capacity options
        capacity_options = [
            {"capacity": cap, "standard": std}
            for cap, std in self.AC_CURRENT_OPTIONS
        ]
        
        # LOGIC: Jika result kosong ("-"), TIDAK ada capacity_detected
        if result == "-":
            print(f"[PM RECTIFIER]   ✓ 2.b: {result} (no capacity - result empty)")
            return {
                "no": "2.b",
                "description": "AC Current Input",
                "result": result,
                "capacity_options": capacity_options,
                "status": ""  # Empty status, not "-"
            }
        else:
            # Jika ada nilai, detect capacity
            capacity_detected = self._detect_capacity_from_value(result, self.AC_CURRENT_OPTIONS)
            standard_selected = self._get_standard_for_capacity(capacity_detected, self.AC_CURRENT_OPTIONS)
            
            print(f"[PM RECTIFIER]   ✓ 2.b: {result} (Capacity: {capacity_detected})")
            return {
                "no": "2.b",
                "description": "AC Current Input",
                "result": result,
                "capacity_options": capacity_options,
                "capacity_detected": capacity_detected,
                "standard_selected": standard_selected,
                "status": self._extract_status_for_field("AC Current Input")
            }
    
    def _extract_dc_current_output(self, section_text: str) -> Dict:
        """
        Extract 2.c - DC Current Output
        
        Result: "15" (ada nilai)
        Logic: Detect capacity dari nilai (15 paling dekat ke 25 = Single)
        """
        print("[PM RECTIFIER] Extracting DC Current Output...")
        
        # Extract result
        result_pattern = r"c\.\s*DC\s+Current\s+Output\s+([\d,\.\-]+)"
        result_match = re.search(result_pattern, section_text, re.IGNORECASE)
        result = result_match.group(1).strip() if result_match else ""
        
        # Build capacity options
        capacity_options = [
            {"capacity": cap, "standard": std}
            for cap, std in self.DC_CURRENT_OPTIONS
        ]
        
        # LOGIC: Jika result ada nilai, detect capacity
        if result and result != "-":
            capacity_detected = self._detect_capacity_from_value(result, self.DC_CURRENT_OPTIONS)
            standard_selected = self._get_standard_for_capacity(capacity_detected, self.DC_CURRENT_OPTIONS)
            
            print(f"[PM RECTIFIER]   ✓ 2.c: {result} (Capacity: {capacity_detected})")
            return {
                "no": "2.c",
                "description": "DC Current Output",
                "result": result,
                "capacity_options": capacity_options,
                "capacity_detected": capacity_detected,
                "standard_selected": standard_selected,
                "status": self._extract_status_for_field("DC Current Output")
            }
        else:
            # Jika kosong
            print(f"[PM RECTIFIER]   ✓ 2.c: {result} (no capacity - result empty)")
            return {
                "no": "2.c",
                "description": "DC Current Output",
                "result": result,
                "capacity_options": capacity_options,
                "status": ""  # Empty status, not "-"
            }
    
    def _detect_capacity_from_value(self, result: str, options: List[Tuple[str, str]]) -> str:
        """Detect capacity dari result value (cari yang paling dekat)"""
        try:
            result_float = float(result.replace(",", "."))
            
            min_diff = float('inf')
            closest_capacity = ""
            
            for capacity_name, standard_value in options:
                # Extract numeric dari standard (e.g., "25 A" → 25)
                std_match = re.search(r'([\d,\.]+)', standard_value)
                if std_match:
                    std_value = float(std_match.group(1).replace(",", "."))
                    diff = abs(result_float - std_value)
                    
                    if diff < min_diff:
                        min_diff = diff
                        closest_capacity = capacity_name
            
            # Extract kata capacity (Single/Dual/Three)
            for word in ["Single", "Dual", "Three"]:
                if word.lower() in closest_capacity.lower():
                    return word
            
            return closest_capacity
            
        except ValueError:
            return ""
    
    def _get_standard_for_capacity(self, capacity: str, options: List[Tuple[str, str]]) -> str:
        """Get standard value untuk capacity tertentu"""
        for cap_name, std_value in options:
            if capacity.lower() in cap_name.lower():
                return f"{std_value} ( {cap_name} )"
        return ""
    
    def _extract_status_for_field(self, description: str) -> str:
        """Extract status (OK/NOK) untuk field tertentu"""
        pattern = rf"{re.escape(description)}[^\n]*(?:\n[^\n]*?){{0,5}}?\b(OK|NOK)\b"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""
    
    # ================================================================
    # BACKUP TESTS (Section 3-4)
    # ================================================================
    def extract_backup_tests(self) -> List[Dict]:
        """Extract Backup Tests items"""
        print("[PM RECTIFIER] Parsing Backup Tests...")
        
        items = []
        
        # Find section
        section_pattern = r"Backup\s+Tests\s*(.*?)(?=Notes|Executor|$)"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            return items
        
        section_text = section_match.group(1)
        
        # 3 - Rectifier Switching test
        if re.search(r"3\.?\s*Rectifier\s+Switching\s+test", section_text, re.IGNORECASE):
            items.append({
                "no": "3",
                "description": "Rectifier Switching test, from the main source (PLN) to back up mode, by turning off Rectifier input MCB",
                "result": "-",
                "standard": "Rectifier Normal Operations",
                "status": ""
            })
            print("[PM RECTIFIER]   ✓ 3: Rectifier Switching test")
        
        # 4 - Power Alarm Monitoring Test
        if re.search(r"4\.?\s*Power\s+Alarm\s+Monitoring\s+Test", section_text, re.IGNORECASE):
            items.append({
                "no": "4",
                "description": "Power Alarm Monitoring Test",
                "result": "-",
                "standard": "Makesure the alarm monitor, by turn off UPS power input MCB during Rect backup test operation - Alarm Monitor fault conditions ( Red Sign / Alert \"Alarm Input Voltage )",
                "status": ""
            })
            print("[PM RECTIFIER]   ✓ 4: Power Alarm Monitoring Test")
        
        return items
    
    # ================================================================
    # PELAKSANA - Reuse dari BasePMParser dengan sedikit modifikasi
    # ================================================================
    def extract_pelaksana_rectifier(self) -> dict:
        """Extract pelaksana - single & multi-line support"""
        print("[PM RECTIFIER] Extracting pelaksana...")
        
        pelaksana = {
            "executor": [],
            "verifikator": None,
            "head_of_sub_department": None
        }
        
        # Find section
        section_pattern = r"Mitra\s*/\s*Internal\s*Signature\s*(.*?)$"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            return pelaksana
        
        section_text = section_match.group(1)
        lines = [l.strip() for l in section_text.split('\n') if l.strip()]
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Skip separators - IMPROVED DETECTION
            # Skip lines with underscores: "___", "( ______ )", etc.
            if "___" in line:
                i += 1
                continue
            
            # Skip lines that are ONLY separators like "( __________ )"
            if re.match(r'^\s*\(\s*[_\s]*\)\s*$', line):
                i += 1
                continue
            
            # Try single-line: "1 Tazki IMS"
            single_match = re.match(r'^(\d+)\s+(\w+)\s+(\w+)$', line)
            if single_match:
                pelaksana["executor"].append({
                    "no": single_match.group(1),
                    "Nama": single_match.group(2),
                    "Mitra / internal": single_match.group(3)
                })
                print(f"[PM RECTIFIER]   ✓ Executor #{single_match.group(1)}: {single_match.group(2)}")
                i += 1
                continue
            
            # Try multi-line: number on separate line
            if re.match(r'^\d+$', line):
                no = line
                
                # Check next line exists and is not a number/separator
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    
                    # Skip if next line is number or separator
                    if re.match(r'^\d+$', next_line) or "___" in next_line or re.match(r'^\s*\(\s*[_\s]*\)\s*$', next_line):
                        i += 1
                        continue
                    
                    nama = next_line
                    mitra = ""
                    
                    # Check third line for company
                    if i + 2 < len(lines):
                        third_line = lines[i + 2]
                        if not re.match(r'^\d+$', third_line) and "___" not in third_line and not re.match(r'^\s*\(\s*[_\s]*\)\s*$', third_line):
                            mitra = third_line
                    
                    pelaksana["executor"].append({
                        "no": no,
                        "Nama": nama,
                        "Mitra / internal": mitra
                    })
                    print(f"[PM RECTIFIER]   ✓ Executor #{no}: {nama}")
                    i += 3 if mitra else 2
                else:
                    i += 1
            else:
                i += 1
        
        print(f"[PM RECTIFIER] Total executors: {len(pelaksana['executor'])}")
        return pelaksana
