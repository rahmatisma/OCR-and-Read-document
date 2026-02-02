"""
Parser untuk Form PM Instalasi Kabel dan Panel Distribusi
Document Code: FM-LAP-D2-SOP-003-009

 REFACTORED VERSION - Lebih ringkas dengan maksimalkan base parser
 Total ~200 lines (vs 500+ sebelumnya)
"""

from parsers.Form_PM_POP.base_pm_parser import BasePMParser
from typing import Dict, List
import re


class PMInstalasiKabelPanelDistribusiParser(BasePMParser):
    """Parser untuk Form Preventive Maintenance Instalasi Kabel dan Panel Distribusi"""
    
    def __init__(self, all_text: str, page_texts: list, ocr_data: list = None):
        super().__init__(all_text, page_texts, ocr_data)
    
    def parse(self) -> dict:
        """Parse dokumen Form PM Instalasi Kabel dan Panel Distribusi"""
        print("\n[PM INSTALASI KABEL] Memulai parsing...")
        
        result = {
            "header": self.extract_header(),
            "informasi_umum": self.extract_informasi_umum_instalasi_kabel(),
            "visual_check": self.extract_visual_check(),
            "performance_measurement": {
                "mcb_temperature": self.extract_mcb_temperature(),
                "cable_temperature": self.extract_cable_temperature()
            },
            "maksure_cable_connection": self.extract_maksure_cable_connection(),
            "notes": self.extract_notes(),
            "pelaksana": self.extract_pelaksana_instalasi_kabel()
        }
        
        print("[PM INSTALASI KABEL]  Parsing selesai!")
        return result
    
    # ================================================================
    # INFORMASI UMUM - Override karena ada field khusus
    # ================================================================
    def extract_informasi_umum_instalasi_kabel(self) -> dict:
        """Extract informasi umum dengan field Availability UPS"""
        print("[PM INSTALASI KABEL] Parsing Informasi Umum...")
        
        info = {
            "location": self._extract_location_safe(),
            "date_time": self._extract_date_time_safe(),
            "brand_type": self._extract_simple_field(r"Brand\s*/?\s*Type\s*:", r"Reg|S/N|\n\n"),
            "reg_number": self._extract_simple_field(r"Reg\.?\s*Number\s*:", r"S/N|Brand|\n\n"),
            "serial_number": self._extract_simple_field(r"S\s*/?\s*N\s*:", r"No\.|Descriptions|\n\n"),
            "availability_ups": self._extract_simple_field(r"Availability\s+UPS\s*:", r"Date|Brand|\n\n")
        }
        
        return info
    
    def _extract_location_safe(self) -> str:
        """Extract Location - stop BEFORE Availability UPS or Date/time"""
        # Pattern: dari Location : sampai sebelum Availability UPS atau newline ganda
        pattern = r"Location\s*:\s*([^\n]*?)(?=\s*(?:Availability\s+UPS|Date\s*/\s*time)|\n\s*\n)"
        match = re.search(pattern, self.all_text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip(' :：-')
            if value and value.lower() not in self.INVALID_VALUES:
                return value
        return ""
    
    def _extract_date_time_safe(self) -> str:
        """Extract Date/time - stop BEFORE Brand/Type"""
        pattern = r"Date\s*/\s*time\s*:\s*([^\n]*?)(?=\s*(?:Brand\s*/\s*Type)|\n\s*\n)"
        match = re.search(pattern, self.all_text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip(' :：-')
            if value and value.lower() not in self.INVALID_VALUES:
                return value
        return ""
    
    # ================================================================
    # VISUAL CHECK - Reuse pattern dari base, custom loop
    # ================================================================
    def extract_visual_check(self) -> List[Dict]:
        """Extract Visual Check items (6 items)"""
        print("[PM INSTALASI KABEL] Parsing Visual Check...")
        
        items = []
        section_text = self._get_section(r"1\.\s*Visual\s+Check", r"2\.\s*Performance")
        if not section_text:
            return items
        
        visual_items = [
            ("a", "Indicator Lamp", "Normal"),
            ("b", "Voltmeter & Ampere meter", "Normal"),
            ("c", "Arrester", "Normal"),
            ("d", "MCB Input UPS", "Normal"),
            ("e", "MCB Output UPS", "Normal"),
            ("f", "MCB Bypass", "Normal")
        ]
        
        for letter, desc, std in visual_items:
            item = self._extract_simple_item(section_text, "1", letter, desc, std)
            if item:
                items.append(item)
        
        return items
    
    # ================================================================
    # MCB & CABLE TEMPERATURE - Simplified extraction
    # ================================================================
    def extract_mcb_temperature(self) -> List[Dict]:
        """Extract MCB Temperature items (5 items)"""
        print("[PM INSTALASI KABEL] Parsing MCB Temperature...")
        
        items = []
        perf_text = self._get_section(r"2\.\s*Performance\s+Measurement", r"3\.|Notes")
        if not perf_text:
            return items
        
        mcb_text = self._get_subsection(perf_text, r"I\.\s*MCB\s+Temperature", r"II\.|Cable")
        if not mcb_text:
            return items
        
        mcb_items = [
            ("a", "Input UPS"),
            ("b", "Output UPS"),
            ("c", "Bypass UPS"),
            ("d", "Load Rack"),
            ("e", "Cooling unit ( AC )")
        ]
        
        for letter, desc in mcb_items:
            item = self._extract_temperature_item(mcb_text, "2.I", letter, desc, "Maks 65 oC")
            if item:
                items.append(item)
        
        return items
    
    def extract_cable_temperature(self) -> List[Dict]:
        """Extract Cable Temperature items (6 items)"""
        print("[PM INSTALASI KABEL] Parsing Cable Temperature...")
        
        items = []
        perf_text = self._get_section(r"2\.\s*Performance\s+Measurement", r"3\.|Notes")
        if not perf_text:
            return items
        
        cable_text = self._get_subsection(perf_text, r"II\.\s*Cable\s+Temperature", r"3\.|Maksure")
        if not cable_text:
            return items
        
        cable_items = [
            ("a", "Input UPS"),
            ("b", "Output UPS"),
            ("c", "Bypass UPS"),
            ("d", "Load Rack"),
            ("e", "Cooling unit ( AC )")
        ]
        
        for letter, desc in cable_items:
            item = self._extract_temperature_item(cable_text, "2.II", letter, desc, "Maks 65 oC")
            if item:
                items.append(item)
        
        # Item f - Performance Check (tanpa standard/status)
        f_pattern = r"f\.\s*Performance\s+Check\s+([\d,\.]+)"
        f_match = re.search(f_pattern, cable_text, re.IGNORECASE)
        if f_match:
            items.append({
                "no": "2.II.f",
                "description": "Performance Check",
                "result": f_match.group(1).strip(),
                "standard": None,
                "status": None
            })
            print(f"[PM INSTALASI KABEL]   ✓ 2.II.f: {f_match.group(1)}")
        
        return items
    
    # ================================================================
    # MAKSURE CABLE CONNECTION
    # ================================================================
    def extract_maksure_cable_connection(self) -> List[Dict]:
        """Extract Cable Connection items (4 items)"""
        print("[PM INSTALASI KABEL] Parsing Maksure Cable Connection...")
        
        items = []
        section_text = self._get_section(r"3\.\s*Maksure\s+All\s+Cable", r"Notes|Executor")
        if not section_text:
            return items
        
        # Items a & b - Available
        for letter, desc in [("a", "Spare of MCB Load Rack"), ("b", "Single Line Diagram")]:
            item = self._extract_simple_item(section_text, "3", letter, desc, "Available")
            if item:
                items.append(item)
        
        # Items c & d - Voltage measurements
        for letter, desc in [("c", "Phase-to-Neutral Measurement"), ("d", "Phase-to-Ground Measurement")]:
            item = self._extract_voltage_item(section_text, "3", letter, desc, "180 – 240 VAC")
            if item:
                items.append(item)
        
        return items
    
    # ================================================================
    # PELAKSANA - Reuse dari base dengan field names yang benar
    # ================================================================
    def extract_pelaksana_instalasi_kabel(self) -> dict:
        """Extract pelaksana - multi-line support dengan field names yang benar"""
        print("[PM INSTALASI KABEL] Extracting pelaksana...")
        
        pelaksana = {
            "executor": [],
            "verifikator": None,
            "head_of_sub_department": None
        }
        
        section_pattern = r"Mitra\s*/\s*Internal\s*Signature\s*(.*?)$"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            return pelaksana
        
        section_text = section_match.group(1)
        lines = [l.strip() for l in section_text.split('\n') if l.strip()]
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Skip separators and signature placeholders
            if "___" in line or re.match(r'^\s*\(\s*_*\s*\)\s*$', line):
                i += 1
                continue
            
            # Multi-line format: number, name, company
            if re.match(r'^\d+$', line):
                no = line
                nama = ""
                mitra = ""
                
                # Check next line for name (skip if it's separator or number)
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # Skip if it's a number, separator, or placeholder
                    if (not re.match(r'^\d+$', next_line) and 
                        "___" not in next_line and 
                        not re.match(r'^\s*\(\s*_*\s*\)\s*$', next_line)):
                        nama = next_line
                        
                        # Check third line for company
                        if i + 2 < len(lines):
                            third_line = lines[i + 2]
                            if (not re.match(r'^\d+$', third_line) and 
                                "___" not in third_line and 
                                not re.match(r'^\s*\(\s*_*\s*\)\s*$', third_line)):
                                mitra = third_line
                
                # Only add if we have valid name (not empty and not placeholder)
                if nama and not nama.startswith("("):
                    pelaksana["executor"].append({
                        "no": no,
                        "Nama": nama,
                        "Mitra / internal": mitra
                    })
                    print(f"[PM INSTALASI KABEL]   ✓ Executor #{no}: {nama}")
                    i += 3
                else:
                    i += 1
            else:
                i += 1
        
        return pelaksana
    
    # ================================================================
    # HELPER METHODS - Reusable extraction patterns
    # ================================================================
    def _get_section(self, start_pattern: str, end_pattern: str) -> str:
        """Get text section between start and end patterns"""
        pattern = rf"{start_pattern}\s*(.*?)(?={end_pattern}|$)"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        return match.group(1) if match else ""
    
    def _get_subsection(self, text: str, start_pattern: str, end_pattern: str) -> str:
        """Get subsection from already extracted text"""
        pattern = rf"{start_pattern}\s*(.*?)(?={end_pattern}|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group(1) if match else ""
    
    def _extract_simple_item(self, section_text: str, section_no: str, letter: str, 
                            desc: str, std: str) -> Dict:
        """Extract simple item: letter. desc result std status"""
        desc_esc = re.escape(desc)
        pattern = rf"{letter}\.\s*{desc_esc}\s+(\w+)\s+{re.escape(std)}\s+(OK|NOK)"
        match = re.search(pattern, section_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            print(f"[PM INSTALASI KABEL]   ✓ {section_no}.{letter}: {match.group(1)}")
            return {
                "no": f"{section_no}.{letter}",
                "description": desc,
                "result": match.group(1).strip(),
                "standard": std,
                "status": match.group(2).strip()
            }
        return None
    
    def _extract_temperature_item(self, section_text: str, section_no: str, letter: str,
                                   desc: str, std: str) -> Dict:
        """Extract temperature item with flexible newline handling"""
        desc_esc = desc.replace("(", r"\(").replace(")", r"\)")
        
        # Pattern with DOTALL to handle newlines
        pattern = rf"{letter}\.\s*{desc_esc}.*?([\d,\.]+).*?{re.escape(std)}.*?(OK|NOK)"
        match = re.search(pattern, section_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            print(f"[PM INSTALASI KABEL]   ✓ {section_no}.{letter}: {match.group(1).strip()}")
            return {
                "no": f"{section_no}.{letter}",
                "description": desc,
                "result": match.group(1).strip(),
                "standard": std,
                "status": match.group(2).strip()
            }
        return None
    
    def _extract_voltage_item(self, section_text: str, section_no: str, letter: str,
                              desc: str, std: str) -> Dict:
        """Extract voltage measurement item"""
        pattern = rf"{letter}\.\s*{re.escape(desc)}\s+([\d,\.]+)\s+{re.escape(std)}\s+(OK|NOK)"
        match = re.search(pattern, section_text, re.IGNORECASE)
        
        if match:
            print(f"[PM INSTALASI KABEL]   ✓ {section_no}.{letter}: {match.group(1)}")
            return {
                "no": f"{section_no}.{letter}",
                "description": desc,
                "result": match.group(1).strip(),
                "standard": std,
                "status": match.group(2).strip()
            }
        return None