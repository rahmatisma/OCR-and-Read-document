import sys
import os
import json
from readers.pdf_reader import read_pdf
from utils.ocr import read_image

OUTPUT_DIR = "output"

def save_output(data, filename):
    """Simpan hasil JSON ke folder output"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    output_path = os.path.join(OUTPUT_DIR, filename + ".json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Hasil disimpan di: {output_path}")

def pengecekan_file(file_path: str):
    # Tentukan jenis file berdasarkan ekstensi
    if file_path.lower().endswith(".pdf"):
        result = read_pdf(file_path,"pdf")
    # elif file_path.lower().endswith((".doc", ".docx")):
    #     result = extract_from_doc(file_path)
    elif file_path.lower().endswith((".jpg", ".jpeg", ".png")):
        result = read_image(file_path)
    else:
        raise ValueError("Format file tidak didukung")

    # Simpan hasil ke JSON
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    save_output(result, base_name)

if __name__ == "__main__":
    file_path = "input/pdf/Survey 1.pdf"
    pengecekan_file(file_path)
