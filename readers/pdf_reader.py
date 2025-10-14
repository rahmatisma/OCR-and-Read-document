import fitz
from readers.ocr.processor import process_pdf_with_images, process_page_ocr
from parsers.dispatcher import dispatch_parser


def read_pdf(pdf_path: str, debug: bool = True) -> dict:
    """
    Membaca dokumen PDF:
    - Mengambil teks (langsung atau OCR jika tidak ada)
    - Memanggil processor untuk ekstraksi gambar (tanda tangan & dokumentasi)
    - Menggabungkan hasil ke satu struktur JSON
    """

    print(f"[INFO] Membaca dokumen PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    all_text = ""
    per_page_text = []

    # 🔹 Langkah 1: Ambil teks per halaman
    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()

        if not text:
            print(f"[INFO] Halaman {page_number} kosong → OCR dijalankan...")
            text = process_page_ocr(page)

        all_text += text + "\n"
        per_page_text.append({"halaman": page_number, "text": text})

    # 🔹 Langkah 2: Jalankan processor untuk ekstraksi tanda tangan & dokumentasi
    print(f"[INFO] Menjalankan ekstraksi gambar (tanda tangan & dokumentasi)...")
    processed_images = process_pdf_with_images(pdf_path)

    # 🔹 Langkah 3: Gabungkan hasil teks + gambar
    parsed_result = dispatch_parser(all_text, per_page_text)

    result = {
        "tanda_tangan": processed_images.get("tanda_tangan", []),
        "dokumentasi": processed_images.get("dokumentasi", []),
        "parsed": parsed_result
    }

    if debug:
        result["_debug"] = {"raw_all_text": all_text}

    doc.close()
    return result
