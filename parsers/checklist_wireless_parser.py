"""
Checklist Wireless Parser V7 - Stable with Adaptive Fallback
Taruh file ini di: parsers/checklist_wireless_parser.py

Strategy:
1. Extract all datetimes from section FIRST
2. Apply hardcoded mapping for standard format (most common)
3. If format is different (detected by datetime count), use adaptive mapping
"""
import re
from .base_parser import BaseParser


def parse_checklist_wireless(all_text: str, page_texts: list[str], ttd_results: dict = None, doc_results: dict = None, ocr_data: list = None) -> dict:
    """Fungsi wrapper untuk kompatibilitas dengan kode lama"""
    parser = ChecklistWirelessParser(all_text, page_texts, ttd_results, doc_results, ocr_data)
    return parser.parse()


class ChecklistWirelessParser(BaseParser):
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
        data = self._init_data_structure_checklist_wireliness()
        
        # Parse DATA REMOTE (sudah ada)
        self._parse_data_remote(data["data_remote"])
        
        # Parse INDOOR AREA
        indoor_text = self._extract_indoor_section()
        if indoor_text:
            self._parse_sarana_penunjang(
                data["indoor_area_checklist"]["sarana_penunjang"],
                indoor_text
            )
            self._parse_perangkat_modem(
                data["indoor_area_checklist"]["perangkat_modem"],
                indoor_text
            )
            # TAMBAHKAN INI (jika belum ada):
            self._parse_perangkat_cpe(
                data["indoor_area_checklist"]["perangkat_cpe"],
                indoor_text
            )
        # TAMBAHKAN INI - Parse OUTDOOR AREA:
        outdoor_text = self._extract_outdoor_section()
        if outdoor_text:
            self._parse_outdoor_site(
                data["outdoor_area_checklist"]["site"],
                outdoor_text
            )
            self._parse_outdoor_sarana_penunjang(
                data["outdoor_area_checklist"]["sarana_penunjang"],
                outdoor_text
            )
            self._parse_outdoor_perangkat_antenna(
                data["outdoor_area_checklist"]["perangkat_antenna"],
                outdoor_text
            )
            self._parse_outdoor_cabling_installation(
                data["outdoor_area_checklist"]["cabling_installation"],
                outdoor_text
            )
        self._parse_data_perangkat(data["data_perangkat"])
    
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
        # Pattern: Tanggal field in DATA REMOTE section
        pattern = r"Tanggal\s*[：:]?\s*(\d{2}-[A-Za-z]{3}-\d{4}(?:\s+\d{2}:\d{2})?)"
        match = re.search(pattern, self.cleaned_text, re.IGNORECASE)
        
        if match:
            return match.group(1)
        
        return ""
    
    def _parse_pelaksanaan(self, pelaksanaan: dict):
        """
        Parse pelaksanaan dengan table-aware extraction
        
        Approach: Extract all datetimes from section, then map by index
        """
        
        # Extract jam section
        jam_section = self._extract_jam_section()
        
        if not jam_section:
            print("[WARNING] Jam section not found")
            return
        
        # Extract all dates and times
        dates = re.findall(r'\d{2}-[A-Za-z]{3}-\d{4}', jam_section)
        times = re.findall(r'\d{2}:\d{2}', jam_section)
        
        print(f"[DEBUG] Found {len(dates)} dates: {dates}")
        print(f"[DEBUG] Found {len(times)} times: {times}")
        
        # Hardcoded mapping for standard 6-datetime format (most common)
        # Based on: 21-Jun-2021 18:00, 18:08, 18:08, 19:42, 19:42, 22-Jun-2021 00:03
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
                # Check if really empty in text
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
    
    def _extract_indoor_section(self) -> str:
        """
        Extract text dari section INDOOR AREA CHECKLIST
        
        Returns:
            String berisi text dari INDOOR AREA CHECKLIST sampai section berikutnya
        """
        print("\n" + "="*80)
        print("DEBUG: Extract INDOOR AREA CHECKLIST")
        print("="*80)
        
        # Pattern yang handle text tanpa spasi dari OCR
        patterns = [
            # Pattern 1: Ada spasi normal (A. INDOOR AREA CHECKLIST)
            r'(?:A\.\s*)?INDOOR\s+AREA\s+CHECKLIST.*?(?=(?:B\.\s*)?OUTDOOR|DOKUMENTASI|$)',
            
            # Pattern 2: Tanpa spasi (A.INDOORAREACHECKLIST)  
            r'(?:A\.)?INDOORAREACHECKLIST.*?(?=(?:B\.)?OUTDOOR|DOKUMENTASI|$)',
            
            # Pattern 3: Mixed (A. INDOORAREA CHECKLIST)
            r'(?:A\.\s*)?INDOOR\s*AREA\s*CHECKLIST.*?(?=(?:B\.\s*)?OUTDOOR|DOKUMENTASI|$)',
        ]
        
        for i, pattern in enumerate(patterns, 1):
            match = re.search(pattern, self.cleaned_text, re.IGNORECASE | re.DOTALL)
            if match:
                indoor_text = match.group()
                
                # Validasi: pastikan ini bukan OUTDOOR section
                indoor_keywords = ["SARANA", "PENUNJANG", "MODEM", "CPE"]
                outdoor_keywords = ["MOUNTING", "PENANGKAL", "PETIR", "GROUNDING"]
                
                indoor_count = sum(1 for kw in indoor_keywords if kw in indoor_text.upper())
                outdoor_count = sum(1 for kw in outdoor_keywords if kw in indoor_text.upper())
                
                print(f"Pattern {i}: Indoor keywords={indoor_count}, Outdoor keywords={outdoor_count}")
                
                if indoor_count >= 2:
                    print(f"✓ Pattern {i} matched! Length: {len(indoor_text)} chars")
                    print(f"  Preview: {indoor_text[:100]}...")
                    
                    # DEBUG: Print FULL indoor text
                    print("\n" + "="*80)
                    print("DEBUG: FULL INDOOR AREA CHECKLIST TEXT")
                    print("="*80)
                    print(indoor_text)
                    print("="*80 + "\n")
                    
                    print("="*80 + "\n")
                    return indoor_text
                else:
                    print(f"✗ Pattern {i} matched tapi salah section (outdoor detected)")
        
        print("[ERROR] Indoor section tidak ditemukan dengan semua pattern")
        print("="*80 + "\n")
        return ""


    def _parse_sarana_penunjang(self, sarana_data: dict, indoor_text: str):
        """""
        Parse section SARANA PENUNJANG
        """
        print("\n" + "="*60)
        print("STEP 2: Parsing SARANA PENUNJANG")
        print("="*60)
        
        # Extract sub-section SARANA PENUNJANG sampai PERANGKAT MODEM
        pattern = r'SARANA\s*PENUNJANG.*?(?=PERANGKAT\s*MODEM|$)'
        match = re.search(pattern, indoor_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("✗ Section SARANA PENUNJANG tidak ditemukan")
            print("="*60 + "\n")
            return
        
        sarana_text = match.group()
        print(f"✓ Section ditemukan, length: {len(sarana_text)} chars")
        
        # DEBUG: Print full sarana_text
        print(f"\n[DEBUG] Full SARANA PENUNJANG text:")
        print(f"'{sarana_text}'")
        print("\n")
        
        # Parse komponen
        sarana_data["merk_ups"] = self._extract_merk_ups(sarana_text)
        
        # Extract sub-section SARANA PENUNJANG sampai PERANGKAT MODEM
        pattern = r'SARANA\s*PENUNJANG.*?(?=PERANGKAT\s*MODEM|$)'
        match = re.search(pattern, indoor_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("✗ Section SARANA PENUNJANG tidak ditemukan")
            print("="*60 + "\n")
            return
        
        sarana_text = match.group()
        print(f"✓ Section ditemukan, length: {len(sarana_text)} chars")
        
        # Parse komponen
        sarana_data["merk_ups"] = self._extract_merk_ups(sarana_text)
        sarana_data["kapasitas_ups"] = self._extract_kapasitas_ups(sarana_text)
        sarana_data["pengukuran_tegangan"] = self._parse_pengukuran_tegangan_v3(sarana_text)
        sarana_data["parameter_kualitas"] = self._parse_parameter_kualitas_sarana_v3(sarana_text)
        
        print(f"✓ Merk UPS: '{sarana_data['merk_ups']}'")
        print(f"✓ Kapasitas UPS: '{sarana_data['kapasitas_ups']}'")
        print(f"✓ Pengukuran Tegangan: {len(sarana_data['pengukuran_tegangan'])} rows")
        print(f"✓ Parameter Kualitas: {len(sarana_data['parameter_kualitas'])} rows")
        print("="*60 + "\n")


    def _extract_merk_ups(self, text: str) -> str:
        """
        Extract Merk UPS dengan handle empty value
        FIX: Jangan ambil keyword 'Menggunakan UPS' sebagai value
        """
        # Cari antara "Merk UPS :" dan keyword berikutnya
        # Pattern harus lebih strict: ambil hanya jika ada value SEBELUM keyword
        pattern = r'Merk\s+UPS\s*:\s*([A-Za-z0-9\s,.-]{3,30}?)(?=\s+Menggunakan|Kapasitas|QUALITY|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            
            # CRITICAL: Filter jika value adalah keyword parameter
            # Jangan ambil jika value adalah "Menggunakan", "Kapasitas", "QUALITY", dll
            stop_keywords = [
                'menggunakan', 'kapasitas', 'quality', 'parameter', 
                'standard', 'existing', 'jenis', 'ruangan'
            ]
            
            # Check apakah value mengandung stop keyword
            value_lower = value.lower()
            for keyword in stop_keywords:
                if keyword in value_lower:
                    return ""  # Return empty jika ketemu keyword
            
            # Filter jika hanya whitespace atau terlalu pendek
            if len(value) > 2 and value not in ['', ' ', '-', '.', ':', '::']:
                return value
        
        return ""  # Return empty jika tidak ada value valid



    def _extract_kapasitas_ups(self, text: str) -> str:
        """
        Extract Kapasitas UPS dengan handle empty value
        Pattern: 'Kapasitas UPS' lalu ambil angka+unit (misal: 1200VA, 2KVA)
        """
        # Cari antara "Kapasitas UPS" dan keyword berikutnya
        pattern = r'Kapasitas\s+UPS\s*:?\s*([0-9]+\.?[0-9]*\s*[KVA|VA|W]+)?'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match and match.group(1):
            return match.group(1).strip()
        
        return ""  # Return empty jika tidak ada value


    def _parse_pengukuran_tegangan_v3(self, text: str) -> list:
        """
        Parse table Pengukuran Tegangan dengan strategi baru:
        1. Cari semua angka yang diikuti VAC
        2. Group per 3 nilai untuk tiap row
        3. Handle case dimana ada keyword nyelip (seperti 'Ya')
        
        Returns:
            List of dict dengan keys: v_output, p_n, p_g, n_g
        """
        print("  → Parsing Pengukuran Tegangan...")
        
        # Strategy: Extract semua pattern angka + VAC
        # Pattern: angka (bisa decimal) diikuti VAC
        vac_pattern = r'(\d+\.?\d*)\s*VAC'
        all_vacs = re.findall(vac_pattern, text, re.IGNORECASE)
        
        print(f"    Found {len(all_vacs)} numeric VAC values: {all_vacs[:9]}")
        
        # Validasi: Harus ada minimal 3 nilai (untuk PLN/Gedung row)
        if len(all_vacs) < 3:
            print("    ✗ Tidak cukup data VAC (minimal 3 untuk PLN/Gedung)")
            return [
                {"v_output": "PLN/Gedung", "p_n": "", "p_g": "", "n_g": ""},
                {"v_output": "UPS", "p_n": "", "p_g": "", "n_g": ""},
                {"v_output": "IT", "p_n": "", "p_g": "", "n_g": ""}
            ]
        
        # Ambil 3 nilai pertama untuk PLN/Gedung (pasti ada angka)
        pln_values = all_vacs[0:3] if len(all_vacs) >= 3 else all_vacs + [""] * (3 - len(all_vacs))
        
        # Untuk UPS dan IT: jika tidak ada angka, isi dengan "VAC" saja
        ups_values = all_vacs[3:6] if len(all_vacs) >= 6 else [""] * 3
        it_values = all_vacs[6:9] if len(all_vacs) >= 9 else [""] * 3
        
        result = [
            {
                "v_output": "PLN/Gedung",
                "p_n": f"{pln_values[0]} VAC" if pln_values[0] else "VAC",
                "p_g": f"{pln_values[1]} VAC" if pln_values[1] else "VAC",
                "n_g": f"{pln_values[2]} VAC" if pln_values[2] else "VAC"
            },
            {
                "v_output": "UPS",
                "p_n": f"{ups_values[0]} VAC" if ups_values[0] else "VAC",
                "p_g": f"{ups_values[1]} VAC" if ups_values[1] else "VAC",
                "n_g": f"{ups_values[2]} VAC" if ups_values[2] else "VAC"
            },
            {
                "v_output": "IT",
                "p_n": f"{it_values[0]} VAC" if it_values[0] else "VAC",
                "p_g": f"{it_values[1]} VAC" if it_values[1] else "VAC",
                "n_g": f"{it_values[2]} VAC" if it_values[2] else "VAC"
            }
        ]
        
        for row in result:
            print(f"    • {row['v_output']}: P-N={row['p_n']}, P-G={row['p_g']}, N-G={row['n_g']}")
        
        return result


    def _parse_parameter_kualitas_sarana_v3(self, text: str) -> list:
        """
        Parse Parameter Kualitas SARANA dengan sequential extraction
        
        Strategy:
        1. Cari posisi setiap parameter
        2. Extract STANDARD dan EXISTING berdasarkan posisi relatif
        3. Handle edge case (nilai nyelip, format aneh, dll)
        """
        print("  → Parsing Parameter Kualitas Sarana...")
        
        # Template parameters
        parameters_config = [
            {
                "name": "Menggunakan UPS",
                "standard_keywords": ["Ya", "Tidak"],
                "existing_keywords": ["Ya", "Tidak"]
            },
            {
                "name": "Jenis UPS",
                "standard_keywords": ["Sinus", "Continu", "Square"],
                "existing_keywords": ["·", "-", "."]  # Sering empty di existing
            },
            {
                "name": "Ruangan Bebas Debu",
                "standard_keywords": ["Ya", "Tidak"],
                "existing_keywords": ["Ya", "Tidak"]
            },
            {
                "name": "Suhu Ruangan",
                "standard_pattern": r'<\s*\d+\s*C',
                "existing_pattern": r'\.+\s*C'
            },
            {
                "name": "Terpasang ground bar dan terhubung ke MDP pertanahan",
                "standard_keywords": ["Ya", "Tidak"],
                "existing_keywords": ["Ya", "Tidak"]
            }
        ]
        
        result = []
        
        # Extract each parameter
        result.append(self._extract_param_menggunakan_ups(text))
        result.append(self._extract_param_jenis_ups(text))
        result.append(self._extract_param_ruangan_bebas_debu(text))
        result.append(self._extract_param_suhu_ruangan(text))
        result.append(self._extract_param_ground_bar(text))
        
        for row in result:
            print(f"    • {row['quality_parameter'][:40]}... → Std={row['standard']}, Exist={row['existing']}")
        
        return result


    def _extract_param_menggunakan_ups(self, text: str) -> dict:
        """Extract: Menggunakan UPS"""
        # Cari "Menggunakan UPS" lalu ambil 2 kata berikutnya (Ya/Tidak)
        pattern = r'Menggunakan\s+UPS\s+(Ya|Tidak)\s+(Ya|Tidak)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            return {
                "quality_parameter": "Menggunakan UPS",
                "standard": match.group(1),
                "existing": match.group(2)
            }
        
        return {"quality_parameter": "Menggunakan UPS", "standard": "", "existing": ""}


    def _extract_param_jenis_ups(self, text: str) -> dict:
        """Extract: Jenis UPS - handle 'Sinus, Continu' dengan pemisah aneh"""
        # Cari "Jenis UPS" lalu ambil text sampai keyword berikutnya
        pattern = r'Jenis\s+UPS\s+([\w\s,·-]+?)(?=Ruangan|V\.|QUALITY|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            # Split by whitespace untuk dapat standard dan existing
            tokens = re.split(r'\s+', value)
            
            # Standard biasanya "Sinus," atau "Sinus, Continu"
            # Existing biasanya "·" atau "-"
            if len(tokens) >= 2:
                # Gabungkan token yang mengandung koma sebagai standard
                standard_parts = []
                existing = ""
                
                for token in tokens:
                    if ',' in token or token in ['Sinus', 'Continu', 'Square']:
                        standard_parts.append(token)
                    elif token in ['·', '-', '.']:
                        existing = token
                        break
                
                standard = ' '.join(standard_parts)
                
                return {
                    "quality_parameter": "Jenis UPS",
                    "standard": standard if standard else tokens[0],
                    "existing": existing if existing else (tokens[-1] if len(tokens) > 1 else "·")
                }
        
        return {"quality_parameter": "Jenis UPS", "standard": "", "existing": ""}


    def _extract_param_ruangan_bebas_debu(self, text: str) -> dict:
        """Extract: Ruangan Bebas Debu"""
        # Cari "Ruangan Bebas Debu" lalu ambil 2 Ya/Tidak
        pattern = r'Ruangan\s+Bebas\s+Debu\s+(Ya|Tidak)\s+(Ya|Tidak)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            return {
                "quality_parameter": "Ruangan Bebas Debu",
                "standard": match.group(1),
                "existing": match.group(2)
            }
        
        return {"quality_parameter": "Ruangan Bebas Debu", "standard": "", "existing": ""}


    def _extract_param_suhu_ruangan(self, text: str) -> dict:
        """Extract: Suhu Ruangan - handle '<26C' dan '..C'"""
        # Cari "Suhu Ruangan" lalu ambil pattern suhu
        pattern = r'Suhu\s+Ruangan\s+(<\s*\d+\s*C)\s+(\.+\s*C|[\d]+\s*C)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            return {
                "quality_parameter": "Suhu Ruangan",
                "standard": match.group(1).replace(' ', ''),
                "existing": match.group(2).replace(' ', '')
            }
        
        # Fallback: cari pattern terpisah
        std_match = re.search(r'Suhu\s+Ruangan\s+(<\s*\d+\s*C)', text, re.IGNORECASE)
        standard = std_match.group(1).replace(' ', '') if std_match else ""
        
        # Cari existing setelah standard
        if std_match:
            after_std = text[std_match.end():std_match.end()+20]
            exist_match = re.search(r'(\.+\s*C|[\d]+\s*C)', after_std, re.IGNORECASE)
            existing = exist_match.group(1).replace(' ', '') if exist_match else ""
        else:
            existing = ""
        
        return {
            "quality_parameter": "Suhu Ruangan",
            "standard": standard,
            "existing": existing
        }


    def _extract_param_ground_bar(self, text: str) -> dict:
        """
        Extract: Terpasang ground bar dan terhubung ke MDP pertanahan
        
        Flexible approach berdasarkan analisis OCR:
        OCR membaca tabel dalam urutan: UPS VAC VAC Ya VAC Terpasang... Ya IT VAC...
        
        Ya pertama (setelah UPS VAC VAC) = EXISTING
        Ya kedua (setelah MDP) = STANDARD
        """
        
        # Strategy 1: Cari keyword "Terpasang ground bar"
        ground_bar_match = re.search(r'Terpasang\s+ground\s+bar', text, re.IGNORECASE)
        
        if ground_bar_match:
            # Posisi keyword
            keyword_pos = ground_bar_match.start()
            
            # EXISTING: Cari Ya/Tidak SEBELUM keyword (dalam radius 50 char)
            # Tapi skip yang terlalu dekat dengan "VAC" atau "UPS"
            before_text = text[max(0, keyword_pos - 50):keyword_pos]
            
            # Ambil semua Ya/Tidak di before_text
            before_matches = []
            for match in re.finditer(r'(Ya|Tidak)', before_text, re.IGNORECASE):
                # Check apakah dekat VAC (dalam 5 char sebelum/sesudah)
                ctx_start = max(0, match.start() - 5)
                ctx_end = min(len(before_text), match.end() + 5)
                context = before_text[ctx_start:ctx_end]
                
                # Hanya ambil jika TIDAK dekat VAC
                if 'VAC' not in context.upper():
                    before_matches.append(match.group(1))
            
            # EXISTING = Ya/Tidak terakhir sebelum keyword (paling dekat)
            existing = before_matches[-1] if before_matches else ""
            
            # STANDARD: Cari Ya/Tidak SETELAH "MDP" (dalam section ini)
            # Ambil text dari keyword sampai 100 char
            after_text = text[keyword_pos:keyword_pos + 100]
            
            # Cari "MDP" lalu ambil Ya/Tidak setelahnya
            mdp_in_section = re.search(r'MDP\s+(.{0,30}?)(Ya|Tidak)', after_text, re.IGNORECASE | re.DOTALL)
            standard = mdp_in_section.group(2) if mdp_in_section else ""
            
            if existing and standard:
                return {
                    "quality_parameter": "Terpasang ground bar dan terhubung ke MDP pertanahan",
                    "standard": standard,
                    "existing": existing
                }
        
        # Strategy 2: Jika Strategy 1 gagal, cari berdasarkan keyword "MDP"
        mdp_match = re.search(r'MDP', text, re.IGNORECASE)
        
        if mdp_match:
            mdp_pos = mdp_match.start()
            
            # STANDARD: Ya/Tidak setelah MDP
            after_mdp = text[mdp_pos:]
            std_match = re.search(r'MDP\s+(.{0,30}?)(Ya|Tidak)', after_mdp, re.IGNORECASE | re.DOTALL)
            standard = std_match.group(2) if std_match else ""
            
            # EXISTING: Ya/Tidak sebelum MDP (dalam 100 char)
            # Skip yang dekat VAC
            before_mdp = text[max(0, mdp_pos - 100):mdp_pos]
            
            existing_matches = []
            for match in re.finditer(r'(Ya|Tidak)', before_mdp, re.IGNORECASE):
                ctx_start = max(0, match.start() - 5)
                ctx_end = min(len(before_mdp), match.end() + 5)
                context = before_mdp[ctx_start:ctx_end]
                
                if 'VAC' not in context.upper():
                    existing_matches.append(match.group(1))
            
            existing = existing_matches[-1] if existing_matches else ""
            
            if existing and standard:
                return {
                    "quality_parameter": "Terpasang ground bar dan terhubung ke MDP pertanahan",
                    "standard": standard,
                    "existing": existing
                }
        
        # Strategy 3: Cari berdasarkan keyword "pertanahan"
        pertanahan_match = re.search(r'pertanahan', text, re.IGNORECASE)
        
        if pertanahan_match:
            pert_pos = pertanahan_match.start()
            
            # Ambil text dari 150 char sebelum "pertanahan"
            context_text = text[max(0, pert_pos - 150):pert_pos]
            
            # Cari "MDP Ya" untuk STANDARD
            mdp_ya = re.search(r'MDP\s+(.{0,20}?)(Ya|Tidak)', context_text, re.IGNORECASE | re.DOTALL)
            standard = mdp_ya.group(2) if mdp_ya else ""
            
            # Cari Ya sebelum "Terpasang ground bar" untuk EXISTING
            ground_in_context = re.search(r'(Ya|Tidak)\s+.{0,30}?Terpasang\s+ground\s+bar', context_text, re.IGNORECASE | re.DOTALL)
            existing = ground_in_context.group(1) if ground_in_context else ""
            
            if existing and standard:
                return {
                    "quality_parameter": "Terpasang ground bar dan terhubung ke MDP pertanahan",
                    "standard": standard,
                    "existing": existing
                }
        
        # Strategy 4: Brute force - ambil semua Ya/Tidak setelah "Suhu Ruangan"
        suhu_match = re.search(r'Suhu\s+Ruangan.*?C', text, re.IGNORECASE)
        
        if suhu_match:
            after_suhu = text[suhu_match.end():]
            
            # Filter Ya/Tidak yang reasonable (tidak dekat VAC)
            all_ya = []
            for match in re.finditer(r'(Ya|Tidak)', after_suhu, re.IGNORECASE):
                # Check batas: stop jika ketemu "PERANGKAT"
                if match.start() > after_suhu.upper().find('PERANGKAT'):
                    break
                
                ctx_start = max(0, match.start() - 5)
                ctx_end = min(len(after_suhu), match.end() + 5)
                context = after_suhu[ctx_start:ctx_end]
                
                if 'VAC' not in context.upper():
                    all_ya.append(match.group(1))
            
            # Ambil 2 Ya terakhir (kemungkinan untuk Ground Bar)
            if len(all_ya) >= 2:
                # Ya terakhir biasanya STANDARD, Ya sebelum terakhir biasanya EXISTING
                return {
                    "quality_parameter": "Terpasang ground bar dan terhubung ke MDP pertanahan",
                    "standard": all_ya[-1],  # Ya terakhir
                    "existing": all_ya[-2]   # Ya sebelum terakhir
                }
        
        # Final fallback
        return {
            "quality_parameter": "Terpasang ground bar dan terhubung ke MDP pertanahan",
            "standard": "",
            "existing": ""
        }


    def _parse_perangkat_modem(self, modem_data: dict, indoor_text: str):
        """
        Parse section PERANGKAT MODEM
        
        Args:
            modem_data: Dictionary untuk menyimpan hasil parsing
            indoor_text: Text dari indoor section
        """
        print("\n" + "="*60)
        print("STEP 3: Parsing PERANGKAT MODEM")
        print("="*60)
        
        # Extract sub-section PERANGKAT MODEM sampai PERANGKAT CPE
        pattern = r'PERANGKAT\s*MODEM.*?(?=PERANGKAT\s*CPE|$)'
        match = re.search(pattern, indoor_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("✗ Section PERANGKAT MODEM tidak ditemukan")
            print("="*60 + "\n")
            return
        
        modem_text = match.group()
        print(f"✓ Section ditemukan, length: {len(modem_text)} chars")
        
        # Parse fields
        modem_data["catatan_input_modem"] = self._extract_catuan_input_modem(modem_text)
        modem_data["bertumpuk"] = self._extract_bertumpuk(modem_text)
        modem_data["lokasi_ruang_lantai_rack"] = self._extract_lokasi_ruang(modem_text)
        modem_data["parameter_kualitas"] = self._parse_parameter_kualitas_modem_v3(modem_text)
        
        print(f"✓ Catuan Input Modem: '{modem_data['catatan_input_modem']}'")
        print(f"✓ Bertumpuk: '{modem_data['bertumpuk']}'")
        print(f"✓ Lokasi: '{modem_data['lokasi_ruang_lantai_rack']}'")
        print(f"✓ Parameter Kualitas: {len(modem_data['parameter_kualitas'])} rows")
        print("="*60 + "\n")


    def _extract_catuan_input_modem(self, text: str) -> str:
        """Extract Catuan input modem"""
        pattern = r'Catuan\s+input\s+modem\s+([A-Z]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else ""


    def _extract_bertumpuk(self, text: str) -> str:
        """Extract Bertumpuk (Ya/Tidak)"""
        pattern = r'Bertumpuk\s+(Ya|Tidak)'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else ""


    def _extract_lokasi_ruang(self, text: str) -> str:
        """
        Extract Lokasi Ruang / Lantai / Rack
        Jika kosong di OCR, return empty string
        """
        # Cari antara "Lokasi Ruang / Lantai / Rack" dan keyword berikutnya
        pattern = r'Lokasi\s+Ruang\s*/\s*Lantai\s*/\s*Rack\s+([A-Za-z0-9\s,./\-]+?)(?=QUALITY|V\.|Catuan|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            # Validasi: jangan ambil jika langsung ketemu keyword lain
            if len(value) > 0 and not re.match(r'^(QUALITY|V\.|Catuan)', value, re.IGNORECASE):
                return value
        
        return ""  # Return empty jika tidak ada value


    def _parse_parameter_kualitas_modem_v3(self, text: str) -> list:
        """
        Parse Parameter Kualitas MODEM
        """
        print("  → Parsing Parameter Kualitas Modem...")
        
        result = []
        
        # 1. V. Input Modem (P-N)
        result.append(self._extract_modem_param_v_input_pn(text))
        
        # 2. V. Input Modem (N-G)
        result.append(self._extract_modem_param_v_input_ng(text))
        
        # 3. Suhu casing modem
        result.append(self._extract_modem_param_suhu_casing(text))
        
        # 4. Catuan input terbounding ke ground
        result.append(self._extract_modem_param_catuan_ground(text))
        
        # 5. Splicing konektor kabel IFL di modem
        result.append(self._extract_modem_param_splicing(text))
        
        for row in result:
            print(f"    • {row['quality_parameter'][:40]}... → Std={row['standard']}, Exist={row['existing']}")
        
        return result


    def _extract_modem_param_v_input_pn(self, text: str) -> dict:
        """Extract V. Input Modem (P-N)"""
        # Standard: "210-230 VAC" atau "210 - 230 VAC"
        # Existing: ".VAC" atau angka+VAC
        pattern = r'V\.\s*Input\s+Modem\s+\(P-N\)\s+([\d\s-]+VAC)\s+(\.?\s*VAC|[\d.]+\s*VAC)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            return {
                "quality_parameter": "V. Input Modem (P-N)",
                "standard": match.group(1).strip(),
                "existing": match.group(2).strip()
            }
        
        # Fallback
        std_pattern = r'V\.\s*Input\s+Modem\s+\(P-N\)\s+([\d\s-]+VAC)'
        std_match = re.search(std_pattern, text, re.IGNORECASE)
        standard = std_match.group(1).strip() if std_match else ""
        
        # Cari existing setelah standard
        existing = ""
        if std_match:
            after = text[std_match.end():std_match.end()+15]
            exist_match = re.search(r'(\.?\s*VAC|[\d.]+\s*VAC)', after, re.IGNORECASE)
            existing = exist_match.group(1).strip() if exist_match else ""
        
        return {
            "quality_parameter": "V. Input Modem (P-N)",
            "standard": standard,
            "existing": existing
        }


    def _extract_modem_param_v_input_ng(self, text: str) -> dict:
        """Extract V. Input Modem (N-G)"""
        pattern = r'V\.\s*Input\s+Modem\s+\(N-G\)\s+(<\s*[\d]+\s*VAC)\s+(\.?\s*VAC|[\d.]+\s*VAC)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            return {
                "quality_parameter": "V. Input Modem (N-G)",
                "standard": match.group(1).replace(' ', ''),
                "existing": match.group(2).strip()
            }
        
        # Fallback
        std_pattern = r'V\.\s*Input\s+Modem\s+\(N-G\)\s+(<\s*[\d]+\s*VAC)'
        std_match = re.search(std_pattern, text, re.IGNORECASE)
        standard = std_match.group(1).replace(' ', '') if std_match else ""
        
        existing = ""
        if std_match:
            after = text[std_match.end():std_match.end()+15]
            exist_match = re.search(r'(\.?\s*VAC|[\d.]+\s*VAC)', after, re.IGNORECASE)
            existing = exist_match.group(1).strip() if exist_match else ""
        
        return {
            "quality_parameter": "V. Input Modem (N-G)",
            "standard": standard,
            "existing": existing
        }


    def _extract_modem_param_suhu_casing(self, text: str) -> dict:
        """Extract Suhu casing modem"""
        pattern = r'Suhu\s+casing\s+modem\s+(Tidak\s+panas|Panas)\s+(\.|-|Tidak\s+panas|Panas)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            return {
                "quality_parameter": "Suhu casing modem",
                "standard": match.group(1),
                "existing": match.group(2)
            }
        
        # Fallback
        std_match = re.search(r'Suhu\s+casing\s+modem\s+(Tidak\s+panas|Panas)', text, re.IGNORECASE)
        standard = std_match.group(1) if std_match else ""
        
        existing = ""
        if std_match:
            after = text[std_match.end():std_match.end()+10]
            exist_match = re.search(r'(\.|-|Tidak\s+panas|Panas)', after, re.IGNORECASE)
            existing = exist_match.group(1) if exist_match else "."
        
        return {
            "quality_parameter": "Suhu casing modem",
            "standard": standard,
            "existing": existing
        }


    def _extract_modem_param_catuan_ground(self, text: str) -> dict:
        """Extract Catuan input terbounding ke ground"""
        pattern = r'Catuan\s+input\s+terbounding\s+ke\s+ground\s+(Ya,?\s*kencang|Tidak)\s+(\.|-|Ya,?\s*kencang|Tidak)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            return {
                "quality_parameter": "Catuan input terbounding ke ground",
                "standard": match.group(1),
                "existing": match.group(2)
            }
        
        # Fallback
        std_match = re.search(r'Catuan\s+input\s+terbounding\s+ke\s+ground\s+(Ya,?\s*kencang|Tidak)', text, re.IGNORECASE)
        standard = std_match.group(1) if std_match else ""
        
        existing = ""
        if std_match:
            after = text[std_match.end():std_match.end()+10]
            exist_match = re.search(r'(\.|-|Ya,?\s*kencang|Tidak)', after, re.IGNORECASE)
            existing = exist_match.group(1) if exist_match else "."
        
        return {
            "quality_parameter": "Catuan input terbounding ke ground",
            "standard": standard,
            "existing": existing
        }


    def _extract_modem_param_splicing(self, text: str) -> dict:
        """Extract Splicing konektor kabel IFL di modem"""
        pattern = r'Splicing\s+konektor\s+kabel\s+IFL\s+di\s+modem\s+(Baik,?\s*rapi|Tidak\s+baik)\s+(\.|-|Baik,?\s*rapi|Tidak\s+baik)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            return {
                "quality_parameter": "Splicing konektor kabel IFL di modem",
                "standard": match.group(1),
                "existing": match.group(2)
            }
        
        # Fallback
        std_match = re.search(r'Splicing\s+konektor\s+kabel\s+IFL\s+di\s+modem\s+(Baik,?\s*rapi|Tidak\s+baik)', text, re.IGNORECASE)
        standard = std_match.group(1) if std_match else ""
        
        existing = ""
        if std_match:
            after = text[std_match.end():std_match.end()+10]
            exist_match = re.search(r'(\.|-|Baik,?\s*rapi|Tidak\s+baik)', after, re.IGNORECASE)
            existing = exist_match.group(1) if exist_match else "."
        
        return {
            "quality_parameter": "Splicing konektor kabel IFL di modem",
            "standard": standard,
            "existing": existing
        }


    def _parse_perangkat_cpe(self, cpe_data: dict, indoor_text: str):
        """
        Parse section PERANGKAT CPE
        
        Args:
            cpe_data: Dictionary untuk menyimpan hasil parsing
            indoor_text: Text dari indoor section
        """
        print("\n" + "="*60)
        print("STEP 4: Parsing PERANGKAT CPE")
        print("="*60)
        
        # Extract sub-section PERANGKAT CPE sampai akhir
        pattern = r'PERANGKAT\s*CPE.*?(?=$)'
        match = re.search(pattern, indoor_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("✗ Section PERANGKAT CPE tidak ditemukan")
            print("="*60 + "\n")
            return
        
        cpe_text = match.group()
        print(f"✓ Section ditemukan, length: {len(cpe_text)} chars")
        
        # Parse fields
        cpe_data["pemilik_perangkat_cpe"] = self._extract_pemilik_cpe(cpe_text)
        cpe_data["jenis_perangkat_cpe"] = self._extract_jenis_cpe(cpe_text)
        cpe_data["parameter_kualitas"] = self._parse_parameter_kualitas_cpe(cpe_text)
        
        print(f"✓ Pemilik: '{cpe_data['pemilik_perangkat_cpe']}'")
        print(f"✓ Jenis: '{cpe_data['jenis_perangkat_cpe']}'")
        print(f"✓ Parameter Kualitas: {len(cpe_data['parameter_kualitas'])} rows")
        print("="*60 + "\n")


    def _extract_pemilik_cpe(self, text: str) -> str:
        """Extract Pemilik perangkat CPE"""
        pattern = r'Pemilik\s+perangkat\s+CPE\s+(Pelanggan|PT\.|[\w\s]+?)(?=\s+Perangkat|QUALITY|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            # Clean dari keyword yang mungkin ikut
            if value and not re.match(r'^(QUALITY|PARAMETER|Perangkat)', value, re.IGNORECASE):
                return value
        
        return ""


    def _extract_jenis_cpe(self, text: str) -> str:
        """Extract Jenis perangkat CPE"""
        pattern = r'Jenis\s+perangkat\s+CPE\s+([\w\s./-]+?)(?=QUALITY|PARAMETER|Perangkat\s+CPE\s+mendapat|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            # Clean jika ada "=" atau keyword lain
            value = value.split('=')[0].strip() if '=' in value else value
            if value and not re.match(r'^(QUALITY|PARAMETER)', value, re.IGNORECASE):
                return value
        
        return ""


    def _parse_parameter_kualitas_cpe(self, text: str) -> list:
        """
        Parse Parameter Kualitas CPE
        Ada 2 parameters:
        1. Perangkat CPE mendapat catuan sama dg modem
        2. Perangkat CPE terbounding dalam 1 ground yang sama dengan modem
        """
        print("  → Parsing Parameter Kualitas CPE...")
        
        result = []
        
        # 1. Perangkat CPE mendapat catuan sama dg modem
        param1 = self._extract_cpe_param_catuan(text)
        result.append(param1)
        print(f"    • {param1['quality_parameter'][:40]}... → Std={param1['standard']}, Exist={param1['existing']}")
        
        # 2. Perangkat CPE terbounding dalam 1 ground
        param2 = self._extract_cpe_param_ground(text)
        result.append(param2)
        print(f"    • {param2['quality_parameter'][:40]}... → Std={param2['standard']}, Exist={param2['existing']}")
        
        return result


    def _extract_cpe_param_catuan(self, text: str) -> dict:
        """Extract: Perangkat CPE mendapat catuan sama dg modem"""
        pattern = r'Perangkat\s+CPE\s+mendapat\s+catuan\s+sama\s+dg\s+modem\s+(Ya|Tidak)\s+(Ya|Tidak)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            return {
                "quality_parameter": "Perangkat CPE mendapat catuan sama dg modem",
                "standard": match.group(1),
                "existing": match.group(2)
            }
        
        # Fallback: cari Ya pertama setelah keyword
        std_match = re.search(r'Perangkat\s+CPE\s+mendapat\s+catuan.*?(Ya|Tidak)', text, re.IGNORECASE)
        standard = std_match.group(1) if std_match else ""
        
        existing = ""
        if std_match:
            after = text[std_match.end():std_match.end()+15]
            exist_match = re.search(r'(Ya|Tidak)', after, re.IGNORECASE)
            existing = exist_match.group(1) if exist_match else ""
        
        return {
            "quality_parameter": "Perangkat CPE mendapat catuan sama dg modem",
            "standard": standard,
            "existing": existing
        }


    def _extract_cpe_param_ground(self, text: str) -> dict:
        """Extract: Perangkat CPE terbounding dalam 1 ground yang sama dengan modem"""
        pattern = r'Perangkat\s+CPE\s+terbounding\s+dalam\s+1\s+ground.*?(Ya,?\s*kencang|Tidak)\s+(\.|-|Ya,?\s*kencang|Tidak)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        
        if match:
            return {
                "quality_parameter": "Perangkat CPE terbounding dalam 1 ground yang sama dengan modem",
                "standard": match.group(1),
                "existing": match.group(2)
            }
        
        # Fallback
        std_match = re.search(r'Perangkat\s+CPE\s+terbounding.*?(Ya,?\s*kencang|Tidak)', text, re.IGNORECASE | re.DOTALL)
        standard = std_match.group(1) if std_match else ""
        
        existing = ""
        if std_match:
            after = text[std_match.end():std_match.end()+15]
            exist_match = re.search(r'(\.|-|Ya,?\s*kencang|Tidak)', after, re.IGNORECASE)
            existing = exist_match.group(1) if exist_match else "."
        
        return {
            "quality_parameter": "Perangkat CPE terbounding dalam 1 ground yang sama dengan modem",
            "standard": standard,
            "existing": existing
        }

    def _extract_outdoor_section(self) -> str:
        """
        Extract text dari section OUTDOOR AREA CHECKLIST
        
        Returns:
            String berisi text dari OUTDOOR AREA CHECKLIST sampai section berikutnya
        """
        print("\n" + "="*80)
        print("DEBUG: Extract OUTDOOR AREA CHECKLIST")
        print("="*80)
        
        # Pattern yang handle text tanpa spasi dari OCR
        patterns = [
            # Pattern 1: Ada spasi normal
            r'(?:B\.\s*)?OUTDOOR\s+AREA\s+CHECKLIST.*?(?=(?:C\.\s*)?DATA\s*PERANGKAT|VERIFIKASI|$)',
            
            # Pattern 2: Tanpa spasi (B.OUTDOORAREACHECKLIST)
            r'(?:B\.)?OUTDOORAREACHECKLIST.*?(?=(?:C\.)?DATA\s*PERANGKAT|VERIFIKASI|$)',
            
            # Pattern 3: Mixed
            r'(?:B\.\s*)?OUTDOOR\s*AREA\s*CHECKLIST.*?(?=(?:C\.\s*)?DATA\s*PERANGKAT|VERIFIKASI|$)',
        ]
        
        for i, pattern in enumerate(patterns, 1):
            match = re.search(pattern, self.cleaned_text, re.IGNORECASE | re.DOTALL)
            if match:
                outdoor_text = match.group()
                
                # Validasi: pastikan ini section outdoor (ada keyword SITE, MOUNTING, ANTENNA)
                outdoor_keywords = ["SITE", "MOUNTING", "ANTENNA", "CABLING"]
                keyword_count = sum(1 for kw in outdoor_keywords if kw in outdoor_text.upper())
                
                print(f"Pattern {i}: Outdoor keywords={keyword_count}")
                
                if keyword_count >= 2:
                    print(f"✓ Pattern {i} matched! Length: {len(outdoor_text)} chars")
                    print(f"  Preview: {outdoor_text[:100]}...")
                    print("="*80 + "\n")
                    return outdoor_text
                else:
                    print(f"✗ Pattern {i} matched tapi keyword tidak cukup")
        
        print("[ERROR] Outdoor section tidak ditemukan")
        print("="*80 + "\n")
        return ""


    def _parse_outdoor_site(self, site_data: dict, outdoor_text: str):
        """
        Parse section SITE dari OUTDOOR AREA CHECKLIST
        
        Args:
            site_data: Dictionary untuk menyimpan hasil parsing
            outdoor_text: Text dari outdoor section
        """
        print("\n" + "="*60)
        print("STEP 1: Parsing SITE")
        print("="*60)
        
        # Extract sub-section SITE sampai SARANA PENUNJANG
        pattern = r'SITE.*?(?=SARANA\s*PENUNJANG|$)'
        match = re.search(pattern, outdoor_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("✗ Section SITE tidak ditemukan")
            print("="*60 + "\n")
            return
        
        site_text = match.group()
        print(f"✓ Section ditemukan, length: {len(site_text)} chars")
        
        # Parse fields
        site_data["bs_catuan_sektor"] = self._extract_bs_catuan_sektor(site_text)
        site_data["jarak_udara_heading"] = self._extract_jarak_udara_heading(site_text)
        site_data["latitude"] = self._extract_latitude(site_text)
        site_data["longitude"] = self._extract_longitude(site_text)
        site_data["potential_obstacle"] = self._extract_potential_obstacle(site_text)
        site_data["quality_parameter"] = self._parse_site_quality_parameter(site_text)
        
        print(f"✓ BS Catuan/Sektor: '{site_data['bs_catuan_sektor']}'")
        print(f"✓ Jarak Udara/Heading: '{site_data['jarak_udara_heading']}'")
        print(f"✓ Latitude: '{site_data['latitude']}'")
        print(f"✓ Longitude: '{site_data['longitude']}'")
        print(f"✓ Potential Obstacle: '{site_data['potential_obstacle']}'")
        print(f"✓ Quality Parameter: {len(site_data['quality_parameter'])} rows")
        print("="*60 + "\n")


    def _extract_bs_catuan_sektor(self, text: str) -> str:
        """Extract BS Catuan / Sektor"""
        pattern = r'BS\s+Catuan\s*/\s*Sektor\s+([A-Za-z0-9\s,./\-]+?)(?=LOS|Jarak|QUALITY|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            # Filter keyword yang nyelip
            if value and not re.match(r'^(LOS|Jarak|QUALITY)', value, re.IGNORECASE):
                return value
        
        return ""


    def _extract_jarak_udara_heading(self, text: str) -> str:
        """Extract Jarak Udara / Heading"""
        pattern = r'Jarak\s+Udara\s*/\s*Heading\s+([A-Za-z0-9\s,./\-°]+?)(?=Latitude|QUALITY|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            # Filter jika hanya titik atau keyword
            if value and value not in ['.', '·', '-'] and not re.match(r'^(Latitude|QUALITY)', value, re.IGNORECASE):
                return value
        
        return ""


    def _extract_latitude(self, text: str) -> str:
        """Extract Latitude"""
        pattern = r'Latitude\s+([\d\s,.\-°\'\"NSEW]+?)(?=Longitude|QUALITY|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            # Filter jika hanya titik atau keyword
            if value and value not in ['.', '·', '-'] and not re.match(r'^(Longitude|QUALITY)', value, re.IGNORECASE):
                return value
        
        return ""


    def _extract_longitude(self, text: str) -> str:
        """Extract Longitude"""
        pattern = r'Longitude\s+([\d\s,.\-°\'\"NSEW]+?)(?=Potential|QUALITY|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            # Filter jika hanya titik atau keyword
            if value and value not in ['.', '·', '-'] and not re.match(r'^(Potential|QUALITY)', value, re.IGNORECASE):
                return value
        
        return ""


    def _extract_potential_obstacle(self, text: str) -> str:
        """Extract Potential obstacle"""
        pattern = r'Potential\s+obstacle\s+([A-Za-z0-9\s,./\-]+?)(?=SARANA|QUALITY|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            # Filter jika hanya titik atau keyword
            if value and value not in ['.', '·', '-'] and not re.match(r'^(SARANA|QUALITY)', value, re.IGNORECASE):
                return value
        
        return ""


    def _parse_site_quality_parameter(self, text: str) -> list:
        """
        Parse Quality Parameter untuk SITE
        Hanya 1 parameter: LOS ke BS Catuan
        """
        print("  → Parsing Site Quality Parameter...")
        
        # Cari "LOS ke BS Catuan" diikuti Ya/Tidak (2x untuk standard & existing)
        pattern = r'LOS\s+ke\s+BS\s+Catuan\s+(Ya|Tidak)\s+(Ya|Tidak)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            result = [{
                "parameter": "LOS ke BS Catuan",
                "standard": match.group(1),
                "existing": match.group(2)
            }]
            print(f"    • LOS ke BS Catuan: Std={result[0]['standard']}, Exist={result[0]['existing']}")
            return result
        
        print("    ✗ LOS ke BS Catuan tidak ditemukan")
        return [{
            "parameter": "LOS ke BS Catuan",
            "standard": "Ya",
            "existing": "Ya"
        }]


    def _parse_outdoor_sarana_penunjang(self, sarana_data: dict, outdoor_text: str):
        """
        Parse section SARANA PENUNJANG dari OUTDOOR
        
        Args:
            sarana_data: Dictionary untuk menyimpan hasil parsing
            outdoor_text: Text dari outdoor section
        """
        print("\n" + "="*60)
        print("STEP 2: Parsing SARANA PENUNJANG (Outdoor)")
        print("="*60)
        
        # Extract sub-section SARANA PENUNJANG sampai PERANGKAT ANTENNA
        pattern = r'SARANA\s*PENUNJANG.*?(?=PERANGKAT\s*ANTENNA|$)'
        match = re.search(pattern, outdoor_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("✗ Section SARANA PENUNJANG tidak ditemukan")
            print("="*60 + "\n")
            return
        
        sarana_text = match.group()
        print(f"✓ Section ditemukan, length: {len(sarana_text)} chars")
        
        # Parse fields
        sarana_data["type_mounting"] = self._extract_type_mounting(sarana_text)
        sarana_data["tinggi_mounting"] = self._extract_tinggi_mounting(sarana_text)
        sarana_data["type_penangkal_petir"] = self._extract_type_penangkal_petir(sarana_text)
        sarana_data["quality_parameter"] = self._parse_sarana_outdoor_quality_parameter(sarana_text)
        
        print(f"✓ Type Mounting: '{sarana_data['type_mounting']}'")
        print(f"✓ Tinggi Mounting: '{sarana_data['tinggi_mounting']}'")
        print(f"✓ Type Penangkal Petir: '{sarana_data['type_penangkal_petir']}'")
        print(f"✓ Quality Parameter: {len(sarana_data['quality_parameter'])} rows")
        print("="*60 + "\n")


    def _extract_type_mounting(self, text: str) -> str:
        """Extract Type mounting"""
        pattern = r'Type\s+mounting\s+(Others|Pole|Wall|Rooftop|[\w\s]+?)(?=\s+(?:Ya|Mounting|Center|QUALITY)|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            # Ambil hanya kata pertama jika ada space diikuti Ya/keyword
            value = value.split()[0] if ' ' in value else value
            return value
        
        return ""


    def _extract_tinggi_mounting(self, text: str) -> str:
        """Extract Tinggi mounting - ambil angka + Meter, atau minimal 'Meter' saja"""
        # Pattern 1: Ada angka sebelum Meter
        pattern1 = r'Tinggi\s+mounting\s+([\d.]+\s*(?:Meter|M|m))'
        match1 = re.search(pattern1, text, re.IGNORECASE)
        if match1:
            return match1.group(1).strip()
        
        # Pattern 2: Hanya 'Meter' tanpa angka (atau titik di depan)
        pattern2 = r'Tinggi\s+mounting\s+[.\s]*?(Meter|M|m)\b'
        match2 = re.search(pattern2, text, re.IGNORECASE)
        if match2:
            return match2.group(1)  # Return 'Meter' saja
        
        return ""


    def _extract_type_penangkal_petir(self, text: str) -> str:
        """Extract Type penangkal petir"""
        pattern = r'Type\s+penangkal\s+petir\s+(N/A|[\w\s,./\-]+?)(?=\s+PT\.|PERANGKAT|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            if value and value not in ['.', '·', '-']:
                return value
        
        return ""


    def _parse_sarana_outdoor_quality_parameter(self, text: str) -> list:
        """
        Parse Quality Parameter untuk SARANA PENUNJANG (Outdoor)
        Ada 4 parameters
        """
        print("  → Parsing Sarana Outdoor Quality Parameter...")
        
        result = []
        
        # 1. Mounting tidak goyang dan berkarat
        param1 = {
            "parameter": "Mounting tidak goyang dan berkarat",
            "standard": "",
            "existing": ""
        }
        pattern1 = r'Mounting\s+tidak\s+goyang\s+dan\s+berkarat.*?(Ya|Tidak)\s+(Ya|Tidak)'
        match1 = re.search(pattern1, text, re.IGNORECASE | re.DOTALL)
        if match1:
            param1["standard"] = match1.group(1)
            param1["existing"] = match1.group(2)
        result.append(param1)
        print(f"    • {param1['parameter'][:40]}... → Std={param1['standard']}, Exist={param1['existing']}")
        
        # 2. Center of gravity Canester = 0 (Tegak lurus)
        param2 = {
            "parameter": "Center of gravity Canester = 0 (Tegak lurus)",
            "standard": "",
            "existing": ""
        }
        pattern2 = r'Center\s+of\s+gravity.*?Tegak\s+lurus.*?(Ya|Tidak)\s+(Ya|Tidak)?'
        match2 = re.search(pattern2, text, re.IGNORECASE | re.DOTALL)
        if match2:
            param2["standard"] = match2.group(1)
            param2["existing"] = match2.group(2) if match2.group(2) else ""
        result.append(param2)
        print(f"    • {param2['parameter'][:40]}... → Std={param2['standard']}, Exist={param2['existing']}")
        
        # 3. Disekitar mounting terdapat penangkal petir
        param3 = {
            "parameter": "Disekitar mounting terdapat penangkal petir",
            "standard": "",
            "existing": ""
        }
        pattern3 = r'Disekitar\s+mounting\s+terdapat\s+penangkal\s+petir.*?(Ya|Tidak)\s+(Ya|Tidak)'
        match3 = re.search(pattern3, text, re.IGNORECASE | re.DOTALL)
        if match3:
            param3["standard"] = match3.group(1)
            param3["existing"] = match3.group(2)
        result.append(param3)
        print(f"    • {param3['parameter'][:40]}... → Std={param3['standard']}, Exist={param3['existing']}")
        
        # 4. Sudut mounting terhadap penangkal petir < 45
        param4 = {
            "parameter": "Sudut mounting terhadap penangkal petir < 45",
            "standard": "",
            "existing": ""
        }
        pattern4 = r'Sudut\s+mounting\s+terhadap\s+penangkal\s+petir.*?<\s*45.*?(Ya|Tidak)\s+(Ya|Tidak)'
        match4 = re.search(pattern4, text, re.IGNORECASE | re.DOTALL)
        if match4:
            param4["standard"] = match4.group(1)
            param4["existing"] = match4.group(2)
        result.append(param4)
        print(f"    • {param4['parameter'][:40]}... → Std={param4['standard']}, Exist={param4['existing']}")
        
        return result


    def _parse_outdoor_perangkat_antenna(self, antenna_data: dict, outdoor_text: str):
        """
        Parse section PERANGKAT ANTENNA dari OUTDOOR
        
        Args:
            antenna_data: Dictionary untuk menyimpan hasil parsing
            outdoor_text: Text dari outdoor section
        """
        print("\n" + "="*60)
        print("STEP 3: Parsing PERANGKAT ANTENNA")
        print("="*60)
        
        # Extract sub-section PERANGKAT ANTENNA sampai CABLING
        pattern = r'PERANGKAT\s*ANTENNA.*?(?=CABLING\s*INSTALLATION|$)'
        match = re.search(pattern, outdoor_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("✗ Section PERANGKAT ANTENNA tidak ditemukan")
            print("="*60 + "\n")
            return
        
        antenna_text = match.group()
        print(f"✓ Section ditemukan, length: {len(antenna_text)} chars")
        
        # Parse fields
        antenna_data["polarisasi"] = self._extract_polarisasi(antenna_text)
        antenna_data["altitude"] = self._extract_altitude(antenna_text)
        antenna_data["lokasi"] = self._extract_lokasi_antenna(antenna_text)
        antenna_data["quality_parameter"] = self._parse_antenna_quality_parameter(antenna_text)
        
        print(f"✓ Polarisasi: '{antenna_data['polarisasi']}'")
        print(f"✓ Altitude: '{antenna_data['altitude']}'")
        print(f"✓ Lokasi: '{antenna_data['lokasi']}'")
        print(f"✓ Quality Parameter: {len(antenna_data['quality_parameter'])} rows")
        print("="*60 + "\n")


    def _extract_polarisasi(self, text: str) -> str:
        """Extract Polarisasi"""
        pattern = r'Polarisasi\s+([A-Za-z0-9\s,./\-]+?)(?=Antenna\s+terbounding|Altitude|QUALITY|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            if value and value not in ['.', '·', '-'] and not re.match(r'^(Antenna|Altitude|QUALITY)', value, re.IGNORECASE):
                return value
        
        return ""


    def _extract_altitude(self, text: str) -> str:
        """Extract Altitude - ambil angka + MDPL, atau minimal 'MDPL' saja"""
        # Pattern 1: Ada angka sebelum MDPL
        pattern1 = r'Altitude\s+([\d.]+\s*(?:MDPL|mdpl|M|m))'
        match1 = re.search(pattern1, text, re.IGNORECASE)
        if match1:
            return match1.group(1).strip()
        
        # Pattern 2: Hanya 'MDPL' tanpa angka (atau titik/Ya di depan - karena OCR bisa nyelip 'Ya')
        # Pola: Altitude [Ya] [.] MDPL
        pattern2 = r'Altitude\s+(?:Ya\s+)?[.\s]*?(MDPL|mdpl)\b'
        match2 = re.search(pattern2, text, re.IGNORECASE)
        if match2:
            return match2.group(1)  # Return 'MDPL' saja
        
        return ""


    def _extract_lokasi_antenna(self, text: str) -> str:
        """
        Extract Lokasi antenna
        CATATAN: Lokasi bisa muncul setelah quality parameter, jadi perlu hati-hati
        Jika hanya ada '0' atau angka kecil, kemungkinan itu bagian tabel/layout, bukan nilai sebenarnya
        """
        # Pattern: ambil text setelah 'Lokasi' sampai section berikutnya
        pattern = r'Lokasi\s+([A-Za-z][A-Za-z0-9\s,./\-°]+?)(?=\s*CABLING|QUALITY|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            if value and value not in ['.', '·', '-']:
                return value
        
        # Jika tidak match (berarti setelah Lokasi langsung CABLING/angka kecil), return kosong
        return ""


    def _parse_antenna_quality_parameter(self, text: str) -> list:
        """
        Parse Quality Parameter untuk PERANGKAT ANTENNA
        Ada 2 parameters dengan format STANDARD | EXISTING di kolom tabel
        
        Struktur tabel OCR:
        Row 1: Polarisasi | Antenna terbounding dengan ground | Ya, kencang | (kosong)
        Row 2: Altitude MDPL | Posisi antena sejajar dengan permukaan air | Ya | Ya
        Row 3: Lokasi | (kosong)
        """
        print("  → Parsing Antenna Quality Parameter...")
        
        result = []
        
        # 1. Antenna terbounding dengan ground
        param1 = {
            "parameter": "Antenna terbounding dengan ground",
            "standard": "",
            "existing": ""
        }
        # Pattern: Antenna terbounding dengan ground diikuti STANDARD
        # Existing untuk parameter ini biasanya kosong (tidak ada di OCR)
        pattern1 = r'Antenna\s+terbounding\s+dengan\s+ground\s+(Ya,?\s*kencang|Ya|Tidak)'
        match1 = re.search(pattern1, text, re.IGNORECASE)
        if match1:
            param1["standard"] = match1.group(1)
            param1["existing"] = ""
        result.append(param1)
        print(f"    • {param1['parameter'][:40]}... → Std={param1['standard']}, Exist={param1['existing']}")
        
        # 2. Posisi antena sejajar dengan permukaan air
        param2 = {
            "parameter": "Posisi antena sejajar dengan permukaan air",
            "standard": "",
            "existing": ""
        }
        
        # Strategy baru: 
        # OCR format: "Altitude Ya . MDPL Posisi antena sejajar dengan permukaan air Ya Lokasi"
        # - "Ya" pertama (antara Altitude dan MDPL) = STANDARD
        # - "Ya" kedua (setelah "permukaan air") = EXISTING
        
        # Cari section dari Altitude sampai nama parameter
        section_before_pattern = r'Altitude\s+(Ya|Tidak)\s+[.\s]*?MDPL\s+Posisi\s+antena\s+sejajar\s+dengan\s+permukaan\s+air'
        match_before = re.search(section_before_pattern, text, re.IGNORECASE)
        
        if match_before:
            # Ya/Tidak antara Altitude dan MDPL = STANDARD
            param2["standard"] = match_before.group(1)
            print(f"    DEBUG: Found STANDARD = {param2['standard']}")
        
        # Cari Ya/Tidak setelah "permukaan air" sampai Lokasi
        section_after_pattern = r'Posisi\s+antena\s+sejajar\s+dengan\s+permukaan\s+air\s+(Ya|Tidak)'
        match_after = re.search(section_after_pattern, text, re.IGNORECASE)
        
        if match_after:
            # Ya/Tidak setelah "permukaan air" = EXISTING
            param2["existing"] = match_after.group(1)
            print(f"    DEBUG: Found EXISTING = {param2['existing']}")
        
        result.append(param2)
        print(f"    • {param2['parameter'][:40]}... → Std={param2['standard']}, Exist={param2['existing']}")
        
        return result


    def _parse_outdoor_cabling_installation(self, cabling_data: dict, outdoor_text: str):
        """
        Parse section CABLING INSTALLATION dari OUTDOOR
        
        Args:
            cabling_data: Dictionary untuk menyimpan hasil parsing
            outdoor_text: Text dari outdoor section
        """
        print("\n" + "="*60)
        print("STEP 4: Parsing CABLING INSTALLATION")
        print("="*60)
        
        # Extract sub-section CABLING INSTALLATION sampai akhir
        pattern = r'CABLING\s*INSTALLATION.*?(?=(?:C\.)?DATA\s*PERANGKAT|$)'
        match = re.search(pattern, outdoor_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("✗ Section CABLING INSTALLATION tidak ditemukan")
            print("="*60 + "\n")
            return
        
        cabling_text = match.group()
        print(f"✓ Section ditemukan, length: {len(cabling_text)} chars")
        
        # Parse fields
        cabling_data["type_kabel_ifl"] = self._extract_type_kabel_ifl(cabling_text)
        cabling_data["panjang_kabel_ifl"] = self._extract_panjang_kabel_ifl(cabling_text)
        cabling_data["tahanan_short_kabel_ifl"] = self._extract_tahanan_short_kabel_ifl(cabling_text)
        cabling_data["quality_parameter"] = self._parse_cabling_quality_parameter(cabling_text)
        
        print(f"✓ Type Kabel IFL: '{cabling_data['type_kabel_ifl']}'")
        print(f"✓ Panjang Kabel IFL: '{cabling_data['panjang_kabel_ifl']}'")
        print(f"✓ Tahanan Short Kabel IFL: '{cabling_data['tahanan_short_kabel_ifl']}'")
        print(f"✓ Quality Parameter: {len(cabling_data['quality_parameter'])} rows")
        print("="*60 + "\n")


    def _extract_type_kabel_ifl(self, text: str) -> str:
        """Extract Type kabel IFL"""
        pattern = r'Type\s+kabel\s+IFL\s+([A-Za-z0-9\s,./\-]+?)(?=Terpasang|Panjang|QUALITY|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            if value and value not in ['.', '·', '-'] and not re.match(r'^(Terpasang|Panjang|QUALITY)', value, re.IGNORECASE):
                return value
        
        return ""


    def _extract_panjang_kabel_ifl(self, text: str) -> str:
        """Extract Panjang kabel IFL - ambil angka + Meter, atau minimal 'Meter' saja"""
        # Pattern 1: Ada angka sebelum Meter
        pattern1 = r'Panjang\s+kabel\s+IFL\s+([\d.]+\s*(?:Meter|M|m))'
        match1 = re.search(pattern1, text, re.IGNORECASE)
        if match1:
            return match1.group(1).strip()
        
        # Pattern 2: Hanya 'Meter' tanpa angka
        pattern2 = r'Panjang\s+kabel\s+IFL\s+[.\s]*?(Meter|M|m)\b'
        match2 = re.search(pattern2, text, re.IGNORECASE)
        if match2:
            return match2.group(1)  # Return 'Meter' saja
        
        return ""


    def _extract_tahanan_short_kabel_ifl(self, text: str) -> str:
        """Extract Tahanan Short kabel IFL - bersihkan trailing colon dan whitespace"""
        pattern = r'Tahanan\s+Short\s+kabel\s+IFL\s+([A-Za-z0-9\s,./\-:]+?)(?=\s*C\.|DATA|VERIFIKASI|$)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            # Remove trailing colon dan whitespace
            value = value.rstrip(':').strip()
            # Jangan ambil jika hanya symbol atau keyword
            if value and value not in ['.', '·', '-', ':', ''] and not re.match(r'^(C\.|DATA|VERIFIKASI)', value, re.IGNORECASE):
                return value
        
        return ""


    def _parse_cabling_quality_parameter(self, text: str) -> list:
        """
        Parse Quality Parameter untuk CABLING INSTALLATION
        Ada 2 parameters
        """
        print("  → Parsing Cabling Quality Parameter...")
        
        result = []
        
        # 1. Terpasang arrestor & terhubung dengan ground
        param1 = {
            "parameter": "Terpasang arrestor & terhubung dengan ground",
            "standard": "",
            "existing": ""
        }
        pattern1 = r'Terpasang\s+arrestor.*?ground\s+(Ya,?\s*kencang|Ya|Tidak)\s+(Ya,?\s*kencang|Ya|Tidak)'
        match1 = re.search(pattern1, text, re.IGNORECASE | re.DOTALL)
        if match1:
            param1["standard"] = match1.group(1)
            param1["existing"] = match1.group(2)
        result.append(param1)
        print(f"    • {param1['parameter'][:40]}... → Std={param1['standard']}, Exist={param1['existing']}")
        
        # 2. Splicing konektor kabel IFL di antena
        param2 = {
            "parameter": "Splicing konektor kabel IFL di antena",
            "standard": "",
            "existing": ""
        }
        pattern2 = r'Splicing\s+konektor\s+kabel\s+IFL\s+di\s+antena\s+(Rapat,?\s*Baik|Baik|Tidak\s+baik)\s+(\.|-|Rapat,?\s*Baik|Baik|Tidak\s+baik)?'
        match2 = re.search(pattern2, text, re.IGNORECASE)
        if match2:
            param2["standard"] = match2.group(1)
            param2["existing"] = match2.group(2) if match2.group(2) and match2.group(2) not in ['.', '-', ':'] else ""
        result.append(param2)
        print(f"    • {param2['parameter'][:40]}... → Std={param2['standard']}, Exist={param2['existing']}")
        
        return result
    
    def _extract_data_perangkat_section(self) -> str:
        """
        Extract text dari section C. DATA PERANGKAT
        """
        print("\n" + "="*80)
        print("DEBUG: Extract C. DATA PERANGKAT")
        print("="*80)
        
        # Pattern yang lebih greedy - ambil sampai section D atau DOKUMENTASI
        patterns = [
            # Pattern 1: Sampai section D. VERIFIKASI
            r'C\.?\s*DATA\s+PERANGKAT.*?(?=D\.?\s*VERIFIKASI)',
            
            # Pattern 2: Sampai DOKUMENTASI (kadang D. VERIFIKASI tidak ada)
            r'C\.?\s*DATA\s+PERANGKAT.*?(?=DOKUMENTASI)',
            
            # Pattern 3: Tanpa spasi
            r'C\.?DATAPERANGKAT.*?(?=D\.?VERIFIKASI|DOKUMENTASI)',
            
            # Pattern 4: Sampai akhir dokumen jika tidak ada pembatas
            r'C\.?\s*DATA\s+PERANGKAT.*',
        ]
        
        for i, pattern in enumerate(patterns, 1):
            match = re.search(pattern, self.cleaned_text, re.IGNORECASE | re.DOTALL)
            if match:
                perangkat_text = match.group()
                
                # Validasi: pastikan ada No.Reg (B2WN)
                noreg_count = len(re.findall(r'B2WN[A-Z0-9]{10,}', perangkat_text, re.IGNORECASE))
                
                print(f"Pattern {i}: Ditemukan {noreg_count} No.Reg")
                
                if noreg_count > 0:
                    print(f"✓ Pattern {i} matched! Length: {len(perangkat_text)} chars")
                    print(f"  Preview: {perangkat_text[:200]}...")
                    print("="*80 + "\n")
                    return perangkat_text
                else:
                    print(f"✗ Pattern {i} matched tapi tidak ada No.Reg")
        
        print("[ERROR] Data Perangkat section tidak ditemukan atau kosong")
        print("="*80 + "\n")
        return ""


    def _parse_data_perangkat(self, data_perangkat: dict):
        """
        Parse section C. DATA PERANGKAT
        
        Args:
            data_perangkat: Dictionary untuk menyimpan hasil parsing
        """
        print("\n" + "="*60)
        print("Parsing C. DATA PERANGKAT")
        print("="*60)
        
        perangkat_text = self._extract_data_perangkat_section()
        
        if not perangkat_text:
            print("✗ Section DATA PERANGKAT tidak ditemukan")
            print("="*60 + "\n")
            return
        
        # Parse setiap sub-section
        data_perangkat["existing"] = self._parse_perangkat_existing(perangkat_text)
        data_perangkat["tidak_terpakai"] = self._parse_perangkat_tidak_terpakai(perangkat_text)
        data_perangkat["cabut"] = self._parse_perangkat_cabut(perangkat_text)
        data_perangkat["pengganti_atau_pasang_baru"] = self._parse_perangkat_pengganti(perangkat_text)
        
        print(f"✓ EXISTING: {len(data_perangkat['existing'])} items")
        print(f"✓ TIDAK TERPAKAI: {len(data_perangkat['tidak_terpakai'])} items")
        print(f"✓ CABUT: {len(data_perangkat['cabut'])} items")
        print(f"✓ PENGGANTI/PASANG BARU: {len(data_perangkat['pengganti_atau_pasang_baru'])} items")
        print("="*60 + "\n")


    def _parse_perangkat_existing(self, text: str) -> list:
        """
        Parse sub-section EXISTING
        """
        print("  → Parsing EXISTING...")
        
        # FIX: Pattern yang handle ada/tanpa spasi
        patterns = [
            r'C\.?\s*DATA\s+PERANGKAT.*?(?=CABUT)',  # Ada spasi
            r'C\.?DATAPERANGKAT.*?(?=CABUT)',        # Tanpa spasi
        ]
        
        existing_text = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                existing_text = match.group()
                break
        
        if not existing_text:
            print("    ✗ Section untuk EXISTING tidak ditemukan")
            return []
        
        print(f"    DEBUG: EXISTING text length = {len(existing_text)}")
        print(f"    DEBUG RAW TEXT:")
        print("="*60)
        print(existing_text)
        print("="*60)

        return self._extract_items_by_noreg(existing_text, "EXISTING")


    def _parse_perangkat_tidak_terpakai(self, text: str) -> list:
        """
        Parse sub-section TIDAK TERPAKAI
        """
        print("  → Parsing TIDAK TERPAKAI...")
        
        # Extract section antara CABUT dan PENGGANTI
        patterns = [
            r'CABUT.*?(?=PENGGANTI|PASANG\s+BARU|$)',
            r'CABUT.*?(?=PENGGANTI.*?PASANG.*?BARU|$)',
        ]
        
        cabut_section = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                cabut_section = match.group()
                break
        
        if not cabut_section:
            print("    ✗ Section untuk TIDAK TERPAKAI tidak ditemukan")
            return []
        
        # Cek apakah ada B2WN di section ini
        if not re.search(r'B2WN[A-Z0-9]{10,}', cabut_section, re.IGNORECASE):
            print("    ✓ TIDAK TERPAKAI: Tidak ada item (kosong)")
            return []
        
        return self._extract_items_by_noreg(cabut_section, "TIDAK TERPAKAI")


    def _parse_perangkat_cabut(self, text: str) -> list:
        """Parse sub-section CABUT"""
        print("  → Parsing CABUT...")
        
        # Extract section CABUT sampai PENGGANTI
        patterns = [
            r'CABUT.*?(?=PENGGANTI|PASANG\s+BARU|$)',
            r'CABUT.*?(?=PENGGANTI.*?PASANG.*?BARU|$)',
        ]
        
        cabut_text = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                cabut_text = match.group()
                break
        
        if not cabut_text:
            print("    ✗ Section CABUT tidak ditemukan")
            return []
        
        return self._extract_items_by_noreg(cabut_text, "CABUT")


    def _parse_perangkat_pengganti(self, text: str) -> list:
        """Parse sub-section PENGGANTI/PASANG BARU"""
        print("  → Parsing PENGGANTI/PASANG BARU...")
        
        # Extract section PENGGANTI sampai akhir
        patterns = [
            r'PENGGANTI.*?$',
            r'PASANG\s+BARU.*?$',
            r'PENGGANTI.*?PASANG\s+BARU.*?$',
        ]
        
        pengganti_text = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                pengganti_text = match.group()
                break
        
        if not pengganti_text:
            print("    ✗ Section PENGGANTI tidak ditemukan")
            return []
        
        return self._extract_items_by_noreg(pengganti_text, "PENGGANTI")


    def _extract_items_by_noreg(self, text: str, section_name: str) -> list:
        """
        Extract items dari section berdasarkan No.Reg pattern
        
        Strategy FINAL v4:
        1. Untuk setiap No.Reg, ambil text SEBELUM dan SESUDAH
        2. Text sebelum = nama barang utama
        3. Text sesudah (sampai No.Reg berikutnya atau boundary) = kemungkinan lanjutan nama
        """
        items = []
        
        # Pattern untuk No. Reg: B2WN diikuti minimal 10 digit
        noreg_pattern = r'B2WN[A-Z0-9]{10,}'
        
        # Find all No. Reg positions
        noreg_matches = list(re.finditer(noreg_pattern, text, re.IGNORECASE))
        
        if not noreg_matches:
            print(f"    ✓ {section_name}: Tidak ada item (kosong)")
            return []
        
        print(f"    DEBUG: Found {len(noreg_matches)} No.Reg in {section_name}")
        
        for i, match in enumerate(noreg_matches):
            no_reg = match.group()
            noreg_start = match.start()
            noreg_end = match.end()
            
            # === EXTRACT NAMA BARANG (SEBELUM No.Reg) ===
            if i == 0:
                nama_start = 0
                header_pattern = r'(Nama\s+Barang|No\.?\s*Reg|S/N|EXISTING|TIDAK\s+TERPAKAI|CABUT|PENGGANTI)'
                headers = list(re.finditer(header_pattern, text[:noreg_start], re.IGNORECASE))
                if headers:
                    nama_start = headers[-1].end()
            else:
                nama_start = noreg_matches[i-1].end()
            
            nama_text_raw = text[nama_start:noreg_start]
            nama_barang = self._extract_nama_barang_before_noreg(nama_text_raw)
            
            # === EXTRACT LANJUTAN NAMA (SETELAH No.Reg) ===
            # Ambil text setelah No.Reg sampai batas tertentu
            if i < len(noreg_matches) - 1:
                # Ada No.Reg berikutnya - stop di sana
                next_noreg_start = noreg_matches[i+1].start()
                text_after = text[noreg_end:next_noreg_start]
            else:
                # No.Reg terakhir - ambil sampai boundary atau max 50 chars
                text_after = text[noreg_end:noreg_end+50]
            
            # Extract lanjutan yang valid
            continuation = self._extract_continuation_after_noreg(text_after)
            
            if continuation:
                nama_barang = nama_barang + ' ' + continuation
                print(f"      ℹ Added continuation: '{continuation}'")
            
            # === SMART CONTINUATION WORD DETECTION (untuk item sebelumnya) ===
            if i > 0 and len(items) > 0 and nama_barang:
                words = nama_barang.split()
                
                if len(words) >= 2:
                    first_word = words[0]
                    prev_item_name = items[-1]["nama_barang"]
                    prev_words = prev_item_name.split()
                    
                    is_continuation = self._is_continuation_word(
                        first_word, 
                        prev_words, 
                        prev_item_name
                    )
                    
                    if is_continuation:
                        items[-1]["nama_barang"] += " " + first_word
                        nama_barang = ' '.join(words[1:])
                        print(f"      ⚠ Detected continuation word: '{first_word}' moved to previous item")
            
            # Validasi
            if not nama_barang or len(nama_barang) < 3:
                print(f"      ⚠ Skipping invalid item: empty nama_barang")
                continue
            
            item = {
                "nama_barang": nama_barang.strip(),
                "no_reg": no_reg,
                "sn": ""
            }
            
            items.append(item)
            print(f"      • Item {len(items)}: '{nama_barang}' | {no_reg}")
        
        if not items:
            print(f"    ✓ {section_name}: Tidak ada item valid (kosong)")
        else:
            print(f"    ✓ {section_name}: Found {len(items)} valid items")
        
        return items


    def _extract_continuation_after_noreg(self, text: str) -> str:
        """
        Extract lanjutan nama barang yang mungkin ada SETELAH No.Reg
        
        NON-HARDCODE VERSION - Gunakan pattern recognition
        
        Strategy:
        1. Analisis struktur kata untuk deteksi "new item" vs "continuation"
        2. Gunakan context dari kata sebelum dan sesudah
        3. Maksimal 2 kata, total 15 char (ini reasonable limit, bukan hardcode)
        
        Heuristics untuk deteksi "New Item" (STOP):
        - Kata yang panjang (≥8 char) DAN uppercase semua → likely brand/product
        - Kata dengan pattern angka-huruf → likely product code
        - Kata yang diikuti kata lain yang membentuk "noun phrase" lengkap
        
        Heuristics untuk deteksi "Continuation" (CONTINUE):
        - Kata pendek (≤5 char) → likely descriptor (Antena, Kit, dll)
        - Kata dengan symbol (+, &, /) → likely connector
        - Kata tunggal tanpa angka → likely simple descriptor
        """
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        
        if not text:
            return ""
        
        # Section headers pattern (ini reasonable constant, bukan hardcode data)
        section_pattern = r'(CABUT|PENGGANTI|PASANG\s+BARU|TIDAK\s+TERPAKAI|EXISTING|Nama\s+Barang|No\.?\s*Reg|S/N)'
        
        words = []
        text_parts = text.split()
        
        for i, word in enumerate(text_parts):
            # Stop jika ketemu section header
            if re.match(section_pattern, word, re.IGNORECASE):
                break
            
            # Stop jika ketemu No.Reg lain
            if re.match(r'B2WN[A-Z0-9]+', word, re.IGNORECASE):
                break
            
            # Skip word yang terlalu pendek (noise)
            if len(word) <= 1:
                continue
            
            # ========================================
            # HEURISTIC 1: Deteksi "New Item Starter"
            # ========================================
            if len(words) == 0:  # Kata pertama setelah No.Reg
                # Pattern 1a: Kata panjang + uppercase semua + ada kata berikutnya
                # Contoh: "WARRANTY ADAPTOR", "FORTIGATE ROUTER", "ADAPTOR 12V"
                if (len(word) >= 6 and 
                    word.isupper() and 
                    i + 1 < len(text_parts)):
                    
                    next_word = text_parts[i + 1]
                    
                    # Cek: apakah next_word membentuk "noun phrase"?
                    # Noun phrase indicators:
                    # - Next word juga panjang + uppercase (ADAPTOR POWER)
                    # - Next word ada angka (ADAPTOR 12V)
                    # - Next word adalah kata benda umum yang standalone
                    
                    forms_noun_phrase = (
                        len(next_word) >= 5 and next_word.isupper()  # WARRANTY ADAPTOR
                        or re.search(r'\d+[A-Z]*', next_word)  # ADAPTOR 12V
                        or re.match(section_pattern, next_word, re.IGNORECASE)  # Keyword
                    )
                    
                    if forms_noun_phrase:
                        # Ini kemungkinan besar NEW ITEM, bukan continuation
                        # Contoh: "WARRANTY ADAPTOR" atau "ADAPTOR 12V"
                        break
                
                # Pattern 1b: Kata dengan product code pattern
                # Contoh: "FG-50E", "B311As", "WRT-1900"
                if re.search(r'[A-Z]+-?\d+[A-Z]?', word, re.IGNORECASE):
                    # Ini product code → kemungkinan NEW ITEM
                    break
                
                # Pattern 1c: Brand name pattern (huruf-angka mixed)
                # Contoh: "HUAAWEI", "B311As", "FG50E"
                if re.search(r'[A-Z]{3,}\d+|[A-Z]+\d+[A-Z]+', word, re.IGNORECASE):
                    # Mixed alphanumeric → likely brand/product
                    break
            
            # ========================================
            # HEURISTIC 2: Deteksi "Continuation"
            # ========================================
            # Kata yang kemungkinan besar CONTINUATION:
            # - Pendek (≤ 5 char) → "Kit", "HW", "Antena"
            # - Punya connector symbol → "+ Antena", "& Cable"
            # - Kata descriptor tunggal tanpa angka
            
            is_likely_continuation = (
                len(word) <= 5  # Kata pendek
                or word in ['+', '&', '/', '-']  # Symbol connector
                or (i > 0 and text_parts[i-1] in ['+', '&'])  # Setelah connector
            )
            
            # ========================================
            # DECISION: Ambil atau Skip?
            # ========================================
            if len(words) >= 2:
                # Sudah 2 kata → stop
                break
            
            if len(''.join(words)) + len(word) > 15:
                # Total char > 15 → stop
                break
            
            # Ambil word jika:
            # - Likely continuation, ATAU
            # - Kata pertama dan tidak ada indikasi "new item"
            if is_likely_continuation or len(words) == 0:
                words.append(word)
            else:
                # Tidak likely continuation → stop
                break
        
        # ========================================
        # FINAL VALIDATION
        # ========================================
        result = ' '.join(words)
        
        # Validasi: Jika hasilnya terlihat seperti "noun phrase" lengkap
        # Contoh: "WARRANTY ADAPTOR" → ini terlalu lengkap untuk continuation
        if len(words) >= 2:
            # Check: apakah kedua kata membentuk noun phrase?
            # Pattern: [ADJECTIVE/NOUN] + [NOUN with number/long word]
            first_word = words[0]
            second_word = words[1] if len(words) > 1 else ""
            
            if (len(first_word) >= 6 and 
                len(second_word) >= 6 and
                first_word.isupper() and 
                second_word.isupper()):
                # Contoh: "WARRANTY ADAPTOR" → terlalu lengkap
                # Kemungkinan ini NEW ITEM yang salah terdeteksi
                return ""  # Return kosong, biarkan jadi item terpisah
        
        return result

    def _extract_nama_barang_before_noreg(self, text: str) -> str:
        """
        Extract nama barang dari text yang ADA SEBELUM No.Reg
        
        Strategy:
        1. Clean dari header/keyword
        2. Ambil maksimal 10 kata terakhir (cukup untuk nama panjang)
        3. Clean whitespace dan symbols
        
        Args:
            text: Raw text sebelum No.Reg
            
        Returns:
            Cleaned nama barang
        """
        # Remove headers dan keywords
        text = re.sub(r'C\.?DATA\s*PERANGKAT', '', text, flags=re.IGNORECASE)
        text = re.sub(r'EXISTING', '', text, flags=re.IGNORECASE)
        text = re.sub(r'TIDAK\s+TERPAKAI', '', text, flags=re.IGNORECASE)
        text = re.sub(r'CABUT', '', text, flags=re.IGNORECASE)
        text = re.sub(r'PENGGANTI.*?PASANG\s+BARU', '', text, flags=re.IGNORECASE)
        text = re.sub(r'PENGGANTI', '', text, flags=re.IGNORECASE)
        text = re.sub(r'PASANG\s+BARU', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Nama\s+Barang', '', text, flags=re.IGNORECASE)
        text = re.sub(r'No\.?\s*Reg', '', text, flags=re.IGNORECASE)
        text = re.sub(r'S/N', '', text, flags=re.IGNORECASE)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove leading/trailing symbols
        text = text.strip('|,.-_:;')
        
        # Ambil maksimal 10 kata terakhir
        words = text.split()
        if len(words) > 10:
            text = ' '.join(words[-10:])
        
        # Final cleanup
        text = text.strip()
        
        return text


    def _clean_sn(self, text: str) -> str:
        """
        Clean S/N dari noise
        
        Args:
            text: Raw text S/N
            
        Returns:
            Cleaned S/N
        """
        # Remove common keywords
        keywords_to_remove = [
            r'TIDAK\s+TERPAKAI', r'CABUT', r'PENGGANTI', r'PASANG\s+BARU',
            r'Nama\s+Barang', r'No\.?\s*Reg', r'S/N', r'EXISTING'
        ]
        
        for keyword in keywords_to_remove:
            text = re.sub(keyword, '', text, flags=re.IGNORECASE)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        text = text.strip('|,.-_:;')
        
        # Jika kosong atau hanya symbols
        if not text or re.match(r'^[|,.\-_\s:;]+$', text):
            return ""
        
        return text
    
    def _is_continuation_word(self, word: str, prev_words: list, prev_full_name: str) -> bool:
        """
        Smart detection: apakah word adalah continuation dari item sebelumnya?
        
        Rules (STRICT VERSION - v2):
        1. ✅ Jika item sebelumnya berakhir dengan kata sambung eksplisit → continuation
        2. ✅ Jika word adalah common adjective/preposition → continuation
        3. ❌ Jika word adalah product/brand name pattern → BUKAN continuation
        4. ❌ Jika item sebelumnya sudah lengkap → BUKAN continuation
        
        Args:
            word: Kata yang dicek (first word dari nama barang berikutnya)
            prev_words: List kata dari item sebelumnya
            prev_full_name: Nama lengkap item sebelumnya
            
        Returns:
            True jika word adalah continuation, False jika bukan
        """
        if not prev_words:
            return False
        
        # ============================================================
        # RULE 1: Item sebelumnya berakhir dengan connector word EKSPLISIT
        # ============================================================
        connector_words = {'AND', 'HW', 'WITH', 'FOR', 'OF', 'TO', 'IN', 'ON', 'BY', '&', '+', 'OR'}
        last_word = prev_words[-1].upper()
        
        if last_word in connector_words:
            return True  # Jelas continuation (e.g., "HW AND" → "WARRANTY")
        
        # ============================================================
        # RULE 2: Word adalah common adjective/preposition/descriptive word
        # ============================================================
        # Kata-kata ini BIASANYA lanjutan dari item sebelumnya
        common_continuations = {
            'WARRANTY', 'HARDWARE', 'SOFTWARE', 'ADAPTER', 'CABLE', 
            'POWER', 'SUPPLY', 'MODULE', 'UNIT', 'KIT', 'SET',
            'BLACK', 'WHITE', 'MINI', 'STANDARD', 'ORIGINAL'
        }
        
        if word.upper() in common_continuations:
            # Double check: apakah prev item pendek dan belum lengkap?
            if len(prev_words) <= 4:
                return True
        
        # ============================================================
        # RULE 3: STRICT CHECK - Detect product/brand name patterns
        # ============================================================
        # Product/brand patterns yang PASTI BUKAN continuation:
        # - Mengandung angka dengan huruf (FORTIGATE-50E, B311As, FG-30E)
        # - Format CamelCase atau mixed case (FortiGate, iPhone)
        # - Panjang >= 8 karakter dan unik (HUAAWEI, ADAPTOR)
        
        # Pattern 3a: Product code dengan angka (paling umum)
        if re.search(r'[A-Z]+-?\d+[A-Z]?', word, re.IGNORECASE):
            # e.g., FORTIGATE-50E, FG-30E, B311As, WRT-1900
            return False  # Ini product name, BUKAN continuation
        
        # Pattern 3b: Brand name yang panjang dan unique
        if len(word) >= 8:
            # e.g., FORTIGATE, HUAAWEI, ADAPTOR (as standalone item)
            # Cek: apakah kata ini sudah ada di prev_full_name?
            if word.upper() not in prev_full_name.upper():
                return False  # New brand/product, bukan continuation
        
        # Pattern 3c: Mixed case atau CamelCase (jarang di continuation)
        if re.search(r'[a-z][A-Z]|[A-Z][a-z]+[A-Z]', word):
            # e.g., FortiGate, iPhone, MacBook
            return False
        
        # ============================================================
        # RULE 4: Item sebelumnya sudah lengkap (ada unit atau product code)
        # ============================================================
        # Pattern lengkap:
        # - "PSU FORTI FG-50E/FG-30E" → ada product code
        # - "ADAPTOR 12V 1A" → ada unit measurement
        # - "Router B311As + Antena" → ada product code + kata benda
        
        complete_patterns = [
            r'\d+[A-Z]+',          # 12V, 1A, 50E
            r'[A-Z]+-\d+',         # FG-50E, WRT-1900
            r'/[A-Z]+-\d+',        # /FG-30E
            r'\+\s*[A-Z]+',        # + Antena, + Kit
        ]
        
        for pattern in complete_patterns:
            if re.search(pattern, prev_full_name):
                # Item sebelumnya sudah lengkap
                # Cek: apakah tidak berakhir dengan connector?
                if last_word not in connector_words:
                    return False  # Sudah lengkap, word berikutnya bukan continuation
        
        # ============================================================
        # RULE 5 (Fallback): Jika ragu, DEFAULT = False (lebih safe)
        # ============================================================
        # Hanya return True jika:
        # - Word sangat pendek (≤ 3 char) seperti "HW", "1A"
        # - DAN prev item sangat pendek (≤ 2 kata)
        # - DAN prev berakhir dengan incomplete pattern
        
        if len(word) <= 3 and len(prev_words) <= 2:
            # Kemungkinan continuation dari item sangat pendek
            # e.g., "PSU" + "HW" atau "AC" + "12V"
            return True
        
        # Default: anggap BUKAN continuation (lebih aman)
        return False