"""
Parser untuk Form PM Lightning Protection and Grounding
Document Code: FM-LAP-D2-SOP-003-008

 Simple structure - no multi-capacity
 Physical Check (9 items: a-i)
 Performance Measurement (3 items: a-c)

Struktur Dokumen:
1. Header (No. Dok, Versi, Hal, Label)
2. Informasi Umum (Location, Date/time) - NO Brand/Type/Reg/SN
3. Physical Check (9 items)
4. Performance Measurement (3 items)
5. Notes
6. Pelaksana
"""

from parsers.Form_PM_POP.base_pm_parser import BasePMParser
from typing import Dict, List
import re


class PMLightningGroundingParser(BasePMParser):
    """Parser untuk Form Preventive Maintenance Lightning Protection and Grounding"""
    
    def __init__(self, all_text: str, page_texts: list, ocr_data: list = None):
        super().__init__(all_text, page_texts, ocr_data)
    
    def parse(self) -> dict:
        """Parse dokumen Form PM Lightning Protection and Grounding"""
        print("\n[PM LIGHTNING] Memulai parsing...")
        
        result = {
            "header": self.extract_header(),
            "informasi_umum": self.extract_informasi_umum_lightning(),
            "physical_check": self.extract_physical_check(),
            "performance_measurement": self.extract_performance_measurement(),
            "notes": self.extract_notes(),
            "pelaksana": self.extract_pelaksana_lightning()
        }
        
        print("[PM LIGHTNING]  Parsing selesai!")
        return result
    
    # ================================================================
    # INFORMASI UMUM - Simplified (hanya Location & Date/time)
    # ================================================================
    def extract_informasi_umum_lightning(self) -> dict:
        """Extract informasi umum - hanya Location dan Date/time"""
        print("[PM LIGHTNING] Parsing Informasi Umum...")
        
        return {
            "location": self._extract_simple_field(r"Location\s*:", r"Date|\n\n"),
            "date_time": self._extract_simple_field(r"Date\s*/?\s*time\s*:", r"No\.|Descriptions|\n\n")
        }
    
    # ================================================================
    # PHYSICAL CHECK (Section 1) - 9 items
    # ================================================================
    def extract_physical_check(self) -> List[Dict]:
        """Extract Physical Check items (a-i)"""
        print("[PM LIGHTNING] Parsing Physical Check...")
        
        items = []
        
        # Find section
        section_pattern = r"1\.\s*Physical\s+Check\s*(.*?)(?=2\.?\s*Performance|Notes|$)"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            print("[PM LIGHTNING] ⚠️ Physical Check section not found")
            return items
        
        section_text = section_match.group(1)
        
        # Define all physical check items
        physical_items = [
            ("a", "Air Terminal", r"a\.\s*Air\s+Terminal\s+(\d+|Ada|Available)\s+(.*?)\s+(OK|NOK)", 
             "Available < 45 with Antenna"),
            
            ("b", "Down Conductor Cable", r"b\.\s*Down\s+Conductor\s+Cable\s+(\d+|Ada|Available)\s+(.*?)\s+(OK|NOK)",
             "Available ( cable > 35 mmsq )"),
            
            ("c", "Ground Rod", r"c\.\s*Ground\s+Rod\s+(Ada|Available)\s+(.*?)\s+(OK|NOK)",
             "Available, No Corrosion"),
            
            ("d", "Bonding Bar", r"d\.\s*Bonding\s+Bar\s+(Ada|Available)\s+(.*?)\s+(OK|NOK)",
             "Available, No Corrosion"),
            
            ("e", "Arrester Condition", r"e\.\s*Arrester\s+Condition\s+(\w+)\s+(.*?)\s+(OK|NOK)",
             "Normal"),
            
            ("f", "Maksure All Equipment to Ground Bar", 
             r"f\.\s*Maksure\s+All\s+Equipment\s+to\s+Ground\s+Bar\s+(Yes|No)\s+(.*?)\s+(OK|NOK)",
             "Yes"),
            
            ("g", "Maksure All Connection Tightened", 
             r"g\.\s*Maksure\s+All\s+Connection\s+Tightened\s+(Yes|No)\s+(.*?)\s+(OK|NOK)",
             "Yes"),
            
            ("h", "OB Light Installed if With Tower", 
             r"h\.\s*OB\s+Light\s+Installed\s+if\s+With\s+Tower\s+(Yes|No)\s+(.*?)\s+(OK|NOK)",
             "Yes & Normal Operation"),
            
            ("i", "Phasa On Site", r"i\.\s*Phasa\s+On\s+Site\s+(\d+)\s+(.*?)\s+(OK|NOK)",
             "1 Phasa / 3 Phasa")
        ]
        
        # Extract each item
        for letter, description, pattern, standard in physical_items:
            item = self._extract_physical_item(section_text, letter, description, pattern, standard)
            if item:
                items.append(item)
        
        return items
    
    def _extract_physical_item(self, section_text: str, letter: str, description: str,
                               pattern: str, standard: str) -> Dict:
        """Helper to extract single physical check item"""
        match = re.search(pattern, section_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            result = match.group(1).strip()
            status = match.group(3).strip()
            
            print(f"[PM LIGHTNING]   ✓ 1.{letter}: {result}")
            return {
                "no": f"1.{letter}",
                "description": description,
                "result": result,
                "standard": standard,
                "status": status
            }
        
        print(f"[PM LIGHTNING]   ⚠️ 1.{letter} not found")
        return None
    
    # ================================================================
    # PERFORMANCE MEASUREMENT (Section 2) - 3 items
    # ================================================================
    def extract_performance_measurement(self) -> List[Dict]:
        """Extract Performance Measurement items (a-c)"""
        print("[PM LIGHTNING] Parsing Performance Measurement...")
        
        items = []
        
        # Find section
        section_pattern = r"2\.?\s*Performance\s+Measurement\s*(.*?)(?=Notes|Executor|$)"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            print("[PM LIGHTNING] ⚠️ Performance Measurement section not found")
            return items
        
        section_text = section_match.group(1)
        
        # Define performance items
        performance_items = [
            ("a", "Arrester Cutoff Voltage ( Power )", 
             r"a\.\s*Arrester\s+Cutoff\s+Voltage\s*\(\s*Power\s*\)\s+(\w+)\s+(.*?)\s+(OK|NOK)",
             "Green = Normal, Red = Defect"),
            
            ("b", "Arrester Cutoff Voltage ( Data )", 
             r"b\.\s*Arrester\s+Cutoff\s+Voltage\s*\(\s*Data\s*\)\s+(\w+)\s+(.*?)\s+(OK|NOK)",
             "Green = Normal, Red = Defect"),
            
            ("c", "Tighten of Nut", 
             r"c\.\s*Tighten\s+of\s+Nut\s+(\w+)\s+(.*?)\s+(OK|NOK)",
             "Tightened")
        ]
        
        # Extract each item
        for letter, description, pattern, standard in performance_items:
            item = self._extract_performance_item(section_text, letter, description, pattern, standard)
            if item:
                items.append(item)
        
        return items
    
    def _extract_performance_item(self, section_text: str, letter: str, description: str,
                                  pattern: str, standard: str) -> Dict:
        """Helper to extract single performance measurement item"""
        match = re.search(pattern, section_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            result = match.group(1).strip()
            status = match.group(3).strip()
            
            print(f"[PM LIGHTNING]   ✓ 2.{letter}: {result}")
            return {
                "no": f"2.{letter}",
                "description": description,
                "result": result,
                "standard": standard,
                "status": status
            }
        
        print(f"[PM LIGHTNING]   ⚠️ 2.{letter} not found")
        return None
    
    # ================================================================
    # PELAKSANA - Reuse pattern dari parser lain
    # ================================================================
    def extract_pelaksana_lightning(self) -> dict:
        """Extract pelaksana - single & multi-line support"""
        print("[PM LIGHTNING] Extracting pelaksana...")
        
        pelaksana = {
            "executor": [],
            "verifikator": None,
            "head_of_sub_department": None
        }
        
        # Find section
        section_pattern = r"Mitra\s*/\s*Internal\s*Signature\s*(.*?)$"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            print("[PM LIGHTNING]   ⚠️ Pelaksana section not found")
            return pelaksana
        
        section_text = section_match.group(1)
        lines = [l.strip() for l in section_text.split('\n') if l.strip()]
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Skip separators
            if "___" in line or re.match(r'^\s*\(\s*[_\s]*\)\s*$', line):
                i += 1
                continue
            
            # Try single-line: "1 Adi IMS"
            single_match = re.match(r'^(\d+)\s+(\w+)\s+(\w+)$', line)
            if single_match:
                pelaksana["executor"].append({
                    "no": single_match.group(1),
                    "Nama": single_match.group(2),
                    "Mitra / internal": single_match.group(3)
                })
                print(f"[PM LIGHTNING]   ✓ Executor #{single_match.group(1)}: {single_match.group(2)}")
                i += 1
                continue
            
            # Try multi-line
            if re.match(r'^\d+$', line):
                no = line
                
                # Check next line
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    
                    # Skip if separator
                    if re.match(r'^\d+$', next_line) or "___" in next_line or re.match(r'^\s*\(\s*[_\s]*\)\s*$', next_line):
                        i += 1
                        continue
                    
                    nama = next_line
                    mitra = ""
                    
                    # Check third line
                    if i + 2 < len(lines):
                        third_line = lines[i + 2]
                        if not re.match(r'^\d+$', third_line) and "___" not in third_line and not re.match(r'^\s*\(\s*[_\s]*\)\s*$', third_line):
                            mitra = third_line
                    
                    pelaksana["executor"].append({
                        "no": no,
                        "Nama": nama,
                        "Mitra / internal": mitra
                    })
                    print(f"[PM LIGHTNING]   ✓ Executor #{no}: {nama}")
                    i += 3 if mitra else 2
                else:
                    i += 1
            else:
                i += 1
        
        print(f"[PM LIGHTNING] Total executors: {len(pelaksana['executor'])}")
        return pelaksana