# parsers/Form_PM_POP/config/pm_labels.py
"""
Konfigurasi label untuk semua Form PM POP
Setiap form PM punya struktur checklist yang berbeda
"""

class PMLabels:
    """Label configuration untuk Form PM POP"""
    
    # ============================================================
    # FORM PM INVERTER -48VDC/220VAC (FM-LAP-D2-SOP-003-005)
    # ============================================================
    PM_INVERTER_LABELS = {
        "header": [
            "No. Dok.",
            "Formulir",
            "Versi",
            "Hal",
            "Label"
        ],
        "informasi_umum": [
            "Location",
            "Date / time",
            "Brand / Type",
            "Reg. Number",
            "S/N"
        ],
        "physical_check": [
            "Environment Condition",
            "LED / display"
        ],
        "performance_check": [
            "DC Input Voltage",
            "DC Current Input",
            "AC Current Output",
            "AC Output Voltage",
            "Equipment Temperature"
        ],
        "footer": [
            "Notes / additional informations",
            "Executor",
            "Verifikator",
            "Head Of Sub Departement"
        ]
    }
    
    # ============================================================
    # FORM PM 1 PHASE UPS (FM-LAP-D2-SOP-003-001)
    # ============================================================
    PM_1PHASE_UPS_LABELS = {
        "header": [
            "No. Dok.",
            "Formulir",
            "Versi",
            "Hal",
            "Label"
        ],
        "informasi_umum": [
            "Location",
            "Date / time",
            "Brand / Type",
            "Reg. Number",
            "S/N",
            "Kapasitas"
        ],
        "checklist": [
            "Physical Check",
            "Input Check",
            "Output Check",
            "Battery Check",
            "Performance Check"
        ]
    }
    
    # ============================================================
    # FORM PM 3 PHASE UPS (FM-LAP-D2-SOP-003-002)
    # ============================================================
    PM_3PHASE_UPS_LABELS = {
        "header": [
            "No. Dok.",
            "Formulir",
            "Versi",
            "Hal",
            "Label"
        ],
        "informasi_umum": [
            "Location",
            "Date / time",
            "Brand / Type",
            "Reg. Number",
            "S/N",
            "Kapasitas"
        ],
        "checklist": [
            "Physical Check",
            "Input Check",
            "Output Check",
            "Battery Check",
            "Bypass Check",
            "Performance Check"
        ]
    }
    
    # ============================================================
    # HELPER METHOD
    # ============================================================
    @classmethod
    def get_labels(cls, form_type: str) -> dict:
        """
        Get labels untuk form type tertentu
        
        Args:
            form_type: 'pm_inverter', 'pm_1phase_ups', dll
            
        Returns:
            Dictionary labels atau None
        """
        mapping = {
            "pm_inverter": cls.PM_INVERTER_LABELS,
            "pm_1phase_ups": cls.PM_1PHASE_UPS_LABELS,
            "pm_3phase_ups": cls.PM_3PHASE_UPS_LABELS,
        }
        
        return mapping.get(form_type)