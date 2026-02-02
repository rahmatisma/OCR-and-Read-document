"""
Parser untuk Form Dokumentasi dan Pendataan Perangkat - FINAL FIXED VERSION
Document Code: FM-LAP-D2-SOP-003-012

🔧 FINAL FIX:
     connect_status → bonding_ground
     Remove redundant fields: bonding, ground
     Keep only: equipment, qty, status, bonding_ground, keterangan

 Struktur dokumen:
    - Header (reuse base)
    - Informasi Umum: Location + Date/time saja
    - Inventory Table (VERTICAL FORMAT!):
        I.  Device Sentral          → equipment, qty, status, bonding_ground
        II. Supporting Facilities   → equipment, qty, status
    - Notes
    - Pelaksana (Executor)

📋 Output Structure:
    device_sentral: [
        {
            "equipment": "Raisecom",
            "qty": "2",
            "status": "Active",
            "bonding_ground": "Connect",  //  Changed from connect_status
            "keterangan": null
        }
    ]
    
    supporting_facilities: [
        {
            "equipment": "AC",
            "qty": "2",
            "status": "Active",
            "bonding_ground": null,  //  No bonding_ground for Section II
            "keterangan": null
        }
    ]
"""

from parsers.Form_PM_POP.base_pm_parser import BasePMParser
from typing import Dict, List
import re


class PMDokumentasiPendataanPerangkatParser(BasePMParser):
    """Parser untuk Form Dokumentasi dan Pendataan Perangkat - FINAL FIXED"""

    def __init__(self, all_text: str, page_texts: list, ocr_data: list = None):
        super().__init__(all_text, page_texts, ocr_data)

    def parse(self) -> dict:
        """Parse dokumen Form Dokumentasi dan Pendataan Perangkat"""
        print("\n[PM DOKUMENTASI FINAL] Memulai parsing...")

        result = {
            "header": self.extract_header(),
            "informasi_umum": self.extract_informasi_umum_dokumentasi(),
            "inventory": self.extract_inventory_fixed(),
            "notes": self.extract_notes(),
            "pelaksana": self.extract_pelaksana_dokumentasi(),
        }

        print("[PM DOKUMENTASI FINAL]  Parsing selesai!")
        return result

    # ================================================================
    # INFORMASI UMUM
    # ================================================================
    def extract_informasi_umum_dokumentasi(self) -> dict:
        """Extract informasi umum — hanya Location dan Date/time"""
        print("[PM DOKUMENTASI FINAL] Parsing Informasi Umum...")

        return {
            "location": self._extract_location(),
            "date_time": self._extract_datetime(),
        }

    def _extract_location(self) -> str:
        """Location — stop sebelum 'Date / time'"""
        pattern = r"Location\s*:\s*(.*?)(?=Date\s*/\s*time)"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            return value if value else ""
        return ""

    def _extract_datetime(self) -> str:
        """Date/time — stop sebelum table header"""
        pattern = r"Date\s*/\s*time\s*:\s*(.*?)(?=NO\s+EQUIPMENT)"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            return value if value else ""
        return ""

    # ================================================================
    # INVENTORY — FIXED VERSION
    # ================================================================
    def extract_inventory_fixed(self) -> dict:
        """Extract inventory — FIXED untuk handle vertical data"""
        print("[PM DOKUMENTASI FINAL] Parsing Inventory...")

        return {
            "device_sentral": self._extract_device_sentral_fixed(),
            "supporting_facilities": self._extract_supporting_facilities_fixed(),
        }

    def _extract_device_sentral_fixed(self) -> List[Dict]:
        """Extract Section I: Device Sentral - FIXED"""
        print("[PM DOKUMENTASI FINAL]   Parsing Section I: Device Sentral...")

        section_text = self._get_section(
            r"I\.\s*DEVICE\s+SENTRAL", r"II\."
        )
        if not section_text:
            print("[PM DOKUMENTASI FINAL]     ⚠️ Section I tidak ditemukan")
            return []

        rows = self._parse_vertical_inventory(section_text, has_bonding_ground=True)
        print(f"[PM DOKUMENTASI FINAL]     ✓ {len(rows)} equipment parsed")
        return rows

    def _extract_supporting_facilities_fixed(self) -> List[Dict]:
        """Extract Section II: Supporting Facilities - FIXED"""
        print("[PM DOKUMENTASI FINAL]   Parsing Section II: Supporting Facilities...")

        section_text = self._get_section(
            r"II\.\s*SUPPORTING\s+FACILITIES", r"Notes"
        )
        if not section_text:
            print("[PM DOKUMENTASI FINAL]     ⚠️ Section II tidak ditemukan")
            return []

        rows = self._parse_vertical_inventory(section_text, has_bonding_ground=False)
        print(f"[PM DOKUMENTASI FINAL]     ✓ {len(rows)} equipment parsed")
        return rows

    def _parse_vertical_inventory(self, section_text: str, has_bonding_ground: bool = True) -> List[Dict]:
        """
        Parse inventory dari VERTICAL format dengan state machine
        
        Args:
            section_text: Text section yang akan di-parse
            has_bonding_ground: Apakah section ini punya Bonding/Ground field
        
        State Machine:
            EXPECTING_EQUIPMENT → EXPECTING_QTY → EXPECTING_STATUS → [EXPECTING_BONDING_GROUND]
            
        Cycle:
            1. Equipment name (text tanpa angka, bukan "Active"/"Shutdown"/"Connect"/"Not Connect")
            2. QTY (pure number)
            3. Status ("Active" atau "Shutdown")
            4. Bonding/Ground (jika has_bonding_ground=True): "Connect" atau "Not Connect"
            5. Repeat ke step 1
        """
        lines = [l.strip() for l in section_text.strip().split("\n") if l.strip()]
        
        # Merge lines dimulai "(" → handle "(SARPEN)"
        merged_lines = []
        for line in lines:
            if line.startswith("(") and merged_lines:
                merged_lines[-1] += " " + line
            else:
                merged_lines.append(line)
        
        print(f"[PM DOKUMENTASI FINAL]     Total lines: {len(merged_lines)}")
        
        # State machine
        STATE_EQUIPMENT = 0
        STATE_QTY = 1
        STATE_STATUS = 2
        STATE_BONDING_GROUND = 3
        
        state = STATE_EQUIPMENT
        current_row = {}
        rows = []
        
        for i, line in enumerate(merged_lines):
            # Skip pure whitespace atau header labels
            if not line or line.upper() in ["BONDING", "GROUND", "KETERANGAN"]:
                continue
            
            if state == STATE_EQUIPMENT:
                # Expecting equipment name
                if re.match(r'^\d+$', line):
                    # Pure number di awal = ini QTY, skip equipment (kosong)
                    print(f"[PM DOKUMENTASI FINAL]       Line {i}: '{line}' | Pure number at EQUIPMENT - skip to QTY")
                    current_row = {"equipment": "", "qty": line}
                    state = STATE_STATUS
                elif line in ["Active", "Shutdown", "Connect", "Not Connect"]:
                    # Status keyword di awal = skip
                    print(f"[PM DOKUMENTASI FINAL]       Line {i}: '{line}' | Status keyword - skip")
                    continue
                else:
                    # Valid equipment name
                    current_row = {"equipment": line}
                    state = STATE_QTY
                    print(f"[PM DOKUMENTASI FINAL]       Line {i}: '{line}' | Equipment ✓")
            
            elif state == STATE_QTY:
                # Expecting QTY (pure number)
                if re.match(r'^\d+$', line):
                    current_row["qty"] = line
                    state = STATE_STATUS
                    print(f"[PM DOKUMENTASI FINAL]       Line {i}: '{line}' | QTY ✓")
                else:
                    # Not a number - treat as new equipment
                    print(f"[PM DOKUMENTASI FINAL]       Line {i}: '{line}' | Expected QTY - treat as new equipment")
                    current_row = {"equipment": line}
                    state = STATE_QTY
            
            elif state == STATE_STATUS:
                # Expecting Status: "Active" atau "Shutdown"
                if line in ["Active", "Shutdown"]:
                    current_row["status"] = line
                    print(f"[PM DOKUMENTASI FINAL]       Line {i}: '{line}' | Status ✓")
                    
                    if has_bonding_ground:
                        state = STATE_BONDING_GROUND
                    else:
                        # No bonding_ground field - row complete
                        current_row["bonding_ground"] = None
                        current_row["keterangan"] = None
                        rows.append(current_row)
                        print(f"[PM DOKUMENTASI FINAL]       ✓ ROW: {current_row}")
                        current_row = {}
                        state = STATE_EQUIPMENT
                else:
                    # Not status - error recovery
                    print(f"[PM DOKUMENTASI FINAL]       Line {i}: '{line}' | Expected STATUS - reset")
                    if current_row:
                        current_row["status"] = None
                        current_row["bonding_ground"] = None
                        current_row["keterangan"] = None
                        rows.append(current_row)
                    current_row = {"equipment": line}
                    state = STATE_QTY
            
            elif state == STATE_BONDING_GROUND:
                # Expecting Bonding/Ground Status: "Connect" atau "Not Connect"
                if "Not Connect" in line:
                    current_row["bonding_ground"] = "Not Connect"
                    print(f"[PM DOKUMENTASI FINAL]       Line {i}: '{line}' | Bonding/Ground: Not Connect ✓")
                elif "Connect" in line:
                    current_row["bonding_ground"] = "Connect"
                    print(f"[PM DOKUMENTASI FINAL]       Line {i}: '{line}' | Bonding/Ground: Connect ✓")
                else:
                    # No bonding/ground info - set as None
                    current_row["bonding_ground"] = None
                    print(f"[PM DOKUMENTASI FINAL]       Line {i}: '{line}' | No bonding/ground")
                
                # Row complete
                current_row["keterangan"] = None
                rows.append(current_row)
                print(f"[PM DOKUMENTASI FINAL]       ✓ ROW: {current_row}")
                current_row = {}
                state = STATE_EQUIPMENT
        
        # Handle incomplete row at end
        if current_row and current_row.get("equipment"):
            current_row.setdefault("qty", None)
            current_row.setdefault("status", None)
            current_row.setdefault("bonding_ground", None)
            current_row.setdefault("keterangan", None)
            rows.append(current_row)
            print(f"[PM DOKUMENTASI FINAL]       ✓ ROW (incomplete): {current_row}")
        
        return rows

    # ================================================================
    # PELAKSANA
    # ================================================================
    def extract_pelaksana_dokumentasi(self) -> dict:
        """Extract pelaksana — handle vertical dan horizontal format"""
        print("[PM DOKUMENTASI FINAL] Extracting pelaksana...")

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
            print("[PM DOKUMENTASI FINAL]   ⚠️ Pelaksana section tidak ditemukan")
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
                    print(f"[PM DOKUMENTASI FINAL]   ✓ Executor #{no}: {nama}")

                i = j
                continue

            # HORIZONTAL fallback: "1 Adi IMS"
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
                        f"[PM DOKUMENTASI FINAL]   ✓ Executor #{parts[0]}: {parts[1]}"
                    )

            i += 1

        return pelaksana

    # ================================================================
    # HELPER
    # ================================================================
    def _get_section(self, start_pattern: str, end_pattern: str) -> str:
        """Extract text antara start dan end patterns"""
        pattern = rf"{start_pattern}\s*(.*?)(?={end_pattern})"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        return match.group(1) if match else ""