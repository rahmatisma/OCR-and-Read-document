from .spk_survey_parser import parse_spk_survey
# from .spk_instalasi_parser import parse_spk_instalasi
# from .spk_aktivasi_parser import parse_spk_aktivasi
# from .spk_dismantle_parser import parse_spk_dismantle
# from .checklist_wireline_parser import parse_checklist_wireline
# from .checklist_wireless_parser import parse_checklist_wireless

PARSERS = {
    "survey": parse_spk_survey,
    # "instalasi": parse_spk_instalasi,
    # "aktivasi": parse_spk_aktivasi,
    # "dismantle": parse_spk_dismantle,
    # "checklist_wireline": parse_checklist_wireline,
    # "checklist_wireless": parse_checklist_wireless,
}
