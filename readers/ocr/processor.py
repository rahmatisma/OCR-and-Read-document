# pipeline utama ocr/penggabungan gambar dan atribut
# ocr/processor.py

import numpy as np
from PIL import Image
from readers.ocr.text_reader import run_ocr

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

        # Panggil fungsi OCR dari utils
        text = run_ocr(img_np)
        return text.strip()

    except Exception as e:
        print(f"[ERROR] Gagal OCR halaman: {e}")
        return ""
