"""
Ekstraksi gambar dokumentasi - FIXED HEADER VALIDATION
- Validasi bahwa label yang ditemukan adalah HEADER, bukan teks biasa
- Skip label yang ada di deskripsi/caption foto
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


def is_valid_header(page, rect, label, min_font_size=10):
    """
    Validasi apakah rect ini adalah HEADER section.
    
    Kriteria UTAMA:
    1. Font size >= min_font_size (default 10pt) → Header pasti font besar
    2. Tidak ada teks di kiri → Bukan bagian dari kalimat (seperti "Capture hasil aktivasi")
    
    Posisi tidak dijadikan kriteria utama karena header bisa muncul di berbagai posisi.
    """
    
    # 1️⃣ CEK FONT SIZE - Kriteria paling penting!
    text_blocks = page.get_text("dict")["blocks"]
    label_font_size = None
    
    for block in text_blocks:
        if block.get("type") == 0:  # Text block
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    span_bbox = fitz.Rect(span["bbox"])
                    if span_bbox.intersects(rect):
                        label_font_size = span.get("size", 0)
                        break
                if label_font_size:
                    break
        if label_font_size:
            break
    
    if label_font_size is None:
        print(f"   [SKIP] '{label}' - font size tidak terdeteksi")
        return False
    
    if label_font_size < min_font_size:
        print(f"   [SKIP] '{label}' - font terlalu kecil: {label_font_size:.1f}pt (minimum: {min_font_size}pt)")
        return False
    
    # 2️⃣ CEK KONTEKS KIRI: Pastikan standalone (bukan bagian dari kalimat)
    left_margin = 100
    left_check_box = fitz.Rect(
        max(0, rect.x0 - left_margin),
        rect.y0 - 3,
        rect.x0 - 5,  # Sedikit gap dari rect
        rect.y1 + 3
    )
    left_text = page.get_textbox(left_check_box).strip()
    
    # Jika ada teks di kiri yang panjang (seperti "Capture"), ini bukan header
    if left_text and len(left_text) > 3:
        print(f"   [SKIP] '{label}' - ada awalan: '{left_text}'")
        return False
    
    # 3️⃣ CEK POSISI (opsional, hanya untuk ekstrem case)
    relative_y = rect.y0 / page.rect.height
    if relative_y > 0.85:  # Hanya skip kalau benar-benar di paling bawah
        print(f"   [SKIP] '{label}' - posisi terlalu bawah: {relative_y:.1%}")
        return False
    
    print(f"   [✓] '{label}' header valid (pos: {relative_y:.1%}, font: {label_font_size:.1f}pt)")
    return True


def find_exact_label(page, label, exclude_keywords=None):
    """
    Cari label dengan exact matching dan validasi header.
    """
    if exclude_keywords is None:
        exclude_keywords = []

    text_instances = page.search_for(label, quads=False)
    if not text_instances:
        return None

    for rect in text_instances:
        # Cek exclude keywords
        nearby = get_nearby_text(page, rect, margin=250).lower()
        if any(keyword.lower() in nearby for keyword in exclude_keywords):
            continue
        
        # ✨ VALIDASI HEADER - INI YANG BARU!
        if not is_valid_header(page, rect, label):
            continue
        
        return rect
    
    return None


def get_exclude_keywords_for_label(label):
    """Kata yang harus dihindari agar tidak salah tangkap."""
    exclude_map = {
        "dokumentasi foto": ["provisioning"],
        "hasil aktivasi": ["capture", "dokumentasi foto"],  # Tambahan: hindari "Capture hasil aktivasi"
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


def generate_section_keywords(target_labels):
    """
    Generate section keywords dari target_labels + keywords umum.
    Untuk deteksi section baru saat continuation.
    """
    common_keywords = [
        "DATA PENEMPATAN PERANGKAT DI LOKASI PELANGGAN",
        "DATA PERIZINAN DAN BIAYA YANG TIMBUL DALAM KAWASAN",
        "DATA PERIZINAN DAN BIAYA YANG TIMBUL DALAM GEDUNG",
        "DATA SPLITTER",
        "DATA HH EKSISTING YANG DIPAKAI",
        "DATA HH BARU",
        "DATA TIANG EKSISTING",
        "DATA TIANG BARU",
        "DATA KAWASAN UMUM",
        "DATA JALUR KABEL",
        "TIME FRAME PEKERJAAN",
        "INFO LAIN LAIN",
        "BOQ FO",
        "BERITA ACARA",
    ]
    
    all_keywords = list(set([label.upper() for label in target_labels] + common_keywords))
    
    return all_keywords


def extract_and_classify_images(pdf_path, doc_type, output_dir="output/images"):
    """
    Ekstraksi gambar berdasarkan label di label_config.
    Langsung pakai semua label tanpa filtering.
    """
    all_labels = LabelConfig.get_labels(doc_type)
    if not all_labels:
        print(f"[ERROR] Tidak ada label untuk doc_type: {doc_type}")
        return []

    # Langsung pakai semua label dari config (tidak ada filtering!)
    target_labels = all_labels
    
    if not target_labels:
        print(f"[WARNING] Tidak ada label ditemukan untuk {doc_type}")
        return []
    
    print(f"[INFO] Total label yang akan diproses: {len(target_labels)}")
    print(f"[INFO] Label: {target_labels}")

    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    print(f"[INFO] Membuka {pdf_path} dengan {len(doc)} halaman...")

    results = []
    processed_pages = set()

    processed_label_per_page = {}  # Track label yang sudah di-proses per halaman
    
    for page_num in range(len(doc)):
        page = doc[page_num]

        # Cek setiap label di halaman ini
        for label in target_labels:
            # Skip kalau label ini sudah di-proses di halaman ini
            if processed_label_per_page.get(page_num) == label:
                continue
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
                    processed_label_per_page[page_num] = label  # Mark label ini sudah di-proses

                # === LOOP UNTUK HALAMAN BERIKUTNYA (CONTINUATION) ===
                next_page_num = page_num + 1
                while next_page_num < len(doc):
                    next_page = doc[next_page_num]
                    text_upper = next_page.get_text("text").upper()

                    ignored_headers = ["SURVEY REPORT", "JARINGAN :", "LINTASARTA", "PORT KOSONG", "INSTALASI REPORT"]
                    found_new_label = False
                    section_in_top_area = False
                    next_section_y = None

                    # 0️⃣ CEK DULU: apakah halaman ini berisi section non-foto di atas?
                    non_foto_keywords = [
                        "BOQ ETHERNET", "BOQ FO", "BOQ", "LIST ITEM", "BERITA ACARA",
                        "DOKUMENTASI FOTO PROVISIONING", "TIME FRAME PEKERJAAN"
                    ]
                    
                    for keyword in non_foto_keywords:
                        if keyword in text_upper:
                            rects = next_page.search_for(keyword)
                            if rects:
                                avg_y = sum([r.y0 for r in rects]) / len(rects)
                                if avg_y < next_page.rect.height * 0.3:
                                    print(f"[INFO] Halaman {next_page_num + 1}: Section non-foto '{keyword}' di atas → stop continuation")
                                    found_new_label = True
                                    section_in_top_area = True
                                    break

                    if found_new_label and section_in_top_area:
                        print(f"[INFO] Stop continuation karena section non-foto di atas")
                        break

                    # 🔍 CEK: Apakah halaman ini hanya berisi sedikit teks (halaman transisi)?
                    # Jika ya, ambil seluruh halaman tanpa deteksi section
                    text_content = next_page.get_text("text").strip()
                    word_count = len(text_content.split())
                    
                    if word_count < 20:  # Halaman dengan sedikit konten
                        # ⚠️ PENTING: Cek dulu apakah ada label BARU di halaman ini!
                        has_new_label = False
                        for check_label in target_labels:
                            if check_label.lower() != label.lower():
                                check_rects = next_page.search_for(check_label)
                                if check_rects:
                                    for check_rect in check_rects:
                                        if is_valid_header(next_page, check_rect, check_label):
                                            has_new_label = True
                                            print(f"[INFO] Halaman {next_page_num + 1}: Konten sedikit tapi ada label baru '{check_label}' → stop continuation")
                                            break
                            if has_new_label:
                                break
                        
                        # Kalau ada label baru, stop continuation (biar halaman ini di-proses di iterasi berikutnya)
                        if has_new_label:
                            break
                        
                        # Kalau tidak ada label baru, ambil sebagai continuation
                        print(f"[INFO] Halaman {next_page_num + 1}: Konten sedikit ({word_count} kata), ambil seluruh halaman")
                        cont_pix = crop_full_page(next_page)
                        
                        # Simpan langsung tanpa validasi section
                        cont_filename = f"{normalize_name(label)}_hal{next_page_num + 1}.jpg"
                        cont_out_path = os.path.join(output_dir, cont_filename)
                        cont_pix.save(cont_out_path)
                        print(f"[OK] Continuation '{label}' → {cont_out_path}")
                        
                        results.append({"jenis": label, "patch_foto": cont_out_path})
                        processed_label_per_page[next_page_num] = label
                        
                        next_page_num += 1
                        continue

                    # 1️⃣ Cek apakah halaman berikut mengandung label FOTO baru
                    for next_label in target_labels:
                        if next_label.lower() != label.lower() and next_label.lower() in text_upper.lower():
                            label_rects = next_page.search_for(next_label)
                            if label_rects:
                                # Validasi apakah ini header
                                for next_rect in label_rects:
                                    if is_valid_header(next_page, next_rect, next_label):
                                        found_new_label = True
                                        section_in_top_area = True
                                        print(f"[INFO] Halaman {next_page_num + 1}: Label dari config '{next_label}' ditemukan → stop")
                                        break
                            if found_new_label:
                                break

                    # 2️⃣ Generate section keywords
                    section_keywords = generate_section_keywords(all_labels)

                    # 3️⃣ Cek posisi section baru berdasarkan section keywords
                    if not found_new_label:
                        for keyword in section_keywords:
                            if keyword.upper() == label.upper():
                                continue
                            
                            if any(ignored in keyword for ignored in ignored_headers):
                                continue
                            
                            rects = next_page.search_for(keyword)
                            if rects:
                                avg_y = sum([r.y0 for r in rects]) / len(rects)
                                if avg_y < next_page.rect.height * 0.3:
                                    section_in_top_area = True
                                    found_new_label = True
                                    print(f"[INFO] Halaman {next_page_num + 1}: Section '{keyword}' di atas → stop continuation")
                                    break
                                else:
                                    next_section_y = min([r.y0 for r in rects])
                                    found_new_label = True
                                    section_in_top_area = False
                                    print(f"[INFO] Halaman {next_page_num + 1}: Section '{keyword}' di tengah → crop sebagian")
                                    break

                    # 4️⃣ Logika berhenti atau potong
                    if found_new_label and section_in_top_area:
                        print(f"[INFO] Stop continuation karena section baru di atas")
                        break

                    elif found_new_label and not section_in_top_area and next_section_y:
                        print(f"[INFO] Crop sebagian halaman (ada section di tengah)")
                        crop_box = fitz.Rect(0, 0, next_page.rect.width, next_section_y - 30)
                        
                        # Validasi: Cek apakah area yang akan di-crop berisi section non-foto
                        crop_text = next_page.get_textbox(crop_box).upper()
                        
                        non_foto_validation_keywords = [
                            "DATA PERIZINAN", "DATA KAWASAN", "DATA SPLITTER", 
                            "DATA HH EKSISTING", "DATA HH BARU", "DATA TIANG",
                            "BOQ", "LIST ITEM", "BERITA ACARA",
                            "DOKUMENTASI FOTO PROVISIONING"
                        ]
                        
                        has_non_foto_section = any(keyword in crop_text for keyword in non_foto_validation_keywords)
                        
                        if has_non_foto_section:
                            print(f"[SKIP] Area crop berisi section non-foto, skip continuation")
                            break
                        
                        cont_pix = next_page.get_pixmap(clip=crop_box)

                    else:
                        # Tidak ada section baru → ambil seluruh halaman
                        cont_pix = crop_full_page(next_page)

                    # ✅ VALIDASI: Cek apakah hasil crop cukup tinggi (minimal 20% tinggi halaman)
                    min_height = next_page.rect.height * 0.2
                    if cont_pix.height < min_height:
                        print(f"[SKIP] Continuation terlalu kecil ({cont_pix.height}px < {min_height:.0f}px), skip halaman {next_page_num + 1}")
                        break

                    # Simpan hasil continuation
                    cont_filename = f"{normalize_name(label)}_hal{next_page_num + 1}.jpg"
                    cont_out_path = os.path.join(output_dir, cont_filename)
                    cont_pix.save(cont_out_path)
                    print(f"[OK] Continuation '{label}' → {cont_out_path}")

                    results.append({"jenis": label, "patch_foto": cont_out_path})
                    
                    if not (found_new_label and not section_in_top_area):
                        processed_pages.add(next_page_num)

                    if found_new_label and not section_in_top_area:
                        print(f"[INFO] Stop continuation, halaman {next_page_num + 1} akan diproses ulang untuk label baru")
                        break

                    next_page_num += 1

                break

    doc.close()
    print(f"\n[INFO] ✓ Selesai ekstraksi. Total gambar: {len(results)}")
    return results