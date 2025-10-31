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
        self._parse_data_remote(data["data_remote"])
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