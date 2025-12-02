"""
Checklist Wireless Parser V11 - CABUT/PENGGANTI EXTRACTION FIXED
Taruh file ini di: parsers/checklist_wireless_parser.py

Critical Fixes:
1. Fixed CABUT/PENGGANTI extraction -gunakan spatial detection dari OCR
2. Extract nama barang per-column (tidak cross-column)
3. Handle multi-line nama barang dengan OCR proximity detection
4. Fallback ke text-based splitting jika OCR data tidak tersedia
"""
import re
from .base_parser import BaseParser


def parse_checklist_wireline(all_text: str, page_texts: list[str], ttd_results: dict = None, doc_results: dict = None, ocr_data: list = None) -> dict:
    """Fungsi wrapper untuk kompatibilitas dengan kode lama"""
    parser = ChecklistWirelineParser(all_text, page_texts, ttd_results, doc_results, ocr_data)
    return parser.parse()


class ChecklistWirelineParser(BaseParser):
    """Parser untuk Form Checklist Maintenance Remote Wireless"""
    
    FIELD_LABELS = [
        "Nama Pelanggan", "Contact Person", "Nomor Jaringan", "Nomor Telepon",
        "Alamat", "Kota", "Propinsi", "Provinsi", "No. SPK", "No SPK", "Tanggal",
        "Jam Perintah", "Jam Persiapan", "Jam Berangkat", "Jam Tiba Di Lokasi",
        "Jam Mulai Kerja", "Jam Selesai Kerja", "Jam Pulang", "Jam Tiba Di Kantor"
    ]
    
    def __init__(self, all_text: str, page_texts: list[str], ttd_results: dict = None, doc_results: dict = None, ocr_data: list = None):
        super().__init__(all_text, page_texts)
        self.ttd_results = ttd_results or {}
        self.doc_results = doc_results or {}
        self.ocr_data = ocr_data or []
        
        self.cleaned_text = self._clean_text(all_text)
        
        self.spatial_map = {}
        if self.ocr_data:
            self._build_spatial_map()
    
    def _clean_text(self, text: str) -> str:
        """Clean text dari OCR artifacts"""
        text = re.sub(r'\b(\d{2})-Jum-(\d{4})', r'\1-Jun-\2', text)
        text = re.sub(r' +', ' ', text)
        text = text.replace('：', ':')
        return text
    
    def _build_spatial_map(self):
        """Build spatial map dari OCR data"""
        for idx, item in enumerate(self.ocr_data):
            text_key = self._normalize_text(item['text'])
            self.spatial_map[text_key] = {
                'text': item['text'],
                'bbox': item.get('bbox', []),
                'position': item.get('position', (0, 0)),
                'index': idx,
                'score': item.get('score', 1.0)
            }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text untuk matching"""
        return text.lower().replace(' ', '').replace(':', '').replace('：', '')
    
    def _find_field_spatial(self, field_pattern: str) -> dict:
        """Cari field label menggunakan spatial map"""
        if not self.spatial_map:
            return None
        
        for text_key, data in self.spatial_map.items():
            if re.search(field_pattern, data['text'], re.IGNORECASE):
                return data
        
        return None
    
    def _get_values_after_field(self, field_index: int, max_items: int = 5) -> list:
        """Ambil multiple values setelah field"""
        if field_index < 0 or field_index >= len(self.ocr_data):
            return []
        
        field_item = self.ocr_data[field_index]
        field_y = field_item['position'][0]
        
        values = []
        
        for i in range(field_index + 1, min(field_index + max_items + 1, len(self.ocr_data))):
            item = self.ocr_data[i]
            item_text = item['text'].strip()
            
            if item_text in [':', '：', '.', ',', '-']:
                continue
            
            if self._is_field_label(item_text):
                break
            
            item_y = item['position'][0]
            y_distance = abs(item_y - field_y)
            
            if y_distance < 40:
                values.append(item_text)
        
        return values
    
    def _is_field_label(self, text: str) -> bool:
        """Check apakah text adalah field label"""
        text_normalized = text.strip().lower()
        for label in self.FIELD_LABELS:
            if label.lower() in text_normalized:
                return True
        return False
    
    def _clean_value(self, value: str) -> str:
        """Clean extracted value"""
        if not value:
            return ""
        
        value = re.sub(r'^[:\：\s]+', '', value)
        value = re.sub(r'^i:', '', value)
        value = value.strip(' :：.,')
        
        return value
    
    def _extract_field_simple(self, field_pattern: str) -> str:
        """Simple extraction untuk non-datetime fields"""
        
        if not self.ocr_data:
            return self._extract_field_regex(field_pattern)
        
        field_info = self._find_field_spatial(field_pattern)
        
        if not field_info:
            return self._extract_field_regex(field_pattern)
        
        field_index = field_info['index']
        values = self._get_values_after_field(field_index, max_items=3)
        
        if not values:
            return self._extract_field_regex(field_pattern)
        
        value = values[0] if values else ""
        cleaned = self._clean_value(value)
        
        return cleaned
    
    def _extract_field_regex(self, field_pattern: str) -> str:
        """Fallback regex extraction"""
        pattern = rf"{field_pattern}\s*[：:]?\s*([^\n]+?)(?=\n|$)"
        match = re.search(pattern, self.cleaned_text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            value = self._clean_value(value)
            
            for label in self.FIELD_LABELS:
                if label in value:
                    value = value.split(label)[0].strip()
            
            if value and not self._is_field_label(value):
                return value
        
        return ""
    
    def parse(self) -> dict:
        """Entry point untuk parsing"""
        data = self._init_data_structure_checklist_wireline()
        
        # Parse DATA REMOTE
        self._parse_data_remote(data["data_remote"])
        self._parse_global_checklist(data["global_checklist"])
        self._parse_data_perangkat(data["data_perangkat"])
        self._parse_indoor_area_checklist(data["indoor_area_checklist"])

        # TAMBAHKAN INI - Parse LINE CHECKLIST
        line_checklist_text = self._extract_line_checklist_section()
        if line_checklist_text:
            self._parse_line_checklist_all(data["line_checklist"], line_checklist_text)
        
        return data
    
    def _parse_data_remote(self, data_remote: dict):
        """Parse bagian data remote"""
        
        data_remote["nama_pelanggan"] = self._extract_field_simple(r"Nama\s*Pelanggan")
        data_remote["contact_person"] = self._extract_field_simple(r"Contact\s*Person")
        data_remote["nomor_jaringan"] = self._extract_field_simple(r"Nomor\s*Jaringan")
        data_remote["nomor_telepon"] = self._extract_field_simple(r"Nomor\s*Telepon")
        data_remote["alamat"] = self._extract_field_simple(r"Alamat")
        data_remote["kota"] = self._extract_field_simple(r"Kota")
        
        # Propinsi with validation
        propinsi = self._extract_field_simple(r"Prop(?:i|o)nsi")
        if "SPK" in propinsi or "spk" in propinsi.lower():
            propinsi = ""
        data_remote["propinsi"] = propinsi
        
        data_remote["no_spk"] = self._extract_field_simple(r"No\.?\s*SPK")
        data_remote["tanggal"] = self._extract_tanggal()
        
        self._parse_pelaksanaan(data_remote["pelaksanaan"])
    
    def _extract_tanggal(self) -> str:
        """Extract tanggal field (bukan jam pelaksanaan)"""
        pattern = r"Tanggal\s*[：:]?\s*(\d{2}-[A-Za-z]{3}-\d{4}(?:\s+\d{2}:\d{2})?)"
        match = re.search(pattern, self.cleaned_text, re.IGNORECASE)
        
        if match:
            return match.group(1)
        
        return ""
    
    def _parse_pelaksanaan(self, pelaksanaan: dict):
        """Parse pelaksanaan dengan table-aware extraction"""
        
        jam_section = self._extract_jam_section()
        
        if not jam_section:
            return
        
        # Extract all dates and times
        dates = re.findall(r'\d{2}-[A-Za-z]{3}-\d{4}', jam_section)
        times = re.findall(r'\d{2}:\d{2}', jam_section)
        
        # Standard mapping for 6-datetime format
        standard_mapping = {
            "jam_perintah": 0,
            "jam_persiapan": 1,
            "jam_berangkat": 2,
            "jam_tiba_di_lokasi": 3,
            "jam_mulai_kerja": 4,
            "jam_selesai_kerja": 5,
            "jam_pulang": None,
            "jam_tiba_di_kantor": None
        }
        
        # Apply mapping
        for field_key, idx in standard_mapping.items():
            if idx is None:
                field_value = self._check_field_in_text(field_key)
                pelaksanaan[field_key] = field_value
            elif idx < len(dates) and idx < len(times):
                pelaksanaan[field_key] = f"{dates[idx]} {times[idx]}"
            elif idx < len(dates):
                pelaksanaan[field_key] = dates[idx]
            else:
                pelaksanaan[field_key] = ""
    
    def _extract_jam_section(self) -> str:
        """Extract jam pelaksanaan section"""
        match = re.search(
            r'Jam\s*Perintah.*?(?=GLOBAL|Latitude|DATA\s*LOKASI|$)', 
            self.cleaned_text, 
            re.IGNORECASE | re.DOTALL
        )
        
        return match.group() if match else ""
    
    def _check_field_in_text(self, field_key: str) -> str:
        """Check if a supposedly empty field actually has value in text"""
        
        pattern_map = {
            "jam_pulang": r"Jam\s*Pulang\s*[：:]?\s*(\d{2}-[A-Za-z]{3}-\d{4}(?:\s+\d{2}:\d{2})?)",
            "jam_tiba_di_kantor": r"Jam\s*Tiba\s*(?:Di\s*)?Kantor\s*[：:]?\s*(\d{2}-[A-Za-z]{3}-\d{4}(?:\s+\d{2}:\d{2})?)"
        }
        
        pattern = pattern_map.get(field_key)
        if not pattern:
            return ""
        
        match = re.search(pattern, self.cleaned_text, re.IGNORECASE)
        return match.group(1) if match else ""
    
    def validate(self) -> bool:
        """Validasi dokumen wireless"""
        return "WIRELESS" in self.all_text.upper() or "WIRELINE" in self.all_text.upper()
    
    # ==================== GLOBAL CHECKLIST PARSER ====================
    
    def _parse_global_checklist(self, global_checklist: dict):
        """Parse bagian GLOBAL CHECKLIST"""
        
        global_section = self._extract_global_section()
        
        if not global_section:
            return
        
        self._parse_data_lokasi(global_checklist["data_lokasi"], global_section)
        self._parse_electrical(global_checklist["electrical"], global_section)
        self._parse_environment(global_checklist["environment"], global_section)
    
    def _extract_global_section(self) -> str:
        """Extract GLOBAL CHECKLIST section"""
        match = re.search(
            r'GLOBAL\s*CHECKLIST.*?(?=\n\s*(?:INDOOR|OUTDOOR)\s*AREA|KESIMPULAN|CHECKLIST\s*PERANGKAT|$)',
            self.cleaned_text,
            re.IGNORECASE | re.DOTALL
        )
        
        return match.group() if match else ""
    
    def _parse_data_lokasi(self, data_lokasi: dict, section_text: str):
        """Parse DATA LOKASI dari GLOBAL CHECKLIST"""
        
        # Extract Latitude
        lat_pattern = r"Latitude\s*[：:]?\s*([\d°'\"\.]+?)(?=\s+Longitude|\s+\d+\.|\s+1\.)"
        lat_match = re.search(lat_pattern, section_text, re.IGNORECASE)
        data_lokasi["latitude"] = lat_match.group(1).strip() if lat_match and lat_match.group(1).strip() != "." else ""
        
        # Extract Longitude
        long_pattern = r"Longitude\s*[：:]?\s*([^\s]+)"
        long_match = re.search(long_pattern, section_text, re.IGNORECASE)
        if long_match:
            long_value = long_match.group(1).strip()
            long_value = re.split(r'(?=Posisi|PLN|UPS|P-N)', long_value, flags=re.IGNORECASE)[0]
            data_lokasi["longitude"] = long_value if long_value != "." else ""
        else:
            data_lokasi["longitude"] = ""
        
        # Extract Posisi Modem
        posisi_pattern = r"Posisi\s*Modem\s*di\s*Lt\.\s*[：:]?\s*([a-zA-Z\s]+?)(?=\s+Ruang|\s+P-N|\s+\d{3})"
        posisi_match = re.search(posisi_pattern, section_text, re.IGNORECASE)
        data_lokasi["posisi_modem_di_lt"] = posisi_match.group(1).strip() if posisi_match else ""
        
        # Extract Ruang
        ruang_pattern = r"Ruang\s*[：:]?\s*([a-zA-Z\s]+?)(?=\s+P-G|\s+\d{3}\.|\s+\d+\s*VAC)"
        ruang_match = re.search(ruang_pattern, section_text, re.IGNORECASE)
        data_lokasi["ruang"] = ruang_match.group(1).strip() if ruang_match else ""
    
    def _parse_electrical(self, electrical: dict, section_text: str):
        """Parse ELECTRICAL section dari GLOBAL CHECKLIST"""
        
        # 1. Output Tegangan yang mengacu ke modem
        tegangan_section = self._extract_tegangan_table(section_text)
        
        if tegangan_section:
            # Extract each row and assign to nested structure
            p_n_data = self._extract_tegangan_row(tegangan_section, "P-N")
            p_g_data = self._extract_tegangan_row(tegangan_section, "P-G")
            n_g_data = self._extract_tegangan_row(tegangan_section, "N-G")
            
            # Assign to existing nested structure
            electrical["output_tegangan_mengacu_modem"]["p_n"] = p_n_data
            electrical["output_tegangan_mengacu_modem"]["p_g"] = p_g_data
            electrical["output_tegangan_mengacu_modem"]["n_g"] = n_g_data
        
        # 2. Grounding Bar terkoneksi ke
        grounding_pattern = r"Grounding\s*Bar\s*terkoneksi\s*ke\s*[：:]?\s*([A-Za-z\s]+?)(?=\s*NDOORAREA|\s*INDOOR|\s*OUTDOOR|\s*$)"
        grounding_match = re.search(grounding_pattern, section_text, re.IGNORECASE)
        
        if grounding_match:
            value = grounding_match.group(1).strip()
            electrical["grounding_bar_terkoneksi_ke"] = value if not re.search(r'INDOOR|OUTDOOR|AREA|NDOOR', value, re.IGNORECASE) else ""
        else:
            electrical["grounding_bar_terkoneksi_ke"] = ""
    
    def _extract_tegangan_table(self, section_text: str) -> str:
        """Extract tegangan table section"""
        
        pattern1 = r'Output\s*Tegangan.*?(?=Grounding\s*Bar|ENVIRONMENT|INDOOR|OUTDOOR|$)'
        match = re.search(pattern1, section_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            return match.group()
        
        pattern2 = r'1\.\s*Output\s*Tegangan.*?(?=\n\s*2\.|$)'
        match = re.search(pattern2, section_text, re.IGNORECASE | re.DOTALL)
        
        if match:
            return match.group()
        
        return ""
    
    def _extract_tegangan_row(self, table_text: str, row_label: str) -> dict:
        """Extract satu row dari tegangan table (PLN, UPS, IT)"""
        
        row_data = {"pln": "", "ups": "", "it": ""}
        
        # Pattern 1: Format dengan angka atau titik
        pattern1 = rf"{row_label}\s+([\d\.]+)\s*VAC\s+([\d\.]+)\s*VAC\s+([\d\.]+)\s*VAC"
        match = re.search(pattern1, table_text, re.IGNORECASE)
        
        if match:
            pln_val = match.group(1).strip()
            ups_val = match.group(2).strip()
            it_val = match.group(3).strip()
            
            row_data["pln"] = f"{pln_val} VAC" if pln_val != "." else ""
            row_data["ups"] = f"{ups_val} VAC" if ups_val != "." else ""
            row_data["it"] = f"{it_val} VAC" if it_val != "." else ""
            return row_data
        
        # Pattern 2: Format dengan explicit ". VAC"
        pattern2 = rf"{row_label}\s+([\d\.]+\s+VAC)\s+(\.\s+VAC)\s+(\.\s+VAC)"
        match = re.search(pattern2, table_text, re.IGNORECASE)
        
        if match:
            pln = match.group(1).strip()
            ups = match.group(2).strip()
            it = match.group(3).strip()
            
            row_data["pln"] = pln if not pln.startswith('.') else ""
            row_data["ups"] = "" if ups.startswith('. ') else ups
            row_data["it"] = "" if it.startswith('. ') else it
            return row_data
        
        # Pattern 3: Flexible fallback
        row_pattern = rf"{row_label}\s+(.+?)(?=\n|P-[NG]|N-G|Grounding|$)"
        row_match = re.search(row_pattern, table_text, re.IGNORECASE)
        
        if row_match:
            row_content = row_match.group(1)
            vac_values = re.findall(r'([\d\.]+)\s*VAC', row_content)
            
            if vac_values:
                if len(vac_values) >= 1:
                    row_data["pln"] = f"{vac_values[0]} VAC" if vac_values[0] != "." else ""
                if len(vac_values) >= 2:
                    row_data["ups"] = f"{vac_values[1]} VAC" if vac_values[1] != "." else ""
                if len(vac_values) >= 3:
                    row_data["it"] = f"{vac_values[2]} VAC" if vac_values[2] != "." else ""
        
        return row_data
    
    def _parse_environment(self, environment: dict, section_text: str):
        """Parse ENVIRONMENT section dari GLOBAL CHECKLIST"""
        
        # 1. AC Pendingin Ruangan
        ac_pattern = r"(?:\d+\.)?\s*AC\s*Pendingin\s*Ruangan\s*[：:]?\s*([A-Za-z]+)"
        ac_match = re.search(ac_pattern, section_text, re.IGNORECASE)
        environment["ac_pendingin_ruangan"] = ac_match.group(1).strip() if ac_match else ""
        
        # 2. Suhu Ruangan Perangkat
        suhu_pattern = r"Suhu\s*Ruangan\s*Perangkat\s*[：:]?\s*([\d\.]+)\s*[°℃C}]?"
        suhu_match = re.search(suhu_pattern, section_text, re.IGNORECASE)
        environment["suhu_ruangan_perangkat"] = f"{suhu_match.group(1).strip()}°" if suhu_match else ""

    # ==================== INDOOR AREA CHECKLIST PARSER ====================

    def _parse_indoor_area_checklist(self, indoor_area: dict):
        """Parse bagian INDOOR AREA CHECKLIST"""
        print("\n" + "="*60)
        print("Parsing INDOOR AREA CHECKLIST")
        print("="*60)
        
        indoor_section = self._extract_indoor_section()
        
        if not indoor_section:
            print("✗ Section INDOOR AREA CHECKLIST tidak ditemukan")
            print("="*60 + "\n")
            return
        
        # Debug: Print section yang ditemukan
        print(f"\n[DEBUG] INDOOR SECTION (first 500 chars):")
        print(repr(indoor_section[:500]))
        print("="*60)
        
        # Parse each subsection
        self._parse_indikator_modem(indoor_area["indikator_modem"], indoor_section)
        self._parse_merek_section(indoor_area["merek"], indoor_section)
        self._parse_modem_fo(indoor_area["modem_fo"], indoor_section)
        self._parse_lc_signal_kop(indoor_area["lc_signal_quality_checked_by_kop"], indoor_section)
        self._parse_lc_signal_avo(indoor_area["lc_signal_quality_checked_by_avo_meter"], indoor_section)
        
        print(f"✓ INDOOR AREA CHECKLIST parsed")
        print("="*60 + "\n")

    def _extract_indoor_section(self) -> str:
        """Extract INDOOR AREA CHECKLIST section - HANDLE KATA NEMPEL"""
        
        print("\n[DEBUG] Searching for INDOOR AREA CHECKLIST section...")
        print(f"[DEBUG] Text length: {len(self.cleaned_text)} chars")
        
        # Check various keyword combinations
        keywords_to_check = [
            "INDOOR AREA CHECKLIST",
            "INDOORAREACHECKLIST",  # Nempel
            "NDOOR AREA CHECKLIST",  # OCR error: I → N
            "NDOORAREACHECKLIST",    # Nempel + OCR error
        ]
        
        for keyword in keywords_to_check:
            if keyword.replace(" ", "") in self.cleaned_text.replace(" ", "").upper():
                print(f"[DEBUG] ✓ Found keyword variation: '{keyword}'")
                break
        else:
            print(f"[DEBUG] ✗ No INDOOR AREA CHECKLIST variation found")
        
        patterns = [
            # Standard patterns
            r'INDOOR\s+AREA\s+CHECKLIST.*?(?=OUTDOOR\s+AREA|LINE\s*CHECKLIST|KESIMPULAN|D\.\s*VERIFIKASI|$)',
            
            # Handle kata nempel (no spaces)
            r'INDOORAREACHECKLIST.*?(?=OUTDOOR|LINE\s*CHECKLIST|KESIMPULAN|$)',
            
            # OCR error: INDOOR → NDOOR
            r'NDOOR\s+AREA\s+CHECKLIST.*?(?=OUTDOOR|LINE\s*CHECKLIST|KESIMPULAN|$)',
            
            # OCR error + kata nempel
            r'NDOORAREACHECKLIST.*?(?=OUTDOOR|LINE\s*CHECKLIST|KESIMPULAN|$)',
            
            # Flexible spacing (allow newlines)
            r'(?:I|N)ND[OO0]R\s*AREA\s*CHECKLIST.*?(?=OUTDOOR|LINE\s*CHECKLIST|KESIMPULAN|$)',
            
            # Very flexible (last resort)
            r'(?:I|N)ND[OO0]R.*?CHECKLIST.*?(?=OUTDOOR|LINE|KESIMPULAN|VERIFIKASI|$)',
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, self.cleaned_text, re.IGNORECASE | re.DOTALL)
            if match:
                section = match.group()
                
                # Validate: ensure it contains expected keywords
                expected_keywords = ['POWER', 'MODEM', 'STANDARD', 'QUALITY', 'PARAMETER']
                keyword_count = sum(1 for kw in expected_keywords if kw in section.upper())
                
                if keyword_count >= 2:
                    print(f"[DEBUG] ✓ Pattern {i+1} matched! Contains {keyword_count}/5 expected keywords")
                    print(f"[DEBUG] Section length: {len(section)} chars")
                    print(f"[DEBUG] First 200 chars: {repr(section[:200])}")
                    return section
                else:
                    print(f"[DEBUG] ⚠ Pattern {i+1} matched but only {keyword_count}/5 keywords found")
        
        print(f"[DEBUG] ✗ No valid pattern matched")
        return ""

    def _parse_indikator_modem(self, indikator_modem: dict, section_text: str):
        """Parse Indikator Modem subsection - COMPLETELY FIXED"""
        print("\n  [INDIKATOR MODEM]")
        
        # POWER
        power_values = self._extract_quality_row_with_ocr(section_text, r"POWER")
        if not power_values:
            power_values = self._extract_quality_row(section_text, r"POWER")
        indikator_modem["power"].update(power_values)
        print(f"    ✓ POWER: {power_values}")
        
        # 109/DCD/LINK-WAN - CRITICAL FIX: Look in the cleaned text directly
        dcd_values = self._extract_quality_row_with_ocr(section_text, r"109[\/]?DCD[\/]?LINK[-]?WAN")
        
        # If OCR fails, try direct text extraction from section_text
        if not dcd_values or not dcd_values.get("standard"):
            # Strategy 1: Look for "109/DCD/LINK-WAN" followed by "ON" or "OFF" on next line
            pattern1 = r'109[\/]?DCD[\/]?LINK[-]?WAN\s*\n\s*(ON|OFF)'
            match = re.search(pattern1, section_text, re.IGNORECASE)
            
            if match:
                dcd_values = {
                    "standard": match.group(1).upper(),
                    "nms_engineer": "",
                    "on_site_teknisi": "",
                    "perbaikan": "",
                    "hasil_akhir": ""
                }
                print(f"    [MANUAL EXTRACT] Found 109/DCD value (newline): '{match.group(1)}'")
            else:
                # Strategy 2: Look for "Modem ON 109/DCD" pattern (for OCR text)
                pattern2 = r'(?:Modem\s+)(\w+)\s+109[\/]?DCD[\/]?LINK[-]?WAN'
                match = re.search(pattern2, section_text, re.IGNORECASE)
                
                if match:
                    value = match.group(1).strip()
                    if value.upper() in ['ON', 'OFF']:
                        dcd_values = {
                            "standard": value.upper(),
                            "nms_engineer": "",
                            "on_site_teknisi": "",
                            "perbaikan": "",
                            "hasil_akhir": ""
                        }
                        print(f"    [MANUAL EXTRACT] Found 109/DCD value (inline): '{value}'")
        
        if not dcd_values:
            dcd_values = {
                "standard": "",
                "nms_engineer": "",
                "on_site_teknisi": "",
                "perbaikan": "",
                "hasil_akhir": ""
            }
        
        indikator_modem["109_dcd_link_wan"].update(dcd_values)
        print(f"    ✓ 109/DCD/LINK-WAN: {dcd_values}")

    def _parse_merek_section(self, merek: dict, section_text: str):
        """Parse Merek subsection - FINAL CORRECT VERSION"""
        print("\n  [MEREK]")
        
        # TD/TXD/103
        td_values = self._extract_quality_row_with_ocr(section_text, r"TD[\/]?TXD[\/]?103")
        if not td_values:
            td_values = self._extract_quality_row(section_text, r"TD[\/]?TXD[\/]?103")
        merek["td_txd_103"].update(td_values)
        print(f"    ✓ TD/TXD/103: {td_values}")
        
        # RD/RXD/104
        rd_values = self._extract_quality_row_with_ocr(section_text, r"RD[\/]?RXD[\/]?104")
        if not rd_values:
            rd_values = self._extract_quality_row(section_text, r"RD[\/]?RXD[\/]?104")
        merek["rd_rxd_104"].update(rd_values)
        print(f"    ✓ RD/RXD/104: {rd_values}")
        
        # RTS/105
        rts_values = self._extract_quality_row_with_ocr(section_text, r"RTS[\/]?105")
        if not rts_values:
            rts_values = self._extract_quality_row(section_text, r"RTS[\/]?105")
        merek["rts_105"].update(rts_values)
        print(f"    ✓ RTS/105: {rts_values}")
        
        # CTS/106
        cts_values = self._extract_quality_row_with_ocr(section_text, r"CTS[\/]?106")
        if not cts_values:
            cts_values = self._extract_quality_row(section_text, r"CTS[\/]?106")
        merek["cts_106"].update(cts_values)
        print(f"    ✓ CTS/106: {cts_values}")
        
        # Alarm LED
        alarm_values = self._extract_quality_row_with_ocr(section_text, r"Alarm\s+LED")
        if not alarm_values:
            alarm_values = self._extract_quality_row(section_text, r"Alarm\s+LED")
        merek["alarm_led"].update(alarm_values)
        print(f"    ✓ Alarm LED: {alarm_values}")
        
        # Front Panel Display - All STU Modem - CRITICAL FIX: Multi-line value
        stu_values = self._extract_quality_row_with_ocr(section_text, r"All\s+STU\s+Modem")
        
        # ALWAYS check for multi-line value in text
        # From debug text: "All STU Modem Quality A No Counter CRC Error Tainet Scorpio"
        manual_match = re.search(
            r'All\s+STU\s+Modem\s+(Quality\s+A)\s*(No\s+Counter\s+CRC\s+Error)?',
            section_text,
            re.IGNORECASE
        )
        
        if manual_match:
            line1 = manual_match.group(1).strip()
            line2 = manual_match.group(2).strip() if manual_match.group(2) else ""
            
            # If line2 exists, combine with SPACE (not newline)
            if line2:
                combined = f"{line1} {line2}"
                stu_values = {
                    "standard": combined,
                    "nms_engineer": "",
                    "on_site_teknisi": "",
                    "perbaikan": "",
                    "hasil_akhir": ""
                }
                print(f"    [MANUAL EXTRACT] All STU Modem multi-line: '{combined}'")
            elif not stu_values or not stu_values.get("standard"):
                stu_values = {
                    "standard": line1,
                    "nms_engineer": "",
                    "on_site_teknisi": "",
                    "perbaikan": "",
                    "hasil_akhir": ""
                }
        
        if not stu_values:
            stu_values = {
                "standard": "",
                "nms_engineer": "",
                "on_site_teknisi": "",
                "perbaikan": "",
                "hasil_akhir": ""
            }
        
        merek["front_panel_display"]["all_stu_modem"].update(stu_values)
        print(f"    ✓ All STU Modem: {stu_values}")
        
        # Front Panel Display - Tainet Scorpio - CRITICAL FIX: Get "Connected KBps"
        tainet_values = self._extract_quality_row_with_ocr(section_text, r"Tainet\s+Scorpio")
        
        # PROBLEM: Need to handle both OCR text and normal text formats
        if not tainet_values or not tainet_values.get("on_site_teknisi") or "KBps" not in tainet_values.get("on_site_teknisi", ""):
            # Pattern 1: For OCR text (inline format)
            # "Tainet Scorpio Connected xxx KBps Connected KBps Modem FO"
            manual_match = re.search(
                r'Tainet\s+Scorpio\s+(Connected\s+xxx\s+KBps)\s+(Connected\s+KBps)',
                section_text,
                re.IGNORECASE
            )
            
            if manual_match:
                tainet_values = {
                    "standard": manual_match.group(1).strip(),
                    "nms_engineer": "",
                    "on_site_teknisi": manual_match.group(2).strip(),
                    "perbaikan": "",
                    "hasil_akhir": ""
                }
                print(f"    [MANUAL EXTRACT OCR] Tainet Scorpio: standard='{manual_match.group(1)}', on_site='{manual_match.group(2)}'")
            else:
                # Pattern 2: For normal text (newline format)
                # "Tainet Scorpio\nConnected xxx KBps\n \nConnected \nKBps"
                manual_match = re.search(
                    r'Tainet\s+Scorpio\s*\n\s*(Connected\s+xxx\s+KBps)\s*\n[^\n]*\n\s*(Connected)\s*\n\s*(KBps)',
                    section_text,
                    re.IGNORECASE
                )
                
                if manual_match:
                    on_site_value = f"{manual_match.group(2).strip()} {manual_match.group(3).strip()}"
                    # Clean any remaining whitespace/newlines
                    on_site_value = re.sub(r'\s+', ' ', on_site_value).strip()
                    tainet_values = {
                        "standard": manual_match.group(1).strip(),
                        "nms_engineer": "",
                        "on_site_teknisi": on_site_value,
                        "perbaikan": "",
                        "hasil_akhir": ""
                    }
                    print(f"    [MANUAL EXTRACT TEXT] Tainet Scorpio: standard='{manual_match.group(1)}', on_site='{on_site_value}'")
        
        # CRITICAL: Clean any newlines in on_site_teknisi regardless of source
        if tainet_values and tainet_values.get("on_site_teknisi"):
            tainet_values["on_site_teknisi"] = re.sub(r'\s+', ' ', tainet_values["on_site_teknisi"]).strip()
        
        if not tainet_values:
            tainet_values = {
                "standard": "",
                "nms_engineer": "",
                "on_site_teknisi": "",
                "perbaikan": "",
                "hasil_akhir": ""
            }
        
        merek["front_panel_display"]["tainet_scorpio"].update(tainet_values)
        print(f"    ✓ Tainet Scorpio: {tainet_values}")

    def _parse_modem_fo(self, modem_fo: dict, section_text: str):
        """Parse Modem FO subsection"""
        print("\n  [MODEM FO]")
        
        optical_values = self._extract_quality_row_with_ocr(section_text, r"Optical\s+LED\s+Alarm")
        if not optical_values:
            optical_values = self._extract_quality_row(section_text, r"Optical\s+LED\s+Alarm")
        modem_fo["optical_led_alarm"].update(optical_values)
        print(f"    ✓ Optical LED Alarm: {optical_values}")

    def _parse_lc_signal_kop(self, lc_signal_kop: dict, section_text: str):
        """Parse LC Signal Quality (Checked by Kop)"""
        print("\n  [LC SIGNAL - KOP]")
        
        # STU 160
        stu160_values = self._extract_quality_row_with_ocr(section_text, r"STU\s+160")
        if not stu160_values:
            stu160_values = self._extract_quality_row(section_text, r"STU\s+160")
        lc_signal_kop["stu_160"].update(stu160_values)
        print(f"    ✓ STU 160: {stu160_values}")
        
        # STU 1088/2304
        stu1088_values = self._extract_quality_row_with_ocr(section_text, r"STU\s+1088[\/]?2304")
        if not stu1088_values:
            stu1088_values = self._extract_quality_row(section_text, r"STU\s+1088[\/]?2304")
        lc_signal_kop["stu_1088_2304"].update(stu1088_values)
        print(f"    ✓ STU 1088/2304: {stu1088_values}")
        
        # ADSL Modem
        adsl_values = self._extract_quality_row_with_ocr(section_text, r"ADSL\s+Modem")
        if not adsl_values:
            adsl_values = self._extract_quality_row(section_text, r"ADSL\s+Modem")
        lc_signal_kop["adsl_modem"].update(adsl_values)
        print(f"    ✓ ADSL Modem: {adsl_values}")

    def _parse_lc_signal_avo(self, lc_signal_avo: dict, section_text: str):
        """Parse LC Signal Quality (Checked by AVO Meter) - FINAL CORRECT VERSION"""
        print("\n  [LC SIGNAL - AVO METER]")
        
        # Extract only the AVO Meter section
        avo_section_match = re.search(
            r'(?:Checked\s+by|by)\s+AVO\s+Meter\)(.*?)(?=OUTDOOR|LINE|KESIMPULAN|$)',
            section_text,
            re.IGNORECASE | re.DOTALL
        )
        
        if avo_section_match:
            avo_section = avo_section_match.group(1)
            print(f"      [AVO SECTION] Isolated AVO section ({len(avo_section)} chars)")
        else:
            avo_section = section_text
            print(f"      [AVO SECTION] Using full section")
        
        # STU 1088/2304 (SEPARATE ROW)
        stu_values = None
        
        # Manual extraction for "400-700 Ω (Tlkm Area)"
        manual_match = re.search(
            r'(400[-–]\s*700\s*[ΩΩ]\s*\([^)]*(?:Tlkm|Tlkma|Area)[^)]*\))',
            avo_section,
            re.IGNORECASE
        )
        
        if manual_match:
            stu_values = {
                "standard": manual_match.group(1).strip(),
                "nms_engineer": "Ω",
                "on_site_teknisi": "",
                "perbaikan": "",
                "hasil_akhir": ""
            }
        
        if not stu_values:
            stu_values = {
                "standard": "",
                "nms_engineer": "",
                "on_site_teknisi": "",
                "perbaikan": "",
                "hasil_akhir": ""
            }
        
        lc_signal_avo["stu_1088_2304"].update(stu_values)
        print(f"    ✓ STU 1088/2304: {stu_values}")
        
        # Tainet (SEPARATE ROW)
        tainet_values = self._extract_quality_row_with_ocr(avo_section, r"(?<!/)Tainet(?!\s+Scorpio)")
        if not tainet_values:
            tainet_values = self._extract_quality_row(avo_section, r"(?<!/)Tainet(?!\s+Scorpio)")
        
        # CRITICAL FIX: Manual extraction for "50-200 Ω (HRB Area)" with better pattern
        # Check if we got wrong value (just "Ω")
        if not tainet_values or not tainet_values.get("standard") or tainet_values.get("standard") == "Ω":
            # Try to find full value in text
            manual_match = re.search(
                r'(50[-–]\s*200\s*[ΩΩ]\s*\([^)]*(?:HRB|Area)[^)]*\))',
                avo_section,
                re.IGNORECASE
            )
            
            if manual_match:
                tainet_values = {
                    "standard": manual_match.group(1).strip(),
                    "nms_engineer": "Ω",
                    "on_site_teknisi": "",
                    "perbaikan": "",
                    "hasil_akhir": ""
                }
                print(f"    [MANUAL EXTRACT] Tainet: standard='{manual_match.group(1)}', nms='Ω'")
            else:
                # If still not found, try alternative pattern for text mode
                # Pattern: "Tainet\n50–200 Ω (HRB Area)\nΩ"
                alt_match = re.search(
                    r'Tainet\s*\n\s*(50[-–]\s*200\s*[ΩΩ]\s*\([^)]*(?:HRB|Area)[^)]*\))\s*\n\s*([ΩΩ])',
                    avo_section,
                    re.IGNORECASE
                )
                
                if alt_match:
                    tainet_values = {
                        "standard": alt_match.group(1).strip(),
                        "nms_engineer": alt_match.group(2).strip(),
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    }
                    print(f"    [MANUAL EXTRACT ALT] Tainet: standard='{alt_match.group(1)}', nms='{alt_match.group(2)}'")
        
        if not tainet_values:
            tainet_values = {
                "standard": "",
                "nms_engineer": "",
                "on_site_teknisi": "",
                "perbaikan": "",
                "hasil_akhir": ""
            }
        
        lc_signal_avo["tainet"].update(tainet_values)
        print(f"    ✓ Tainet: {tainet_values}")
        
        # Adtran Express - CRITICAL FIX: NO Ω at all (neither standard nor NMS)
        adtran_values = self._extract_quality_row_with_ocr(avo_section, r"Adtran\s+Express")
        if not adtran_values:
            adtran_values = self._extract_quality_row(avo_section, r"Adtran\s+Express")
        
        # Extract "48-50 VDc (QUAD CES SHDSL)" - WITHOUT Ω anywhere
        manual_match = re.search(
            r'(48[-–]50\s+VDc\s+\(QUAD\s+CES\s+SHDSL\))',
            avo_section.replace('\n', ' '),
            re.IGNORECASE
        )
        
        if manual_match:
            adtran_values = {
                "standard": manual_match.group(1).strip(),  # NO Ω
                "nms_engineer": "",                         # NO Ω in NMS either
                "on_site_teknisi": "",
                "perbaikan": "",
                "hasil_akhir": ""
            }
            print(f"    [MANUAL EXTRACT] Adtran Express: standard='{manual_match.group(1)}' (no Ω anywhere)")
        elif adtran_values and adtran_values.get("standard"):
            # Clean and ensure NO Ω anywhere
            standard = re.sub(r'\s+', ' ', adtran_values["standard"]).strip()
            standard = standard.replace('Ω', '').strip()
            adtran_values["standard"] = standard
            adtran_values["nms_engineer"] = ""  # NO Ω in NMS
        
        if not adtran_values:
            adtran_values = {
                "standard": "",
                "nms_engineer": "",
                "on_site_teknisi": "",
                "perbaikan": "",
                "hasil_akhir": ""
            }
        
        # FORCE: Ensure nms_engineer is empty (no Ω)
        adtran_values["nms_engineer"] = ""
        
        lc_signal_avo["adtran_express"].update(adtran_values)
        print(f"    ✓ Adtran Express: {adtran_values}")

    def _extract_quality_row(self, section_text: str, row_label_pattern: str) -> dict:
        """
        Extract quality parameter row - ENHANCED TEXT EXTRACTION
        
        This is the fallback when OCR fails.
        """
        result = {
            "standard": "",
            "nms_engineer": "",
            "on_site_teknisi": "",
            "perbaikan": "",
            "hasil_akhir": ""
        }
        
        # Find row label
        row_match = re.search(row_label_pattern, section_text, re.IGNORECASE)
        
        if not row_match:
            print(f"      [TEXT EXTRACT] ✗ Pattern '{row_label_pattern}' not found")
            return result
        
        label_text = row_match.group()
        label_end = row_match.end()
        
        print(f"\n      [TEXT EXTRACT] Pattern: {row_label_pattern}")
        print(f"      [TEXT EXTRACT] Found label: '{label_text}'")
        
        # Extract text after label (up to 400 chars)
        after_label = section_text[label_end:label_end + 400]
        
        # ENHANCED: Try to extract first meaningful value after label
        # Remove leading whitespace/newlines
        after_label = after_label.lstrip()
        
        # Split by newline and get first non-empty line
        lines = after_label.split('\n')
        
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            
            # Skip empty, noise, or next row labels
            if not line or self._is_noise_text(line) or self._looks_like_next_row_label(line):
                continue
            
            # Found a valid value - put it in standard
            result["standard"] = line
            print(f"      [TEXT EXTRACT] ✓ Found value: '{line}'")
            break
        
        print(f"      [TEXT EXTRACT] ✓ Result: {result}")
        
        return result

    def _extract_row_line_by_line(self, after_label_text: str) -> dict:
        """
        Extract row values line by line with SMART FILTERING
        """
        result = {
            "standard": "",
            "nms_engineer": "",
            "on_site_teknisi": "",
            "perbaikan": "",
            "hasil_akhir": ""
        }
        
        lines = after_label_text.split('\n')
        
        # ... existing code untuk collect values ...
        
        values = []
        i = 0
        
        while i < min(len(lines), 20):
            line = lines[i].strip()
            
            if not line or line in ['.', '..', '...', '-', '--', 'xxx', 'XXX', ' ']:
                i += 1
                continue
            
            if self._is_noise_text(line):
                i += 1
                continue
            
            if self._looks_like_next_row_label(line):
                break
            
            combined_value = line
            
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                
                if (next_line and 
                    next_line not in ['.', '..', '...', '-', '--', 'xxx', 'XXX'] and
                    not self._is_noise_text(next_line) and
                    not self._looks_like_next_row_label(next_line) and
                    len(next_line) > 2 and
                    not self._looks_like_separate_value(line, next_line)):
                    
                    combined_value = f"{line} {next_line}"
                    i += 1
            
            values.append(combined_value)
            i += 1
            
            if len(values) >= 5:
                break
        
        print(f"      [LINE EXTRACT] Extracted values: {values}")
        
        # Map values to fields
        field_keys = ["standard", "nms_engineer", "on_site_teknisi", "perbaikan", "hasil_akhir"]
        
        for idx, value in enumerate(values):
            if idx < len(field_keys):
                result[field_keys[idx]] = value
        
        # Clean placeholders
        for key in result:
            if result[key] in ['.', '..', '...', '-', '--', 'xxx', 'XXX']:
                result[key] = ""
            result[key] = result[key].strip()
        
        # ADDED: Post-processing - Clean newlines dari all values
        for key in result:
            if result[key]:
                result[key] = re.sub(r'\s*\n\s*', ' ', result[key]).strip()
        
        return result

    def _is_noise_text(self, text: str) -> bool:
        """Check apakah text adalah noise yang harus di-skip"""
        text_lower = text.lower().strip()
        
        noise_patterns = [
            r'^merek\s*:',
            r'^front\s+panel',
            r'^\d+\.\s*$',
            r'^lc\s+signal',
            r'^quality\s*$',
            r'^checked\s+by',
            r'^kop\s*\)',
            r'^\(checked',
            r'^perangkat',
            r'^indoor\s+area',
            r'^outdoor\s+area',
            r'^avo\s+meter\)',  # ADDED: Skip "AVO Meter)"
            r'^\(avo\s+meter',   # ADDED: Skip "(AVO Meter"
        ]
        
        for pattern in noise_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False

    def _looks_like_separate_value(self, current_line: str, next_line: str) -> bool:
        """Check apakah next_line adalah value terpisah"""
        current_lower = current_line.lower().strip()
        next_lower = next_line.lower().strip()
        
        # Jika current ends dengan closing punctuation → separate
        if current_line.endswith(')') or current_line.endswith('Ω'):
            return True
        
        # Jika next mulai dengan angka → separate
        if re.match(r'^\d+', next_line):
            return True
        
        # Jika next adalah common keyword → separate
        common_keywords = ['connected', 'green', 'on', 'off', 'blink', 'quality', 'sos', 'jangkrik', 'bersih']
        if any(keyword in next_lower for keyword in common_keywords):
            return True
        
        # Special case: "Quality A" + "No Counter" → combine
        if 'quality' in current_lower and next_lower.startswith('no'):
            return False
        
        return True

    def _looks_like_next_row_label(self, text: str) -> bool:
        """Check apakah text adalah label row berikutnya"""
        text_lower = text.lower()
        
        row_label_indicators = [
            r'\b(power|dcd|link|wan)\b',
            r'\b(td|rd|rts|cts)[/]?(txd|rxd)?\b',
            r'\balarm\s+led\b',
            r'\bfront\s+panel\b',
            r'\boptical\b',
            r'\b(stu|adsl|modem|tainet|scorpio)\b',
            r'\b(bivocom|hrb|adtran)\b',
            r'\b(quality|parameter|standard)\b',
            r'\b(indoor|outdoor|area)\b',
            r'\b(signal|checked|by)\b',
            r'^\d{3}[/]',
        ]
        
        for pattern in row_label_indicators:
            if re.search(pattern, text_lower):
                return True
        
        return False

    def _extract_quality_row_with_ocr(self, section_text: str, row_label_pattern: str) -> dict:
        """
        Extract quality row using OCR spatial data - COMPLETELY FIXED VERSION
        
        Key fixes:
        1. Stricter Y-distance threshold (20px instead of 30px) to avoid next row contamination
        2. Better duplicate detection (same X and same text)
        3. Improved validation
        """
        if not self.ocr_data:
            print(f"      [OCR EXTRACT] OCR data not available, will use text-based fallback")
            return None
        
        result = {
            "standard": "",
            "nms_engineer": "",
            "on_site_teknisi": "",
            "perbaikan": "",
            "hasil_akhir": ""
        }
        
        # Find row label in OCR data
        label_item = None
        label_idx = None
        
        for idx, ocr_item in enumerate(self.ocr_data):
            text = ocr_item['text']
            if re.search(row_label_pattern, text, re.IGNORECASE):
                label_item = ocr_item
                label_idx = idx
                break
        
        if not label_item:
            print(f"      [OCR EXTRACT] Label not found in OCR data, will use text-based fallback")
            return None
        
        # Get label coordinates
        bbox = label_item.get('bbox', [])
        if bbox and len(bbox) > 0:
            label_y = bbox[0][1]
            label_x = bbox[0][0]
        else:
            label_y, label_x = label_item.get('position', (0, 0))
        
        print(f"\n      [OCR EXTRACT] Found label at Y={label_y}, X={label_x}")
        
        # CRITICAL: Skip items in label column (X < 250)
        LABEL_COLUMN_MAX_X = 250
        
        # Collect items on same row - STRICTER Y threshold (20px instead of 30px)
        row_items = []
        seen_items = set()  # Track seen (x, text) to avoid duplicates
        
        for i in range(label_idx + 1, min(label_idx + 20, len(self.ocr_data))):
            item = self.ocr_data[i]
            item_bbox = item.get('bbox', [])
            
            if item_bbox and len(item_bbox) > 0:
                item_y = item_bbox[0][1]
                item_x = item_bbox[0][0]
            else:
                item_y, item_x = item.get('position', (0, 0))
            
            y_distance = abs(float(item_y) - float(label_y))
            
            # STRICTER: If more than 20px away vertically, stop
            if y_distance > 20:
                break
            
            text = item['text'].strip()
            
            # Skip empty or noise
            if not text or text in ['|', '.', '..', '-']:
                continue
            
            # Skip if X position is in label column
            if float(item_x) < LABEL_COLUMN_MAX_X:
                print(f"        [SKIP LABEL] X={item_x:.0f} | '{text}'")
                continue
            
            # CRITICAL: Check for duplicates (same X position and same text)
            item_key = (round(float(item_x)), text)
            if item_key in seen_items:
                print(f"        [SKIP DUPLICATE] X={item_x:.0f} | '{text}'")
                continue
            seen_items.add(item_key)
            
            row_items.append({
                'text': text,
                'x': float(item_x),
                'y': float(item_y)
            })
        
        # Sort by X coordinate (left to right)
        row_items.sort(key=lambda x: x['x'])
        
        print(f"      [OCR EXTRACT] Found {len(row_items)} items on row")
        for item in row_items:
            print(f"        X={item['x']:.0f} | '{item['text']}'")
        
        # Map directly to fields (no grouping to avoid contamination)
        field_keys = ["standard", "nms_engineer", "on_site_teknisi", "perbaikan", "hasil_akhir"]
        
        for idx, item in enumerate(row_items):
            if idx < len(field_keys):
                result[field_keys[idx]] = item['text']
        
        # Clean empty placeholders
        for key in result:
            value = result[key]
            if value in ['.', '..', '...', '-', '--', 'xxx', 'XXX']:
                result[key] = ""
            result[key] = result[key].strip()
        
        # VALIDATION: If standard is empty, trigger fallback
        if not result['standard']:
            print(f"      [OCR EXTRACT] ⚠ Empty standard detected, triggering text-based fallback")
            return None
        
        print(f"      [OCR EXTRACT] ✓ Result: {result}")
        
        return result

    def _is_likely_label(self, text: str) -> bool:
        """Check apakah text kemungkinan adalah label (bukan value)"""
        text_lower = text.lower().strip()
        
        # Common row/section labels
        label_keywords = [
            'modem', 'indikator', 'merek', 'quality', 'signal', 
            'checked', 'kop', 'avo', 'meter', 'front', 'panel',
            'display', 'lc signal', 'tainet', 'scorpio'
        ]
        
        # Check if text is exactly a label keyword
        if text_lower in label_keywords:
            return True
        
        # Check if text contains label patterns
        if any(keyword in text_lower for keyword in ['indikator', 'quality', 'checked by']):
            return True
        
        return False

    # ============================================================================
    # 3. EXTRACT LINE CHECKLIST SECTION
    # ============================================================================
    def _extract_line_checklist_section(self) -> str:
        """Extract section LINE CHECKLIST dari document"""
        print("\n" + "="*80)
        print("DEBUG: Extract LINE CHECKLIST")
        print("="*80)
        
        # IMPROVED: Capture more content, termasuk Tes Konektivitas
        patterns = [
            r'LINE\s+CHECKLIST.*?(?=VERIFIKASI|DOKUMENTASI|FORM\s+CHECKLIST|$)',
            r'LINECHECKLIST.*?(?=VERIFIKASI|DOKUMENTASI|FORM\s+CHECKLIST|$)',
            r'LINE\s*CHECKLIST.*?(?=VERIFIKASI|DOKUMENTASI|FORM\s+CHECKLIST|$)',
        ]
        
        for i, pattern in enumerate(patterns, 1):
            match = re.search(pattern, self.cleaned_text, re.IGNORECASE | re.DOTALL)
            if match:
                line_text = match.group()
                
                # More lenient keyword check
                keywords = ["SITE AREA", "HRB", "LINE FO", "TES", "KONEKTIVITAS"]
                keyword_count = sum(1 for kw in keywords if kw in line_text.upper())
                
                if keyword_count >= 2:  # Lowered threshold
                    print(f"✓ Pattern {i} matched! Length: {len(line_text)} chars")
                    print(f"  Keywords found: {keyword_count}/5")
                    print("="*80 + "\n")
                    return line_text
        
        print("[ERROR] LINE CHECKLIST section tidak ditemukan")
        print("="*80 + "\n")
        return ""


    # ============================================================================
    # 4. MASTER PARSER
    # ============================================================================
    def _parse_line_checklist_all(self, line_checklist: dict, line_text: str):
        """Parse semua sub-section LINE CHECKLIST"""
        print("\n" + "="*60)
        print("Parsing LINE CHECKLIST")
        print("="*60)
        
        self._parse_line_site_area(line_checklist["site_area"], line_text)
        self._parse_line_hrb_r_lintas(line_checklist["hrb_r_lintas"], line_text)
        self._parse_line_fo(line_checklist["line_fo"], line_text)
        self._parse_line_tes_konektivitas(line_checklist["tes_konektivitas"], line_text)
        
        print("="*60 + "\n")


    # ============================================================================
    # 5. PARSE SITE AREA
    # ============================================================================
    def _parse_line_site_area(self, site_area: dict, line_text: str):
        """Parse Site Area section"""
        print("  → Parsing Site Area...")
        
        pattern = r'Site\s+Area.*?(?=HRB|Tes\s+Konektivitas|$)'
        match = re.search(pattern, line_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("    ✗ Site Area tidak ditemukan")
            return
        
        site_text = match.group()
        
        items = [
            "Kabel RJ-11",
            "Phone Box",
            "KTB/DP Wall",
            "DP Telkom",
            "Sub Gedung",
            "MDF Gedung",
            "T-Line Gedung"
        ]
        
        for item in items:
            param = self._extract_line_parameter(site_text, item)
            site_area["parameter_kualitas"].append(param)
            print(f"    • {param['line_checklist']}: Std='{param['standard'][:40]}...'")
        
        print(f"    ✓ Site Area: {len(site_area['parameter_kualitas'])} items")


    # ============================================================================
    # 6. PARSE HRB/R.LINTAS
    # ============================================================================
    def _parse_line_hrb_r_lintas(self, hrb_data: dict, line_text: str):
        """Parse HRB/R.Lintas section"""
        print("  → Parsing HRB/R.Lintas...")
        
        pattern = r'HRB.*?(?=Line\s+FO|Tes\s+Konektivitas|$)'
        match = re.search(pattern, line_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("    ✗ HRB/R.Lintas tidak ditemukan")
            return
        
        hrb_text = match.group()
        
        # Special handling untuk T-Line dengan (TX,LC)
        items = [
            ("T-Line (TX,LC)", r'T-Line'),
            ("Kabel Data", r'Kabel\s+Data'),
            ("Port Sentral", r'Port\s+Sentral')
        ]
        
        for display_name, search_pattern in items:
            param = self._extract_line_parameter(hrb_text, display_name, search_pattern)
            hrb_data["parameter_kualitas"].append(param)
            print(f"    • {param['line_checklist']}: Std='{param['standard'][:40]}...'")
        
        print(f"    ✓ HRB/R.Lintas: {len(hrb_data['parameter_kualitas'])} items")


    # ============================================================================
    # 7. PARSE LINE FO
    # ============================================================================
    def _parse_line_fo(self, line_fo: dict, line_text: str):
        """Parse Line FO section"""
        print("  → Parsing Line FO...")
        
        pattern = r'Line\s+FO.*?(?=Tes\s+Konektivitas|$)'
        match = re.search(pattern, line_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("    ✗ Line FO tidak ditemukan")
            return
        
        fo_text = match.group()
        
        items = [
            "Cek Signal FO",
            "Koneksi OTB"
        ]
        
        for item in items:
            param = self._extract_line_parameter(fo_text, item)
            line_fo["parameter_kualitas"].append(param)
            print(f"    • {param['line_checklist']}: Std='{param['standard'][:40]}...'")
        
        print(f"    ✓ Line FO: {len(line_fo['parameter_kualitas'])} items")


    # ============================================================================
    # 8. PARSE TES KONEKTIVITAS
    # ============================================================================
    def _parse_line_tes_konektivitas(self, tes_data: dict, line_text: str):
        """Parse Tes Konektivitas section"""
        print("  → Parsing Tes Konektivitas...")
        
        # IMPROVED: Multiple pattern variations
        patterns = [
            r'Tes\s+Konektivitas.*?(?=FORM\s+CHECKLIST|DATA\s+PERANGKAT|VERIFIKASI|$)',
            r'TesKonektivitas.*?(?=FORM\s+CHECKLIST|DATA\s+PERANGKAT|VERIFIKASI|$)',  # No space
            r'Tes.*?Konektivitas.*?(?=FORM\s+CHECKLIST|DATA\s+PERANGKAT|VERIFIKASI|$)',  # Flexible
        ]
        
        tes_text = None
        for pattern in patterns:
            match = re.search(pattern, line_text, re.IGNORECASE | re.DOTALL)
            if match:
                tes_text = match.group()
                break
        
        if not tes_text:
            print("    ✗ Tes Konektivitas tidak ditemukan")
            # FALLBACK: Try OCR-based extraction if text-based fails
            if hasattr(self, 'ocr_data') and self.ocr_data:
                print("    → Trying OCR-based fallback...")
                self._parse_tes_konektivitas_ocr(tes_data)
            return
        
        items = [
            "Bit Error Rate",
            "Ping"
        ]
        
        for item in items:
            param = self._extract_line_parameter(tes_text, item)
            tes_data["parameter_kualitas"].append(param)
            print(f"    • {param['line_checklist']}: Std='{param['standard'][:40]}...'")
        
        print(f"    ✓ Tes Konektivitas: {len(tes_data['parameter_kualitas'])} items")

    def _parse_tes_konektivitas_ocr(self, tes_data: dict):
        """Fallback: Extract Tes Konektivitas using OCR data"""
        if not hasattr(self, 'ocr_data') or not self.ocr_data:
            return
        
        # Find "Bit Error Rate" and "Ping" in OCR
        items_to_find = {
            "Bit Error Rate": None,
            "Ping": None
        }
        
        for idx, item in enumerate(self.ocr_data):
            text = item.get('text', '').strip()
            
            if 'Bit Error' in text or 'BIT ERROR' in text.upper():
                # Extract next items for standard value
                standard = self._extract_ocr_value_after(idx, max_items=3)
                items_to_find["Bit Error Rate"] = standard
            
            elif text.lower() == 'ping':
                # Extract next items for standard value
                standard = self._extract_ocr_value_after(idx, max_items=3)
                items_to_find["Ping"] = standard
        
        # Add to tes_data
        for item_name, standard in items_to_find.items():
            if standard:
                tes_data["parameter_kualitas"].append({
                    "line_checklist": item_name,
                    "standard": standard,
                    "existing": "",
                    "perbaikan": "",
                    "hasil_akhir": ""
                })
                print(f"    • [OCR] {item_name}: Std='{standard[:40]}...'")

    def _extract_ocr_value_after(self, start_idx: int, max_items: int = 5) -> str:
        """Extract value from OCR items after start_idx"""
        values = []
        current_y = self.ocr_data[start_idx]['bbox'][0][1]  # Y position
        
        for i in range(start_idx + 1, min(start_idx + max_items + 1, len(self.ocr_data))):
            item = self.ocr_data[i]
            text = item.get('text', '').strip()
            item_y = item['bbox'][0][1]
            
            # Stop if Y distance too large (different row/section)
            if abs(item_y - current_y) > 30:
                break
            
            # Skip keywords
            if text in ['STANDARD', 'EXISTING', 'PERBAIKAN', 'HASIL AKHIR']:
                continue
            
            if text:
                values.append(text)
        
        return ' '.join(values)


    # ============================================================================
    # 9. MAIN EXTRACTION LOGIC
    # ============================================================================
    def _extract_line_parameter(self, text: str, item_name: str, search_pattern: str = None) -> dict:
        """Extract single parameter"""
        if search_pattern is None:
            search_pattern = re.escape(item_name)
        
        print(f"      DEBUG: Extracting '{item_name}'")
        
        # TRY OCR FIRST (if available)
        if hasattr(self, 'ocr_data') and self.ocr_data:
            ocr_result = self._extract_line_param_ocr(item_name, section_name="LINE CHECKLIST")
            
            if ocr_result['standard']:
                # Clean the value
                cleaned_std = self._clean_value_smart(ocr_result['standard'])
                ocr_result['standard'] = cleaned_std
                
                if cleaned_std:  # Only use if not empty after cleaning
                    print(f"        ✓ OCR SUCCESS (cleaned): '{cleaned_std[:50]}...'")
                    return ocr_result
        
        # FALLBACK: Regex extraction
        result = self._extract_line_param_regex(text, item_name, search_pattern)
        
        if not result['standard']:
            print(f"        ⚠ Both OCR and Regex failed for '{item_name}'")
        
        return result


    def _extract_line_param_ocr(self, item_name: str, section_name: str = "LINE CHECKLIST") -> dict:
        """Extract parameter using OCR data (filtered by section)"""
        
        # ============================================================================
        # STEP 1: Find LINE CHECKLIST section boundaries
        # ============================================================================
        section_start_idx = None
        section_end_idx = None
        
        for idx, item in enumerate(self.ocr_data):
            text = item.get('text', '').strip().upper()
            
            # Find section start
            if 'LINECHECKLIST' in text or 'LINE CHECKLIST' in text:
                section_start_idx = idx
            
            # Find section end
            if section_start_idx:
                next_section_keywords = [
                    'VERIFIKASI', 'DOKUMENTASI', 'FORM CHECKLIST',
                    'DATAPERANGKAT', 'DATA PERANGKAT',
                    'GLOBALCHECKLIST', 'GLOBAL CHECKLIST'
                ]
                
                if any(keyword in text for keyword in next_section_keywords):
                    section_end_idx = idx
                    break
        
        if not section_start_idx:
            return {"line_checklist": item_name, "standard": "", "existing": "", "perbaikan": "", "hasil_akhir": ""}
        
        if not section_end_idx:
            section_end_idx = len(self.ocr_data)
        
        print(f"        [SECTION FILTER] Using OCR items [{section_start_idx}:{section_end_idx}]")
        
        # ============================================================================
        # STEP 2: Find item label with FUZZY matching
        # ============================================================================
        label_idx = None
        
        # Try exact match first
        for idx in range(section_start_idx, section_end_idx):
            text = self.ocr_data[idx].get('text', '').strip()
            if item_name.lower() in text.lower():
                label_idx = idx
                break
        
        # ✅ FIX: Fuzzy matching for T-Line (TXLC) or (TX,LC)
        if label_idx is None and 'T-Line' in item_name and ('TX' in item_name or 'TXLC' in item_name):
            print(f"        [FUZZY] Trying fuzzy match for '{item_name}'...")
            
            for idx in range(section_start_idx, section_end_idx):
                text = self.ocr_data[idx].get('text', '').strip()
                
                # Match "T-Line" anywhere
                if 'T-Line' in text or 'T Line' in text or 'TLine' in text or 'T-Line' in text:
                    # Look ahead for (TX,LC) or (TXLC) pattern in next few items
                    found_tx = False
                    for next_idx in range(idx, min(idx + 5, section_end_idx)):
                        next_text = self.ocr_data[next_idx].get('text', '').strip()
                        if 'TX' in next_text or 'LC' in next_text or '(T' in next_text or 'TXLC' in next_text:
                            found_tx = True
                            break
                    
                    if found_tx:
                        label_idx = idx
                        print(f"        [FUZZY FOUND] Using idx={idx}, text='{text}'")
                        break
        
        if label_idx is None:
            print(f"        ✗ Label '{item_name}' not found in section")
            return {"line_checklist": item_name, "standard": "", "existing": "", "perbaikan": "", "hasil_akhir": ""}
        
        # ============================================================================
        # STEP 3: Get label position and find next item
        # ============================================================================
        label_y = self.ocr_data[label_idx]['bbox'][0][1]
        label_x = self.ocr_data[label_idx]['bbox'][0][0]
        
        print(f"        [LABEL FOUND] '{item_name}' at Y={label_y:.1f}, X={label_x:.1f}")
        
        # Find next item dynamically
        LEFT_COLUMN_X_MAX = 200
        
        next_item_y = None
        for idx in range(label_idx + 1, section_end_idx):
            check_item = self.ocr_data[idx]
            check_y = check_item['bbox'][0][1]
            check_x = check_item['bbox'][0][0]
            check_text = check_item.get('text', '').strip()
            
            # ✅ FIX: Skip (TX,LC) atau (TXLC) or similar patterns
            if re.match(r'^\([A-Z,]+\)$', check_text):
                print(f"        [SKIP SUFFIX] '{check_text}' at Y={check_y:.1f}")
                continue
            
            if check_x < LEFT_COLUMN_X_MAX and check_y > label_y + 20:
                if len(check_text) > 3:
                    next_item_y = check_y
                    print(f"        [NEXT ITEM] at Y={next_item_y:.1f} ('{check_text}')")
                    break
        
        if next_item_y:
            max_y = next_item_y - 5
        else:
            max_y = label_y + 80  # ✅ Increased from 60 to 80 for multi-line items
        
        print(f"        [Y BOUNDARY] {label_y:.1f} to {max_y:.1f} (span={max_y-label_y:.1f}px)")
        
        # ============================================================================
        # STEP 4: Extract values
        # ============================================================================
        standard_parts = []
        existing_value = ""
        
        STANDARD_X_MIN = 300
        STANDARD_X_MAX = 650
        EXISTING_X_MIN = 650
        EXISTING_X_MAX = 900
        
        for idx in range(section_start_idx, section_end_idx):
            item = self.ocr_data[idx]
            item_y = item['bbox'][0][1]
            item_x = item['bbox'][0][0]
            text = item.get('text', '').strip()
            
            if idx == label_idx or text in ['STANDARD', 'EXISTING', 'PERBAIKAN', 'HASIL AKHIR']:
                continue
            
            # Same row
            if abs(item_y - label_y) <= 15:
                if STANDARD_X_MIN <= item_x <= STANDARD_X_MAX:
                    standard_parts.append(text)
                    print(f"          [STD] X={item_x:.0f} | '{text}'")
                elif EXISTING_X_MIN <= item_x <= EXISTING_X_MAX:
                    existing_value = text
                    print(f"          [EXT] X={item_x:.0f} | '{text}'")
            
            # Multi-line
            elif label_y < item_y <= max_y:
                if STANDARD_X_MIN <= item_x <= STANDARD_X_MAX:
                    if text not in ['Site Area', 'HRB', 'Line FO', 'Tes']:
                        standard_parts.append(text)
                        print(f"          [STD+] Y={item_y:.0f} X={item_x:.0f} | '{text}'")
        
        # ============================================================================
        # STEP 4.5: ✅ SPECIAL HANDLING FOR T-LINE - Look for "Tahanan Loop" below
        # ============================================================================
        if 'T-Line' in item_name:
            print(f"        [T-LINE SPECIAL] Looking for additional Tahanan Loop data...")
            
            # Determine which T-Line this is based on context
            is_hrb_tline = '(TXLC)' in item_name or '(TX' in item_name or 'TX,LC' in item_name
            is_gedung_tline = 'Gedung' in item_name
            
            print(f"        [T-LINE TYPE] HRB={is_hrb_tline}, Gedung={is_gedung_tline}")
            
            # Look for "Tahanan Loop" text in extended range
            for idx in range(section_start_idx, section_end_idx):
                item = self.ocr_data[idx]
                item_y = item['bbox'][0][1]
                item_x = item['bbox'][0][0]
                text = item.get('text', '').strip()
                
                # Check if this is "Tahanan Loop" text in rows below label
                if ('Tahanan Loop' in text or 'Tahanan' in text) and ':' in text:
                    # Must be below label and within extended range
                    if label_y < item_y <= max_y + 50:  # Extended range
                        if STANDARD_X_MIN <= item_x <= STANDARD_X_MAX + 50:
                            # Found "Tahanan Loop : ..." 
                            print(f"          [TAHANAN FOUND] Y={item_y:.0f} X={item_x:.0f} | '{text}'")
                            
                            # ✅ FIX: Check if this "Tahanan Loop" line is already in standard_parts
                            already_included = any(text in part for part in standard_parts)
                            
                            if not already_included:
                                standard_parts.append(text)
                                print(f"          [TAHANAN ADDED] '{text}'")
                            else:
                                print(f"          [TAHANAN SKIP] Already in standard_parts")
                            
                            # Look for EXISTING value in EXISTING column (not the Ω inside "Tahanan Loop : 010-100 Ω")
                            tahanan_y = item_y
                            
                            # ✅ FIX: Only look for standalone Ω or 0 in EXISTING column
                            # NOT the Ω that's part of "010-100 Ω"
                            for idx2 in range(idx + 1, min(idx + 10, section_end_idx)):
                                exist_item = self.ocr_data[idx2]
                                exist_y = exist_item['bbox'][0][1]
                                exist_x = exist_item['bbox'][0][0]
                                exist_text = exist_item.get('text', '').strip()
                                
                                # Same row or very close (within 15px)
                                if abs(exist_y - tahanan_y) <= 15:
                                    # Check EXISTING column ONLY
                                    if EXISTING_X_MIN <= exist_x <= EXISTING_X_MAX:
                                        # ✅ CRITICAL: Only accept if it's JUST "Ω" or "0" (not part of bigger text)
                                        if exist_text in ['Ω', 'Ω', '0']:
                                            existing_value = exist_text
                                            print(f"          [TAHANAN EXISTING] X={exist_x:.0f} | '{exist_text}'")
                                            break
                                        else:
                                            print(f"          [TAHANAN SKIP NON-STANDALONE] '{exist_text}' at X={exist_x:.0f}")
                            
                            break  # Found Tahanan Loop, stop searching
        
        # ============================================================================
        # STEP 5: Final check - For T-Line items, look for standalone Ω or 0
        # ============================================================================
        if 'T-Line' in item_name and not existing_value:
            for idx in range(section_start_idx, section_end_idx):
                item = self.ocr_data[idx]
                item_y = item['bbox'][0][1]
                item_x = item['bbox'][0][0]
                text = item.get('text', '').strip()
                
                # Within Y range (check both same row and multi-line area)
                if label_y - 5 <= item_y <= max_y + 50:
                    # Check EXISTING column
                    if EXISTING_X_MIN <= item_x <= EXISTING_X_MAX:
                        # If it's Ω or a number or 0
                        if text in ['Ω', 'Ω', '0'] or (text.isdigit() and len(text) <= 3):
                            existing_value = text
                            print(f"          [EXT T-LINE FINAL] X={item_x:.0f} | '{text}'")
                            break
        
        standard = ' '.join(standard_parts).strip()
        
        # ============================================================================
        # STEP 6: Clean values (preserve Ω and important keywords)
        # ============================================================================
        # Count Ω symbols before cleaning
        omega_count_before = standard.count('Ω') + standard.count('Ω')

        # Clean standard
        standard = self._clean_value_smart(standard)

        # ✅ FIX: Check if Ω was lost during cleaning
        omega_count_after = standard.count('Ω') + standard.count('Ω')

        # Only restore Ω if it was completely removed (not if it still exists)
        if omega_count_before > 0 and omega_count_after == 0:
            # Add it back if there's a number range before (like "200-400")
            if re.search(r'\d+[-–]\d+\s*$', standard) or re.search(r':\s*\d+[-–]\d+\s*$', standard):
                standard = standard.rstrip() + ' Ω'
                print(f"        → Restored Ω (was lost in cleaning)")

        # ✅ Don't clean EXISTING if it's special value
        if existing_value:
            if existing_value in ['Ω', 'Ω', '0'] or existing_value.isdigit():
                pass  # Keep as is
            else:
                existing_value = self._clean_value_smart(existing_value)

        print(f"        → Final: Std='{standard[:60]}...', Exist='{existing_value}'")
        
        return {
            "line_checklist": item_name,
            "standard": standard,
            "existing": existing_value,
            "perbaikan": "",
            "hasil_akhir": ""
        }


    def _clean_value_smart(self, value: str) -> str:
        """
        Clean value using PATTERN detection (not keyword blacklist)
        Preserve important values like OK, Ω, numbers
        """
        if not value:
            return value
        
        original_value = value
        
        # ✅ Pattern 1: Remove voltage/amperage specs (pattern: number + V/A)
        value = re.sub(r'\d+V\.?\s*\d*\.?\d*A', '', value, flags=re.IGNORECASE)
        value = re.sub(r'\d+V(?!\w)', '', value)
        value = re.sub(r'\d+\.?\d*A(?!\w)', '', value)
        
        # ✅ Pattern 2: Remove "FOR" followed by single letter (pattern: FOR + char)
        value = re.sub(r'\bFOR\s+[A-Z]\b', '', value, flags=re.IGNORECASE)
        
        # ✅ Pattern 3: Filter words carefully - WHITELIST important ones
        words = value.split()
        cleaned_words = []
        
        # Important keywords that should NEVER be removed
        WHITELIST = ['OK', 'NO', 'ON', 'OFF', 'Ω', 'Ω', 'YES', 'A', 'B']
        
        for word in words:
            # ✅ WHITELIST: Keep important words
            if word.upper() in WHITELIST or word in WHITELIST:
                cleaned_words.append(word)
                continue
            
            # Keep numbers
            if word.isdigit() or re.match(r'^\d+[-–]\d+$', word):
                cleaned_words.append(word)
                continue
            
            # Keep technical abbreviations (short ALL CAPS)
            if word.isupper() and len(word) <= 3:
                # These are allowed technical terms
                if word in ['STU', 'LED', 'CRC', 'RTS', 'CTS', 'SOS', 'NMS', 'VDc']:
                    cleaned_words.append(word)
                    continue
                # Skip noise like "S/N", "Reg" (will be filtered by pattern below)
            
            # ✅ Skip if looks like registration code (mix of letters/numbers, long)
            if re.match(r'^[A-Z0-9]{5,}$', word):
                continue
            
            # ✅ Skip common noise patterns
            if word.upper() in ['S/N', 'REG', 'NO.', 'NAMA']:
                continue
            
            cleaned_words.append(word)
        
        value = ' '.join(cleaned_words)
        
        # ✅ Special case: If value becomes empty but original had Ω, restore it
        if not value.strip() and ('Ω' in original_value or 'Ω' in original_value):
            return 'Ω'
        
        # ✅ Don't remove if it's a valid single value like "Ω", "0", "OK"
        if value.strip() in ['Ω', 'Ω', '0', 'OK', 'ON', 'OFF']:
            return value.strip()
        
        # ✅ Pattern 4: Remove if ALL CAPS and looks like header (long text with /)
        if value.isupper() and len(value) > 10 and '/' in value:
            return ""
        
        # Clean up whitespace
        value = re.sub(r'\s+', ' ', value).strip()
        value = re.sub(r'\s*([,.:;])\s*', r'\1 ', value).strip()
        
        return value
    

    # ============================================================================
    # 10. REGEX EXTRACTION CORE
    # ============================================================================
    def _extract_line_param_regex(self, text: str, item_name: str, search_pattern: str) -> dict:
        """
        Extract parameter dari format vertikal (TEXT-based extraction)
        
        SIMPLE & ROBUST APPROACH:
        1. Find item name
        2. Capture lines until we hit ANOTHER line that starts with CAPITAL and has NO leading spaces
        3. Filter out suffix patterns like (XXX)
        4. Last line if single char/symbol = EXISTING
        """
        
        print(f"        [REGEX] Extracting '{item_name}'...")
        
        # ============================================================================
        # STEP 1: Find start position of this item
        # ============================================================================
        
        # Find where this item starts
        item_match = re.search(rf'^{search_pattern}\s*$', text, re.MULTILINE | re.IGNORECASE)
        
        if not item_match:
            print(f"        ✗ Item not found")
            return {
                "line_checklist": item_name,
                "standard": "",
                "existing": "",
                "perbaikan": "",
                "hasil_akhir": ""
            }
        
        start_pos = item_match.end()
        remaining_text = text[start_pos:]
        
        # ============================================================================
        # STEP 2: Find end position (next item that starts at column 0)
        # ============================================================================
        
        # Strategy: Find next line that:
        # - Starts at beginning of line (^)
        # - Starts with capital letter
        # - Has at least 3 chars
        # - Is NOT indented (no leading spaces)
        # - Is NOT a value line (doesn't start with "No " or "OK," or numbers)
        
        # Split remaining text into lines
        lines_after = remaining_text.split('\n')
        
        value_lines = []
        
        for i, line in enumerate(lines_after):
            line_stripped = line.strip()
            
            # Empty line - skip
            if not line_stripped:
                continue
            
            # Check if this line is a NEW ITEM (left-aligned, capital start, looks like item name)
            # NEW ITEM indicators:
            # - Line has NO leading spaces (left-aligned)
            # - Starts with capital
            # - Length > 3
            # - Is NOT a common value pattern
            
            has_leading_space = line.startswith(' ') or line.startswith('\t')
            starts_with_capital = line_stripped and line_stripped[0].isupper()
            looks_like_value = line_stripped.startswith(('No ', 'OK,', 'Durasi', '100', 'Tahanan', 'Sedikit', '('))
            
            # If line is left-aligned, starts with capital, and doesn't look like a value
            if not has_leading_space and starts_with_capital and len(line_stripped) > 3 and not looks_like_value:
                # This is likely the next item - stop here
                print(f"        → Stopped at line {i}: '{line_stripped[:40]}'")
                break
            
            # Otherwise, include this line
            value_lines.append(line_stripped)
        
        if not value_lines:
            print(f"        ✗ No value lines found")
            return {
                "line_checklist": item_name,
                "standard": "",
                "existing": "",
                "perbaikan": "",
                "hasil_akhir": ""
            }
        
        print(f"        → Captured {len(value_lines)} lines")
        for idx, line in enumerate(value_lines):
            print(f"           [{idx}] '{line}'")
        
        # ============================================================================
        # STEP 3: Filter lines
        # ============================================================================
        
        filtered_lines = []
        
        for line in value_lines:
            # Skip headers
            if line.upper() in ['STANDARD', 'EXISTING', 'PERBAIKAN', 'HASIL AKHIR']:
                continue
            
            # Skip decorations
            if re.match(r'^[\|\-\_=\s]+$', line):
                continue
            
            # Skip suffix patterns like (TX,LC)
            if re.match(r'^\([^)]+\)$', line):
                print(f"        → Skip suffix: '{line}'")
                continue
            
            # Clean
            line = line.strip('|:._- ')
            
            if not line:
                continue
            
            # Keep single chars if they're special (Ω or digits)
            if len(line) == 1:
                if line in ['Ω', 'Ω'] or line.isdigit():
                    filtered_lines.append(line)
                continue
            
            filtered_lines.append(line)
        
        print(f"        → After filter: {len(filtered_lines)} lines")
        print(f"           {filtered_lines}")
        
        if not filtered_lines:
            return {
                "line_checklist": item_name,
                "standard": "",
                "existing": "",
                "perbaikan": "",
                "hasil_akhir": ""
            }
        
        # ============================================================================
        # STEP 4: Separate STANDARD vs EXISTING
        # ============================================================================
        
        existing = ""
        standard_lines = filtered_lines
        
        # Check if last line is single special char
        last_line = filtered_lines[-1]
        
        if len(last_line) == 1 and (last_line in ['Ω', 'Ω', '0'] or last_line.isdigit()):
            existing = last_line
            standard_lines = filtered_lines[:-1]
            print(f"        → EXISTING detected: '{existing}'")
        
        # Join standard
        standard = ' '.join(standard_lines)
        standard = re.sub(r'\s+', ' ', standard).strip()
        
        # Clean up
        standard = re.sub(r'Noised\.\s*Tdk', 'Noised, Tdk', standard)
        
        print(f"        → FINAL Standard: '{standard[:80]}...'")
        print(f"        → FINAL Existing: '{existing}'")
        
        return {
            "line_checklist": item_name,
            "standard": standard,
            "existing": existing,
            "perbaikan": "",
            "hasil_akhir": ""
        }


    # ============================================================================
    # HELPER METHOD (optional, jika butuh check item name)
    # ============================================================================
    def _is_line_item_name(self, text: str) -> bool:
        """Check apakah text adalah nama item LINE CHECKLIST"""
        line_items = [
            "Kabel RJ", "Phone Box", "KTB", "DP Wall", "DP Telkom",
            "Sub Gedung", "MDF Gedung", "T-Line", "Kabel Data",
            "Port Sentral", "Cek Signal", "Koneksi OTB",
            "Bit Error", "Ping"
        ]
        
        text_lower = text.lower()
        for item in line_items:
            if item.lower() in text_lower:
                return True
        
        return False


    # ==================== DATA PERANGKAT PARSER - FIXED VERSION ====================
    
    def _extract_data_perangkat_section(self) -> str:
        """Extract text dari section C. DATA PERANGKAT"""
        
        patterns = [
            r'(?:C\.\s*)?DATA\s+PERANGKAT.*?(?=(?:D\.\s*)?VERIFIKASI|DOKUMENTASI|$)',
            r'(?:C\.)?DATAPERANGKAT.*?(?=(?:D\.)?VERIFIKASI|DOKUMENTASI|$)',
            r'(?:C\.\s*)?DATA\s*PERANGKAT.*?(?=(?:D\.\s*)?VERIFIKASI|DOKUMENTASI|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.cleaned_text, re.IGNORECASE | re.DOTALL)
            if match:
                perangkat_text = match.group()
                
                # IMPROVED DEBUG: Show items in Y range
                if self.ocr_data:
                    print("\n" + "="*80)
                    print("DEBUG: OCR ITEMS IN DATA PERANGKAT SECTION (IMPROVED)")
                    print("="*80)
                    
                    # Find Y range of relevant items
                    relevant_y_coords = []
                    for item in self.ocr_data:
                        text = item['text']
                        if any(kw in text.upper() for kw in ['EXISTING', 'CABUT', 'ADAPTER', 'BIVOCOM', 'B2WS']):
                            bbox = item.get('bbox', [])
                            if bbox and len(bbox) > 0 and len(bbox[0]) >= 2:
                                y_coord = bbox[0][1]
                                relevant_y_coords.append(y_coord)
                    
                    if relevant_y_coords:
                        y_min = min(relevant_y_coords) - 50
                        y_max = max(relevant_y_coords) + 100
                        
                        print(f"Showing items in Y range: {y_min:.0f} to {y_max:.0f}")
                        
                        for i, item in enumerate(self.ocr_data):
                            bbox = item.get('bbox', [])
                            if bbox and len(bbox) > 0 and len(bbox[0]) >= 2:
                                x_coord = bbox[0][0]
                                y_coord = bbox[0][1]
                            else:
                                y_coord, x_coord = item.get('position', (0, 0))
                            
                            # Show items in Y range
                            if y_min <= y_coord <= y_max:
                                text_preview = item['text'][:40]
                                print(f"[{i:3d}] Y={y_coord:6.1f} X={x_coord:6.1f} | '{text_preview}'")
                    
                    print("="*80 + "\n")
                
                perangkat_keywords = ["EXISTING", "CABUT", "TIDAK TERPAKAI", "PENGGANTI"]
                keyword_count = sum(1 for kw in perangkat_keywords if kw in perangkat_text.upper())
                
                if keyword_count >= 2:
                    return perangkat_text
        
        return ""
    
    def _parse_data_perangkat(self, data_perangkat: dict):
        """Parse section C. DATA PERANGKAT - FIXED V3 (HANDLE SINGLE ITEM)"""
        print("\n" + "="*60)
        print("Parsing C. DATA PERANGKAT (FIXED V3)")
        print("="*60)
        
        perangkat_text = self._extract_data_perangkat_section()
        
        if not perangkat_text:
            print("✗ Section DATA PERANGKAT tidak ditemukan")
            print("="*60 + "\n")
            return
        
        print("\n[DEBUG] FULL PERANGKAT TEXT:")
        print(repr(perangkat_text[:500]))
        print("=" * 60)
        
        # ========== EXISTING/TIDAK TERPAKAI ==========
        existing_section = self._extract_section_before_cabut(perangkat_text)
        
        if existing_section:
            print("\n[EXISTING SECTION] Using OCR-based extraction...")
            
            # Count No.Reg in section
            noreg_pattern = r'B2W[A-Z][A-Z0-9]{10,}'
            noreg_count = len(re.findall(noreg_pattern, existing_section, re.IGNORECASE))
            
            print(f"[EXISTING SECTION] Found {noreg_count} No.Reg(s)")
            
            if noreg_count == 1:
                # SINGLE ITEM - use simplified extraction
                print("[EXISTING SECTION] Single item detected, using simplified OCR extraction")
                existing_items = self._extract_single_item_ocr(existing_section, "EXISTING")
                data_perangkat["existing"] = existing_items
                data_perangkat["tidak_terpakai"] = []
            elif noreg_count >= 2:
                # MULTIPLE ITEMS - use column detection
                print("[EXISTING SECTION] Multiple items detected, using column detection")
                all_items_existing = self._extract_items_by_noreg_with_column_detect(existing_section)
                
                if all_items_existing:
                    existing_items = []
                    tidak_terpakai_items = []
                    
                    for item in all_items_existing:
                        column = item.get('column', None)
                        item_clean = {k: v for k, v in item.items() if k != 'column'}
                        
                        if column == 'left':
                            existing_items.append(item_clean)
                        elif column == 'right':
                            tidak_terpakai_items.append(item_clean)
                    
                    data_perangkat["existing"] = existing_items
                    data_perangkat["tidak_terpakai"] = tidak_terpakai_items
                    
                    print(f"✓ OCR extraction: EXISTING={len(existing_items)}, TIDAK_TERPAKAI={len(tidak_terpakai_items)}")
                else:
                    # Fallback
                    print("⚠ OCR extraction failed, using text-based fallback")
                    left_col, right_col = self._split_columns_by_header(existing_section)
                    left_items = self._extract_items_by_noreg(left_col, "EXISTING_COL")
                    right_items = self._extract_items_by_noreg(right_col, "TIDAK_TERPAKAI_COL")
                    
                    if len(left_items) == 0 and len(right_items) > 0:
                        print("[SWAP] Swapping EXISTING ↔ TIDAK TERPAKAI")
                        data_perangkat["existing"] = right_items
                        data_perangkat["tidak_terpakai"] = left_items
                    else:
                        data_perangkat["existing"] = left_items
                        data_perangkat["tidak_terpakai"] = right_items
            else:
                print("[EXISTING SECTION] No No.Reg found")
                data_perangkat["existing"] = []
                data_perangkat["tidak_terpakai"] = []
        
        # ========== CABUT/PENGGANTI ==========
        cabut_section = self._extract_section_after_cabut(perangkat_text)
        
        print("\n[DEBUG] RAW CABUT SECTION:")
        print(repr(cabut_section))
        print("=" * 60)
        
        if cabut_section:
            all_items = self._extract_items_by_noreg_with_column_detect(cabut_section)
            
            if all_items:
                cabut_items = []
                pengganti_items = []
                
                for item in all_items:
                    column = item.get('column', None)
                    item_clean = {k: v for k, v in item.items() if k != 'column'}
                    
                    if column == 'left':
                        cabut_items.append(item_clean)
                    elif column == 'right':
                        pengganti_items.append(item_clean)
                
                data_perangkat["cabut"] = cabut_items
                data_perangkat["pengganti_atau_pasang_baru"] = pengganti_items
                
                print(f"✓ OCR-based extraction: CABUT={len(cabut_items)}, PENGGANTI={len(pengganti_items)}")
            else:
                print("⚠ OCR extraction failed, using fallback")
                left_col, right_col = self._split_columns_by_header(cabut_section)
                left_items = self._extract_items_by_noreg(left_col, "CABUT_COL")
                right_items = self._extract_items_by_noreg(right_col, "PENGGANTI_COL")
                
                if len(left_items) == 0 and len(right_items) > 0:
                    print("[SWAP] Swapping CABUT ↔ PENGGANTI")
                    data_perangkat["cabut"] = right_items
                    data_perangkat["pengganti_atau_pasang_baru"] = left_items
                else:
                    data_perangkat["cabut"] = left_items
                    data_perangkat["pengganti_atau_pasang_baru"] = right_items
        
        # Extract Note
        note_pattern = r'Note\s*:\s*(.+?)$'
        note_match = re.search(note_pattern, perangkat_text, re.IGNORECASE)
        if note_match:
            data_perangkat["note"] = note_match.group(1).strip()
        
        print(f"\n✓ EXISTING: {len(data_perangkat['existing'])} items")
        print(f"✓ TIDAK TERPAKAI: {len(data_perangkat['tidak_terpakai'])} items")
        print(f"✓ CABUT: {len(data_perangkat['cabut'])} items")
        print(f"✓ PENGGANTI: {len(data_perangkat['pengganti_atau_pasang_baru'])} items")
        print("="*60 + "\n")

    def _extract_section_before_cabut(self, text: str) -> str:
        """Extract section EXISTING/TIDAK TERPAKAI"""
        pattern = r'(?:EXISTING.*?)(?=\bCABUT\b|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group() if match else ""

    def _extract_section_after_cabut(self, text: str) -> str:
        """Extract section CABUT/PENGGANTI"""
        pattern = r'\bCABUT\b.*?$'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group() if match else ""

    def _split_columns_by_header(self, text: str) -> tuple:
        """Split text menjadi 2 kolom berdasarkan header 'Nama Barang'"""
        header_pattern = r'Nama\s+Barang'
        headers = list(re.finditer(header_pattern, text, re.IGNORECASE))
        
        if len(headers) < 2:
            return text, ""
        
        first_header_start = headers[0].start()
        second_header_start = headers[1].start()
        
        left_column = text[first_header_start:second_header_start]
        right_column = text[second_header_start:]
        
        return left_column.strip(), right_column.strip()

    def _extract_items_by_noreg(self, text: str, section_name: str) -> list:
        """
        Extract items dari text berdasarkan No.Reg pattern - FIXED V2
        
        Strategy:
        - Hanya ambil text BEFORE No.Reg sebagai nama barang
        - Jangan ambil text AFTER No.Reg (karena bisa jadi bagian dari item berikutnya)
        """
        items = []
        
        if not text or len(text) < 10:
            return []
        
        noreg_pattern = r'B2W[A-Z][A-Z0-9]{10,}'
        noreg_matches = list(re.finditer(noreg_pattern, text, re.IGNORECASE))
        
        if not noreg_matches:
            return []
        
        print(f"    [{section_name}] Found {len(noreg_matches)} No.Reg patterns")
        
        for i, match in enumerate(noreg_matches):
            no_reg = match.group()
            noreg_start = match.start()
            noreg_end = match.end()
            
            # FIXED V2: Only extract nama barang BEFORE No.Reg
            if i == 0:
                # First item: start from beginning (skip headers)
                nama_before_start = 0
                
                # Skip headers if they exist
                header_match = re.search(r'Nama\s+Barang', text[:noreg_start], re.IGNORECASE)
                if header_match:
                    nama_before_start = header_match.end()
            else:
                # Subsequent items: start from previous No.Reg end
                nama_before_start = noreg_matches[i-1].end()
            
            nama_before_raw = text[nama_before_start:noreg_start]
            
            # Clean nama barang
            nama_barang = self._clean_nama_barang_flexible(nama_before_raw)
            
            # Skip if too short or empty
            if not nama_barang or len(nama_barang) < 3:
                print(f"    [{section_name}] Skipping No.Reg {no_reg}: nama_barang too short ('{nama_barang}')")
                continue
            
            # FIXED V2: Check for trailing single character after No.Reg (like "B")
            trailing_char = ""
            after_noreg_snippet = text[noreg_end:noreg_end+30].strip()
            
            # Check if first character after No.Reg is a single letter
            if after_noreg_snippet and len(after_noreg_snippet) > 0:
                first_char = after_noreg_snippet[0]
                if first_char.isalpha() and (len(after_noreg_snippet) == 1 or not after_noreg_snippet[1].isalnum()):
                    trailing_char = first_char
                    print(f"    [{section_name}] Found trailing char '{trailing_char}' for {no_reg}")
            
            final_no_reg = no_reg + trailing_char
            
            items.append({
                "nama_barang": nama_barang,
                "no_reg": final_no_reg,
                "sn": ""
            })
            
            print(f"    [{section_name}] ✓ Item {i+1}: '{nama_barang}' | {final_no_reg}")
        
        return items
    
    def _extract_items_by_noreg_with_column_detect(self, text: str) -> list:
        """
        Extract items dengan automatic column detection - FIXED VERSION
        
        Strategy:
        1. Find all No.Reg positions
        2. Try spatial detection first (if OCR data available)
        3. Fallback: text-based column detection
        
        Returns:
            list of items dengan flag 'column': 'left' atau 'right'
        """
        print(f"\n    [COLUMN DETECT] Starting...")
        
        if not text or len(text) < 10:
            print(f"    [COLUMN DETECT] Text too short")
            return []
        
        noreg_pattern = r'B2W[A-Z][A-Z0-9]{10,}'
        noreg_matches = list(re.finditer(noreg_pattern, text, re.IGNORECASE))
        
        if not noreg_matches:
            print(f"    [COLUMN DETECT] No No.Reg found")
            return []
        
        print(f"    [COLUMN DETECT] Found {len(noreg_matches)} No.Reg")
        
        # Try spatial detection first
        if self.ocr_data:
            items_with_columns = self._detect_columns_by_spatial_fixed(noreg_matches, text)
            if items_with_columns:
                print(f"    [COLUMN DETECT] ✓ Success via SPATIAL method")
                return items_with_columns
        
        # Fallback: Text-based column detection
        print(f"    [COLUMN DETECT] Using TEXT-BASED method")
        return self._extract_items_text_based(noreg_matches, text)
    
    def _detect_columns_by_spatial_fixed(self, noreg_matches: list, text: str) -> list:
        """
        Detect columns menggunakan OCR bbox/position data - FIXED V8
        
        Updates V8:
        - Better handling untuk multi-line nama barang
        - Updated call to _extract_nama_barang_from_ocr with better logging
        """
        if not self.ocr_data:
            return None
        
        noreg_spatial = []
        
        for match in noreg_matches:
            no_reg_text = match.group()
            
            found = False
            for ocr_idx_scan, ocr_item in enumerate(self.ocr_data):
                if no_reg_text in ocr_item['text']:
                    bbox = ocr_item.get('bbox', [])
                    position = ocr_item.get('position', (0, 0))
                    
                    if bbox and len(bbox) == 4:
                        x_coord = bbox[0][0]
                        y_coord = bbox[0][1]
                    elif position:
                        y_coord = position[0]
                        x_coord = position[1]
                    else:
                        continue
                    
                    try:
                        x_coord = float(x_coord)
                        y_coord = float(y_coord)
                    except Exception:
                        print(f"      [SPATIAL] ⚠ Gagal konversi koordinat untuk {no_reg_text}: {bbox}")
                        continue
                    
                    # Check for trailing single character with X coordinate validation
                    trailing_char = ""
                    
                    # Only check for trailing char if No.Reg doesn't already end with a letter after digits
                    if not re.search(r'\d[A-Z]$', no_reg_text):
                        for j in range(ocr_idx_scan + 1, min(ocr_idx_scan + 5, len(self.ocr_data))):
                            next_item = self.ocr_data[j]
                            next_text = next_item['text'].strip()
                            
                            # Check if it's a single letter
                            if len(next_text) == 1 and next_text.isalpha():
                                next_bbox = next_item.get('bbox', [])
                                if next_bbox and len(next_bbox) > 0:
                                    next_y = next_bbox[0][1]
                                    next_x = next_bbox[0][0]
                                else:
                                    next_pos = next_item.get('position', (0, 0))
                                    next_y = next_pos[0]
                                    next_x = next_pos[1]
                                
                                y_distance = abs(float(next_y) - y_coord)
                                x_distance = abs(float(next_x) - x_coord)
                                
                                # Check both Y distance (<25px) AND X distance (<150px)
                                if y_distance < 25 and x_distance < 150:
                                    trailing_char = next_text
                                    print(f"      [SPATIAL] ✓ Found trailing '{trailing_char}' for {no_reg_text} (Y dist={y_distance:.1f}px, X dist={x_distance:.1f}px)")
                                    break
                    
                    # Append trailing character if found
                    final_no_reg = no_reg_text + trailing_char
                    
                    noreg_spatial.append({
                        'no_reg': final_no_reg,
                        'x_coord': x_coord,
                        'y_coord': y_coord,
                        'match': match,
                        'ocr_idx': ocr_idx_scan
                    })
                    found = True
                    break
            
            if not found:
                print(f"      [SPATIAL] No.Reg {no_reg_text} not found in OCR data")
        
        if len(noreg_spatial) < len(noreg_matches):
            print(f"      [SPATIAL] Incomplete: {len(noreg_spatial)}/{len(noreg_matches)}")
            return None
        
        if len(noreg_spatial) < 2:
            return None
        
        # Calculate X coordinate range
        x_coords = [item['x_coord'] for item in noreg_spatial]
        x_min = min(x_coords)
        x_max = max(x_coords)
        x_range = x_max - x_min
        
        print(f"      [SPATIAL] X range: {x_min:.0f} to {x_max:.0f} (range={x_range:.0f}px)")
        
        if x_range < 100:
            print(f"      [SPATIAL] Range too small, treating as single column")
            return None
        
        x_threshold = x_min + (x_range / 2)
        print(f"      [SPATIAL] X threshold: {x_threshold:.0f}px")
        
        # Classify items
        items = []
        
        for spatial_item in noreg_spatial:
            no_reg = spatial_item['no_reg']
            x_coord = spatial_item['x_coord']
            y_coord = spatial_item['y_coord']
            ocr_idx = spatial_item['ocr_idx']
            
            column = 'left' if x_coord < x_threshold else 'right'

            print(f"\n      [PROCESSING] NoReg={no_reg} at Y={y_coord:.0f}, X={x_coord:.0f}, Column={column}")
            print(f"      [PROCESSING] OCR Index={ocr_idx}")
            
            # Print OCR items dalam radius Y ±50px untuk debugging
            print(f"      [NEARBY ITEMS] Showing items within Y={y_coord-50:.0f} to Y={y_coord+60:.0f}:")
            for i, item in enumerate(self.ocr_data):
                bbox = item.get('bbox', [])
                if bbox and len(bbox) > 0:
                    item_x, item_y = bbox[0][0], bbox[0][1]
                else:
                    item_y, item_x = item.get('position', (0, 0))
                
                if (y_coord - 50) <= item_y <= (y_coord + 60):
                    print(f"        [{i:3d}] Y={item_y:6.1f} X={item_x:6.1f} | '{item['text'][:40]}'")
            
            # Extract nama barang menggunakan OCR data (UPDATED CALL)
            nama_barang = self._extract_nama_barang_from_ocr(ocr_idx, x_coord, y_coord, column, x_threshold)
            
            if not nama_barang or len(nama_barang) < 3:
                print(f"      [SPATIAL] ⚠ Skipping {no_reg}: nama_barang too short ('{nama_barang}')")
                continue
            
            items.append({
                "nama_barang": nama_barang,
                "no_reg": no_reg,
                "sn": "",
                "column": column
            })
            
            print(f"      • Spatial FINAL: '{nama_barang}' | {no_reg} | X={x_coord:.0f} → {column}")
        
        return items if items else None
    
    def _extract_nama_barang_from_ocr(self, noreg_idx: int, noreg_x: float, noreg_y: float, column: str, x_threshold: float) -> str:
        """
        Extract nama barang dari OCR data - FIXED V6 (SUPPORT MULTI-LINE AFTER NoReg)
        
        Fixes V6:
        - Explicitly scan items AFTER noreg_idx untuk capture multi-line text
        - Perbesar y_max dari 25px ke 60px
        - Add sequential scanning untuk items di bawah No.Reg
        """
        nama_parts = []
        
        # Find CLOSEST table header Y coordinate
        header_y = None
        header_candidates = []
        
        for i in range(max(0, noreg_idx - 30), noreg_idx):
            item = self.ocr_data[i]
            text = item['text'].strip().lower()
            
            if text in ['nama barang', 'no. reg', 'no.reg', 's/n']:
                bbox = item.get('bbox', [])
                if bbox and len(bbox) > 0:
                    y_coord = bbox[0][1]
                    header_candidates.append((i, y_coord, text))
        
        if header_candidates:
            header_candidates.sort(key=lambda x: x[1], reverse=True)
            header_idx, header_y, header_text = header_candidates[0]
            print(f"      [OCR EXTRACT v6] Found header '{header_text}' at index={header_idx}, Y={header_y}")
        
        # Y range - EXTENDED for multi-line support
        if header_y is not None:
            y_min = header_y + 10
        else:
            y_min = noreg_y - 50  # Extend upward
        
        y_max = noreg_y + 60  # CHANGED: Extended from 25 to 60
        
        # X range dengan batas strict
        if column == 'left':
            x_min = 0
            x_max = 400
        else:
            x_min = 600
            x_max = float('inf')
        
        print(f"      [OCR EXTRACT v6] Header Y={header_y}, NoReg Y={noreg_y:.0f}")
        print(f"      [OCR EXTRACT v6] Column={column}, Y: {y_min:.0f}-{y_max:.0f}, X: {x_min:.0f}-{x_max:.0f}")
        
        # Comprehensive blacklist
        keyword_blacklist = [
            'nama barang', 'nama', 'barang', 'no. reg', 'no.reg', 'no reg', 'no', 'reg', 's/n', 'sn',
            'cabut', 'pengganti', 'penggantl', 'pasang baru', 'existing', 'tidak terpakai',
            'jam', 'perintah', 'persiapan', 'berangkat', 'tiba', 'lokasi', 'mulai', 'selesai', 'kerja', 'pulang', 'kantor',
            'gedung', 'sub', 'mdf', 'lantai', 'ruang',
            'berkarat', 'bad', 'contact', 'putus',
            'note', 'pergantian', 'psu', 'verifikasi', 'pelaksana', 'pelanggan',
            'aug', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'sep', 'oct', 'nov', 'dec',
            'agt', 'agu', 'mei', 'okt', 'des'
        ]
        
        # ========== NEW V6: Explicitly scan items AFTER noreg_idx ==========
        print(f"      [OCR EXTRACT v6] === SCANNING ITEMS AFTER noreg_idx={noreg_idx} ===")
        
        for offset in range(1, 15):  # Scan next 15 items after No.Reg
            next_idx = noreg_idx + offset
            
            if next_idx >= len(self.ocr_data):
                break
            
            ocr_item = self.ocr_data[next_idx]
            text = ocr_item['text'].strip()
            text_lower = text.lower()
            
            # Skip empty or too short
            if not text or len(text) < 2:
                continue
            
            # Skip single character
            if len(text) == 1:
                print(f"        [SKIP AFTER] Single char: '{text}'")
                continue
            
            # Skip date/time patterns
            if re.match(r'\d{2}-[A-Za-z]{3}-\d{4}', text) or re.match(r'\d{2}:\d{2}', text):
                print(f"        [SKIP AFTER] Date/Time: '{text}'")
                continue
            
            # Skip blacklisted keywords
            if any(keyword in text_lower for keyword in keyword_blacklist):
                print(f"        [SKIP AFTER] Blacklisted: '{text}'")
                continue
            
            # Skip No.Reg patterns
            if re.match(r'B2W[A-Z][A-Z0-9]{10,}', text, re.IGNORECASE):
                print(f"        [SKIP AFTER] NoReg pattern: '{text}'")
                continue
            
            # Get coordinates
            bbox = ocr_item.get("bbox", [])
            position = ocr_item.get("position", (0, 0))
            
            if bbox and isinstance(bbox[0], (list, tuple)) and len(bbox[0]) >= 2:
                item_x = float(bbox[0][0])
                item_y = float(bbox[0][1])
            elif position and isinstance(position, (list, tuple)) and len(position) == 2:
                item_y, item_x = map(float, position)
            else:
                continue
            
            # Check Y distance from No.Reg
            y_distance = abs(item_y - noreg_y)
            
            # If too far vertically, stop scanning
            if y_distance > 60:
                print(f"        [STOP AFTER] Item too far: Y distance = {y_distance:.0f}px")
                break
            
            # Check X range (must be in same column)
            if not (x_min <= item_x <= x_max):
                print(f"        [SKIP AFTER] Wrong column: '{text}' X={item_x:.0f} (need {x_min:.0f}-{x_max:.0f})")
                continue
            
            # Check if Y is below No.Reg (we only want items AFTER/BELOW)
            if item_y < noreg_y:
                print(f"        [SKIP AFTER] Item above NoReg: '{text}' Y={item_y:.0f}")
                continue
            
            # ADD to parts
            nama_parts.append((item_y, text))
            print(f"        [ADD AFTER NoReg] Y={item_y:.0f} X={item_x:.0f} | '{text}'")
        
        print(f"      [OCR EXTRACT v6] === END SCANNING AFTER ===")
        # ========== END NEW V6 CODE ==========
        
        # ========== ORIGINAL: Scan all items in Y range (for items BEFORE No.Reg) ==========
        print(f"      [OCR EXTRACT v6] === SCANNING ALL ITEMS IN Y RANGE ===")
        
        for i, ocr_item in enumerate(self.ocr_data):
            if i == noreg_idx:
                continue
            
            # Skip items we already processed in AFTER scan
            if i > noreg_idx and i <= noreg_idx + 15:
                continue
            
            text = ocr_item['text'].strip()
            text_lower = text.lower()
            
            # Skip empty or too short
            if not text or len(text) < 2:
                continue
            
            # Skip single character
            if len(text) == 1:
                continue
            
            # Skip date/time patterns
            if re.match(r'\d{2}-[A-Za-z]{3}-\d{4}', text) or re.match(r'\d{2}:\d{2}', text):
                continue
            
            # Skip blacklisted keywords
            if any(keyword in text_lower for keyword in keyword_blacklist):
                continue
            
            # Skip No.Reg patterns
            if re.match(r'B2W[A-Z][A-Z0-9]{10,}', text, re.IGNORECASE):
                continue
            
            # Get coordinates
            bbox = ocr_item.get("bbox", [])
            position = ocr_item.get("position", (0, 0))
            
            if bbox and isinstance(bbox[0], (list, tuple)) and len(bbox[0]) >= 2:
                item_x = float(bbox[0][0])
                item_y = float(bbox[0][1])
            elif position and isinstance(position, (list, tuple)) and len(position) == 2:
                item_y, item_x = map(float, position)
            else:
                continue
            
            # Y range check
            if not (y_min <= item_y <= y_max):
                continue
            
            # X range check
            if not (x_min <= item_x <= x_max):
                continue
            
            # Add to parts (items BEFORE No.Reg)
            nama_parts.append((item_y, text))
            print(f"        [ADD BEFORE] Y={item_y:.0f} X={item_x:.0f} | '{text}'")
        
        print(f"      [OCR EXTRACT v6] === END SCANNING ALL ===")
        # ========== END ORIGINAL CODE ==========
        
        # Sort by Y coordinate and combine
        nama_parts.sort(key=lambda x: x[0])
        nama_barang = ' '.join([part[1] for part in nama_parts])
        
        print(f"      [OCR EXTRACT v6] Found {len(nama_parts)} parts")
        print(f"      [OCR EXTRACT v6] Combined: '{nama_barang}'")
        
        # Clean and return
        cleaned = self._clean_nama_barang_flexible(nama_barang)
        print(f"      [OCR EXTRACT v6] Final Result: '{cleaned}'")
        
        return cleaned

    
    def _extract_items_text_based(self, noreg_matches: list, text: str) -> list:
        """
        Fallback: Extract items using text-based column detection - FIXED v4
        
        Strategy: 
        - Item 1 (CABUT): Ambil BEFORE noreg1 + AFTER noreg1 sampai sebelum item2 mulai
        - Item 2 (PENGGANTI): Ambil AFTER noreg1 sampai noreg2 + AFTER noreg2
        """
        items = []
        
        if len(noreg_matches) != 2:
            print(f"    [TEXT-BASED] Only supports 2 items, found {len(noreg_matches)}")
            return []
        
        print(f"    [TEXT-BASED] Processing 2 items")
        
        # Find ALL "Nama Barang" headers
        header_matches = list(re.finditer(r'Nama\s+Barang', text, re.IGNORECASE))
        
        if len(header_matches) < 2:
            print(f"    [TEXT-BASED] Need 2 headers, found {len(header_matches)}")
            return []
        
        # Get positions
        left_header_end = header_matches[0].end()
        right_header_start = header_matches[1].start()
        
        noreg1_start = noreg_matches[0].start()
        noreg1_end = noreg_matches[0].end()
        noreg1_text = noreg_matches[0].group()
        
        noreg2_start = noreg_matches[1].start()
        noreg2_end = noreg_matches[1].end()
        noreg2_text = noreg_matches[1].group()
        
        print(f"    [TEXT-BASED] Left header ends: {left_header_end}")
        print(f"    [TEXT-BASED] Right header starts: {right_header_start}")
        print(f"    [TEXT-BASED] NoReg1: {noreg1_start}-{noreg1_end} = {noreg1_text}")
        print(f"    [TEXT-BASED] NoReg2: {noreg2_start}-{noreg2_end} = {noreg2_text}")
        
        # ========== ITEM 1 (CABUT - kolom kiri) ==========
        # BEFORE: dari left_header_end sampai noreg1_start
        before1 = text[left_header_end:noreg1_start]
        
        # AFTER: dari noreg1_end sampai right_header_start (awal kolom kanan)
        after1 = text[noreg1_end:right_header_start]
        
        # Combine
        combined1 = before1 + " " + after1
        
        # Clean
        combined1 = re.sub(r'No\.?\s*Reg', '', combined1, flags=re.IGNORECASE)
        combined1 = re.sub(r'S/N', '', combined1, flags=re.IGNORECASE)
        combined1 = re.sub(r'Nama\s+Barang', '', combined1, flags=re.IGNORECASE)
        combined1 = re.sub(r'B2W[A-Z][A-Z0-9]{10,}', '', combined1, flags=re.IGNORECASE)
        
        nama1 = self._clean_nama_barang_flexible(combined1)
        
        print(f"      [ITEM 1 CABUT] Before ({left_header_end}-{noreg1_start}): {repr(before1[:80])}")
        print(f"      [ITEM 1 CABUT] After ({noreg1_end}-{right_header_start}): {repr(after1[:80])}")
        print(f"      [ITEM 1 CABUT] Cleaned: {repr(nama1)}")
        
        if nama1 and len(nama1) >= 3:
            items.append({
                "nama_barang": nama1,
                "no_reg": noreg1_text,
                "sn": "",
                "column": "left"
            })
        
        # ========== ITEM 2 (PENGGANTI - kolom kanan) ==========
        # BEFORE: dari right_header_start sampai noreg2_start
        # Tapi skip bagian yang overlap dengan AFTER item1
        before2_start = max(right_header_start, noreg1_end + len(after1.strip()) + 1)
        before2 = text[right_header_start:noreg2_start]
        
        # AFTER: dari noreg2_end sampai "Note" atau akhir
        note_pos = text.find("Note", noreg2_end)
        after2_end = note_pos if note_pos > 0 else len(text)
        after2 = text[noreg2_end:after2_end]
        
        # Combine
        combined2 = before2 + " " + after2
        
        # Clean
        combined2 = re.sub(r'No\.?\s*Reg', '', combined2, flags=re.IGNORECASE)
        combined2 = re.sub(r'S/N', '', combined2, flags=re.IGNORECASE)
        combined2 = re.sub(r'Nama\s+Barang', '', combined2, flags=re.IGNORECASE)
        combined2 = re.sub(r'B2W[A-Z][A-Z0-9]{10,}', '', combined2, flags=re.IGNORECASE)
        
        # Remove "B BIVOCOM" pattern (keep only first occurrence)
        combined2 = re.sub(r'\s+B\s+BIVOCOM', '', combined2)
        
        nama2 = self._clean_nama_barang_flexible(combined2)
        
        print(f"      [ITEM 2 PENGGANTI] Before ({right_header_start}-{noreg2_start}): {repr(before2[:80])}")
        print(f"      [ITEM 2 PENGGANTI] After ({noreg2_end}-{after2_end}): {repr(after2[:80])}")
        print(f"      [ITEM 2 PENGGANTI] Cleaned: {repr(nama2)}")
        
        if nama2 and len(nama2) >= 3:
            items.append({
                "nama_barang": nama2,
                "no_reg": noreg2_text,
                "sn": "",
                "column": "right"
            })
        
        return items
    
    def _clean_nama_barang_flexible(self, text: str) -> str:
        """
        Clean nama barang dengan flexible rules - ENHANCED V2
        
        Enhancements:
        - Better handling of multi-line text
        - Remove duplicate words
        - Better whitespace normalization
        """
        
        # Remove section markers at beginning
        text = re.sub(r'^CABUT\s+PENGGANTL?/?\s*PASANG\s+BARU\s+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^CABUT\s+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^PENGGANTL?/?\s*PASANG\s+BARU\s+', '', text, flags=re.IGNORECASE)
        
        # Remove "Note:" and after
        text = re.sub(r'\s+Note\s*:.*$', '', text, flags=re.IGNORECASE)
        
        # Remove section headers
        text = re.sub(r'^C\.?DATA\s*PERANGKAT\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^EXISTING\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^TIDAK\s+TERPAKAI\s*', '', text, flags=re.IGNORECASE)
        
        # Remove ALL variations of table headers
        text = re.sub(r'Nama\s+Barang\s+(?:No\.?\s*Reg\s+)?(?:S/N\s+)?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Nama\s+Barang\s*', '', text, flags=re.IGNORECASE)
        
        # Remove standalone "No. Reg" and "S/N" (anywhere in text)
        text = re.sub(r'\bNo\.?\s*Reg\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bS/N\b', '', text, flags=re.IGNORECASE)
        
        # Normalize whitespace
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Strip
        text = text.strip()
        text = text.strip('|,.-_:;')
        
        # Remove any leaked No.Reg
        text = re.sub(r'B2W[A-Z][A-Z0-9]{10,}', '', text, flags=re.IGNORECASE)
        
        # NEW V2: Remove duplicate consecutive words
        words = text.split()
        cleaned_words = []
        prev_word = None
        
        for word in words:
            word_lower = word.lower()
            if word_lower != prev_word:
                cleaned_words.append(word)
                prev_word = word_lower
        
        text = ' '.join(cleaned_words)
        
        # Final cleanup
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _extract_single_item_ocr(self, text: str, section_name: str) -> list:
        """
        Extract SINGLE item menggunakan OCR data - FOR EXISTING SECTION
        
        Used when there's only 1 No.Reg (no need for column detection)
        """
        print(f"\n    [{section_name}] Extracting SINGLE item with OCR...")
        
        if not self.ocr_data:
            print(f"    [{section_name}] No OCR data available")
            return []
        
        # Find No.Reg
        noreg_pattern = r'B2W[A-Z][A-Z0-9]{10,}'
        noreg_matches = list(re.finditer(noreg_pattern, text, re.IGNORECASE))
        
        if len(noreg_matches) != 1:
            print(f"    [{section_name}] Expected 1 No.Reg, found {len(noreg_matches)}")
            return []
        
        no_reg_text = noreg_matches[0].group()
        print(f"    [{section_name}] No.Reg found: {no_reg_text}")
        
        # Find No.Reg in OCR data
        noreg_ocr_idx = None
        noreg_x = None
        noreg_y = None
        
        for i, ocr_item in enumerate(self.ocr_data):
            if no_reg_text in ocr_item['text']:
                bbox = ocr_item.get('bbox', [])
                position = ocr_item.get('position', (0, 0))
                
                if bbox and len(bbox) > 0 and len(bbox[0]) >= 2:
                    noreg_x = float(bbox[0][0])
                    noreg_y = float(bbox[0][1])
                elif position:
                    noreg_y = float(position[0])
                    noreg_x = float(position[1])
                else:
                    continue
                
                noreg_ocr_idx = i
                print(f"    [{section_name}] Found at OCR index {i}, Y={noreg_y:.0f}, X={noreg_x:.0f}")
                break
        
        if noreg_ocr_idx is None:
            print(f"    [{section_name}] No.Reg not found in OCR data")
            return []
        
        # Check for trailing character
        trailing_char = ""
        if not re.search(r'\d[A-Z]$', no_reg_text):
            for j in range(noreg_ocr_idx + 1, min(noreg_ocr_idx + 5, len(self.ocr_data))):
                next_item = self.ocr_data[j]
                next_text = next_item['text'].strip()
                
                if len(next_text) == 1 and next_text.isalpha():
                    next_bbox = next_item.get('bbox', [])
                    if next_bbox and len(next_bbox) > 0:
                        next_y = next_bbox[0][1]
                        next_x = next_bbox[0][0]
                    else:
                        next_pos = next_item.get('position', (0, 0))
                        next_y = next_pos[0]
                        next_x = next_pos[1]
                    
                    y_distance = abs(float(next_y) - noreg_y)
                    x_distance = abs(float(next_x) - noreg_x)
                    
                    if y_distance < 25 and x_distance < 150:
                        trailing_char = next_text
                        print(f"    [{section_name}] Found trailing '{trailing_char}'")
                        break
        
        final_no_reg = no_reg_text + trailing_char
        
        # Extract nama barang using OCR - SIMPLIFIED (no column detection needed)
        nama_barang = self._extract_nama_barang_single_item(noreg_ocr_idx, noreg_x, noreg_y)
        
        if not nama_barang or len(nama_barang) < 3:
            print(f"    [{section_name}] Nama barang too short: '{nama_barang}'")
            return []
        
        item = {
            "nama_barang": nama_barang,
            "no_reg": final_no_reg,
            "sn": ""
        }
        
        print(f"    [{section_name}] ✓ Extracted: '{nama_barang}' | {final_no_reg}")
        
        return [item]
    
    def _extract_nama_barang_single_item(self, noreg_idx: int, noreg_x: float, noreg_y: float) -> str:
        """
        Extract nama barang untuk SINGLE item - V6 WITH INDEX PROXIMITY
        
        Strategy:
        - Find section Y boundaries (header to CABUT marker)
        - Items must be NEAR No.Reg in OCR index (within ±20 indices)
        - Items must be in FAR LEFT column (X < 100)
        """
        print(f"      [SINGLE ITEM v6] Extracting at noreg_idx={noreg_idx}, Y={noreg_y:.0f}, X={noreg_x:.0f}")
        
        # === Find Y boundaries ===
        header_y = None
        for i in range(max(0, noreg_idx - 30), noreg_idx):
            item = self.ocr_data[i]
            text = item['text'].strip().lower()
            if 'nama barang' in text:
                bbox = item.get('bbox', [])
                if bbox and len(bbox) > 0:
                    header_y = bbox[0][1]
                    break
        
        cabut_y = None
        for i in range(noreg_idx, min(noreg_idx + 50, len(self.ocr_data))):
            item = self.ocr_data[i]
            text = item['text'].strip().lower()
            if text == 'cabut' or text.startswith('cabut'):
                bbox = item.get('bbox', [])
                if bbox and len(bbox) > 0:
                    cabut_y = bbox[0][1]
                    break
        
        y_min = (header_y + 15) if header_y else (noreg_y - 50)
        y_max = (cabut_y - 5) if cabut_y else (noreg_y + 80)
        
        print(f"      [SINGLE ITEM v6] Y: [{y_min:.0f}, {y_max:.0f}]")
        print(f"      [SINGLE ITEM v6] Index range: [{noreg_idx-20}, {noreg_idx+20}]")
        
        # === Collect items ===
        nama_parts = []
        
        semantic_blacklist = [
            'nama barang', 'no. reg', 'no.reg', 's/n',
            'existing', 'tidak terpakai', 'cabut', 'pengganti',
        ]
        
        print(f"      [SINGLE ITEM v6] === Scanning OCR items ===")
        
        for i, ocr_item in enumerate(self.ocr_data):
            if i == noreg_idx:
                continue
            
            # FILTER 0: Index proximity (within ±20 of No.Reg)
            index_distance = abs(i - noreg_idx)
            if index_distance > 20:
                continue
            
            text = ocr_item['text'].strip()
            text_lower = text.lower()
            
            if not text or len(text) < 3:
                continue
            
            if any(kw in text_lower for kw in semantic_blacklist):
                continue
            
            if re.match(r'B2W[A-Z][A-Z0-9]{10,}', text, re.IGNORECASE):
                continue
            
            bbox = ocr_item.get("bbox", [])
            if bbox and isinstance(bbox[0], (list, tuple)) and len(bbox[0]) >= 2:
                item_x = float(bbox[0][0])
                item_y = float(bbox[0][1])
            else:
                position = ocr_item.get("position", (0, 0))
                if position:
                    item_y, item_x = map(float, position)
                else:
                    continue
            
            # FILTER 1: Y boundaries
            if not (y_min <= item_y <= y_max):
                continue
            
            # FILTER 2: X position (FAR LEFT)
            if item_x > 100:
                continue
            
            nama_parts.append((item_y, text))
            print(f"        [ADD] idx={i} (Δ={index_distance}) Y={item_y:.0f} X={item_x:.0f} | '{text}'")
        
        nama_parts.sort(key=lambda x: x[0])
        nama_barang = ' '.join([part[1] for part in nama_parts])
        
        print(f"      [SINGLE ITEM v6] Found {len(nama_parts)} parts")
        print(f"      [SINGLE ITEM v6] Combined: '{nama_barang}'")
        
        cleaned = self._clean_nama_barang_flexible(nama_barang)
        print(f"      [SINGLE ITEM v6] Final: '{cleaned}'")
        
        return cleaned

    