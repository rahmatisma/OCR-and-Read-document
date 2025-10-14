# readers/ocr/processor.py

import os
import numpy as np
from PIL import Image
import fitz
from readers.ocr.text_reader import run_ocr
from readers.ocr.image_extractor import extract_and_classify_images


def ensure_dir(path):
    """Pastikan direktori ada sebelum digunakan."""
    if not os.path.exists(path):
        os.makedirs(path)


def process_page_ocr(page) -> str:
    """
    Proses OCR pada satu halaman PDF:
    - Render halaman ke gambar (numpy array)
    - Kirim ke OCR
    - Kembalikan teks hasilnya
    """
    try:
        pix = page.get_pixmap()
        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        img_np = np.array(img)

        text = run_ocr(img_np)
        return text.strip()

    except Exception as e:
        print(f"[ERROR] Gagal OCR halaman: {e}")
        return ""


def process_pdf_with_images(pdf_path, output_dir="output/images"):
    """
    Jalankan pipeline lengkap:
    1. Jalankan ekstraksi & klasifikasi gambar (melalui image_extractor)
    2. Kembalikan hasil ke struktur siap parser
    """
    print(f"[INFO] Mengekstrak gambar dari PDF: {pdf_path}")

    results = {
        "tanda_tangan": [],
        "dokumentasi": []
    }

    try:
        ensure_dir(output_dir)
        img_results = extract_and_classify_images(pdf_path, output_dir=output_dir)

        # # --- Tanda tangan ---
        # for ttd_item in img_results.get("ttd", []):
        #     results["tanda_tangan"].append({
        #         "peran": None,              # diisi nanti oleh parser
        #         "patch_image": ttd_item.get("file"),  # ganti nama field
        #         "nama": None
        #     })

        # # --- Dokumentasi ---
        # for doc_item in img_results.get("dokumentasi", []):
        #     results["dokumentasi"].append({
        #         "jenis": None,                    # diisi nanti oleh parser
        #         "patch_foto": doc_item.get("file"),
        #         "keterangan": None
        #     })

        return results

    except Exception as e:
        print(f"[ERROR] Gagal mengekstrak gambar PDF: {e}")
        return results
