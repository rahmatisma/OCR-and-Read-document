"""
Parser untuk Form PM 1 Phase UPS (FM-LAP-D2-SOP-003-001)
Taruh file ini di: parsers/Form_PM_POP/pm_1phase_ups_parser.py
"""

from .base_pm_parser import BasePMParser
from typing import Dict, List
import re


class PM1PhaseUPSParser(BasePMParser):
    """
    Parser untuk Formulir Preventive Maintenance 1 Phase UPS
    """
    
    def parse(self) -> dict:
        """
        Parse form PM 1 Phase UPS
        
        Returns:
            Dictionary berisi hasil parsing
        """
        print("[PM 1 Phase UPS Parser] Memulai parsing...")
        
        # Inisialisasi struktur
        data = self._init_pm_structure()
        
        # Extract sections
        data["header"] = self.extract_header()
        data["informasi_umum"] = self.extract_informasi_umum()
        data["checklist_items"] = self._parse_all_checklist_items()
        data["notes"] = self.extract_notes()
        data["pelaksana"] = self.extract_pelaksana()
        
        print("[PM 1 Phase UPS Parser] Parsing selesai!")
        return data
    
    def _parse_all_checklist_items(self) -> List[Dict]:
        """
        Parse semua checklist items untuk form 1 Phase UPS
        
        Form ini memiliki 4 kategori:
        1. Visual Check (3 items)
        2. Performance and Capacity Check (10 items)
        3. Backup Tests (2 items)
        4. Power Alarm Monitoring Test (1 item)
        
        Returns:
            List berisi semua checklist items
        """
        checklist = []
        
        # 1. Visual Check
        visual_check = self._parse_visual_check()
        if visual_check:
            checklist.append({
                "kategori": "Visual Check",
                "items": visual_check
            })
        
        # 2. Performance and Capacity Check
        performance_check = self._parse_performance_check()
        if performance_check:
            checklist.append({
                "kategori": "Performance and Capacity Check",
                "items": performance_check
            })
        
        # 3. Backup Tests
        backup_tests = self._parse_backup_tests()
        if backup_tests:
            checklist.append({
                "kategori": "Backup Tests",
                "items": backup_tests
            })
        
        # 4. Power Alarm Monitoring Test
        power_alarm = self._parse_power_alarm_test()
        if power_alarm:
            checklist.append({
                "kategori": "Power Alarm Monitoring Test",
                "items": power_alarm
            })
        
        return checklist
    
    def _parse_visual_check(self) -> List[Dict]:
        """
        Parse Visual Check section
        
        Items:
        a. Environment Condition
        b. LED / display
        c. Battery Connection
        """
        items = []
        
        # Define items dengan standard nya
        visual_items = [
            {
                "no": "1a",
                "description": "Environment Condition",
                "standard": "Clean, No dust"
            },
            {
                "no": "1b",
                "description": "LED / display",
                "standard": "Normal"
            },
            {
                "no": "1c",
                "description": "Battery Connection",
                "standard": "Tighten, No Corrosion"
            }
        ]
        
        for item in visual_items:
            # Coba extract result dan status dari OCR data atau text
            result = self._extract_checklist_result(item["no"], item["description"])
            status = self._extract_checklist_status(item["no"], item["description"])
            
            items.append({
                "no": item["no"],
                "description": item["description"],
                "result": result,
                "operational_standard": item["standard"],
                "status": status
            })
        
        return items
    
    def _parse_performance_check(self) -> List[Dict]:
        """
        Parse Performance and Capacity Check section
        
        Items a-j dengan standard yang berbeda-beda
        """
        items = []
        
        # Define items dengan standard nya
        performance_items = [
            {
                "no": "2a",
                "description": "AC input voltage",
                "standard": "180-240 VAC"
            },
            {
                "no": "2b",
                "description": "AC output voltage",
                "standard": "210-240 VAC"
            },
            {
                "no": "2c",
                "description": "Neutral – Ground Output Voltage",
                "standard": "< 1 VAC"
            },
            {
                "no": "2d",
                "description": "AC current input",
                "standard": "14 A (UPS 3 kVA) / 23 A (UPS 5 kVA) / 27 A (UPS 6 kVA)"
            },
            {
                "no": "2e",
                "description": "AC current output",
                "standard": "10 A (UPS 3 kVA) / 18 A (UPS 5 kVA) / 22 A (UPS 6 kVA)"
            },
            {
                "no": "2f",
                "description": "UPS temperature",
                "standard": "0-40 °C"
            },
            {
                "no": "2g",
                "description": "Output frequency",
                "standard": "49.75-50.25 Hz"
            },
            {
                "no": "2h",
                "description": "Charging voltage",
                "standard": "See Battery Performance table"
            },
            {
                "no": "2i",
                "description": "Charging current",
                "standard": "0 Ampere, on-line mode"
            },
            {
                "no": "2j",
                "description": "FAN",
                "standard": "Berputar"
            }
        ]
        
        for item in performance_items:
            result = self._extract_checklist_result(item["no"], item["description"])
            status = self._extract_checklist_status(item["no"], item["description"])
            
            items.append({
                "no": item["no"],
                "description": item["description"],
                "result": result,
                "operational_standard": item["standard"],
                "status": status
            })
        
        return items
    
    def _parse_backup_tests(self) -> List[Dict]:
        """
        Parse Backup Tests section
        """
        items = []
        
        backup_items = [
            {
                "no": "3a",
                "description": "UPS Switching test, from the main source (PLN) to back up mode, by turning off UPS input MCB",
                "standard": "UPS Normal Operations"
            },
            {
                "no": "3b",
                "description": "Battery voltage (on Backup Mode)",
                "standard": "See Battery Performance table",
                "sub_items": [
                    "Measurement I (at the beginning)",
                    "Measurement II (15th minutes)"
                ]
            }
        ]
        
        for item in backup_items:
            result = self._extract_checklist_result(item["no"], item["description"])
            status = self._extract_checklist_status(item["no"], item["description"])
            
            item_data = {
                "no": item["no"],
                "description": item["description"],
                "result": result,
                "operational_standard": item["standard"],
                "status": status
            }
            
            # Handle sub-items jika ada
            if "sub_items" in item:
                item_data["sub_measurements"] = []
                for sub in item["sub_items"]:
                    sub_result = self._extract_sub_result(item["no"], sub)
                    item_data["sub_measurements"].append({
                        "measurement": sub,
                        "result": sub_result
                    })
            
            items.append(item_data)
        
        return items
    
    def _parse_power_alarm_test(self) -> List[Dict]:
        """
        Parse Power Alarm Monitoring Test section
        """
        items = [{
            "no": "4",
            "description": "Makesure the Simonica alarm monitor, by turn off UPS power input MCB during UPS backup test operation",
            "result": self._extract_checklist_result("4", "Simonica alarm"),
            "operational_standard": "Simonica Alarm",
            "status": self._extract_checklist_status("4", "Simonica alarm")
        }]
        
        return items
    
    def _extract_checklist_result(self, item_no: str, description: str) -> str:
        """
        Extract result dari checklist item menggunakan OCR data atau text matching
        
        Args:
            item_no: Nomor item (misal "1a", "2b")
            description: Deskripsi item
            
        Returns:
            Result string atau empty string
        """
        # TODO: Implement extraction logic menggunakan OCR data
        # Untuk sementara return empty string
        # Nanti bisa ditambahkan logic untuk:
        # 1. Cari baris dengan item_no di OCR data
        # 2. Extract text di kolom "Result"
        # 3. Return nilai yang ditemukan
        
        return ""
    
    def _extract_checklist_status(self, item_no: str, description: str) -> str:
        """
        Extract status (OK/NOK) dari checklist item
        
        Args:
            item_no: Nomor item
            description: Deskripsi item
            
        Returns:
            Status string (OK/NOK) atau empty string
        """
        # TODO: Implement extraction logic
        return ""
    
    def _extract_sub_result(self, item_no: str, measurement: str) -> str:
        """
        Extract result untuk sub-measurement (seperti Measurement I, II)
        
        Args:
            item_no: Nomor item parent
            measurement: Nama measurement
            
        Returns:
            Result string
        """
        # TODO: Implement extraction logic
        return ""