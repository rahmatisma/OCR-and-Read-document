import os
import json
from datetime import datetime
from readers.pdf_reader import read_pdf
from readers.ocr.text_reader import run_ocr
from difflib import SequenceMatcher

OUTPUT_DIR = "output"  # Default untuk testing lokal
LARAVEL_STORAGE_PATH = None  # Akan diset dari Flask

# Mapping document type ke folder struktur
DOCUMENT_TYPE_MAPPING = {
    'spk_survey': 'spk/survey',
    'spk_instalasi': 'spk/instalasi',
    'spk_dismantle': 'spk/dismantle',
    'spk_aktivasi': 'spk/aktivasi',
    'checklist_wireline': 'checklist/wireline',
    'checklist_wireless': 'checklist/wireless',
    
    'form_pm_1phase_ups': 'form_pm/1phase_ups',
    'form_pm_3phase_ups': 'form_pm/3phase_ups',
    'form_pm_ac': 'form_pm/ac',
    'form_pm_permohonan_tindak_lanjut': 'form_pm/permohonan_tindak_lanjut',
    'form_pm_tindak_lanjut': 'form_pm/tindak_lanjut',
    'form_pm_genset': 'form_pm/genset',
    'form_pm_jadwal_sentral': 'form_pm/jadwal_sentral',
    'form_pm_inverter': 'form_pm/inverter',
    'form_pm_ruang_shelter': 'form_pm/ruang_shelter',
    'form_pm_rectifier': 'form_pm/rectifier',
    'form_pm_petir_grounding': 'form_pm/petir_grounding',
    'form_pm_instalasi_kabel': 'form_pm/instalasi_kabel',
    'form_pm_battery': 'form_pm/battery',
    'form_pm_dokumentasi_perangkat': 'form_pm/dokumentasi_perangkat',
    
    'unknown': 'unknown'
}


def set_laravel_storage_path(path: str):
    """Set path Laravel storage dari Flask"""
    global LARAVEL_STORAGE_PATH
    LARAVEL_STORAGE_PATH = path
    print(f"📁 Laravel storage path set to: {path}")


def get_output_base_dir():
    """Get base directory untuk output"""
    if LARAVEL_STORAGE_PATH and os.path.exists(LARAVEL_STORAGE_PATH):
        # ✅ FIX: Return ke folder 'output' di dalam storage/app/public
        return os.path.join(LARAVEL_STORAGE_PATH, 'output')
    return OUTPUT_DIR


def get_document_folder_name(doc_type: str) -> str:
    """
    Generate nama folder berdasarkan jenis dokumen + timestamp
    
    Args:
        doc_type: 'spk_survey', 'checklist_wireless', etc.
    
    Returns:
        Nama folder: 'survey_20241230_143022'
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Extract jenis dari doc_type
    # spk_survey → survey
    # checklist_wireless → wireless
    if '_' in doc_type:
        jenis = doc_type.split('_', 1)[1]  # Ambil setelah underscore pertama
    else:
        jenis = doc_type
    
    return f"{jenis}_{timestamp}"


def get_document_category_path(doc_type: str) -> str:
    """
    Get path kategori dari document type
    
    Args:
        doc_type: 'spk_survey', 'checklist_wireless', etc.
    
    Returns:
        'spk/survey', 'checklist/wireless', dll
    """
    return DOCUMENT_TYPE_MAPPING.get(doc_type, 'unknown')


def save_output(data, filename, subfolder=None):
    """Simpan hasil JSON ke folder output"""
    base_dir = get_output_base_dir()
    
    if subfolder:
        output_folder = os.path.join(base_dir, subfolder)
    else:
        output_folder = base_dir
    
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename + ".json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ JSON disimpan di: {output_path}")


def convert_paths_to_relative(data, base_path: str):
    """
    Convert absolute path ke relative path untuk Laravel
    
    Contoh:
        Input:  D:/laragon/www/project/storage/app/public/extracted/spk/survey/survey_20241230/images/foto.jpg
        Output: extracted/spk/survey/survey_20241230/images/foto.jpg
    
    Args:
        data: Dict/List yang mungkin mengandung path
        base_path: Base path Laravel storage (storage/app/public)
    
    Returns:
        Data dengan path yang sudah relatif
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                result[key] = convert_paths_to_relative(value, base_path)
            elif isinstance(value, str) and ('patch_foto' in key or 'path' in key.lower()):
                # Convert path jika key mengandung 'patch_foto' atau 'path'
                if os.path.isabs(value):
                    try:
                        # Coba ambil path relatif dari base_path
                        relative = os.path.relpath(value, base_path)
                        # Normalize separator untuk web (forward slash)
                        result[key] = relative.replace('\\', '/')
                    except ValueError:
                        # Jika gagal (beda drive di Windows), gunakan path asli
                        result[key] = value.replace('\\', '/')
                else:
                    result[key] = value.replace('\\', '/')
            else:
                result[key] = value
        return result
    
    elif isinstance(data, list):
        return [convert_paths_to_relative(item, base_path) for item in data]
    
    else:
        return data


def pengecekan_file(file_path: str, laravel_storage_path: str = None):
    """Process PDF dan simpan hasil ke folder yang ditentukan"""
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{file_path}' tidak ditemukan.")
    
    print(f"🔍 DEBUG: laravel_storage_path parameter = {laravel_storage_path}")
    print(f"🔍 DEBUG: Parameter is None? {laravel_storage_path is None}")

    # Set Laravel storage path jika diberikan
    if laravel_storage_path:
        set_laravel_storage_path(laravel_storage_path)

    print(f"🔍 DEBUG: LARAVEL_STORAGE_PATH global = {LARAVEL_STORAGE_PATH}")
    
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    base_dir = get_output_base_dir()  # Ini sekarang akan return .../storage/app/public/output
    
    print(f"🔍 DEBUG: base_dir from get_output_base_dir() = {base_dir}")

    if file_path.lower().endswith(".pdf"):
        print(f"\n{'='*60}")
        print(f"📄 Memproses PDF: {base_name}")
        print(f"{'='*60}\n")
        
        # 1. Proses PDF dulu untuk deteksi jenis dokumen
        temp_images_folder = os.path.join(base_dir, "temp", base_name, "images")
        os.makedirs(temp_images_folder, exist_ok=True)
        
        print(f"📁 Folder temporary: {temp_images_folder}\n")
        
        # 2. Proses PDF dengan temp folder
        result = read_pdf(file_path, output_dir=temp_images_folder)
        
        # 3. Deteksi jenis dokumen dari hasil parsing
        doc_type = result.get('parsed', {}).get('document_type', 'unknown')
        print(f"\n🔍 Jenis dokumen terdeteksi: {doc_type}")
        
        # 4. Buat folder final berdasarkan jenis dokumen
        category_path = get_document_category_path(doc_type)
        folder_name = get_document_folder_name(doc_type)
        
        # ✅ FIX: Struktur folder yang benar
        # base_dir = D:/laragon/.../storage/app/public/output
        # final = D:/laragon/.../storage/app/public/output/extracted/spk/survey/survey_xxx
        final_doc_folder = os.path.join(base_dir, "extracted", category_path, folder_name)
        final_images_folder = os.path.join(final_doc_folder, "images")
        
        print(f"📁 Folder final: {final_doc_folder}")
        print(f"📁 Folder gambar final: {final_images_folder}\n")
        
        # 5. Pindahkan gambar dari temp ke folder final
        import shutil
        if os.path.exists(temp_images_folder):
            os.makedirs(final_images_folder, exist_ok=True)
            
            for item in os.listdir(temp_images_folder):
                src = os.path.join(temp_images_folder, item)
                dst = os.path.join(final_images_folder, item)
                
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    print(f"  ✓ Moved: {item}")
            
            shutil.rmtree(os.path.join(base_dir, "temp", base_name))
            print(f"🗑️  Folder temporary dihapus\n")
        
        # 6. Update path di result
        if 'dokumentasi' in result and isinstance(result['dokumentasi'], list):
            for doc_item in result['dokumentasi']:
                if 'patch_foto' in doc_item:
                    old_path = doc_item['patch_foto']
                    filename = os.path.basename(old_path)
                    new_path = os.path.join(final_images_folder, filename)
                    doc_item['patch_foto'] = new_path
                    print(f"  📝 Updated path: {filename}")
        
        # 7. ✅ FIX: Convert path relatif dari storage/app/public (BUKAN dari output)
        if laravel_storage_path:
            print(f"\n🔄 Converting paths to relative from: {laravel_storage_path}")
            result = convert_paths_to_relative(result, laravel_storage_path)
            
            if result.get('dokumentasi') and len(result['dokumentasi']) > 0:
                sample_path = result['dokumentasi'][0].get('patch_foto', 'N/A')
                print(f"✅ Sample converted path: {sample_path}")
                # Path sekarang: output/extracted/spk/survey/survey_xxx/images/foto.jpg
            
            print(f"✅ Paths converted\n")
        
        # 8. Simpan JSON
        json_path = os.path.join(final_doc_folder, f"{folder_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"✅ JSON disimpan di: {json_path}")
        
        print(f"\n{'='*60}")
        print(f"✅ Selesai! Hasil disimpan di: {final_doc_folder}")
        print(f"{'='*60}\n")

    return result

def load_ground_truth(doc_name):
    """Load ground truth dari file JSON"""
    gt_path = os.path.join("evaluation", "ground_truth", f"{doc_name}_ground_truth.json")
    
    if not os.path.exists(gt_path):
        return None
    
    with open(gt_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_field_accuracy(ground_truth, parsed_result):
    """
    Hitung akurasi per field
    
    Returns:
        {
            "total_fields": 8,
            "correct": 6,
            "incorrect": 2,
            "accuracy": 75.0,
            "details": {...}
        }
    """
    if not ground_truth:
        return {"error": "Ground truth not found"}
    
    gt_fields = ground_truth.get('fields', {})
    parsed_fields = parsed_result.get('parsed', {})
    
    total = len(gt_fields)
    correct = 0
    details = {}
    
    for field_name, gt_value in gt_fields.items():
        parsed_value = parsed_fields.get(field_name, "")
        
        # Normalisasi string untuk perbandingan
        gt_str = str(gt_value).strip().lower()
        parsed_str = str(parsed_value).strip().lower()
        
        # Hitung similarity ratio
        similarity = SequenceMatcher(None, gt_str, parsed_str).ratio()
        
        is_correct = similarity >= 0.9  # 90% similarity dianggap benar
        
        if is_correct:
            correct += 1
        
        details[field_name] = {
            "ground_truth": gt_value,
            "parsed": parsed_value,
            "correct": is_correct,
            "similarity": round(similarity * 100, 2)
        }
    
    accuracy = (correct / total * 100) if total > 0 else 0
    
    return {
        "total_fields": total,
        "correct": correct,
        "incorrect": total - correct,
        "accuracy": round(accuracy, 2),
        "details": details
    }


if __name__ == "__main__":
    # Testing mode (tanpa Laravel)
    cek = True
    while cek == True:
        dokument = input("Masukan dokument : ")
        
        file_map = {
            "survey": "input/pdf/Survey 1.pdf",
            "instalasi": "input/pdf/instalasi.pdf",
            "dismantle": "input/pdf/Dismantl.pdf",
            "aktivasi": "input/pdf/Aktifasi.pdf",
            "1": "input/pdf/form checklist maintenance remote wireless.pdf",
            "2": "input/pdf/form chcklisr wireline.pdf",
            "3": "input/pdf/Flasma - WIRELINE.pdf",
            "4": "input/pdf/FORM PM POP GRAND MALL BEKASI-5.pdf",
            "5": "input/pdf/Formulir Preventive Maintenance 1 Phase UPS.pdf"
            
        }
        
        file_path = file_map.get(dokument)
        
        if not file_path:
            print("Kaga ada dokument kaya gitu kocakkkk")
            exit()
        
        try:
            # Testing tanpa Laravel storage path
            pengecekan_file(file_path)
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        if input("Mau input lagi? (y/n) ") != "y":
            cek = False