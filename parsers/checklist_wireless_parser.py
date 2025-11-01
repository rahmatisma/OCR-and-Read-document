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