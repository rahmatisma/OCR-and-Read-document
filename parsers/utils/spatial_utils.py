"""
Spatial Utilities for OCR-based Parsing

Provides tools for:
- Building spatial index from OCR data
- Coordinate-based field extraction
- Proximity-based value collection

Used by parsers that process OCR output with bounding box coordinates.
"""

import re
from typing import Optional, List, Dict, Any


class SpatialMapBuilder:
    """Build spatial index from OCR data for fast lookup"""
    
    @staticmethod
    def build(ocr_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Build spatial map from OCR data
        
        Args:
            ocr_data: List of OCR items with format:
                      [{'text': str, 'score': float, 'bbox': list, 'position': tuple}, ...]
        
        Returns:
            Dict mapping normalized text to OCR item metadata
            Format: {normalized_text: {'text': original, 'bbox': [...], 'position': (...), 'index': int}}
        """
        spatial_map = {}
        
        for idx, item in enumerate(ocr_data):
            text_key = SpatialMapBuilder._normalize_text(item['text'])
            spatial_map[text_key] = {
                'text': item['text'],
                'bbox': item.get('bbox', []),
                'position': item.get('position', (0, 0)),
                'index': idx,
                'score': item.get('score', 1.0)
            }
        
        return spatial_map
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalize text for matching (remove spaces, punctuation, lowercase)
        
        Args:
            text: Raw text string
        
        Returns:
            Normalized text key
        """
        normalized = text.lower().replace(' ', '').replace(':', '').replace('：', '')
        return normalized


class CoordinateFieldExtractor:
    """Extract fields using coordinate-based proximity detection"""
    
    # Common field labels for stop detection
    COMMON_FIELD_LABELS = [
        "Nama Pelanggan", "Contact Person", "Nomor Jaringan", "Nomor Telepon",
        "Alamat", "Kota", "Propinsi", "Provinsi", "No. SPK", "No SPK", "Tanggal",
        "Jam Perintah", "Jam Persiapan", "Jam Berangkat", "Jam Tiba Di Lokasi",
        "Jam Mulai Kerja", "Jam Selesai Kerja", "Jam Pulang", "Jam Tiba Di Kantor"
    ]
    
    def __init__(self, ocr_data: List[Dict[str, Any]], spatial_map: Dict[str, Dict[str, Any]]):
        """
        Initialize extractor
        
        Args:
            ocr_data: Raw OCR data list
            spatial_map: Pre-built spatial index from SpatialMapBuilder
        """
        self.ocr_data = ocr_data
        self.spatial_map = spatial_map
    
    def find_field_label(self, field_pattern: str) -> Optional[Dict[str, Any]]:
        """
        Find field label in spatial map using regex pattern
        
        Args:
            field_pattern: Regex pattern to match field label
        
        Returns:
            Field metadata dict or None if not found
        """
        if not self.spatial_map:
            return None
        
        for text_key, data in self.spatial_map.items():
            original_text = data['text']
            if re.search(field_pattern, original_text, re.IGNORECASE):
                return data
        
        return None
    
    def get_values_after_field(self, field_index: int, max_items: int = 5,same_line_threshold: int = 40) -> List[str]:
        """
        Get multiple values after field label based on spatial proximity
        
        Args:
            field_index: Index of field label in ocr_data
            max_items: Maximum number of items to collect
            same_line_threshold: Y-distance threshold to consider "same line" (pixels)
        
        Returns:
            List of value strings found after the field
        """
        if field_index < 0 or field_index >= len(self.ocr_data):
            return []
        
        field_item = self.ocr_data[field_index]
        field_y = field_item['position'][0]
        
        values = []
        
        for i in range(field_index + 1, min(field_index + max_items + 1, len(self.ocr_data))):
            item = self.ocr_data[i]
            item_text = item['text'].strip()
            
            # Skip punctuation only
            if item_text in [':', '：', '.', ',', '-']:
                continue
            
            # Stop at next field label
            if self._is_field_label(item_text):
                break
            
            item_y = item['position'][0]
            y_distance = abs(item_y - field_y)
            
            # Collect if on same line (or very close vertically)
            if y_distance < same_line_threshold:
                values.append(item_text)
        
        return values
    
    def extract_simple_field(self, field_pattern: str) -> str:
        """
        Extract simple text field using coordinate data
        
        Args:
            field_pattern: Regex pattern for field label
        
        Returns:
            Extracted and cleaned field value
        """
        # Find field label
        field_info = self.find_field_label(field_pattern)
        
        if not field_info:
            return ""
        
        field_index = field_info['index']
        
        # Get values after field
        values = self.get_values_after_field(field_index, max_items=3)
        
        if not values:
            return ""
        
        # Take first value and clean
        value = values[0]
        cleaned = self.clean_value(value)
        
        return cleaned
    
    @staticmethod
    def clean_value(value: str) -> str:
        """
        Clean extracted value (remove leading colons, whitespace, artifacts)
        
        Args:
            value: Raw extracted value
        
        Returns:
            Cleaned value string
        """
        if not value:
            return ""
        
        # Remove leading punctuation and whitespace
        value = re.sub(r'^[:\：\s]+', '', value)
        
        # Remove OCR artifacts like "i:21-Jun-2021" -> "21-Jun-2021"
        value = re.sub(r'^i:', '', value)
        
        # Remove trailing punctuation
        value = value.strip(' :：.,')
        
        return value
    
    def _is_field_label(self, text: str) -> bool:
        """
        Check if text is a field label (stop extraction)
        
        Args:
            text: Text to check
        
        Returns:
            True if text matches a known field label
        """
        text_normalized = text.strip().lower()
        for label in self.COMMON_FIELD_LABELS:
            if label.lower() in text_normalized:
                return True
        return False


class ValueCleaner:
    """Utility for cleaning extracted values"""
    
    @staticmethod
    def remove_leading_colon(value: str) -> str:
        """Remove leading colon from value like ':BANK...' -> 'BANK...'"""
        return re.sub(r'^[:\：\s]+', '', value).strip()
    
    @staticmethod
    def remove_ocr_artifacts(value: str) -> str:
        """Remove common OCR artifacts"""
        # Remove 'i:' prefix (common OCR mistake)
        value = re.sub(r'^i:', '', value)
        return value
    
    @staticmethod
    def normalize_special_chars(value: str) -> str:
        """Normalize special characters (Chinese colon, etc)"""
        value = value.replace('：', ':')
        return value
    
    @staticmethod
    def clean_all(value: str) -> str:
        """Apply all cleaning steps"""
        if not value:
            return ""
        
        value = ValueCleaner.normalize_special_chars(value)
        value = ValueCleaner.remove_leading_colon(value)
        value = ValueCleaner.remove_ocr_artifacts(value)
        value = value.strip(' :：.,')
        
        return value