import fitz  # PyMuPDF
import os
import io
from PIL import Image
import numpy as np

# ---------- helper fitur gambar ----------
def image_features_from_bytes(image_bytes, thumb_max=200):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img.size
    gray = np.array(img.convert("L"))

    hist = np.bincount(gray.flatten(), minlength=256).astype(float)
    hist = hist / (hist.sum() + 1e-12)
    entropy = -np.sum(hist * np.log2(hist + 1e-12))

    arr = np.array(img)
    prop_white = np.mean(np.all(arr > [240, 240, 240], axis=2))
    prop_dark  = np.mean(np.all(arr < [80, 80, 80], axis=2))
    prop_yellow = np.mean((arr[:,:,0] > 150) & (arr[:,:,1] > 150) & (arr[:,:,2] < 120))

    thumb = img.copy()
    thumb.thumbnail((thumb_max, thumb_max))
    thumb_arr = np.array(thumb).reshape(-1, 3)
    unique_colors = len(np.unique(thumb_arr, axis=0))

    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    edge = np.zeros_like(gray, dtype=float)
    edge[:,1:] += gx
    edge[1:,:] += gy
    edge_density = float((edge > 30).mean())

    return {
        "size": (w, h),
        "entropy": float(entropy),
        "unique_colors": int(unique_colors),
        "prop_white": float(prop_white),
        "prop_dark": float(prop_dark),
        "prop_yellow": float(prop_yellow),
        "edge_density": float(edge_density),
        "pil_size": (w, h),
        "pil_image": img
    }

# ---------- classifier ----------
def classify_features(feat, thresholds=None):
    t = {
        "tiny_w": 100, "tiny_h": 100,
        "orn_h": 120, "orn_entropy": 1.8, "orn_edge": 0.02,
        "logo_dark_prop": 0.6, "logo_max_w": 500, "logo_max_h": 300,
        "ttd_white_prop": 0.6, "ttd_dark_prop": 0.25, "ttd_edge": 0.04,
        "dokumentasi_entropy": 4.5, "dokumentasi_colors": 10000, "dokumentasi_edge": 0.5,
        "area_dokumentasi": 200000
    }
    if thresholds:
        t.update(thresholds)

    w, h = feat["size"]
    entropy = feat["entropy"]
    unique_colors = feat["unique_colors"]
    prop_white = feat["prop_white"]
    prop_dark = feat["prop_dark"]
    prop_yellow = feat["prop_yellow"]
    edge_density = feat["edge_density"]
    area = w * h

    # aturan skip
    if w < t["tiny_w"] and h < t["tiny_h"]:
        return "skip", "tiny_logo"
    if h < t["orn_h"] and entropy < t["orn_entropy"] and edge_density < t["orn_edge"]:
        return "skip", "ornament_banner"
    if prop_dark > t["logo_dark_prop"] and w < t["logo_max_w"] and h < t["logo_max_h"]:
        return "skip", "dark_logo"

    # ttd
    if prop_white > t["ttd_white_prop"] and prop_dark < t["ttd_dark_prop"] and edge_density > t["ttd_edge"]:
        return "ttd", "white_bg_stroke"

    # dokumentasi
    if entropy > t["dokumentasi_entropy"] or unique_colors > t["dokumentasi_colors"] or prop_yellow > 0.001 or edge_density > t["dokumentasi_edge"]:
        return "dokumentasi", "photo_features"

    if area > t["area_dokumentasi"]:
        return "dokumentasi", "area_big"
    if prop_white > 0.5 and edge_density > 0.03:
        return "ttd", "white_and_some_edge"

    if h < 150 and w < 400:
        return "skip", "small_nonimportant"
    return "dokumentasi", "default_dokumentasi"

# ---------- helper untuk path ----------
def make_doc_paths(base_dir, doc_name):
    doc_base = os.path.join(base_dir, doc_name)
    ttd_path = os.path.join(doc_base, "ttd")
    dokumentasi_path = os.path.join(doc_base, "dokumentasi")
    os.makedirs(ttd_path, exist_ok=True)
    os.makedirs(dokumentasi_path, exist_ok=True)
    return {"ttd": ttd_path, "dokumentasi": dokumentasi_path}

# ---------- fungsi utama ----------
def extract_and_classify_images(pdf_path, output_dir="output/images", thresholds=None, keep_page_fallback=False):
    os.makedirs(output_dir, exist_ok=True)
    doc_name = os.path.splitext(os.path.basename(pdf_path))[0]
    paths = make_doc_paths(output_dir, doc_name)

    doc = fitz.open(pdf_path)
    results = {"ttd": [], "dokumentasi": [], "skip": []}
    extracted = set()

    for page_number, page in enumerate(doc, start=1):
        images = page.get_images(full=True)
        if not images:
            if keep_page_fallback:
                pix = page.get_pixmap(dpi=150)
                fname = f"page{page_number:03d}_full.png"
                fullpath = os.path.join(output_dir, doc_name, fname)
                pix.save(fullpath)
                results.setdefault("fallback", []).append({"page": page_number, "file": fullpath})
            continue

        for img_index, img in enumerate(images, start=1):
            xref = img[0]
            if xref in extracted:
                continue
            extracted.add(xref)

            base = doc.extract_image(xref)
            image_bytes = base["image"]
            ext = base.get("ext", "png")
            feat = image_features_from_bytes(image_bytes)
            label, reason = classify_features(feat, thresholds=thresholds)

            if label in ["ttd", "dokumentasi"]:
                dest_dir = paths[label]
                dest_path = os.path.join(dest_dir, f"page{page_number:03d}_img{img_index}.{ext}")
                with open(dest_path, "wb") as f:
                    f.write(image_bytes)
                results[label].append({
                    "page": page_number,
                    "file": dest_path,
                    "features": {k: feat[k] for k in ("entropy","unique_colors","prop_white","prop_dark","prop_yellow","edge_density")},
                    "reason": reason
                })
            else:
                # skip
                continue

        print(f"[INFO] page {page_number}: processed {len(images)} images")

    return results
