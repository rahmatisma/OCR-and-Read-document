"""
Base Parser Class - Kelas induk untuk semua parser
Taruh file ini di: parsers/base_parser.py
"""
from abc import ABC, abstractmethod
from typing import Optional
from parsers.utils.text_utils import TextNormalizer, RegexSearcher, KeyNormalizer


class BaseParser(ABC):
    """
    Kelas induk untuk semua parser (SPK Survey, Instalasi, Dismantle, dll)
    Berisi fungsi-fungsi umum yang digunakan oleh semua parser
    """
    
    def __init__(self, all_text: str, page_texts: list[str]):
        """
        Initialize parser
        
        Args:
            all_text: Full text dari dokumen
            page_texts: List text per halaman
        """
        self.all_text = TextNormalizer.normalize(all_text)
        self.page_texts = page_texts
        self.text_normalizer = TextNormalizer()
        self.regex_searcher = RegexSearcher()
        self.key_normalizer = KeyNormalizer()
    
    @abstractmethod
    def parse(self) -> dict:
        """
        Method utama untuk parsing dokumen
        Method ini HARUS diimplementasi oleh setiap parser turunan
        
        Returns:
            Dictionary berisi hasil parsing
        """
        pass
    
    def search_regex(self, pattern: str, text: str = None, allow_multiline: bool = False) -> Optional[str]:
        """
        Wrapper untuk RegexSearcher.search()
        Jika text tidak diberikan, gunakan self.all_text
        
        Args:
            pattern: Regex pattern
            text: Text yang akan di-search (default: self.all_text)
            allow_multiline: Apakah newline dianggap spasi
            
        Returns:
            Hasil search atau None
        """
        if text is None:
            text = self.all_text
        return self.regex_searcher.search(pattern, text, allow_multiline)
    
    def normalize_key(self, label: str) -> str:
        """
        Wrapper untuk KeyNormalizer.normalize()
        
        Args:
            label: Label yang akan dinormalisasi
            
        Returns:
            Key dalam format snake_case
        """
        return self.key_normalizer.normalize(label)
    
    def clean_text(self, text: str) -> str:
        """
        Wrapper untuk TextNormalizer.clean()
        
        Args:
            text: Text yang akan dibersihkan
            
        Returns:
            Text yang sudah dibersihkan
        """
        return self.text_normalizer.clean(text)
    
    def _init_data_structure(self) -> dict:
        """
        Inisialisasi struktur data kosong
        Bisa di-override oleh parser turunan jika butuh struktur berbeda
        
        Returns:
            Dictionary struktur data kosong
        """
        return {
            "spk": {},
            "pelanggan": {},
            "jaringan": {},
            "pelaksanaan": {},
            "vendor": {},
            "pekerja_cabut": {},
            "informasi_gedung": {},
            "sarpen_ruang_server": {},
            "lokasi_antena": {},
            "perizinan_biaya_gedung": {},
            "penempatan_perangkat": {},
            "perizinan_biaya_kawasan": {},
            "kawasan_umum": {},
            "data_splitter": {},
            "data_hh_eksisting": [],
            "data_hh_baru": [],
            "berita_acara": {},
            "pelaksanan_berita_acara": {},
        }
    
    def _init_data_structure_checklist_wireliness(self) -> dict:
        """
        Inisialisasi struktur data kosong
        Bisa di-override oleh parser turunan jika butuh struktur berbeda
        
        Returns:
            Dictionary struktur data kosong
        """
        return {
            "data_remote": {
                "nama_pelanggan": "",
                "contact_person": "",
                "alamat": "",
                "kota": "",
                "propinsi": "",
                "no_spk": "",
                "nomor_jaringan": "",
                "nomor_telepon": "",
                "tanggal": "",
                "pelaksanaan": {
                    "jam_perintah": "",
                    "jam_persiapan": "",
                    "jam_berangkat": "",
                    "jam_tiba_di_lokasi": "",
                    "jam_mulai_kerja": "",
                    "jam_selesai_kerja": "",
                    "jam_pulang": "",
                    "jam_tiba_di_kantor": "",
                    "keterangan": ""
                }
            },
            "indoor_area_checklist": {
                "sarana_penunjang": {
                    "merk_ups": "",
                    "kapasitas_ups": "",
                    "pengukuran_tegangan": [],
                    "parameter_kualitas": []
                },
                "perangkat_modem": {
                    "catatan_input_modem": "",
                    "bertumpuk": "",
                    "lokasi_ruang_lantai_rack": "",
                    "parameter_kualitas": []
                },
                "perangkat_cpe": {
                    "pemilik_perangkat_cpe": "",
                    "jenis_perangkat_cpe": "",
                    "parameter_kualitas": []
                }
            },
            "outdoor_area_checklist": {
                "site": {
                    "bs_catuan_sektor": "",
                    "jarak_udara_heading": "",
                    "latitude": "",
                    "longitude": "",
                    "potential_obstacle": "",
                    "quality_parameter": []
                },
                "sarana_penunjang": {
                    "type_mounting": "",
                    "quality_parameter": [],
                    "tinggi_mounting": "",
                    "type_penangkal_petir": ""
                },
                "perangkat_antenna": {
                    "polarisasi": "",
                    "altitude": "",
                    "lokasi": "",
                    "quality_parameter": []
                },
                "cabling_installation": {
                    "type_kabel_ifl": "",
                    "panjang_kabel_ifl": "",
                    "tahanan_short_kabel_ifl": "",
                    "quality_parameter": []
                }
            },
            "data_perangkat": {
                "existing": [],
                "tidak_terpakai": [],
                "cabut": [],
                "pengganti_atau_pasang_baru": []
            }
        }
    
    def _init_data_structure_checklist_wireline(self) -> dict:
        """
        Inisialisasi struktur data kosong
        Bisa di-override oleh parser turunan jika butuh struktur berbeda
        
        Returns:
            Dictionary struktur data kosong
        """
        return {
            "data_remote": {
                "nama_pelanggan": "",
                "contact_person": "",
                "alamat": "",
                "kota": "",
                "no_spk": "",
                "nomor_jaringan": "",
                "nomor_telepon": "",
                "propinsi": "",
                "tanggal": "",
                "pelaksanaan": {
                    "jam_perintah": "",
                    "jam_persiapan": "",
                    "jam_berangkat": "",
                    "jam_tiba_di_lokasi": "",
                    "jam_mulai_kerja": "",
                    "jam_selesai_kerja": "",
                    "jam_pulang": "",
                    "jam_tiba_di_kantor": "",
                    "keterangan": ""
                }
            },
            "global_checklist": {
                "data_lokasi": {
                    "latitude": "",
                    "longitude": "",
                    "posisi_modem_di_lt": "",
                    "ruang": ""
                },
                "electrical": {
                    "output_tegangan_mengacu_modem": {
                        "p_n": {
                            "pln": "",
                            "ups": "",
                            "it": ""
                        },
                        "p_g": {
                            "pln": "",
                            "ups": "",
                            "it": ""
                        },
                        "n_g": {
                            "pln": "",
                            "ups": "",
                            "it": ""
                        }
                    },
                    "grounding_bar_terkoneksi_ke": ""
                },
                "environment": {
                    "ac_pendingin_ruangan": "",
                    "suhu_ruangan_perangkat": ""
                }
            },
            "indoor_area_checklist": {
                "indikator_modem": {
                    "power": {
                        "standard": "",  # CHANGED: dari "ON (green)" ke ""
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    },
                    "109_dcd_link_wan": {
                        "standard": "",  # CHANGED
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    }
                },
                "merek": {
                    "td_txd_103": {
                        "standard": "",  # CHANGED
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    },
                    "rd_rxd_104": {
                        "standard": "",  # CHANGED
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    },
                    "rts_105": {
                        "standard": "",  # CHANGED
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    },
                    "cts_106": {
                        "standard": "",  # CHANGED
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    },
                    "alarm_led": {
                        "standard": "",  # CHANGED
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    },
                    "front_panel_display": {
                        "all_stu_modem": {
                            "standard": "",  # CHANGED
                            "nms_engineer": "",
                            "on_site_teknisi": "",
                            "perbaikan": "",
                            "hasil_akhir": ""
                        },
                        "tainet_scorpio": {
                            "standard": "",  # CHANGED
                            "nms_engineer": "",
                            "on_site_teknisi": "",
                            "perbaikan": "",
                            "hasil_akhir": ""
                        }
                    }
                },
                "modem_fo": {
                    "optical_led_alarm": {
                        "standard": "",  # CHANGED
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    }
                },
                "lc_signal_quality_checked_by_kop": {
                    "stu_160": {
                        "standard": "",  # CHANGED
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    },
                    "stu_1088_2304": {
                        "standard": "",  # CHANGED
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    },
                    "adsl_modem": {
                        "standard": "",  # CHANGED
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    }
                },
                "lc_signal_quality_checked_by_avo_meter": {
                    "stu_1088_2304": {
                        "standard": "",  # CHANGED
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    },
                    "tainet": {
                        "standard": "",  # CHANGED
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    },
                    "adtran_express": {
                        "standard": "",  # CHANGED
                        "nms_engineer": "",
                        "on_site_teknisi": "",
                        "perbaikan": "",
                        "hasil_akhir": ""
                    }
                }
            },
            # "line_checklist": {
            #     "site_area": {
            #         "parameter_kualitas": []
            #     },
            #     "hrb_r_lintas": {
            #         "parameter_kualitas": []
            #     },
            #     "line_fo": {
            #         "parameter_kualitas": []
            #     },
            #     "tes_konektivitas": {
            #         "parameter_kualitas": []
            #     }
            # },
            "data_perangkat": {
                "existing": [],
                "tidak_terpakai": [],
                "cabut": [],
                "pengganti_atau_pasang_baru": [],
                "note": ""
            }
        }