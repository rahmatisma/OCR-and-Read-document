"""
Parser untuk Form PM Pole / Tower
Document Code: FM-LAP-D2-SOP-003-011

 Struktur dokumen:
    - Header (reuse base)
    - Informasi Umum: Location, Date/time, Type Pole (field khusus)
    - 1. Physical Check: 8 items (a-h) — description & standard MULTI-LINE
    - 2. Performance Measurement: 1 item (a) — result berupa angka
    - Notes
    - Pelaksana (Executor)

⚠️  KEY CHALLENGES yang sudah di-handle:
    1. Description dan Standard bisa MULTI-LINE (misal item a, b, c, d, h)
    2. Huruf dalam kata (misal "structurally strong") bisa tertangkap sebagai
       item marker kalau regex tidak di-anchor ke start-of-line
    3. Location & Date/time bisa KOSONG di form
    4. "Normal" bisa muncul di Standard (misal "Normal Condition:") —
       heuristic: ambil "Normal" PERTAMA sebagai Result
"""

from parsers.Form_PM_POP.base_pm_parser import BasePMParser
from typing import Dict, List
import re


class PMPoleTowerParser(BasePMParser):
    """Parser untuk Form Preventive Maintenance Pole / Tower"""

    def __init__(self, all_text: str, page_texts: list, ocr_data: list = None):
        super().__init__(all_text, page_texts, ocr_data)

    def parse(self) -> dict:
        """Parse dokumen Form PM Pole / Tower"""
        print("\n[PM POLE TOWER] Memulai parsing...")

        result = {
            "header": self.extract_header(),
            "informasi_umum": self.extract_informasi_umum_pole_tower(),
            "physical_check": self.extract_physical_check(),
            "performance_measurement": self.extract_performance_measurement(),
            "notes": self.extract_notes(),
            "pelaksana": self.extract_pelaksana_pole_tower(),
        }

        print("[PM POLE TOWER]  Parsing selesai!")
        return result

    # ================================================================
    # INFORMASI UMUM — Override karena ada "Type Pole" dan tidak ada
    # Brand/Type, Reg Number, S/N
    # ================================================================
    def extract_informasi_umum_pole_tower(self) -> dict:
        """
        Extract informasi umum Pole / Tower.

        Fields:
            - location   : bisa kosong
            - date_time  : bisa kosong
            - type_pole  : SST / Pole / Tripole / Triangle / Triangle Wired
        """
        print("[PM POLE TOWER] Parsing Informasi Umum...")

        return {
            "location": self._extract_location_pole(),
            "date_time": self._extract_datetime_pole(),
            "type_pole": self._extract_type_pole(),
        }

    def _extract_location_pole(self) -> str:
        """
        Extract Location — stop SEBELUM 'Date / time' atau 'Type Pole'.
        Handles kosong (field tidak diisi).
        """
        pattern = r"Location\s*:\s*(.*?)(?=Date\s*/\s*time|Type\s+Pole)"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            return value if value else ""
        return ""

    def _extract_datetime_pole(self) -> str:
        """
        Extract Date / time — stop SEBELUM 'Type Pole'.
        Handles kosong.
        """
        pattern = r"Date\s*/\s*time\s*:\s*(.*?)(?=Type\s+Pole)"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip().strip(":")
            return value.strip() if value.strip() else ""
        return ""

    def _extract_type_pole(self) -> str:
        """Extract Type Pole (single-line field)"""
        pattern = r"Type\s+Pole\s*:\s*([^\n]+)"
        match = re.search(pattern, self.all_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    # ================================================================
    # PHYSICAL CHECK — 8 items (a–h)
    #
    # Tantangan utama di sini:
    #   - Description bisa MULTI-LINE (misal "Pole/Tower Foundation
    #     Flange/Base\nPlate Condition")
    #   - Standard juga MULTI-LINE (misal "Condition: No cracks and no\n
    #     settlement in the building's soil\nor concrete structure.")
    #   - Huruf di tengah kata ("structurally strong") bisa tertangkap
    #     kalau regex tidak di-anchor ke start-of-line
    #
    # Solusi: Manual line-by-line grouping berdasarkan item marker
    #   "^[a-h]\." di start of line → mulai item baru
    #   Lines lainnya → append ke item current
    # ================================================================
    def extract_physical_check(self) -> List[Dict]:
        """Extract Physical Check items (8 items: a–h)"""
        print("[PM POLE TOWER] Parsing Physical Check...")

        # Ambil section antara "1. Physical Check" dan "2. Performance"
        section_text = self._get_section(
            r"1\.\s*Physical\s+Check", r"2\.\s*Performance"
        )
        if not section_text:
            print("[PM POLE TOWER]   ⚠️ Physical Check section tidak ditemukan")
            return []

        # Group lines per item menggunakan manual split
        items_raw = self._split_items_by_marker(section_text, "abcdefgh")

        items = []
        for letter in sorted(items_raw.keys()):
            item = self._parse_physical_check_item(letter, items_raw[letter])
            if item:
                items.append(item)
                print(
                    f"[PM POLE TOWER]   ✓ 1.{letter}: "
                    f"result={item['result']}, status={item['status']}"
                )

        return items

    def _parse_physical_check_item(self, letter: str, raw_lines: List[str]) -> Dict:
        """
        Parse satu item Physical Check dari list of raw lines.

        Logic:
            1. Flatten lines menjadi satu string (normalize whitespace)
            2. Extract Status (OK/NOK) dari akhir string
            3. Cari "Normal" pertama sebagai Result
            4. Sebelum Result = Description
            5. Setelah Result = Standard
        """
        # Flatten + normalize whitespace
        content = " ".join(" ".join(raw_lines).split())

        # Step 1: Extract Status (OK / NOK) dari akhir
        status_match = re.search(r"\s+(OK|NOK)\s*$", content, re.IGNORECASE)
        status = status_match.group(1) if status_match else None
        content_no_status = (
            content[: status_match.start()].strip() if status_match else content
        )

        # Step 2: Cari "Normal" pertama sebagai Result
        # "Normal" bisa muncul di Standard juga (misal "Normal Condition:")
        # tapi untuk Physical Check, Result selalu "Normal" yang pertama
        result_match = re.search(r"\bNormal\b", content_no_status, re.IGNORECASE)

        if result_match:
            description = content_no_status[: result_match.start()].strip()
            result = "Normal"
            # Standard = sisa setelah "Normal", strip leading colon/space
            standard = content_no_status[result_match.end() :].strip().lstrip(" :")
        else:
            # Fallback: cari angka sebagai result
            num_match = re.search(r"\b(\d+(?:[,.]\d+)?)\b", content_no_status)
            if num_match:
                description = content_no_status[: num_match.start()].strip()
                result = num_match.group(1)
                standard = content_no_status[num_match.end() :].strip()
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
    # PERFORMANCE MEASUREMENT — 1 item (a)
    # Result berupa angka (misal "90" untuk inclination)
    # ================================================================
    def extract_performance_measurement(self) -> List[Dict]:
        """Extract Performance Measurement items"""
        print("[PM POLE TOWER] Parsing Performance Measurement...")

        section_text = self._get_section(
            r"2\.\s*Performance\s+Measurement", r"Notes|$"
        )
        if not section_text:
            print("[PM POLE TOWER]   ⚠️ Performance section tidak ditemukan")
            return []

        # Gunakan semua letter a-z sebagai valid markers
        items_raw = self._split_items_by_marker(
            section_text, "abcdefghijklmnopqrstuvwxyz"
        )

        items = []
        for letter in sorted(items_raw.keys()):
            item = self._parse_performance_item(letter, items_raw[letter])
            if item:
                items.append(item)
                print(
                    f"[PM POLE TOWER]   ✓ 2.{letter}: "
                    f"result={item['result']}, status={item['status']}"
                )

        return items

    def _parse_performance_item(self, letter: str, raw_lines: List[str]) -> Dict:
        """
        Parse satu item Performance Measurement.
        Result berupa ANGKA (bukan "Normal").
        """
        content = " ".join(" ".join(raw_lines).split())

        # Extract Status
        status_match = re.search(r"\s+(OK|NOK)\s*$", content, re.IGNORECASE)
        status = status_match.group(1) if status_match else None
        content_no_status = (
            content[: status_match.start()].strip() if status_match else content
        )

        # Extract Result = angka pertama
        result_match = re.search(r"\b(\d+(?:[,.]\d+)?)\b", content_no_status)
        if result_match:
            description = content_no_status[: result_match.start()].strip()
            result = result_match.group(1)
            standard = content_no_status[result_match.end() :].strip()
        else:
            description = content_no_status
            result = None
            standard = None

        return {
            "no": f"2.{letter}",
            "description": description,
            "result": result,
            "standard": standard,
            "status": status,
        }

    # ================================================================
    # PELAKSANA — Handle dua format dari PDF extraction:
    #
    # VERTICAL (tiap kolom di baris terpisah — format aktual):     HORIZONTAL (satu baris):
    #   1                                                            1 Azki IMS
    #   Azki
    #   IMS
    #   2
    #   3
    #
    # PDF reader kadang extract tabel kolom-per-kolom sehingga
    # "No", "Nama", "Mitra" masing-masing jadi baris tersendiri.
    # Solusi: sequential scan — kalau ketemu angka, ambil lines
    # berikutnya sebagai nama + mitra sampai angka berikutnya.
    # ================================================================
    def extract_pelaksana_pole_tower(self) -> dict:
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

    # ================================================================
    # HELPER METHODS
    # ================================================================
    def _get_section(self, start_pattern: str, end_pattern: str) -> str:
        """
        Extract text section antara start dan end patterns.
        Gunakan DOTALL agar '.' match newlines.
        """
        pattern = rf"{start_pattern}\s*(.*?)(?={end_pattern})"
        match = re.search(pattern, self.all_text, re.IGNORECASE | re.DOTALL)
        return match.group(1) if match else ""

    def _split_items_by_marker(
        self, section_text: str, valid_letters: str
    ) -> Dict[str, List[str]]:
        """
        Split section text menjadi dict {letter: [lines]} berdasarkan
        item markers "x." di START OF LINE.

        Ini menghindari false positive dari huruf di tengah kata
        (misal "structurally" yang mengandung huruf 'g').

        Args:
            section_text: Text section yang akan di-split
            valid_letters: String berisi huruf yang valid sebagai marker
                          (misal "abcdefgh")

        Returns:
            Dict mapping letter -> list of lines (termasuk sisa dari marker line)
        """
        lines = section_text.strip().split("\n")
        items_dict = {}
        current_letter = None

        for line in lines:
            # Check marker: huruf valid di START OF LINE diikuti "."
            marker_match = re.match(
                rf"^([{valid_letters}])\.\s*(.*)", line, re.IGNORECASE
            )
            if marker_match:
                current_letter = marker_match.group(1).lower()
                items_dict[current_letter] = [marker_match.group(2)]
            elif current_letter:
                # Append ke item current (continuation lines)
                items_dict[current_letter].append(line)

        return items_dict