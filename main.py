import os
import json
from readers.pdf_reader import read_pdf
# from readers.ocr.text_reader import run_ocr

OUTPUT_DIR = "output/json"

def save_output(data, filename):
    """Simpan hasil JSON ke folder output"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, filename + ".json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Hasil disimpan di: {output_path}")


def pengecekan_file(file_path: str):
    """Deteksi tipe file dan jalankan pipeline yang sesuai"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{file_path}' tidak ditemukan.")

    base_name = os.path.splitext(os.path.basename(file_path))[0]

    if file_path.lower().endswith(".pdf"):
        print("[INFO] Proses PDF dimulai...")
        # Jalankan pipeline utama PDF (OCR + parsing + ekstraksi gambar)
        result = read_pdf(file_path)

    # elif file_path.lower().endswith((".jpg", ".jpeg", ".png")):
    #     print("[INFO] Proses gambar tunggal dimulai...")
    #     text = run_ocr(file_path)
    #     result = {"ocr_text": text}

    else:
        raise ValueError("Format file tidak didukung.")

    # Simpan hasil ke JSON
    save_output(result, base_name)


if __name__ == "__main__":
    cek = True
    while cek == True:
        # Ganti path sesuai file input kamu
        dokument = "1"  # survey / instalasi / dismantle
        if dokument == "survey":
            file_path = "input/pdf/Survey 1.pdf"
        elif dokument == "instalasi":
            file_path = "input/pdf/instalasi.pdf"
        elif dokument == "dismantle":
            file_path = "input/pdf/Dismantl.pdf"
        elif dokument == "aktivasi":
            file_path = "input/pdf/Aktifasi.pdf"
        elif dokument == "1":
            file_path = "input/pdf/form checklist maintenance remote wireless-debug 1-2.pdf"
        elif dokument == "2":
            file_path = "input/pdf/form chcklisr wireline.pdf"
        elif dokument == "3":
            file_path = "input/pdf/Flasma - WIRELINE.pdf"
        else:
            print("Kaga ada dokument kaya gitu kocakkkk")
            exit()
        pengecekan_file(file_path)
        if input("Mau input lagi? (y/n)") != "y":
            cek = False

