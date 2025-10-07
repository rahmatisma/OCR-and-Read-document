import os
import json
from readers.pdf_reader import read_pdf
from readers.ocr.image_extractor import extract_and_classify_images
from readers.ocr.text_reader import run_ocr

OUTPUT_DIR = "output/json"

def save_output(data, filename):
    """Simpan hasil JSON ke folder output"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, filename + ".json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"[✅] Hasil disimpan di: {output_path}")

def pengecekan_file(file_path: str):
    """Deteksi tipe file dan jalankan pipeline yang sesuai"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{file_path}' tidak ditemukan.")

    base_name = os.path.splitext(os.path.basename(file_path))[0]

    if file_path.lower().endswith(".pdf"):
        print("[INFO] Proses PDF dimulai...")

        # 1️⃣ Proses teks & OCR
        text_result = read_pdf(file_path)

        # 2️⃣ Proses gambar (ttd & dokumentasi)
        image_result = extract_and_classify_images(file_path)

        # 3️⃣ Gabungkan hasil
        result = {
            "text_result": text_result,
            "image_result": image_result
        }

    elif file_path.lower().endswith((".jpg", ".jpeg", ".png")):
        print("[INFO] Proses gambar tunggal dimulai...")
        text = run_ocr(file_path)
        result = {"ocr_text": text}

    else:
        raise ValueError("Format file tidak didukung.")

    # 4️⃣ Simpan hasil ke JSON
    save_output(result, base_name)

if __name__ == "__main__":
    file_path = "input/pdf/Survey 1.pdf"
    pengecekan_file(file_path)
