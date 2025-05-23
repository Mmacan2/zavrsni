from flask import Flask, render_template, request
import cv2
import numpy as np
import os
from PIL import Image, ImageSequence
from utils import extract_template_boxes, group_into_rows
import shutil

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

CELL_LABELS = ["AND", "OR", "NAND", "NOR", "XOR", "XNOR", "pojacalo", "invertor"]

os.makedirs("uploads", exist_ok=True)
os.makedirs("static/temp", exist_ok=True)
os.makedirs("static/final", exist_ok=True)
os.makedirs("static/final/unselected", exist_ok=True)
for label in CELL_LABELS:
    os.makedirs(os.path.join("static/final", label), exist_ok=True)

def get_next_upload_id(counter_file="upload_counter.txt"):
    if not os.path.exists(counter_file):
        with open(counter_file, "w") as f:
            f.write("1")
        return "upload_001"
    with open(counter_file, "r+") as f:
        count = int(f.read().strip())
        next_id = count + 1
        f.seek(0)
        f.write(str(next_id))
        f.truncate()
    return f"upload_{next_id:03d}"

def compute_homography(template_path, target_path):
    template_gray = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    target_gray = cv2.imread(target_path, cv2.IMREAD_GRAYSCALE)
    orb = cv2.ORB_create(5000)
    kp1, des1 = orb.detectAndCompute(template_gray, None)
    kp2, des2 = orb.detectAndCompute(target_gray, None)
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(matcher.match(des1, des2), key=lambda x: x.distance)
    src_pts = np.float32([kp1[m.queryIdx].pt for m in matches[:100]]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches[:100]]).reshape(-1, 1, 2)
    H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    return H

def warp_and_extract_cells(template_path, target_path, boxes_2d, upload_id, page_index=0):
    aligned_img = cv2.imread(target_path)
    H = compute_homography(template_path, target_path)
    result_paths = []

    for i in range(8):
        try:
            x, y, w, h = boxes_2d[13][1 + i]
            src_pts = np.float32([[x, y], [x + w, y + h]]).reshape(-1, 1, 2)
            dst_pts = cv2.perspectiveTransform(src_pts, H)
            (x1, y1), (x2, y2) = dst_pts[:, 0]
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])

            pad = 12
            cy1, cy2 = y1 + pad, y2 - pad
            cx1, cx2 = x1 + pad, x2 - pad
            if cy2 > cy1 and cx2 > cx1:
                cropped = aligned_img[cy1:cy2, cx1:cx2]
            else:
                cropped = aligned_img[y1:y2, x1:x2]

            gate_name = CELL_LABELS[i]
            gate_folder = os.path.join("static", "temp", upload_id, f"page_{page_index}", gate_name)
            os.makedirs(gate_folder, exist_ok=True)
            filename = f"{gate_name}.png"
            save_path = os.path.join(gate_folder, filename)
            cv2.imwrite(save_path, cropped)
            result_paths.append(os.path.relpath(save_path, "static").replace("\\", "/"))
        except Exception as e:
            print(f"[ERROR] Cell {i+1} on page {page_index} failed: {e}")
            continue

    return result_paths

@app.route("/", methods=["GET", "POST"])
def index():
    result_imgs = []
    message = None
    upload_id = None

    if request.method == "POST" and "files" in request.files:
        os.makedirs("static/temp", exist_ok=True)
        uploaded_files = request.files.getlist("files")
        upload_id = get_next_upload_id()
        template_path = "clean_template/clean_form.tiff"
        boxes = extract_template_boxes(template_path)
        cell_structure = group_into_rows(boxes)

        global_page_index = 0  # NEW: keep a global index across all files

        for file in uploaded_files:
            upload_dir = os.path.abspath(app.config["UPLOAD_FOLDER"])
            os.makedirs(upload_dir, exist_ok=True)

            filepath = os.path.join(upload_dir, file.filename)
            file.save(filepath)

            if filepath.lower().endswith((".tif", ".tiff")):
                img = Image.open(filepath)
                for page in ImageSequence.Iterator(img):
                    temp_page_path = os.path.join(upload_dir, f"{upload_id}_page_{global_page_index}.png")
                    page.save(temp_page_path)
                    paths = warp_and_extract_cells(template_path, temp_page_path, cell_structure, upload_id, global_page_index)
                    result_imgs.extend(paths)
                    global_page_index += 1

    selected = request.form.getlist("selected")
    if selected:
        for img_path in selected:
            parts = img_path.split("/")
            if len(parts) < 5:
                continue
            _, upload_id, page_folder, cell_name, filename_img = parts
            try:
                dst_folder = os.path.join("static", "saved", upload_id, page_folder, cell_name)
                os.makedirs(dst_folder, exist_ok=True)
                src = os.path.join("static", img_path.replace("/", os.sep))
                dst = os.path.join(dst_folder, filename_img)
                shutil.copyfile(src, dst)

                final_name = f"{upload_id}_{page_folder}_{cell_name}.png"
                final_dst = os.path.join("static", "final", cell_name, final_name)
                shutil.copyfile(src, final_dst)
            except Exception as e:
                print(f"[ERROR] Failed to save selected {filename_img}: {e}")

        # Only check unselected for current upload
        all_temp_imgs = []
        temp_upload_dir = os.path.join("static", "temp", upload_id)
        for root, _, files in os.walk(temp_upload_dir):
            for f in files:
                full_path = os.path.join(root, f)
                relative = os.path.relpath(full_path, "static").replace("\\", "/")
                all_temp_imgs.append(relative)

        selected_set = {p.replace("\\", "/") for p in selected}
        unselected = set(all_temp_imgs) - selected_set

        for img_path in unselected:
            try:
                clean_path = img_path.replace("\\", "/")
                parts = clean_path.split("/")
                _, upload_id, page_folder, cell_name, filename_img = parts
                dst_folder = os.path.join("static", "saved", upload_id, page_folder, "unselected")
                os.makedirs(dst_folder, exist_ok=True)
                src = os.path.join("static", *parts)
                dst = os.path.join(dst_folder, filename_img)
                shutil.copyfile(src, dst)

                final_name = f"{upload_id}_{page_folder}_{cell_name}.png"
                final_dst = os.path.join("static", "final", "unselected", final_name)
                shutil.copyfile(src, final_dst)
            except Exception as e:
                print(f"[ERROR] Failed to save unselected {img_path}: {e}")

        message = "Images saved successfully."

    return render_template("index.html", result_imgs=result_imgs, message=message)

if __name__ == "__main__":
    app.run(debug=True)
