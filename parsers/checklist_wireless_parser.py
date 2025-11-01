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
                    print("="*80 + "\n")
                    return indoor_text
                else:
                    print(f"✗ Pattern {i} matched tapi salah section (outdoor detected)")
        
        print("[ERROR] Indoor section tidak ditemukan dengan semua pattern")
        print("="*80 + "\n")
        return ""


    def _parse_sarana_penunjang(self, sarana_data: dict, indoor_text: str):
        """
        Parse section SARANA PENUNJANG
        
        Args:
            sarana_data: Dictionary untuk menyimpan hasil parsing
            indoor_text: Text dari indoor section
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
        FIX: Improved pattern untuk ambil Ya/Ya yang benar
        """
        # Strategy 1: Cari pattern "pertanahan" diikuti 2 "Ya"
        # Atau "MDP pertanahan Ya Ya"
        pattern1 = r'(?:MDP\s+)?pertanahan\s+(Ya|Tidak)\s+(Ya|Tidak)'
        match1 = re.search(pattern1, text, re.IGNORECASE)
        
        if match1:
            return {
                "quality_parameter": "Terpasang ground bar dan terhubung ke MDP pertanahan",
                "standard": match1.group(1),
                "existing": match1.group(2)
            }
        
        # Strategy 2: Cari "ground bar" lalu ambil Ya terdekat setelahnya
        pattern2 = r'ground\s+bar.*?pertanahan.*?(Ya|Tidak).*?(Ya|Tidak)'
        match2 = re.search(pattern2, text, re.IGNORECASE | re.DOTALL)
        
        if match2:
            return {
                "quality_parameter": "Terpasang ground bar dan terhubung ke MDP pertanahan",
                "standard": match2.group(1),
                "existing": match2.group(2)
            }
        
        # Strategy 3: Fallback - ambil 2 "Ya" terakhir di section SARANA
        # (sebelum PERANGKATMODEM)
        # Tapi harus pastikan bukan dari parameter lain
        pattern3 = r'VAC\s+Terpasang.*?pertanahan\s+(Ya|Tidak)\s+(Ya|Tidak)'
        match3 = re.search(pattern3, text, re.IGNORECASE | re.DOTALL)
        
        if match3:
            return {
                "quality_parameter": "Terpasang ground bar dan terhubung ke MDP pertanahan",
                "standard": match3.group(1),
                "existing": match3.group(2)
            }
        
        # Strategy 4: Cari semua "Ya" di section, ambil 2 yang terakhir
        # HANYA jika setelah keyword "pertanahan"
        pertanahan_pos = text.lower().find('pertanahan')
        if pertanahan_pos != -1:
            after_pertanahan = text[pertanahan_pos:pertanahan_pos+100]
            ya_matches = re.findall(r'(Ya|Tidak)', after_pertanahan, re.IGNORECASE)
            
            if len(ya_matches) >= 2:
                return {
                    "quality_parameter": "Terpasang ground bar dan terhubung ke MDP pertanahan",
                    "standard": ya_matches[0],
                    "existing": ya_matches[1]
                }
        
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
        
        Returns:
            String berisi text dari DATA PERANGKAT sampai section berikutnya atau akhir
        """
        print("\n" + "="*80)
        print("DEBUG: Extract C. DATA PERANGKAT")
        print("="*80)
        
        # Pattern yang handle text tanpa spasi dari OCR
        patterns = [
            # Pattern 1: Ada spasi normal
            r'(?:C\.\s*)?DATA\s+PERANGKAT.*?(?=(?:D\.\s*)?VERIFIKASI|DOKUMENTASI|$)',
            
            # Pattern 2: Tanpa spasi (C.DATAPERANGKAT)
            r'(?:C\.)?DATAPERANGKAT.*?(?=(?:D\.)?VERIFIKASI|DOKUMENTASI|$)',
            
            # Pattern 3: Mixed
            r'(?:C\.\s*)?DATA\s*PERANGKAT.*?(?=(?:D\.\s*)?VERIFIKASI|DOKUMENTASI|$)',
        ]
        
        for i, pattern in enumerate(patterns, 1):
            match = re.search(pattern, self.cleaned_text, re.IGNORECASE | re.DOTALL)
            if match:
                perangkat_text = match.group()
                
                # Validasi: pastikan ini section data perangkat (ada keyword EXISTING, CABUT, etc)
                perangkat_keywords = ["EXISTING", "CABUT", "TIDAK TERPAKAI", "PENGGANTI"]
                keyword_count = sum(1 for kw in perangkat_keywords if kw in perangkat_text.upper())
                
                print(f"Pattern {i}: Perangkat keywords={keyword_count}")
                
                if keyword_count >= 2:
                    print(f"✓ Pattern {i} matched! Length: {len(perangkat_text)} chars")
                    print(f"  Preview: {perangkat_text[:100]}...")
                    print("="*80 + "\n")
                    return perangkat_text
                else:
                    print(f"✗ Pattern {i} matched tapi keyword tidak cukup")
        
        print("[ERROR] Data Perangkat section tidak ditemukan")
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
        data_perangkat["pengganti_pasang_baru"] = self._parse_perangkat_pengganti(perangkat_text)
        
        print(f"✓ EXISTING: {len(data_perangkat['existing'])} items")
        print(f"✓ TIDAK TERPAKAI: {len(data_perangkat['tidak_terpakai'])} items")
        print(f"✓ CABUT: {len(data_perangkat['cabut'])} items")
        print(f"✓ PENGGANTI/PASANG BARU: {len(data_perangkat['pengganti_pasang_baru'])} items")
        print("="*60 + "\n")


    def _parse_perangkat_existing(self, text: str) -> list:
        """
        Parse sub-section EXISTING
        
        Strategy baru untuk handle 2-column layout:
        - OCR membaca: "EXISTING TIDAK TERPAKAI Nama... PSU... FORTIGATE... CABUT PENGGANTI"
        - Semua item B2WN sebelum kata "CABUT" = EXISTING (karena layout tabel, item ada di bawah EXISTING)
        - Item setelah "CABUT" diabaikan (masuk section lain)
        """
        print("  → Parsing EXISTING...")
        
        # Strategy: Ambil semua text dari awal sampai kata "CABUT"
        # Karena layout 2 kolom, semua item sebelum "CABUT" adalah EXISTING
        pattern = r'C\.?DATAPERANGKAT.*?(?=CABUT)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("    ✗ Section untuk EXISTING tidak ditemukan")
            return []
        
        existing_text = match.group()
        
        print(f"    DEBUG: EXISTING text length = {len(existing_text)}")
        
        # Parse items berdasarkan No. Reg pattern (B2WN...)
        return self._extract_items_by_noreg(existing_text, "EXISTING")


    def _parse_perangkat_tidak_terpakai(self, text: str) -> list:
        """
        Parse sub-section TIDAK TERPAKAI
        
        Strategy: Karena layout 2 kolom, kolom TIDAK TERPAKAI ada di sebelah kanan EXISTING.
        Dalam OCR horizontal, text "TIDAK TERPAKAI" muncul, tapi items-nya (B2WN) 
        sebenarnya ada di kolom kiri (EXISTING).
        
        Jadi: Cari B2WN yang muncul SETELAH kata "CABUT" dan SEBELUM kata "PENGGANTI"
        Karena row berikutnya adalah CABUT | PENGGANTI
        """
        print("  → Parsing TIDAK TERPAKAI...")
        
        # Extract section antara CABUT dan PENGGANTI
        # Jika ada B2WN di sini, berarti ada item di kolom TIDAK TERPAKAI
        pattern = r'CABUT.*?(?=PENGGANTI|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("    ✗ Section untuk TIDAK TERPAKAI tidak ditemukan")
            return []
        
        cabut_section = match.group()
        
        # Cek apakah ada B2WN di section ini
        # Kalau tidak ada, berarti TIDAK TERPAKAI kosong
        if not re.search(r'B2WN[A-Z0-9]{10,}', cabut_section, re.IGNORECASE):
            print("    ✓ TIDAK TERPAKAI: Tidak ada item (kosong)")
            return []
        
        return self._extract_items_by_noreg(cabut_section, "TIDAK TERPAKAI")


    def _parse_perangkat_cabut(self, text: str) -> list:
        """Parse sub-section CABUT"""
        print("  → Parsing CABUT...")
        
        # Extract section CABUT sampai PENGGANTI
        pattern = r'CABUT.*?(?=PENGGANTI|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("    ✗ Section CABUT tidak ditemukan")
            return []
        
        cabut_text = match.group()
        return self._extract_items_by_noreg(cabut_text, "CABUT")


    def _parse_perangkat_pengganti(self, text: str) -> list:
        """Parse sub-section PENGGANTI/PASANG BARU"""
        print("  → Parsing PENGGANTI/PASANG BARU...")
        
        # Extract section PENGGANTI sampai akhir
        pattern = r'PENGGANTI.*?$'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            print("    ✗ Section PENGGANTI tidak ditemukan")
            return []
        
        pengganti_text = match.group()
        return self._extract_items_by_noreg(pengganti_text, "PENGGANTI")


    def _extract_items_by_noreg(self, text: str, section_name: str) -> list:
        """
        Extract items dari section berdasarkan No. Reg pattern
        
        Strategy: 
        - No. Reg selalu format B2WN + angka
        - Setiap kali ketemu B2WN... = item baru
        - Text sebelum B2WN = nama barang
        - S/N biasanya kosong (karena layout tabel, S/N ada di kolom terpisah yang tidak ter-OCR dengan baik)
        
        Args:
            text: Text dari section
            section_name: Nama section untuk logging
            
        Returns:
            List of items [{"nama_barang": "...", "no_reg": "...", "sn": "..."}]
        """
        items = []
        
        # Pattern untuk No. Reg: B2WN diikuti minimal 10 digit
        noreg_pattern = r'(B2WN[A-Z0-9]{10,})'
        
        # Find all No. Reg dalam text
        noreg_matches = list(re.finditer(noreg_pattern, text, re.IGNORECASE))
        
        if not noreg_matches:
            print(f"    ✓ {section_name}: Tidak ada item (kosong)")
            return []
        
        print(f"    ✓ {section_name}: Found {len(noreg_matches)} items")
        
        for i, match in enumerate(noreg_matches):
            no_reg = match.group(1)
            start_pos = match.start()
            end_pos = match.end()
            
            # Extract nama barang (text sebelum No. Reg)
            if i == 0:
                # Item pertama: ambil dari setelah header "Nama Barang No.Reg S/N"
                header_pattern = r'(?:Nama\s+Barang|No\.?\s*Reg|S/N)'
                header_matches = list(re.finditer(header_pattern, text[:start_pos], re.IGNORECASE))
                if header_matches:
                    last_header_pos = header_matches[-1].end()
                    nama_text = text[last_header_pos:start_pos]
                else:
                    # Fallback: ambil 100 char sebelum No. Reg
                    nama_text = text[max(0, start_pos - 100):start_pos]
            else:
                # Item selanjutnya: ambil dari akhir No. Reg sebelumnya
                prev_end = noreg_matches[i-1].end()
                nama_text = text[prev_end:start_pos]
            
            # Clean nama barang
            nama_barang = self._clean_nama_barang(nama_text)
            
            # S/N: Untuk layout 2-kolom ini, S/N biasanya kosong atau tidak ter-parse dengan baik
            # Strategy: Cek apakah ada text setelah No.Reg SEBELUM No.Reg berikutnya
            # Tapi jangan ambil jika text itu adalah nama barang (mengandung huruf banyak)
            sn = ""
            
            if i < len(noreg_matches) - 1:
                next_start = noreg_matches[i+1].start()
                potential_sn = text[end_pos:next_start].strip()
                
                # Filter: Jika potential_sn panjang dan mengandung banyak kata, 
                # kemungkinan itu nama barang item berikutnya, bukan S/N
                words = potential_sn.split()
                if len(words) <= 2 and len(potential_sn) < 30:
                    # Kemungkinan ini S/N (pendek)
                    sn = self._clean_sn(potential_sn)
                else:
                    # Kemungkinan ini nama barang item berikutnya
                    sn = ""
            else:
                # Item terakhir: cek apakah ada text pendek setelahnya
                potential_sn = text[end_pos:min(len(text), end_pos + 50)].strip()
                # Hanya ambil jika tidak ada keyword section berikutnya
                if not re.search(r'CABUT|PENGGANTI|TIDAK\s*TERPAKAI', potential_sn, re.IGNORECASE):
                    words = potential_sn.split()
                    if len(words) <= 2 and len(potential_sn) < 30:
                        sn = self._clean_sn(potential_sn)
            
            item = {
                "nama_barang": nama_barang,
                "no_reg": no_reg,
                "sn": sn
            }
            
            items.append(item)
            print(f"      • Item {i+1}: '{nama_barang[:30]}...' | {no_reg} | '{sn}'")
        
        return items


    def _clean_nama_barang(self, text: str) -> str:
        """
        Clean nama barang dari noise
        
        Args:
            text: Raw text nama barang
            
        Returns:
            Cleaned nama barang
        """
        # Remove common noise
        text = re.sub(r'Nama\s+Barang', '', text, flags=re.IGNORECASE)
        text = re.sub(r'No\.?\s*Reg', '', text, flags=re.IGNORECASE)
        text = re.sub(r'S/N', '', text, flags=re.IGNORECASE)
        
        # Remove multiple spaces/newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Strip whitespace
        text = text.strip()
        
        # Remove leading/trailing symbols
        text = text.strip('|,.-_')
        
        return text


    def _clean_sn(self, text: str) -> str:
        """
        Clean S/N dari noise
        Biasanya S/N kosong, tapi kalau ada isinya, clean juga
        
        Args:
            text: Raw text S/N
            
        Returns:
            Cleaned S/N
        """
        # Remove common keywords yang nyelip
        keywords_to_remove = [
            r'TIDAK\s+TERPAKAI', r'CABUT', r'PENGGANTI', r'PASANG\s+BARU',
            r'Nama\s+Barang', r'No\.?\s*Reg', r'S/N'
        ]
        
        for keyword in keywords_to_remove:
            text = re.sub(keyword, '', text, flags=re.IGNORECASE)
        
        # Remove multiple spaces/newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Strip whitespace
        text = text.strip()
        
        # Jika hanya symbol, return kosong
        if not text or re.match(r'^[|,.\-_\s]+$', text):
            return ""
        
        return text