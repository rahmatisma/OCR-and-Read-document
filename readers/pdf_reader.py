import fitz
from readers.ocr.processor import process_page_ocr
from parsers.dispatcher import dispatch_parser

def read_pdf(pdf_path: str, debug: bool = True) -> dict:
    doc = fitz.open(pdf_path)
    all_text = ""
    per_page_text = []

    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()

        if not text:
            print(f"[INFO] Halaman {page_number} kosong → OCR dijalankan...")
            text = process_page_ocr(page)

        all_text += text + "\n"
        per_page_text.append({"halaman": page_number, "text": text})

    parsed_result = dispatch_parser(all_text, per_page_text)

    result = {
        "metadata": {
            "source": pdf_path,
            "total_pages": len(doc)
        },
        "raw_text": all_text,
        "pages": per_page_text,
        "parsed": parsed_result
    }

    if debug:
        result["_debug"] = {"raw_all_text": all_text}

    return result
