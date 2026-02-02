"""
Parser untuk Form Preventive Maintenance AC - FIXED VERSION V2
Document Code: FM-LAP-D2-SOP-003-004

 FIXED ISSUES V2:
    1. Input Current parsing - properly format standard dengan newlines
    2. Standard format: "¾ -1 PK ≤ 4 A\n2 PK ≤ 10 A"
    3. Better handling of multi-line standards

📋 Format Standard yang benar:
    Input Current AC
    AC = 1 PK 3,26 Amp ¾ -1 PK ≤ 4 A
                        2 PK ≤ 10 A
                        OK
"""

from parsers.Form_PM_POP.base_pm_parser import BasePMParser
from typing import Dict, List, Optional
import re


# Known result values untuk Physical Check AC
KNOWN_RESULTS = ["No Dust", "Clean", "Normal", "Good", "Bad", "Dirty"]


class PMACParser(BasePMParser):
    """Parser untuk Form Preventive Maintenance AC - FIXED V2"""

    def __init__(self, all_text: str, page_texts: list, ocr_data: list = None):
        super().__init__(all_text, page_texts, ocr_data)

    def parse(self) -> dict:
        """Parse dokumen Form PM AC"""
        print("\n[PM AC FIXED V2] Memulai parsing...")

        result = {
            "header": self.extract_header(),
            "informasi_umum": self.extract_informasi_umum_ac(),
            "physical_check": self.extract_physical_check(),
            "psi_pressure": self.extract_psi_pressure(),
            "input_current": self.extract_input_current_fixed_v2(),
            "output_temperature": self.extract_output_temperature_fixed(),
            "notes": self.extract_notes(),
            "pelaksana": self.extract_pelaksana_ac(),
        }

        print("[PM AC FIXED V2]  Parsing selesai!")
        return result

    # ================================================================
    # INFORMASI UMUM
    # ================================================================
    def extract_informasi_umum_ac(self) -> dict:
        """Extract informasi umum AC"""
        print("[PM AC FIXED V2] Parsing Informasi Umum...")

        result = {
            "location": self._extract_location(),
            "date_time": self._extract_datetime_fixed(),
            "reg_number": self._extract_reg_number_fixed(),
            "brand_type": self._extract_brand_type_fixed(),
            "serial_number": self._extract_serial_number(),
            "capacity": self._extract_capacity(),
        }
        
        print(f"[PM AC FIXED V2]   Location: '{result['location']}'")
        print(f"[PM AC FIXED V2]   Date/Time: '{result['date_time']}'")
        print(f"[PM AC FIXED V2]   Reg Number: '{result['reg_number']}'")
        print(f"[PM AC FIXED V2]   Brand/Type: '{result['brand_type']}'")
        print(f"[PM AC FIXED V2]   S/N: {result['serial_number']}")
        print(f"[PM AC FIXED V2]   Capacity: '{result['capacity']}'")
        
        return result

    def _extract_location(self) -> str:
        """Location — stop sebelum 'Date / time'"""
        pattern = r"Location\s*:\s*(.*?)(?=Date\s*/\s*time)"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            return value if value else ""
        return ""

    def _extract_datetime_fixed(self) -> str:
        """Date/time — handle berbagai format"""
        pattern = r"Date\s*/\s*time\s*:\s*([^\n]+?)(?=\s+Reg\.?\s*Number)"
        match = re.search(pattern, self.all_text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            value = re.sub(r'\s+', ' ', value)
            if value and value != '-':
                return value
        
        pattern2 = r"Date\s*/\s*time\s*:\s*([^\n]+)"
        match2 = re.search(pattern2, self.all_text, re.IGNORECASE)
        
        if match2:
            full_line = match2.group(1).strip()
            if re.search(r'Reg\.?\s*Number', full_line, re.IGNORECASE):
                parts = re.split(r'Reg\.?\s*Number', full_line, maxsplit=1, flags=re.IGNORECASE)
                value = parts[0].strip()
                if value and value != '-':
                    return value
            else:
                if full_line and full_line != '-':
                    return full_line
        
        return ""

    def _extract_reg_number_fixed(self) -> str:
        """Reg.Number — handle berbagai format"""
        pattern = r"Reg\.?\s*Number\s*:\s*([^\n]+)"
        match = re.search(pattern, self.all_text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            value = value.strip('-').strip()
            if value and value not in ['-', '_', '']:
                return value
        
        return ""

    def _extract_brand_type_fixed(self) -> str:
        """Brand/Type — handle berbagai format"""
        pattern = r"Brand\s*/\s*Type\s*:\s*(.*?)(?=\s+S\s*/?\s*N\s*:)"
        match = re.search(pattern, self.all_text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            value = re.sub(r'\s+', ' ', value)
            if value and value != '-':
                return value
        
        pattern2 = r"Brand\s*/\s*Type\s*:\s*([^\n]+)"
        match2 = re.search(pattern2, self.all_text, re.IGNORECASE)
        
        if match2:
            full_line = match2.group(1).strip()
            if re.search(r'S\s*/?\s*N\s*:', full_line, re.IGNORECASE):
                parts = re.split(r'S\s*/?\s*N\s*:', full_line, maxsplit=1, flags=re.IGNORECASE)
                value = parts[0].strip()
                if value and value != '-':
                    return value
            else:
                if full_line and full_line != '-':
                    return full_line
        
        return ""

    def _extract_serial_number(self) -> dict:
        """S/N multi-value — AC 1 dan AC 2"""
        ac_1 = ""
        ac_2 = ""

        ac1_match = re.search(
            r"S\s*/?\s*N\s*:.*?AC\s*1\s*:\s*(\S+)",
            self.all_text,
            re.IGNORECASE,
        )
        if ac1_match:
            ac_1 = ac1_match.group(1).strip()

        ac2_match = re.search(
            r"AC\s*2\s*:\s*(\S+)", self.all_text, re.IGNORECASE
        )
        if ac2_match:
            ac_2 = ac2_match.group(1).strip()

        return {"ac_1": ac_1, "ac_2": ac_2}

    def _extract_capacity(self) -> str:
        """Capacity — stop sebelum 'AC 2' atau table header"""
        pattern = r"Capacity\s*:\s*(.*?)(?=AC\s*\d|N0\.|No\.)"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            return value if value else ""
        return ""

    # ================================================================
    # PHYSICAL CHECK
    # ================================================================
    def extract_physical_check(self) -> List[Dict]:
        """Extract Physical Check items (5 items: a-e)"""
        print("[PM AC FIXED V2] Parsing Physical Check...")

        section_text = self._get_section(r"1\.\s*Physical\s+Check", r"2\.")
        if not section_text:
            print("[PM AC FIXED V2]   ⚠️ Physical Check section tidak ditemukan")
            return []

        items_raw = self._split_items_by_marker(section_text, "abcde")

        items = []
        for letter in sorted(items_raw.keys()):
            item = self._parse_physical_check_item(letter, items_raw[letter])
            if item:
                items.append(item)
                print(
                    f"[PM AC FIXED V2]   ✓ 1.{letter}: "
                    f"result={item['result']}, status={item['status']}"
                )

        return items

    def _parse_physical_check_item(self, letter: str, raw_lines: List[str]) -> Dict:
        """Parse satu item Physical Check"""
        content = " ".join(" ".join(raw_lines).split())

        # Extract Status
        status_match = re.search(r"\s+(OK|NOK)\s*$", content, re.IGNORECASE)
        status = status_match.group(1) if status_match else None
        content_no_status = (
            content[: status_match.start()].strip() if status_match else content
        )

        # Cari known result — posisi PALING KIRI
        earliest_match = None
        earliest_pos = len(content_no_status)

        for known in KNOWN_RESULTS:
            m = re.search(
                rf"\b{re.escape(known)}\b", content_no_status, re.IGNORECASE
            )
            if m and m.start() < earliest_pos:
                earliest_match = m
                earliest_pos = m.start()

        if earliest_match:
            description = content_no_status[: earliest_match.start()].strip()
            result = earliest_match.group(0)
            standard = content_no_status[earliest_match.end() :].strip()
        else:
            description = content_no_status
            result = None
            standard = None

        return {
            "no": f"1.{letter}",
            "description": description,
            "result": result,
            "standard": standard,
            "status": status,
        }

    # ================================================================
    # PSI PRESSURE
    # ================================================================
    def extract_psi_pressure(self) -> Optional[Dict]:
        """Extract section 2: PSI Pressure"""
        print("[PM AC FIXED V2] Parsing PSI Pressure...")

        section_text = self._get_section(r"2\.\s*PSI\s+Pressure", r"3\.")
        if not section_text:
            print("[PM AC FIXED V2]   ⚠️ PSI Pressure tidak ditemukan")
            return None

        content = " ".join(section_text.split())

        # Extract Status
        status_match = re.search(r"\s+(OK|NOK)\s*$", content, re.IGNORECASE)
        status = status_match.group(1) if status_match else None
        content_no_status = (
            content[: status_match.start()].strip() if status_match else content
        )

        # Strip trailing "-"
        content_no_status = content_no_status.rstrip(" -").strip()

        # Result = angka + "psi"
        result_match = re.search(
            r"(\d+(?:[,.]\d+)?\s*psi)\b", content_no_status, re.IGNORECASE
        )

        if result_match:
            result = result_match.group(1)
            standard = content_no_status[result_match.end() :].strip()
            print(f"[PM AC FIXED V2]   ✓ PSI Pressure: result={result}, status={status}")
            return {
                "no": "2",
                "description": "PSI Pressure",
                "result": result,
                "standard": standard,
                "status": status,
            }

        print("[PM AC FIXED V2]   ⚠️ PSI Pressure result tidak ditemukan")
        return None

    # ================================================================
    # INPUT CURRENT — FIXED VERSION V2
    # 
    # Format di PDF (berdasarkan gambar):
    #   "3. Input Current AC
    #    AC = 1 PK 3,26 Amp ¾ -1 PK ≤ 4 A
    #                        2 PK ≤ 10 A
    #                        OK"
    #
    # Output JSON yang diharapkan:
    #   {
    #     "description": "Input Current AC (AC = 1 PK)",
    #     "result": "3,26 Amp",
    #     "standard": "¾ -1 PK ≤ 4 A\n2 PK ≤ 10 A",
    #     "status": "OK"
    #   }
    # ================================================================
    def extract_input_current_fixed_v2(self) -> Optional[Dict]:
        """Extract section 3: Input Current AC - FIXED VERSION V2"""
        print("[PM AC FIXED V2] Parsing Input Current...")

        # Get raw section text (preserve newlines)
        section_pattern = r"3\.\s*Input\s+Current\s+AC\s*(.*?)(?=4\.|Notes|$)"
        section_match = re.search(section_pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        
        if not section_match:
            print("[PM AC FIXED V2]   ⚠️ Input Current tidak ditemukan")
            return None

        section_text = section_match.group(1)
        
        # Extract Status first
        status = ""
        status_match = re.search(r"\b(OK|NOK)\b", section_text, re.IGNORECASE)
        if status_match:
            status = status_match.group(1)
            # Remove status dari section text untuk processing
            section_text = section_text[:status_match.start()] + section_text[status_match.end():]

        # Extract AC capacity: "AC = 1 PK"
        ac_capacity = ""
        capacity_match = re.search(r"AC\s*=\s*(\d+)\s*PK", section_text, re.IGNORECASE)
        if capacity_match:
            ac_capacity = f"AC = {capacity_match.group(1)} PK"

        # Extract Result: angka + "Amp"
        result = ""
        result_match = re.search(r"(\d+[,\.]\d+)\s*Amp", section_text, re.IGNORECASE)
        if result_match:
            result = f"{result_match.group(1)} Amp"

        # Extract Standard - ini bagian yang penting!
        # Format: "¾ -1 PK ≤ 4 A" di satu baris, "2 PK ≤ 10 A" di baris berikutnya
        standard = ""
        
        if result_match:
            # Ambil text setelah result
            text_after_result = section_text[result_match.end():].strip()
            
            # Split by newlines
            lines = text_after_result.split('\n')
            
            # Filter dan clean setiap line
            standard_lines = []
            for line in lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Skip lines that only contain status
                if re.match(r'^\s*(OK|NOK)\s*$', line, re.IGNORECASE):
                    continue
                
                # Clean the line
                # Replace multiple spaces dengan single space
                line = re.sub(r'\s+', ' ', line)
                
                # Tambahkan ke standard_lines
                standard_lines.append(line)
            
            # Join dengan newline
            standard = '\n'.join(standard_lines)

        # Build description
        description = "Input Current AC"
        if ac_capacity:
            description += f" ({ac_capacity})"

        print(f"[PM AC FIXED V2]   ✓ Input Current:")
        print(f"[PM AC FIXED V2]     - Description: {description}")
        print(f"[PM AC FIXED V2]     - Result: {result}")
        print(f"[PM AC FIXED V2]     - Standard: {repr(standard)}")  # Use repr to see \n
        print(f"[PM AC FIXED V2]     - Status: {status}")

        return {
            "no": "3",
            "description": description,
            "result": result,
            "standard": standard,
            "status": status,
        }

    # ================================================================
    # OUTPUT TEMPERATURE
    # ================================================================
    def extract_output_temperature_fixed(self) -> Optional[Dict]:
        """Extract section 4: Output Temperature AC"""
        print("[PM AC FIXED V2] Parsing Output Temperature...")

        section_text = self._get_section(
            r"4\.\s*Output\s+Temperature\s+AC", r"Notes|$"
        )
        if not section_text:
            print("[PM AC FIXED V2]   ⚠️ Output Temperature tidak ditemukan")
            return None

        content = " ".join(section_text.split())

        # Extract Status
        status_match = re.search(r"\s+(OK|NOK)\s*$", content, re.IGNORECASE)
        status = status_match.group(1) if status_match else None
        content_no_status = (
            content[: status_match.start()].strip() if status_match else content
        )

        # Ellipsis pattern
        ellipsis_pattern = r'[…\.]{3,}'
        
        # Cari angka range (16 - 20)
        range_match = re.search(r'(\d+)\s*-\s*(\d+)', content_no_status)
        
        result = None
        standard = ""
        
        if range_match:
            temp_min = range_match.group(1)
            temp_max = range_match.group(2)
            
            before_range = content_no_status[:range_match.start()].strip()
            before_range = re.sub(ellipsis_pattern, '', before_range).strip()
            
            result_before = re.search(r'(\d+(?:[,\.]\d+)?)\s*$', before_range)
            if result_before:
                result = result_before.group(1)
            
            standard = f"{temp_min} - {temp_max}°C"
        else:
            num_match = re.search(r'(\d+(?:[,\.]\d+)?)', content_no_status)
            if num_match:
                ellipsis_match = re.search(ellipsis_pattern, content_no_status)
                
                if ellipsis_match and num_match.start() < ellipsis_match.start():
                    result = num_match.group(1)
                    standard = ""
                elif ellipsis_match:
                    result = None
                    standard = f"{num_match.group(1)}°C"
                else:
                    result = num_match.group(1)

        print(f"[PM AC FIXED V2]   ✓ Output Temperature:")
        print(f"[PM AC FIXED V2]     - Result: {result}")
        print(f"[PM AC FIXED V2]     - Standard: {standard}")
        print(f"[PM AC FIXED V2]     - Status: {status}")

        return {
            "no": "4",
            "description": "Output Temperature AC",
            "result": result,
            "standard": standard,
            "status": status,
        }

    # ================================================================
    # PELAKSANA
    # ================================================================
    def extract_pelaksana_ac(self) -> dict:
        """Extract pelaksana section"""
        print("[PM AC FIXED V2] Extracting pelaksana...")

        pelaksana = {
            "executor": [],
            "verifikator": None,
            "head_of_sub_department": None,
        }

        section_match = re.search(
            r"No\s+Nama\s+Mitra\s*/\s*Internal\s+Signature\s*(.*?)$",
            self.all_text,
            re.IGNORECASE | re.DOTALL,
        )
        if not section_match:
            print("[PM AC FIXED V2]   ⚠️ Pelaksana section tidak ditemukan")
            return pelaksana

        lines = [
            l.strip()
            for l in section_match.group(1).split("\n")
            if l.strip()
        ]

        i = 0
        while i < len(lines):
            line = lines[i]

            # Skip placeholders
            if "___" in line or re.match(r"^\(\s*_+", line):
                i += 1
                continue

            # VERTICAL: line = angka saja
            if re.match(r"^\d+$", line):
                no = line
                nama = ""
                mitra = ""

                j = i + 1
                collected = []
                while j < len(lines):
                    next_line = lines[j]
                    if re.match(r"^\d+$", next_line):
                        break
                    if "___" in next_line or re.match(r"^\(\s*_+", next_line):
                        break
                    collected.append(next_line)
                    j += 1

                if len(collected) >= 1:
                    nama = collected[0]
                if len(collected) >= 2:
                    mitra = collected[1]

                if nama:
                    pelaksana["executor"].append(
                        {
                            "no": no,
                            "Nama": nama,
                            "Mitra / internal": mitra,
                        }
                    )
                    print(f"[PM AC FIXED V2]   ✓ Executor #{no}: {nama}")

                i = j
                continue

            # HORIZONTAL: "1 ADI IMS"
            parts = line.split()
            parts = [p for p in parts if p.strip()]
            
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
                    print(f"[PM AC FIXED V2]   ✓ Executor #{parts[0]}: {parts[1]}")

            i += 1

        return pelaksana

    # ================================================================
    # HELPER METHODS
    # ================================================================
    def _get_section(self, start_pattern: str, end_pattern: str) -> str:
        """Extract text antara start dan end patterns"""
        pattern = rf"{start_pattern}\s*(.*?)(?={end_pattern})"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        return match.group(1) if match else ""

    def _split_items_by_marker(
        self, section_text: str, valid_letters: str
    ) -> Dict[str, List[str]]:
        """Split section text menjadi dict {letter: [lines]}"""
        lines = section_text.strip().split("\n")
        items_dict = {}
        current_letter = None

        for line in lines:
            marker_match = re.match(
                rf"^([{valid_letters}])\.\s*(.*)", line, re.IGNORECASE
            )
            if marker_match:
                current_letter = marker_match.group(1).lower()
                items_dict[current_letter] = [marker_match.group(2)]
            elif current_letter:
                items_dict[current_letter].append(line)

        return items_dict