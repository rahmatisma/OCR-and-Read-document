"""
DateTime Utilities for Wireless Parser

Provides tools for:
- Parsing datetime strings with multiple formats
- Extracting jam pelaksanaan section
- Mapping datetime values to fields (table-aware)

Specific to Checklist Wireless format (table with 6 datetime + 2 empty fields).
"""

import re
from typing import Optional, List, Dict, Tuple


# Standard datetime mapping for Wireless format (2 rows x 4 columns)
# Based on: ROW1: Jam Perintah, Persiapan, Berangkat, Tiba Lokasi
#           ROW2: Jam Mulai Kerja, Selesai Kerja, Pulang, Tiba Kantor
WIRELESS_DATETIME_MAPPING = {
    "jam_perintah": 0,          # dates[0] + times[0]
    "jam_persiapan": 1,         # dates[1] + times[1]
    "jam_berangkat": 2,         # dates[2] + times[2]
    "jam_tiba_di_lokasi": 3,    # dates[3] + times[3]
    "jam_mulai_kerja": 4,       # dates[4] + times[4]
    "jam_selesai_kerja": 5,     # dates[5] + times[5]
    "jam_pulang": None,         # Usually empty (check with regex)
    "jam_tiba_di_kantor": None  # Usually empty (check with regex)
}


class DateTimeParser:
    """Parse datetime strings with multiple format support"""
    
    # Common datetime patterns
    PATTERN_DATETIME_FULL = r'(\d{2}-[A-Za-z]{3}-\d{4})\s+(\d{2}:\d{2})'  # 21-Jun-2021 18:00
    PATTERN_DATETIME_CONCAT = r'(\d{2}-[A-Za-z]{3}-\d{4})(\d{2}:\d{2})'   # 21-Jun-202118:00
    PATTERN_DATE_ONLY = r'(\d{2}-[A-Za-z]{3}-\d{4})'                       # 21-Jun-2021
    PATTERN_TIME_ONLY = r'(\d{2}:\d{2})'                                   # 18:00
    
    @staticmethod
    def parse(text: str) -> str:
        """
        Parse datetime string with multiple pattern attempts
        
        Args:
            text: Raw text that may contain datetime
        
        Returns:
            Parsed datetime string (DD-Mon-YYYY HH:MM or DD-Mon-YYYY or HH:MM)
            Empty string if no pattern matches
        
        Examples:
            >>> DateTimeParser.parse("21-Jun-2021 18:00")
            "21-Jun-2021 18:00"
            
            >>> DateTimeParser.parse("21-Jun-202118:00")
            "21-Jun-2021 18:00"
            
            >>> DateTimeParser.parse("21-Jun-2021")
            "21-Jun-2021"
        """
        if not text:
            return ""
        
        # Try Pattern 1: Normal format with space
        match = re.search(DateTimeParser.PATTERN_DATETIME_FULL, text)
        if match:
            return f"{match.group(1)} {match.group(2)}"
        
        # Try Pattern 2: Concatenated format (no space)
        match = re.search(DateTimeParser.PATTERN_DATETIME_CONCAT, text)
        if match:
            return f"{match.group(1)} {match.group(2)}"
        
        # Try Pattern 3: Date only
        match = re.search(DateTimeParser.PATTERN_DATE_ONLY, text)
        if match:
            date_str = match.group(1)
            # Try to find time in remaining text
            time_match = re.search(DateTimeParser.PATTERN_TIME_ONLY, text)
            if time_match:
                return f"{date_str} {time_match.group(1)}"
            return date_str
        
        # Try Pattern 4: Time only (standalone)
        match = re.search(DateTimeParser.PATTERN_TIME_ONLY, text)
        if match:
            return match.group(1)
        
        return ""
    
    @staticmethod
    def extract_all_dates(text: str) -> List[str]:
        """
        Extract all date patterns from text
        
        Args:
            text: Text to search
        
        Returns:
            List of date strings (DD-Mon-YYYY format)
        
        Example:
            >>> DateTimeParser.extract_all_dates("21-Jun-2021 22-Jun-2021")
            ["21-Jun-2021", "22-Jun-2021"]
        """
        return re.findall(DateTimeParser.PATTERN_DATE_ONLY, text)
    
    @staticmethod
    def extract_all_times(text: str) -> List[str]:
        """
        Extract all time patterns from text
        
        Args:
            text: Text to search
        
        Returns:
            List of time strings (HH:MM format)
        
        Example:
            >>> DateTimeParser.extract_all_times("18:00 19:42 00:03")
            ["18:00", "19:42", "00:03"]
        """
        return re.findall(DateTimeParser.PATTERN_TIME_ONLY, text)
    
    @staticmethod
    def combine_date_time(dates: List[str], times: List[str]) -> List[str]:
        """
        Combine parallel lists of dates and times
        
        Args:
            dates: List of date strings
            times: List of time strings
        
        Returns:
            List of combined "DD-Mon-YYYY HH:MM" strings
        
        Example:
            >>> dates = ["21-Jun-2021", "22-Jun-2021"]
            >>> times = ["18:00", "00:03"]
            >>> DateTimeParser.combine_date_time(dates, times)
            ["21-Jun-2021 18:00", "22-Jun-2021 00:03"]
        """
        combined = []
        for i in range(min(len(dates), len(times))):
            combined.append(f"{dates[i]} {times[i]}")
        return combined


class JamSectionExtractor:
    """Extract and parse Jam Pelaksanaan section"""
    
    # Section boundary patterns
    SECTION_START = r'Jam\s*Perintah'
    SECTION_END = r'(?:GLOBAL|Latitude|DATA\s*LOKASI)'
    
    @staticmethod
    def extract(text: str) -> str:
        """
        Extract jam pelaksanaan section from full text
        
        Args:
            text: Full document text
        
        Returns:
            Extracted section text, or empty string if not found
        
        Example:
            Text: "... Tanggal: 21-Jun-2021 Jam Perintah: ... GLOBAL CHECKLIST ..."
            Returns: "Jam Perintah: ... " (everything between start and end)
        """
        pattern = rf'{JamSectionExtractor.SECTION_START}.*?(?={JamSectionExtractor.SECTION_END}|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        
        return match.group() if match else ""
    
    @staticmethod
    def extract_datetimes_from_section(section_text: str) -> Tuple[List[str], List[str]]:
        """
        Extract all dates and times from jam section
        
        Args:
            section_text: Jam pelaksanaan section text
        
        Returns:
            Tuple of (dates, times) lists
        
        Example:
            >>> section = "Jam Perintah 21-Jun-2021 18:00 Jam Persiapan 21-Jun-2021 18:08"
            >>> dates, times = JamSectionExtractor.extract_datetimes_from_section(section)
            >>> dates
            ["21-Jun-2021", "21-Jun-2021"]
            >>> times
            ["18:00", "18:08"]
        """
        dates = DateTimeParser.extract_all_dates(section_text)
        times = DateTimeParser.extract_all_times(section_text)
        
        return dates, times


class WirelessDateTimeMapper:
    """Map extracted datetime values to wireless fields"""
    
    @staticmethod
    def map_to_fields(dates: List[str], times: List[str], 
                      full_text: str = "") -> Dict[str, str]:
        """
        Map datetime arrays to wireless fields using standard mapping
        
        Args:
            dates: List of extracted dates
            times: List of extracted times
            full_text: Full text for checking empty fields (optional)
        
        Returns:
            Dictionary mapping field names to datetime values
        
        Example:
            >>> dates = ["21-Jun-2021", "21-Jun-2021", ...]  # 6 dates
            >>> times = ["18:00", "18:08", ...]               # 6 times
            >>> result = WirelessDateTimeMapper.map_to_fields(dates, times)
            >>> result
            {
                "jam_perintah": "21-Jun-2021 18:00",
                "jam_persiapan": "21-Jun-2021 18:08",
                ...
                "jam_pulang": "",
                "jam_tiba_di_kantor": ""
            }
        """
        result = {}
        
        for field_key, index in WIRELESS_DATETIME_MAPPING.items():
            if index is None:
                # Field expected to be empty (check with regex if full_text provided)
                if full_text:
                    value = WirelessDateTimeMapper._check_empty_field(field_key, full_text)
                    result[field_key] = value
                else:
                    result[field_key] = ""
            elif index < len(dates) and index < len(times):
                # Both date and time available
                result[field_key] = f"{dates[index]} {times[index]}"
            elif index < len(dates):
                # Only date available
                result[field_key] = dates[index]
            else:
                # No data available
                result[field_key] = ""
        
        return result
    
    @staticmethod
    def _check_empty_field(field_key: str, text: str) -> str:
        """
        Check if a supposedly empty field actually has value in text
        
        Args:
            field_key: Field name (e.g., "jam_pulang")
            text: Full text to search
        
        Returns:
            Datetime value if found, empty string otherwise
        """
        # Field-specific patterns
        patterns = {
            "jam_pulang": r'Jam\s*Pulang\s*[：:]?\s*(\d{2}-[A-Za-z]{3}-\d{4}(?:\s+\d{2}:\d{2})?)',
            "jam_tiba_di_kantor": r'Jam\s*Tiba\s*(?:Di\s*)?Kantor\s*[：:]?\s*(\d{2}-[A-Za-z]{3}-\d{4}(?:\s+\d{2}:\d{2})?)'
        }
        
        pattern = patterns.get(field_key)
        if not pattern:
            return ""
        
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else ""


# Convenience function for quick datetime parsing
def parse_datetime_string(text: str) -> str:
    """
    Convenience wrapper for DateTimeParser.parse()
    
    Args:
        text: Text containing datetime
    
    Returns:
        Parsed datetime string
    
    Example:
        >>> parse_datetime_string("21-Jun-2021 18:00")
        "21-Jun-2021 18:00"
    """
    return DateTimeParser.parse(text)