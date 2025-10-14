# debug_extract_dokumentasi.py
import fitz  # PyMuPDF
import os

# Daftar label teks yang akan dicari
TARGET_LABELS = [
    "Dokumentasi foto",
    "Foto penempatan perangkat di lokasi pelanggan",
    "Foto jalur kabel dalam gedung",
    "Plan jalur dalam gedung",
    "Data jalur kabel",
    "Foto splitter",
    "Foto hh eksisting yang dipakai",
    "Foto lokasi hh baru"
]

PDF_PATH = "input/pdf/Survey 1.pdf"
OUTPUT_DIR = "output/images"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def normalize_name(label: str) -> str:
    """Ubah label menjadi nama file yang aman."""
    name = label.lower().replace(" ", "_").replace("/", "_")
    return name

def crop_after_label(page, label_text):
    """Cari posisi label di halaman dan crop area di bawahnya."""
    text_instances = page.search_for(label_text, quads=False)
    if not text_instances:
        return None  # Tidak ditemukan teksnya

    # Ambil posisi label terakhir (asumsi paling bawah adalah yang relevan)
    rect = text_instances[-1]
    page_height = page.rect.height

    # Crop mulai sedikit di bawah teks (misal +30 pixel)
    crop_box = fitz.Rect(0, rect.y1 + 30, page.rect.width, page_height)
    pix = page.get_pixmap(clip=crop_box)
    return pix

def main():
    doc = fitz.open(PDF_PATH)
    print(f"[INFO] Membuka {PDF_PATH} dengan {len(doc)} halaman...")

    for page_num, page in enumerate(doc, start=1):
        text_page = page.get_text("text").lower()
        for label in TARGET_LABELS:
            if label.lower() in text_page:
                pix = crop_after_label(page, label)
                if pix:
                    filename = f"{normalize_name(label)}_hal{page_num}.jpg"
                    out_path = os.path.join(OUTPUT_DIR, filename)
                    pix.save(out_path)
                    print(f"{label} → disimpan: {out_path}")
                else:
                    print(f"Tidak bisa crop {label} di halaman {page_num}")
    doc.close()
    print("[Selesai]")

if __name__ == "__main__":
    main()
