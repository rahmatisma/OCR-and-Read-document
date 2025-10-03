import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from utils.ocr import read_image  # OCR hanya terima gambar, balikin teks
from parsers.dispatcher import dispatch_parser  # parser template

def read_pdf(pdf_path: str, debug: bool = True) -> dict:
    """
    Membaca PDF halaman per halaman:
    - Jika ada teks → langsung dipakai
    - Jika kosong → convert ke image, lalu OCR
    - Setelah terkumpul → lempar ke dispatcher parser
    """
    doc = fitz.open(pdf_path)

    all_text = ""
    per_page_text = []

    for page_number, page in enumerate(doc, start=1):
        # Ambil teks bawaan PDF
        text = page.get_text("text").strip()

        if not text:
            print(f"[INFO] Halaman {page_number} kosong → OCR dijalankan...")
            pix = page.get_pixmap()
            mode = "RGBA" if pix.alpha else "RGB"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)

            # Konversi ke numpy array untuk OCR
            img_np = np.array(img)
            ocr_text = read_image(img_np)
            text = ocr_text.strip()

        all_text += text + "\n"
        per_page_text.append({"halaman": page_number, "text": text})

    # --- lempar ke dispatcher parser untuk pilih template ---
    parsed_result = dispatch_parser(all_text, per_page_text)

    result = {"parsed": parsed_result}

    if debug:
        result["_debug"] = {
            "per_page_text": per_page_text,
            "raw_all_text": all_text
        }

    return result
