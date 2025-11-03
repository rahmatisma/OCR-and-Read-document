# readers/ocr/label_config.py
"""
Konfigurasi label dokumentasi untuk setiap jenis SPK
"""

class LabelConfig:
    """Config label untuk ekstraksi gambar dokumentasi per jenis SPK"""
    
    # Label untuk SPK Survey
    SPK_SURVEY = [
        "Dokumentasi foto",
        "Foto penempatan perangkat di lokasi pelanggan",
        "Foto jalur kabel dalam gedung",
        "Plan jalur dalam gedung",
        "Data jalur kabel",
        "Foto splitter",
        "Foto hh eksisting yang dipakai",
        "Foto lokasi hh baru"
    ]
    
    # Label untuk SPK Instalasi
    SPK_INSTALASI = [
        "HASIL INSTALASI",
        "PHOTO INSTALASI ETHERNET",
        "FOTO LAIN-LAIN",
        "LIST ITEM"
    ]
    
    # Label untuk SPK Dismantle
    SPK_DISMANTLE = [
        "HASIL PEKERJAAN CABUT",
        "DISMANTLE ITEMS",
    ]
    
    # Label untuk SPK Aktivasi
    SPK_AKTIVASI = [
        "HASIL AKTIVASI",
        "DOKUMENTASI FOTO",
        "LIST ITEM"
    ]
    
    # Label untuk Checklist Wireline
    CHECKLIST_WIRELINE = [
        "Dokumentasi foto wireline",
        "Foto ODP/ODC"
    ]
    
    # Label untuk Checklist Wireless
    CHECKLIST_WIRELESS = [
        "Dokumentasi foto wireless",
        "Foto tower/pole"
    ]
    
    # Label untuk Maintenance Remote Wireless
    MAINTENANCE_REMOTE_WIRELESS = [
        "Dokumentasi foto maintenance",
        "Foto before maintenance"
    ]
    
    @classmethod
    def get_labels(cls, doc_type: str) -> list:
        """
        Mendapatkan daftar label berdasarkan tipe dokumen
        
        Args:
            doc_type: Tipe dokumen (contoh: "spk_survey", "spk_instalasi")
            
        Returns:
            List label yang sesuai, atau list kosong jika tidak ditemukan
        """
        # Normalize doc_type
        normalized_type = doc_type.upper().replace(" ", "_").replace("-", "_")
        
        # Mapping doc_type ke attribute class
        mapping = {
            "SPK_SURVEY": cls.SPK_SURVEY,
            "SPK_INSTALASI": cls.SPK_INSTALASI,
            "SPK_DISMANTLE": cls.SPK_DISMANTLE,
            "SPK_AKTIVASI": cls.SPK_AKTIVASI,
            "CHECKLIST_WIRELINE": cls.CHECKLIST_WIRELINE,
            "CHECKLIST_WIRELESS": cls.CHECKLIST_WIRELESS,
            "MAINTENANCE_REMOTE_WIRELESS": cls.MAINTENANCE_REMOTE_WIRELESS,
        }
        
        labels = mapping.get(normalized_type, [])
        
        if not labels:
            print(f"[WARNING] Label untuk '{doc_type}' tidak ditemukan dalam config")
        else:
            print(f"[INFO] Menggunakan {len(labels)} label untuk '{doc_type}'")
        
        return labels