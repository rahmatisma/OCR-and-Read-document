# readers/ocr/image_extractor.py
"""
Ekstraksi gambar dokumentasi - FINAL FIXED VERSION
- Bisa menangkap lanjutan halaman (misal "Foto Splitter" 2 halaman)
- Abaikan header seperti "SURVEY REPORT FO"
- Hanya berhenti di section baru yang benar-benar di atas halaman
"""

import fitz  # PyMuPDF
import os
import re
from .label_config import LabelConfig


def normalize_name(label: str) -> str:
    """Ubah label menjadi nama file yang aman."""
    name = label.lower().replace(" ", "_").replace("/", "_")
    return name


def get_nearby_text(page, rect, margin=200):
    """Ambil teks di sekitar rectangle."""
    clip_box = fitz.Rect(
        max(0, rect.x0 - 5),
        max(0, rect.y0 - 5),
        min(page.rect.width, rect.x1 + margin),
        rect.y1 + 5
    )
    text = page.get_textbox(clip_box).strip()
    return re.sub(r'\s+', ' ', text)


def find_exact_label(page, label, exclude_keywords=None):
    """Cari label dengan exact matching dan pengecualian kata tertentu."""
    if exclude_keywords is None:
        exclude_keywords = []

    text_instances = page.search_for(label, quads=False)
    if not text_instances:
        return None

    for rect in text_instances:
        nearby = get_nearby_text(page, rect, margin=250).lower()
        if any(keyword.lower() in nearby for keyword in exclude_keywords):
            continue
        return rect
    return None


def has_any_label_from_list(page, target_labels):
    """Cek apakah halaman ini punya label apapun dari list."""
    text = page.get_text("text").lower()
    for label in target_labels:
        if label.lower() in text:
            instances = page.search_for(label, quads=False)
            if instances:
                return True
    return False


def get_exclude_keywords_for_label(label):
    """Kata yang harus dihindari agar tidak salah tangkap."""
    exclude_map = {
        "dokumentasi foto": ["provisioning"],
    }
    return exclude_map.get(label.lower(), [])


def crop_from_label(page, label_rect):
    """Crop dari bawah label sampai akhir halaman."""
    crop_box = fitz.Rect(
        0,
        label_rect.y1 + 30,
        page.rect.width,
        page.rect.height
    )
    return page.get_pixmap(clip=crop_box)


def crop_full_page(page):
    """Crop seluruh halaman."""
    return page.get_pixmap()


def is_valid_continuation_page(page, target_labels):
    """Validasi halaman lanjutan (tanpa label baru & cukup konten)."""
    text = page.get_text("text")
    text_upper = text.upper()

    # Jika ada label lain → bukan lanjutan
    if has_any_label_from_list(page, target_labels):
        return False, False, None

    ignored_headers = ["SURVEY REPORT", "JARINGAN :", "LINTASARTA"]
    non_continuation_keywords = [
        "DATA PENEMPATAN PERANGKAT DI LOKASI PELANGGAN",
        "FOTO JALUR KABEL DALAM GEDUNG",
        "PLAN JALUR DALAM GEDUNG",
        "DATA PERIZINAN DAN BIAYA YANG TIMBUL DALAM KAWASAN",
        "DATA HH EKSISTING YANG DIPAKAI",
        "DATA HH BARU",
        "DATA TIANG EKSISTING",
    ]

    for keyword in non_continuation_keywords:
        if any(ignored in keyword for ignored in ignored_headers):
            continue
        if keyword in text_upper:
            return False, False, None

    cleaned = text
    for ig in ignored_headers:
        cleaned = cleaned.replace(ig, "")
    if len(cleaned.strip()) < 20:
        return False, False, None

    return True, False, None


def extract_and_classify_images(pdf_path, doc_type, output_dir="output/images"):
    """
    Ekstraksi gambar:
    - Tangkap halaman berurutan (multi-page)
    - Lanjut terus sampai ketemu label baru / section baru (di atas halaman)
    - Jika ada teks section baru di tengah halaman, crop hanya sampai situ
    """
    target_labels = LabelConfig.get_labels(doc_type)
    if not target_labels:
        print(f"[ERROR] Tidak ada label untuk doc_type: {doc_type}")
        return []

    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    print(f"[INFO] Membuka {pdf_path} dengan {len(doc)} halaman...")
    print(f"[INFO] Menggunakan {len(target_labels)} label untuk {doc_type}")

    results = []
    processed_pages = set()

    for page_num in range(len(doc)):
        if page_num in processed_pages:
            continue

        page = doc[page_num]

        # Cek setiap label di halaman ini
        for label in target_labels:
            exclude_keywords = get_exclude_keywords_for_label(label)
            label_rect = find_exact_label(page, label, exclude_keywords)

            if label_rect:
                print(f"[INFO] Menemukan '{label}' di halaman {page_num + 1}")

                # Crop dari bawah label sampai akhir halaman
                pix = crop_from_label(page, label_rect)
                if pix:
                    filename = f"{normalize_name(label)}_hal{page_num + 1}.jpg"
                    out_path = os.path.join(output_dir, filename)
                    pix.save(out_path)
                    print(f"[OK] {label} → {out_path}")

                    results.append({"jenis": label, "patch_foto": out_path})
                    processed_pages.add(page_num)

                # === LOOP UNTUK HALAMAN BERIKUTNYA ===
                next_page_num = page_num + 1
                while next_page_num < len(doc):
                    next_page = doc[next_page_num]
                    text_upper = next_page.get_text("text").upper()

                    ignored_headers = ["SURVEY REPORT", "JARINGAN :", "LINTASARTA", "PORT KOSONG"]
                    found_new_label = False
                    section_in_top_area = False
                    next_section_y = None

                    # 1️⃣ Cek apakah halaman berikut mengandung label baru
                    for next_label in target_labels:
                        if next_label.lower() != label.lower() and next_label.lower() in text_upper.lower():
                            found_new_label = True
                            break

                    # 2️⃣ Cek posisi section baru berdasarkan header
                    section_keywords = [
                        "DATA PENEMPATAN PERANGKAT DI LOKASI PELANGGAN",
                        "FOTO JALUR KABEL DALAM GEDUNG",
                        "PLAN JALUR DALAM GEDUNG",
                        "DATA PERIZINAN DAN BIAYA YANG TIMBUL DALAM KAWASAN",
                        "DATA SPLITTER",
                        "DATA HH EKSISTING YANG DIPAKAI",
                        "DATA HH BARU",
                        "DATA TIANG EKSISTING",
                    ]

                    for keyword in section_keywords:
                        rects = next_page.search_for(keyword)
                        if rects:
                            avg_y = sum([r.y0 for r in rects]) / len(rects)
                            if avg_y < next_page.rect.height * 0.3:  # header di bagian atas
                                section_in_top_area = True
                                found_new_label = True
                                break
                            else:
                                # Header di tengah halaman → potong sampai sebelum section
                                next_section_y = min([r.y0 for r in rects])
                                found_new_label = True
                                section_in_top_area = False
                                break

                    # 3️⃣ Logika berhenti atau potong
                    if found_new_label and section_in_top_area:
                        print(f"[INFO] Halaman {next_page_num + 1}: Ditemukan label/section baru → stop continuation.")
                        break

                    elif found_new_label and not section_in_top_area and next_section_y:
                        print(f"[INFO] Halaman {next_page_num + 1}: Potong sampai sebelum section berikutnya.")
                        crop_box = fitz.Rect(0, 0, next_page.rect.width, next_section_y - 30)
                        cont_pix = next_page.get_pixmap(clip=crop_box)

                    else:
                        # Tidak ada section baru → ambil seluruh halaman
                        cont_pix = crop_full_page(next_page)

                    # Simpan hasil continuation
                    cont_filename = f"{normalize_name(label)}_hal{next_page_num + 1}.jpg"
                    cont_out_path = os.path.join(output_dir, cont_filename)
                    cont_pix.save(cont_out_path)
                    print(f"[OK] Continuation → {cont_out_path}")

                    results.append({"jenis": label, "patch_foto": cont_out_path})
                    processed_pages.add(next_page_num)

                    next_page_num += 1

                break  # stop setelah label pertama di halaman ini

    doc.close()
    print(f"\n[INFO] ✓ Selesai ekstraksi. Total gambar: {len(results)}")
    return results

