"""
Parser untuk Form PM Battery - V5 FINAL (Multi-Line Accumulation)
Document Code: FM-LAP-D2-SOP-003-010

 V5 FINAL FIXES:
    - Accumulate numbers across multiple lines
    - Form triplets dynamically
    - Fully adaptive to any number of batteries (not hardcoded)
    - Handle incomplete data (e.g., 18 instead of 20 batteries)

📋 Real PDF Format:
    1  12,5     ← Line 1
    80          ← Line 2  
    11  12,5    ← Line 3
    80          ← Line 4
    1  13,1     ← Line 5
    100         ← Line 6
    
    Each triplet spans multiple lines!
"""

from parsers.Form_PM_POP.base_pm_parser import BasePMParser
from typing import Dict, List, Optional, Tuple
import re


class PMBatteryParser(BasePMParser):
    """Parser untuk Form Preventive Maintenance Battery - V5 FINAL"""
    
    def __init__(self, all_text: str, page_texts: list, ocr_data: list = None):
        super().__init__(all_text, page_texts, ocr_data)
    
    def parse(self) -> dict:
        """Parse dokumen Form PM Battery"""
        print("\n[PM BATTERY V5] Memulai parsing...")
        
        result = {
            "header": self.extract_header(),
            "informasi_umum": self.extract_informasi_umum_battery(),
            "battery_banks": self.extract_battery_banks_v5(),
            "measurement_test": self.extract_measurement_test_fixed(),
            "notes": self.extract_notes(),
            "pelaksana": self.extract_pelaksana()
        }
        
        print("[PM BATTERY V5]  Parsing selesai!")
        return result
    
    # ================================================================
    # INFORMASI UMUM
    # ================================================================
    def extract_informasi_umum_battery(self) -> dict:
        """Extract informasi umum dengan field Battery Temperature dan Battery Bank"""
        print("[PM BATTERY V5] Parsing Informasi Umum...")
        
        info = {
            "location": self._extract_simple_field(r"Location\s*:", r"Date|Battery|\n\n"),
            "date_time": self._extract_simple_field(r"Date\s*/?\s*time\s*:", r"Battery|Location|\n\n"),
            "battery_temperature": self._extract_simple_field(r"Battery\s+Temperature\s*:", r"Battery\s+Bank|Date|\n\n"),
            "battery_bank": self._extract_simple_field(r"Battery\s+Bank\s*:", r"Bank\s*:|Temperature|\n\n")
        }
        
        print(f"[PM BATTERY V5]   Location: {info['location']}")
        print(f"[PM BATTERY V5]   Date/Time: {info['date_time']}")
        print(f"[PM BATTERY V5]   Battery Temperature: {info['battery_temperature']}")
        print(f"[PM BATTERY V5]   Battery Bank: {info['battery_bank']}")
        
        return info
    
    # ================================================================
    # BATTERY BANKS - V5 (Multi-Line Accumulation)
    # ================================================================
    def extract_battery_banks_v5(self) -> List[Dict]:
        """
        Extract battery banks - V5 FINAL
        
        KEY IMPROVEMENT: Accumulate numbers across lines to form triplets
        """
        print("[PM BATTERY V5] Parsing Battery Banks...")
        
        banks = []
        
        # Find all bank pairs (UPS + Recti)
        pair_pattern = r'Bank\s*:\s*(\d+)\s+(UPS)\s*\n\s*Battery\s+Type\s*:\s*([^\n]+)\s*\n\s*Battery\s+Brand\s*:\s*([^\n]+)\s*\n\s*End\s+Device\s+Batt\s*:\s*([^\n]+)\s*\n\s*Bank\s*:\s*\1\s+(Recti)\s*\n\s*Battery\s+Type\s*:\s*([^\n]+)\s*\n\s*Battery\s+Brand\s*:\s*([^\n]+)\s*\n\s*End\s+Device\s+Batt\s*:\s*([^\n]+)'
        
        pair_matches = list(re.finditer(pair_pattern, self.all_text, re.IGNORECASE))
        
        print(f"[PM BATTERY V5]   Found {len(pair_matches)} bank pairs")
        
        for pair_idx, pair_match in enumerate(pair_matches):
            bank_number = pair_match.group(1)
            
            # UPS info
            ups_type = pair_match.group(3).strip()
            ups_brand = pair_match.group(4).strip()
            ups_end_device = pair_match.group(5).strip()
            
            # Recti info
            recti_type = pair_match.group(7).strip()
            recti_brand = pair_match.group(8).strip()
            recti_end_device = pair_match.group(9).strip()
            
            print(f"[PM BATTERY V5]   Processing Bank {bank_number}...")
            print(f"[PM BATTERY V5]     UPS: {ups_brand} {ups_type} ({ups_end_device})")
            print(f"[PM BATTERY V5]     Recti: {recti_brand} {recti_type} ({recti_end_device})")
            
            # Extract table
            table_start = pair_match.end()
            
            # Determine table end
            if pair_idx < len(pair_matches) - 1:
                table_end = pair_matches[pair_idx + 1].start()
            else:
                # Last pair
                measurement_match = re.search(
                    r'(\*\s*Measurement|\*\s*Standard|No\.\s+Descriptions)', 
                    self.all_text[table_start:], 
                    re.IGNORECASE
                )
                if measurement_match:
                    table_end = table_start + measurement_match.start()
                else:
                    table_end = len(self.all_text)
            
            table_text = self.all_text[table_start:table_end]
            
            # Parse table - V5 method (multi-line accumulation)
            ups_data, recti_data = self._parse_shared_table_v5(table_text, bank_number)
            
            # Create banks
            banks.append({
                "bank_number": bank_number,
                "bank_type": "UPS",
                "battery_type": ups_type,
                "battery_brand": ups_brand,
                "end_device_batt": ups_end_device,
                "voltage_soh_table": ups_data
            })
            
            banks.append({
                "bank_number": bank_number,
                "bank_type": "Recti",
                "battery_type": recti_type,
                "battery_brand": recti_brand,
                "end_device_batt": recti_end_device,
                "voltage_soh_table": recti_data
            })
        
        print(f"[PM BATTERY V5]   Total banks created: {len(banks)}")
        return banks
    
    def _parse_shared_table_v5(self, table_text: str, bank_number: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Parse SHARED table - V5 FIXED (Reject row numbers as voltage)
        """
        print(f"[PM BATTERY V5]     Parsing shared table for Bank {bank_number}...")
        
        ups_data = []
        recti_data = []
        
        # Remove header lines first
        lines = table_text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip headers and empty lines
            if not line or re.match(r'^No\s+Voltage\s+SOH', line, re.IGNORECASE):
                continue
            cleaned_lines.append(line)
        
        # Rejoin into single text for number extraction
        cleaned_text = ' '.join(cleaned_lines)
        
        # Extract ALL numbers (including decimals with comma or dot)
        all_numbers = re.findall(r'\d+(?:[,\.]\d+)?', cleaned_text)
        
        print(f"[PM BATTERY V5]     Extracted {len(all_numbers)} total numbers")
        print(f"[PM BATTERY V5]     First 20 numbers: {all_numbers[:20]}")
        
        # Form triplets
        triplets = []
        i = 0
        
        while i + 2 < len(all_numbers):
            no = all_numbers[i]
            voltage = all_numbers[i + 1]
            soh = all_numbers[i + 2]
            
            # Validate this is a valid triplet
            try:
                no_int = int(no)
                voltage_float = float(voltage.replace(',', '.'))
                soh_int = int(soh)
                
                # CRITICAL FIX: Reject if voltage looks like a row number
                # Valid battery voltage: 10.0-15.0 VDC
                # Row numbers: 1-20 (whole numbers)
                # If voltage is a whole number 1-20, it's likely a row number!
                
                is_valid_voltage = 10.0 <= voltage_float <= 15.0
                is_valid_soh = 0 <= soh_int <= 100
                is_reasonable_no = 1 <= no_int <= 20
                
                # NEW: Check if voltage is a whole number in row range
                is_voltage_whole_number = voltage_float == int(voltage_float)
                is_in_row_range = 1 <= voltage_float <= 20
                
                # Reject if voltage looks like row number
                if is_voltage_whole_number and is_in_row_range:
                    print(f"[PM BATTERY V5]       ⚠️ Skip: V={voltage} is likely row number, not voltage")
                    i += 1
                    continue
                
                # Also reject if SOH is very low (<10) which is unrealistic
                if soh_int < 10:
                    print(f"[PM BATTERY V5]       ⚠️ Skip: SOH={soh} too low (<10%)")
                    i += 1
                    continue
                
                if is_valid_voltage and is_valid_soh and is_reasonable_no:
                    triplets.append((no, voltage, soh))
                    print(f"[PM BATTERY V5]       Triplet {len(triplets)}: ({no}, {voltage}, {soh}) ✓")
                    i += 3  # Move to next triplet
                    continue
                else:
                    # Invalid triplet
                    if not is_valid_voltage:
                        print(f"[PM BATTERY V5]       ⚠️ Skip: V={voltage} out of range (10-15 VDC)")
                    elif not is_valid_soh:
                        print(f"[PM BATTERY V5]       ⚠️ Skip: SOH={soh} out of range (0-100%)")
                    else:
                        print(f"[PM BATTERY V5]       ⚠️ Skip: No={no} unreasonable")
                    i += 1
            except (ValueError, AttributeError) as e:
                print(f"[PM BATTERY V5]       ⚠️ Parse error at index {i}: {e}, trying shift...")
                i += 1
        
        print(f"[PM BATTERY V5]     Total triplets formed: {len(triplets)}")
        
        # Mapping logic tetap sama...
        ups_numbers_seen = set()
        recti_numbers_seen = set()
        
        for triplet_idx, (no, voltage, soh) in enumerate(triplets):
            entry = {
                "no": no,
                "voltage": voltage,
                "soh": soh
            }
            
            if no in ups_numbers_seen:
                if no not in recti_numbers_seen:
                    recti_data.append(entry)
                    recti_numbers_seen.add(no)
                    print(f"[PM BATTERY V5]         → Recti (duplicate no {no})")
                else:
                    print(f"[PM BATTERY V5]         → Skip (already in Recti)")
            else:
                ups_data.append(entry)
                ups_numbers_seen.add(no)
                print(f"[PM BATTERY V5]         → UPS (first no {no})")
        
        # Sort by number
        ups_data.sort(key=lambda x: int(x['no']))
        recti_data.sort(key=lambda x: int(x['no']))
        
        print(f"[PM BATTERY V5]     Final: UPS={len(ups_data)} rows, Recti={len(recti_data)} rows")
        
        return (ups_data, recti_data)
    
    # ================================================================
    # MEASUREMENT TEST
    # ================================================================
    def extract_measurement_test_fixed(self) -> List[Dict]:
        """Extract measurement test"""
        print("[PM BATTERY V5] Parsing Measurement Test...")
        
        items = []
        
        # Find measurement section
        section_pattern = r"No\.\s+Descriptions\s+Result\s+Operational\s+Standard\s+Status.*?(?=Notes|Executor|$)"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            print("[PM BATTERY V5]   ⚠️ Measurement section not found")
            return items
        
        section_text = section_match.group(0)
        print(f"[PM BATTERY V5]   Section found: {len(section_text)} chars")
        
        # Find all item markers
        item_pattern = r'\n\s*([1-9][a-z]?\.|[a-z]\.)\s+'
        item_markers = list(re.finditer(item_pattern, section_text, re.IGNORECASE))
        
        print(f"[PM BATTERY V5]   Found {len(item_markers)} item markers")
        
        for idx, marker in enumerate(item_markers):
            item_no = marker.group(1).rstrip('.')
            item_start = marker.end()
            
            # Find item end
            if idx < len(item_markers) - 1:
                item_end = item_markers[idx + 1].start()
            else:
                item_end = len(section_text)
            
            item_text = section_text[item_start:item_end].strip()
            
            # Parse item
            parsed = self._parse_measurement_item_fixed(item_no, item_text)
            if parsed:
                items.append(parsed)
                print(f"[PM BATTERY V5]   ✓ Item {item_no}: {parsed['description'][:40]}...")
        
        print(f"[PM BATTERY V5]   Total measurement items: {len(items)}")
        return items
    
    def _parse_measurement_item_fixed(self, item_no: str, item_text: str) -> Optional[Dict]:
        """Parse satu measurement item"""
        # Clean
        clean_text = re.sub(r'\s+', ' ', item_text).strip()
        
        # Extract status (OK/NOK at the end)
        status = None
        status_match = re.search(r'\b(OK|NOK)\b\s*$', clean_text, re.IGNORECASE)
        
        if status_match:
            status = status_match.group(1)
            clean_text = clean_text[:status_match.start()].strip()
        
        # Extract operational standard
        standard = None
        std_patterns = [
            r'(Min\s+[\d,\.]+\s+\w+)',
            r'(≥\s*[\d,\.]+\s*\w+)',
            r'([\d,\.]+\s*-\s*[\d,\.]+\s*\w+)',
        ]
        
        for std_pattern in std_patterns:
            std_match = re.search(std_pattern, clean_text, re.IGNORECASE)
            if std_match:
                standard = std_match.group(1).strip()
                clean_text = clean_text[:std_match.start()].strip()
                break
        
        # What's left: description and result
        parts = clean_text.split()
        
        result = None
        description = clean_text
        
        if len(parts) >= 2:
            result = parts[-1]
            description = ' '.join(parts[:-1])
        elif len(parts) == 1:
            result = parts[0]
            description = ""
        
        return {
            "no": item_no,
            "description": description.strip(),
            "result": result if result else "",
            "operational_standard": standard,
            "status": status
        }
    
    # ================================================================
    # NOTES
    # ================================================================
    def extract_notes(self) -> Optional[str]:
        """Extract notes dengan support multi-line"""
        print("[PM BATTERY V5] Parsing Notes...")
        
        pattern = r"Notes\s*/\s*additional\s+informations?\s*:\s*(.*?)(?=Executor|Verifikator|Pelaksana|$)"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("[PM BATTERY V5]   No notes found")
            return None
        
        notes = match.group(1).strip()
        
        # Clean excessive newlines
        notes = re.sub(r'\n\s*\n+', '\n', notes)
        notes = re.sub(r'[ \t]+', ' ', notes)
        
        if notes:
            print(f"[PM BATTERY V5]   ✓ Notes found: {len(notes)} chars")
            return notes
        
        return None