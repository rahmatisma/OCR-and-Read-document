import os
import json
from readers.pdf_reader import read_pdf
from readers.ocr.text_reader import run_ocr

OUTPUT_DIR = "output"

def save_output(data, filename, subfolder=None):
    """Simpan hasil JSON ke folder output"""
    if subfolder:
        output_folder = os.path.join(OUTPUT_DIR, subfolder)
    else:
        output_folder = OUTPUT_DIR
    
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename + ".json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ JSON disimpan di: {output_path}")


def pengecekan_file(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{file_path}' tidak ditemukan.")

    base_name = os.path.splitext(os.path.basename(file_path))[0]

    if file_path.lower().endswith(".pdf"):
        print(f"\n{'='*60}")
        print(f"📄 Memproses PDF: {base_name}")
        print(f"{'='*60}\n")
        
        # 1. Buat folder untuk dokumen ini
        doc_folder = os.path.join(OUTPUT_DIR, base_name)
        images_folder = os.path.join(doc_folder, "images")
        os.makedirs(images_folder, exist_ok=True)
        
        print(f"📁 Folder dibuat: {doc_folder}")
        print(f"📁 Folder gambar: {images_folder}\n")
        
        # 2. Proses PDF dengan output_dir yang sudah ditentukan
        result = read_pdf(file_path, output_dir=images_folder)
        
        # 3. Simpan JSON di folder dokumen
        save_output(result, base_name, subfolder=base_name)
        
        print(f"\n{'='*60}")
        print(f"✅ Selesai! Hasil disimpan di: {doc_folder}")
        print(f"{'='*60}\n")

    elif file_path.lower().endswith((".jpg", ".jpeg", ".png")):
        print("[INFO] Proses gambar tunggal dimulai...")
        text = run_ocr(file_path)
        result = {"ocr_text": text}
        
        # Simpan JSON di folder output utama
        save_output(result, base_name)

    else:
        raise ValueError("Format file tidak didukung.")

    return result


# if __name__ == "__main__":
#     cek = True
#     while cek == True:
#         # Ganti path sesuai file input kamu
#         dokument = input("Masukan dokument : ")  # survey / instalasi / dismantle
#         if dokument == "survey":
#             file_path = "input/pdf/Survey 1.pdf"
#         elif dokument == "instalasi":
#             file_path = "input/pdf/instalasi.pdf"
#         elif dokument == "dismantle":
#             file_path = "input/pdf/Dismantl.pdf"
#         elif dokument == "aktivasi":
#             file_path = "input/pdf/Aktifasi.pdf"
#         elif dokument == "1":
#             file_path = "input/pdf/form checklist maintenance remote wireless.pdf"
#         elif dokument == "2":
#             file_path = "input/pdf/form chcklisr wireline.pdf"
#         elif dokument == "3":
#             file_path = "input/pdf/Flasma - WIRELINE.pdf"
#         else:
#             print("Kaga ada dokument kaya gitu kocakkkk")
#             exit()
        
#         try:
#             pengecekan_file(file_path)
#         except Exception as e:
#             print(f"❌ Error: {e}")
#             import traceback
#             traceback.print_exc()
        
#         if input("Mau input lagi? (y/n) ") != "y":
#             cek = False