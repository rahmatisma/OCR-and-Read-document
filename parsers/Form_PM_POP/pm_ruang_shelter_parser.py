"""
Parser untuk Form PM Shelter Room / ODC - FIXED VERSION
Document Code: FM-LAP-D2-SOP-003-006

 FIXES:
    - Room Temperature: result="" (kosong), standard="<25C Shelter Room" (gabung)
    - Tetap object dengan checklist (bukan flat array)

Struktur Dokumen:
1. Header (No. Dok, Versi, Hal, Label)
2. Informasi Umum (Location, Date/time, Type)
3. Physical Check (Room Condition, Lock Condition)
4. Room Infrastructure (Layout, Security, Access, Technical)
5. Room Temperature (multi-option: Shelter/ODC/Pole ODC) ← FIXED
6. Notes
7. Pelaksana (Executor, Verifikator, Head)
"""

from parsers.Form_PM_POP.base_pm_parser import BasePMParser
from typing import Dict, List
import re


class PMRuangShelterParser(BasePMParser):
    """Parser untuk Form Preventive Maintenance Shelter Room / ODC"""
    
    def __init__(self, all_text: str, page_texts: list, ocr_data: list = None):
        super().__init__(all_text, page_texts, ocr_data)
        
        # Room temperature options - (threshold, room_type)
        self.TEMPERATURE_OPTIONS = [
            ("<25C", "Shelter Room"),
            ("<35C", "Outdoor Cabinet (ODC)"),
            ("<40C", "Pole Outdoor Cabinet (ODC)")
        ]
    
    def parse(self) -> dict:
        """Parse dokumen Form PM Shelter Room / ODC"""
        print("\n[PM SHELTER] Memulai parsing...")
        
        result = {
            "header": self.extract_header(),
            "informasi_umum": self.extract_informasi_umum_shelter(),
            "physical_check": self.extract_physical_check(),
            "room_infrastructure": self.extract_room_infrastructure(),
            "room_temperature": self.extract_room_temperature_fixed(),  # ← FIXED METHOD
            "notes": self.extract_notes(),
            "pelaksana": self.extract_pelaksana_shelter()
        }
        
        print("[PM SHELTER]  Parsing selesai!")
        return result
    
    # ================================================================
    # INFORMASI UMUM - Override untuk field "Type"
    # ================================================================
    def extract_informasi_umum_shelter(self) -> dict:
        """Extract informasi umum untuk Shelter form"""
        print("[PM SHELTER] Parsing Informasi Umum...")
        
        return {
            "location": self._extract_simple_field(r"Location\s*:", r"Date|Type|\n\n"),
            "date_time": self._extract_simple_field(r"Date\s*/?\s*time\s*:", r"Type|No\.|\n\n"),
            "type": self._extract_simple_field(r"Type\s*:", r"No\.|Descriptions|\n\n")
        }
    
    # ================================================================
    # PHYSICAL CHECK (Section 1)
    # ================================================================
    def extract_physical_check(self) -> List[Dict]:
        """Extract Physical Check items"""
        print("[PM SHELTER] Parsing Physical Check...")
        
        items = []
        
        # Find Physical Check section
        section_pattern = r"1\.\s*Physical\s+Check\s*(.*?)(?=2\.\s*Room\s+Infrastructure|Notes|$)"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            print("[PM SHELTER] ⚠️ Physical Check section not found")
            return items
        
        section_text = section_match.group(1)
        
        # 1.a - Room Condition
        room_cond_pattern = r"a\.\s*Room\s+Condition\s+(\w+)\s+(.*?)\s+(OK|NOK)"
        room_cond_match = re.search(room_cond_pattern, section_text, re.IGNORECASE | re.DOTALL)
        
        if room_cond_match:
            items.append({
                "no": "1.a",
                "description": "Room Condition",
                "result": room_cond_match.group(1).strip(),
                "standard": "Clean, free from leaks, and free from contamination",
                "status": room_cond_match.group(3).strip()
            })
            print(f"[PM SHELTER]   ✓ 1.a: {room_cond_match.group(1)}")
        
        # 1.b - Lock Condition
        lock_pattern = r"b\.\s*Room\s*/\s*Shelter\s+Lock\s+Condition\s+(\w+)\s+(.*?)\s+(OK|NOK)"
        lock_match = re.search(lock_pattern, section_text, re.IGNORECASE | re.DOTALL)
        
        if lock_match:
            items.append({
                "no": "1.b",
                "description": "Room / Shelter Lock Condition",
                "result": lock_match.group(1).strip(),
                "standard": "Durable and easily operable",
                "status": lock_match.group(3).strip()
            })
            print(f"[PM SHELTER]   ✓ 1.b: {lock_match.group(1)}")
        
        return items
    
    # ================================================================
    # ROOM INFRASTRUCTURE (Section 2)
    # ================================================================
    def extract_room_infrastructure(self) -> List[Dict]:
        """Extract Room Infrastructure items"""
        print("[PM SHELTER] Parsing Room Infrastructure...")
        
        items = []
        
        # Find Room Infrastructure section
        section_pattern = r"2\.\s*Room\s+Infrastructure\s*(.*?)(?=3\.\s*Room\s+Temprature|Notes|$)"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            print("[PM SHELTER] ⚠️ Room Infrastructure section not found")
            return items
        
        section_text = section_match.group(1)
        
        # 2.a - Room Layout
        layout_item = self._extract_infrastructure_item(
            section_text, 
            "a", 
            "Room Layout",
            r"a\.\s*Room\s+Layout\s+(\w+)\s+(.*?)\s+(OK|NOK)",
            "Functionality, maintainability, user comfort, and aesthetic"
        )
        if layout_item:
            items.append(layout_item)
            print(f"[PM SHELTER]   ✓ 2.a: {layout_item['result']}")
        
        # 2.b - Security Management Control
        security_item = self._extract_infrastructure_item(
            section_text,
            "b",
            "Security Management Control",
            r"b\.\s*Security\s+Management\s+Control\s+(\w+)\s+(.*?)\s+(OK|NOK)",
            "Secure, *CCTV-monitored (optional)"
        )
        if security_item:
            items.append(security_item)
            print(f"[PM SHELTER]   ✓ 2.b: {security_item['result']}")
        
        # 2.c - Ease Of Access
        access_item = self._extract_infrastructure_item(
            section_text,
            "c",
            "Ease Of Access",
            r"c\.\s*Ease\s+Of\s+Access\s+(\w+)\s+(.*?)\s+(OK|NOK)",
            "Safe and efficient personnel movement, and ease of access to equipment"
        )
        if access_item:
            items.append(access_item)
            print(f"[PM SHELTER]   ✓ 2.c: {access_item['result']}")
        
        # 2.d - Technical Aspects
        technical_item = self._extract_infrastructure_item(
            section_text,
            "d",
            "Technical Aspects",
            r"d\.\s*Technical\s+Aspects\s+(\w+)\s+(.*?)\s+(OK|NOK)",
            "Availability of power supply, lightning protection, grounding system, lighting, air conditioning, fire protection, and *CCTV monitored (optional)"
        )
        if technical_item:
            items.append(technical_item)
            print(f"[PM SHELTER]   ✓ 2.d: {technical_item['result']}")
        
        return items
    
    def _extract_infrastructure_item(self, section_text: str, letter: str, 
                                    description: str, pattern: str, 
                                    standard: str) -> Dict:
        """Helper to extract single infrastructure item"""
        match = re.search(pattern, section_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            return {
                "no": f"2.{letter}",
                "description": description,
                "result": match.group(1).strip(),
                "standard": standard,
                "status": match.group(3).strip()
            }
        
        print(f"[PM SHELTER]   ⚠️ 2.{letter} not found")
        return None
    
    # ================================================================
    # ROOM TEMPERATURE (Section 3) - FIXED VERSION
    # ================================================================
    def extract_room_temperature_fixed(self) -> Dict:
        """
        Extract Room Temperature section - FIXED
        
        Format di PDF:
        3. Room Temperature
        <25C   Shelter Room                     OK
        <35C   Outdoor Cabinet (ODC)            OK
        <40C   Pole Outdoor Cabinet (ODC)       OK
        
        Format JSON yang BENAR:
        {
            "no": "3",
            "description": "Room Temperature",
            "checklist": [
                {
                    "result": "",              ← KOSONG!
                    "standard": "<25C Shelter Room",  ← GABUNG threshold + room_type
                    "status": "OK"
                }
            ]
        }
        """
        print("[PM SHELTER] Parsing Room Temperature (FIXED)...")
        
        # Find Room Temperature section
        section_pattern = r"3\.\s*Room\s+Temprature\s*(.*?)(?=Notes|Executor|$)"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            print("[PM SHELTER] ⚠️ Room Temperature section not found")
            return {
                "no": "3",
                "description": "Room Temperature",
                "checklist": []
            }
        
        section_text = section_match.group(1)
        
        # Extract status for EACH option
        checklist = []
        for threshold, room_type in self.TEMPERATURE_OPTIONS:
            status = self._extract_status_for_temperature_option(section_text, threshold, room_type)
            
            #  FIXED: Gabung threshold + room_type jadi standard
            checklist.append({
                "result": "",  # ← KOSONG sesuai permintaan
                "standard": f"{threshold} {room_type}",  # ← GABUNG
                "status": status
            })
            
            print(f"[PM SHELTER]   ✓ {threshold} {room_type}: '{status}'")
        
        return {
            "no": "3",
            "description": "Room Temperature",
            "checklist": checklist
        }
    
    def _extract_status_for_temperature_option(self, section_text: str, threshold: str, room_type: str) -> str:
        """Extract status (OK/NOK) untuk specific temperature option"""
        # Clean threshold
        threshold_clean = threshold.replace("<", "").replace("C", "")
        
        # Escape room_type untuk regex
        room_type_pattern = re.escape(room_type)
        room_type_pattern = room_type_pattern.replace(r"\ \(ODC\)", r"(?:\s|\n)*\(ODC\)")
        
        # Pattern flexible
        pattern = rf"<{threshold_clean}[\uf0b0°]?C\s+{room_type_pattern}\s*\n?\s*(OK|NOK)"
        match = re.search(pattern, section_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        # Fallback: line-by-line search
        lines = section_text.split('\n')
        for i, line in enumerate(lines):
            if re.search(rf"<{threshold_clean}[\uf0b0°]?C", line):
                combined_line = line
                if i + 1 < len(lines):
                    combined_line += " " + lines[i + 1]
                
                if room_type.replace(" ", "") in combined_line.replace(" ", "").replace("\n", ""):
                    for j in range(i, min(i + 3, len(lines))):
                        if re.search(r'\bOK\b', lines[j], re.IGNORECASE):
                            return "OK"
                        elif re.search(r'\bNOK\b', lines[j], re.IGNORECASE):
                            return "NOK"
        
        return ""
    
    # ================================================================
    # PELAKSANA - Multi-line support
    # ================================================================
    def extract_pelaksana_shelter(self) -> dict:
        """Extract pelaksana section dengan single-line dan multi-line support"""
        print("[PM SHELTER] Extracting pelaksana...")
        
        pelaksana = {
            "executor": [],
            "verifikator": None,
            "head_of_sub_department": None
        }
        
        # Find pelaksana section
        section_pattern = r"Mitra\s*/\s*Internal\s*Signature\s*(.*?)$"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            print("[PM SHELTER]   ⚠️ Pelaksana section not found")
            return pelaksana
        
        section_text = section_match.group(1)
        lines = [l.strip() for l in section_text.split('\n') if l.strip()]
        
        print(f"[PM SHELTER] Found {len(lines)} non-empty lines")
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Skip signature placeholders
            if "___" in line or re.match(r'^\s*\(\s*_*\s*\)?\s*$', line):
                i += 1
                continue
            
            # Try single-line: "1 Tazki IMS"
            single_match = re.match(r'^(\d+)\s+(\w+)\s+(\w+)$', line)
            
            if single_match:
                executor = {
                    "no": single_match.group(1),
                    "Nama": single_match.group(2),
                    "Mitra / internal": single_match.group(3)
                }
                pelaksana["executor"].append(executor)
                print(f"[PM SHELTER]   ✓ Executor #{executor['no']}: {executor['Nama']} - {executor['Mitra / internal']} (single-line)")
                i += 1
                continue
            
            # Try multi-line: number on separate line
            if re.match(r'^\d+$', line):
                no = line
                nama = ""
                mitra = ""
                
                # Next line = name
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if not re.match(r'^\d+$', next_line) and "___" not in next_line and not re.match(r'^\s*\(\s*_*\s*\)?\s*$', next_line):
                        nama = next_line
                        
                        # Third line = company
                        if i + 2 < len(lines):
                            third_line = lines[i + 2]
                            if not re.match(r'^\d+$', third_line) and "___" not in third_line and not re.match(r'^\s*\(\s*_*\s*\)?\s*$', third_line):
                                mitra = third_line
                
                if nama:
                    executor = {
                        "no": no,
                        "Nama": nama,
                        "Mitra / internal": mitra
                    }
                    pelaksana["executor"].append(executor)
                    print(f"[PM SHELTER]   ✓ Executor #{no}: {nama} - {mitra} (multi-line)")
                    i += 3
                else:
                    i += 1
            else:
                i += 1
        
        print(f"[PM SHELTER] Total executors extracted: {len(pelaksana['executor'])}")
        return pelaksana