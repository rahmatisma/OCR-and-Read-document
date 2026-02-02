"""
Parser untuk Form PM Inverter -48VDC/220VAC
Document Code: FM-LAP-D2-SOP-003-005

 FIXED V3: Changed to checklist-based structure
 FIXED V3: All capacity options shown in array
 FIXED V3: Better pelaksana extraction with proper field names

Struktur Dokumen:
1. Header (No. Dok, Versi, Hal, Label)
2. Informasi Umum (Location, Date/time, Brand, S/N)
3. Physical Check (Environment, LED)
4. Performance & Capacity Check (DC Input, AC Output, Temperature)
5. Notes
6. Pelaksana (Executor, Verifikator, Head)
"""

from parsers.Form_PM_POP.base_pm_parser import BasePMParser
from typing import Dict, List
import re


class PMInverterParser(BasePMParser):
    """Parser untuk Form Preventive Maintenance Inverter -48VDC/220VAC"""
    
    def __init__(self, all_text: str, page_texts: list, ocr_data: list = None):
        super().__init__(all_text, page_texts, ocr_data)
        
        # Capacity options untuk DC/AC Current
        self.DC_CURRENT_OPTIONS = [
            ("500VA", "9 A"),
            ("1000VA", "16 A"),
            ("2000VA", "33 A")
        ]
        
        self.AC_CURRENT_OPTIONS = [
            ("500VA", "2 A"),
            ("1000VA", "4 A"),
            ("2000VA", "7 A")
        ]
    
    def parse(self) -> dict:
        """Parse dokumen Form PM Inverter"""
        print("\n[PM INVERTER] Memulai parsing...")
        
        result = {
            "header": self.extract_header(),
            "informasi_umum": self.extract_informasi_umum(),
            "physical_check": self.extract_physical_check(),
            "performance_check": self.extract_performance_check(),
            "notes": self.extract_notes(),
            "pelaksana": self.extract_pelaksana()
        }
        
        print("[PM INVERTER]  Parsing selesai!")
        return result
    
    # ================================================================
    # PHYSICAL CHECK
    # ================================================================
    def extract_physical_check(self) -> List[Dict]:
        """
        Extract Physical Check items
        
        Format:
        1. Physical Check
        a. Environment Condition  Clean  Clean, No dust  OK
        b. LED / display          Normal Normal          OK
        """
        print("[PM INVERTER] Parsing Physical Check...")
        
        items = []
        
        # Find Physical Check section - more flexible pattern
        section_pattern = r"1\.\s*Physical\s+Check\s*(.*?)(?=2\.\s*Performance|Notes|Executor|$)"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            print("[PM INVERTER] ⚠️ Physical Check section not found")
            return items
        
        section_text = section_match.group(1)
        
        # Extract item a (Environment Condition)
        env_pattern = r"a\.\s*Environment\s+Condition\s+(\w+)\s+.*?(Clean[^\n]*?)\s+(OK|NOK)"
        env_match = re.search(env_pattern, section_text, re.IGNORECASE)
        
        if env_match:
            items.append({
                "no": "1.a",
                "description": "Environment Condition",
                "result": env_match.group(1).strip(),
                "standard": "Clean, No dust",
                "status": env_match.group(3).strip()
            })
            print(f"[PM INVERTER]   ✓ 1.a: {env_match.group(1)}")
        else:
            print("[PM INVERTER]   ⚠️ 1.a not found")
        
        # Extract item b (LED/display)
        led_pattern = r"b\.\s*LED\s*/\s*display\s*\*?\)?\s*(\w+)\s+.*?(Normal[^\n]*?)\s+(OK|NOK)"
        led_match = re.search(led_pattern, section_text, re.IGNORECASE)
        
        if led_match:
            items.append({
                "no": "1.b",
                "description": "LED / display",
                "result": led_match.group(1).strip(),
                "standard": "Normal",
                "status": led_match.group(3).strip()
            })
            print(f"[PM INVERTER]   ✓ 1.b: {led_match.group(1)}")
        else:
            print("[PM INVERTER]   ⚠️ 1.b not found")
        
        return items
    
    # ================================================================
    # PERFORMANCE CHECK - FIXED V3
    # ================================================================
    def extract_performance_check(self) -> List[Dict]:
        """
        Extract Performance and Capacity Check items
        
         FIXED V3: Returns checklist-based structure for multi-capacity items
        
        Format:
        2. Performance and Capacity Check
        a. DC Input Voltage     52,9   48 - 56 VDC        OK
        b. DC Current Input *)  1,01   9 A ( 500 VA )   OK
                                       16 A ( 1000 VA )
                                       33 A ( 2000 VA )
        c. AC Current Output *) -      2 A ( 500 VA )   OK
                                -      4 A ( 1000 VA )
                                       7 A ( 2000 VA )
        d. AC Output Voltage    114,9  190 – 230 VAC      OK
        e. Equipment Temp       25,2   0-35 °C            OK
        """
        print("[PM INVERTER] Parsing Performance & Capacity Check...")
        
        items = []
        
        # Find Performance section
        section_pattern = r"2\.\s*Performance\s+and\s+Capacity\s+Check\s*(.*?)(?=3\.|Notes|Executor|$)"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            print("[PM INVERTER] ⚠️ Performance section not found")
            return items
        
        section_text = section_match.group(1)
        
        # 2.a - DC Input Voltage (single value)
        dc_voltage_item = self._extract_dc_input_voltage(section_text)
        if dc_voltage_item:
            items.append(dc_voltage_item)
            print(f"[PM INVERTER]   ✓ 2.a: {dc_voltage_item['result']}")
        else:
            print("[PM INVERTER]   ⚠️ 2.a not found")
        
        # 2.b - DC Current Input (checklist with multiple capacities)
        dc_current_item = self._extract_dc_current_checklist(section_text)
        if dc_current_item:
            items.append(dc_current_item)
            print(f"[PM INVERTER]   ✓ 2.b: checklist with {len(dc_current_item['checklist'])} items")
        else:
            print("[PM INVERTER]   ⚠️ 2.b not found")
        
        # 2.c - AC Current Output (checklist with multiple capacities)
        ac_current_item = self._extract_ac_current_checklist(section_text)
        if ac_current_item:
            items.append(ac_current_item)
            print(f"[PM INVERTER]   ✓ 2.c: checklist with {len(ac_current_item['checklist'])} items")
        else:
            print("[PM INVERTER]   ⚠️ 2.c not found")
        
        # 2.d - AC Output Voltage (single value)
        ac_voltage_item = self._extract_ac_output_voltage(section_text)
        if ac_voltage_item:
            items.append(ac_voltage_item)
            print(f"[PM INVERTER]   ✓ 2.d: {ac_voltage_item['result']}")
        else:
            print("[PM INVERTER]   ⚠️ 2.d not found")
        
        # 2.e - Equipment Temperature (single value)
        temp_item = self._extract_equipment_temperature(section_text)
        if temp_item:
            items.append(temp_item)
            print(f"[PM INVERTER]   ✓ 2.e: {temp_item['result']}")
        else:
            print("[PM INVERTER]   ⚠️ 2.e not found")
        
        return items
    
    def _extract_dc_input_voltage(self, section_text: str) -> Dict:
        """Extract 2.a - DC Input Voltage (single value)"""
        pattern = r"a\.\s*DC\s+Input\s+Voltage\s+([\d\.,]+)\s+.*?(48\s*-\s*56\s*VDC).*?(OK|NOK)"
        match = re.search(pattern, section_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            return {
                "no": "2.a",
                "description": "DC Input Voltage ",
                "result": match.group(1).strip(),
                "standard": "48 - 56 VDC ",
                "status": match.group(3).strip()
            }
        return None
    
    def _extract_dc_current_checklist(self, section_text: str) -> Dict:
        """
        Extract 2.b - DC Current Input as checklist
        
         Returns all capacity options with filled/unfilled values
        
        Pattern:
        b. DC Current Input *)  1,01   9 A ( 500 VA )   OK
                                       16 A ( 1000 VA )
                                       33 A ( 2000 VA )
        
        Output format:
        {
            "no": "2.b",
            "description": "DC Current Input",
            "checklist": [
                {"result": "1,01", "capacity": "500VA", "standard": "9 A", "status": "OK"},
                {"result": "", "capacity": "1000VA", "standard": "16 A", "status": ""},
                {"result": "", "capacity": "2000VA", "standard": "33 A", "status": ""}
            ]
        }
        """
        # Extract the main result value (first number after "DC Current Input")
        result_pattern = r"b\.\s*DC\s+Current\s+Input\s*\*?\)?\s+([\d\.,\-]+)"
        result_match = re.search(result_pattern, section_text, re.IGNORECASE)
        
        if not result_match:
            return None
        
        main_result = result_match.group(1).strip()
        
        # Extract status (OK/NOK) - usually appears after the first capacity line
        status_pattern = r"b\.\s*DC\s+Current\s+Input.*?9\s*A.*?(OK|NOK)"
        status_match = re.search(status_pattern, section_text, re.IGNORECASE | re.DOTALL)
        main_status = status_match.group(1).strip() if status_match else ""
        
        # Detect which capacity is selected (based on proximity to result)
        selected_capacity = self._detect_capacity_for_dc_current(section_text, main_result)
        
        # Build checklist - ALL options shown
        checklist = []
        for capacity, standard in self.DC_CURRENT_OPTIONS:
            if capacity == selected_capacity:
                # This is the selected option - has result and status
                checklist.append({
                    "result": main_result,
                    "capacity": capacity,
                    "standard": standard,
                    "status": main_status
                })
            else:
                # Not selected - empty result and status
                checklist.append({
                    "result": "",
                    "capacity": capacity,
                    "standard": standard,
                    "status": ""
                })
        
        return {
            "no": "2.b",
            "description": "DC Current Input",
            "checklist": checklist
        }
    
    def _extract_ac_current_checklist(self, section_text: str) -> Dict:
        """
        Extract 2.c - AC Current Output as checklist
        
         Returns all capacity options with filled/unfilled values
        
        IMPORTANT: Ada 2 baris dengan nilai "-" di dokumen
        
        Pattern:
        c. AC Current Output *) -      2 A ( 500 VA )   OK
                                -      4 A ( 1000 VA )
                                       7 A ( 2000 VA )
        """
        # Extract the main result value (first value after "AC Current Output")
        result_pattern = r"c\.\s*AC\s+Current\s+Output\s*\*?\)?\s+([\d\.,\-]+)"
        result_match = re.search(result_pattern, section_text, re.IGNORECASE)
        
        if not result_match:
            return None
        
        main_result = result_match.group(1).strip()
        
        # Extract status - find which line has OK/NOK
        status_pattern = r"c\.\s*AC\s+Current\s+Output.*?2\s*A.*?(OK|NOK)"
        status_match = re.search(status_pattern, section_text, re.IGNORECASE | re.DOTALL)
        main_status = status_match.group(1).strip() if status_match else ""
        
        # Detect selected capacity
        selected_capacity = self._detect_capacity_for_ac_current(section_text, main_result, main_status)
        
        # Build checklist - ALL options shown
        checklist = []
        for capacity, standard in self.AC_CURRENT_OPTIONS:
            if capacity == selected_capacity:
                # Selected option
                checklist.append({
                    "result": main_result,
                    "capacity": capacity,
                    "standard": standard,
                    "status": main_status
                })
            else:
                # Not selected
                checklist.append({
                    "result": "",
                    "capacity": capacity,
                    "standard": standard,
                    "status": ""
                })
        
        return {
            "no": "2.c",
            "description": "AC Current Output",
            "checklist": checklist
        }
    
    def _extract_ac_output_voltage(self, section_text: str) -> Dict:
        """Extract 2.d - AC Output Voltage (single value)"""
        pattern = r"d\.\s*AC\s+Output\s+Voltage\s*\*?\)?\s+([\d\.,]+)\s+.*?(190\s*–\s*230\s*VAC).*?(OK|NOK)"
        match = re.search(pattern, section_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            return {
                "no": "2.d",
                "description": "AC Output Voltage ",
                "result": match.group(1).strip(),
                "standard": "190 – 230 VAC",
                "status": match.group(3).strip()
            }
        return None
    
    def _extract_equipment_temperature(self, section_text: str) -> Dict:
        """Extract 2.e - Equipment Temperature (single value)"""
        pattern = r"e\.\s*Equipment\s+Temperature\s+([\d\.,]+)\s+.*?(0\s*-\s*35).*?(OK|NOK)"
        match = re.search(pattern, section_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            return {
                "no": "2.e",
                "description": "Equipment Temperature",
                "result": match.group(1).strip(),
                "standard": "0-35 c",
                "status": match.group(3).strip()
            }
        return None
    
    # ================================================================
    # CAPACITY DETECTION HELPERS
    # ================================================================
    def _detect_capacity_for_dc_current(self, section_text: str, result_value: str) -> str:
        """
        Detect which DC Current capacity is selected
        
        Method: Find which capacity appears closest to the result value with OK status
        """
        # Find the line with result value and OK
        for capacity, standard in self.DC_CURRENT_OPTIONS:
            # Pattern: result ... standard ... capacity ... OK
            pattern = rf"{re.escape(result_value)}[^\n]*{re.escape(standard)}[^\n]*{re.escape(capacity)}[^\n]*OK"
            if re.search(pattern, section_text, re.IGNORECASE):
                return capacity
        
        # Fallback: based on value magnitude
        try:
            result_float = float(result_value.replace(",", ".").replace("-", "0"))
            if result_float < 12:
                return "500VA"
            elif result_float < 25:
                return "1000VA"
            else:
                return "2000VA"
        except ValueError:
            return "500VA"
    
    def _detect_capacity_for_ac_current(self, section_text: str, result_value: str, status: str) -> str:
        """
        Detect which AC Current capacity is selected
        
        IMPORTANT: Cari baris yang memiliki OK status
        """
        # Extract AC Current section
        ac_section_pattern = r"c\.\s*AC\s+Current\s+Output.*?(?=d\.|e\.|Notes|$)"
        ac_match = re.search(ac_section_pattern, section_text, re.IGNORECASE | re.DOTALL)
        
        if not ac_match:
            return "500VA"
        
        ac_text = ac_match.group(0)
        
        # Find which capacity line has OK status
        for capacity, standard in self.AC_CURRENT_OPTIONS:
            # Pattern: standard ... capacity ... OK
            pattern = rf"{re.escape(standard)}[^\n]*{re.escape(capacity)}[^\n]*OK"
            if re.search(pattern, ac_text, re.IGNORECASE):
                return capacity
        
        # Fallback: first option
        return "500VA"
    
    # ================================================================
    # PELAKSANA - FIXED V4 (Multi-line support)
    # ================================================================
    def extract_pelaksana(self) -> dict:
        """
        Extract pelaksana section - FIXED V4
        
         Handles MULTI-LINE data (number, name, company in separate lines)
         Uses correct field names: "Nama" and "Mitra / internal"
        
        Format in PDF (data can be in separate lines):
        Executor | Verifikator | Head Of Sub Departement
        No | Nama | Mitra/Internal | Signature
        
        1       <- Line 1
        Adi     <- Line 2  
        IMS     <- Line 3
        
        Returns:
            {
                "executor": [{"no": "1", "Nama": "Adi", "Mitra / internal": "IMS"}],
                "verifikator": null,
                "head_of_sub_department": null
            }
        """
        print("[PM INVERTER] Extracting pelaksana...")
        
        pelaksana = {
            "executor": [],
            "verifikator": None,
            "head_of_sub_department": None
        }
        
        # Find pelaksana section - after "Mitra / Internal" header
        section_pattern = r"Mitra\s*/\s*Internal\s*Signature\s*(.*?)$"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            print("[PM INVERTER]   ⚠️ Pelaksana section not found")
            return pelaksana
        
        section_text = section_match.group(1)
        lines = [l.strip() for l in section_text.split('\n')]
        
        # Remove empty lines
        lines = [l for l in lines if l]
        
        print(f"[PM INVERTER] Found {len(lines)} non-empty lines")
        
        # Process lines in groups of 3: number, name, company
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Skip signature placeholders
            if "___" in line or re.match(r'^\s*\(\s*_*\s*\)?\s*$', line):
                i += 1
                continue
            
            # Check if this line is a number (start of executor entry)
            if re.match(r'^\d+$', line):
                no = line
                nama = ""
                mitra = ""
                
                # Next line should be name
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # Skip if it's a number or separator
                    if not re.match(r'^\d+$', next_line) and "___" not in next_line and not re.match(r'^\s*\(\s*_*\s*\)?\s*$', next_line):
                        nama = next_line
                        
                        # Line after should be company
                        if i + 2 < len(lines):
                            third_line = lines[i + 2]
                            if not re.match(r'^\d+$', third_line) and "___" not in third_line and not re.match(r'^\s*\(\s*_*\s*\)?\s*$', third_line):
                                mitra = third_line
                
                # Only add if we have at least number and name
                if nama:
                    executor = {
                        "no": no,
                        "Nama": nama,
                        "Mitra / internal": mitra
                    }
                    pelaksana["executor"].append(executor)
                    print(f"[PM INVERTER]   ✓ Executor #{no}: {nama} - {mitra}")
                    i += 3  # Skip the 3 lines we just processed
                else:
                    i += 1
            else:
                i += 1
        
        print(f"[PM INVERTER] Total executors extracted: {len(pelaksana['executor'])}")
        return pelaksana