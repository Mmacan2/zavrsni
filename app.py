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

os.makedirs("uploads", exist_ok=True)
os.makedirs("static/temp", exist_ok=True)

CELL_LABELS = ["AND", "OR", "NAND", "NOR", "XOR", "XNOR", "pojacalo", "invertor"]

def ensure_page_folders(page_folder):
    base = os.path.join("static", "saved", page_folder)
    labels = CELL_LABELS + ["unselected"]
    for label in labels:
        folder_path = os.path.join(base, label)
        os.makedirs(folder_path, exist_ok=True)

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

def warp_and_extract_cells(template_path, target_path, boxes_2d, filename, page_index=0):
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

            # Simple trim
            pad = 5  # 👈 Change this number to adjust how many pixels are trimmed
            cy1, cy2 = y1 + pad, y2 - pad
            cx1, cx2 = x1 + pad, x2 - pad

            if cy2 > cy1 and cx2 > cx1:
                cropped = aligned_img[cy1:cy2, cx1:cx2]
            else:
                cropped = aligned_img[y1:y2, x1:x2]

            folder = f"static/temp/{filename}/page_{page_index}"
            os.makedirs(folder, exist_ok=True)
            save_path = f"{folder}/cell_{i+1}.png"
            cv2.imwrite(save_path, cropped)
            result_paths.append(f"temp/{filename}/page_{page_index}/cell_{i+1}.png")

        except Exception as e:
            print(f"[ERROR] Cell {i+1} on page {page_index} failed: {e}")
            continue

    return result_paths


@app.route("/", methods=["GET", "POST"])
def index():
    result_imgs = []
    message = None

    # Handle uploads
    if request.method == "POST" and "files" in request.files:
        shutil.rmtree("static/temp", ignore_errors=True)
        os.makedirs("static/temp", exist_ok=True)

        uploaded_files = request.files.getlist("files")
        template_path = "clean_template/clean_form.tiff"
        boxes = extract_template_boxes(template_path)
        cell_structure = group_into_rows(boxes)

        for file in uploaded_files:
            filename = os.path.splitext(file.filename)[0]
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)  # Ensure uploads/ exists
            file.save(filepath)

            if filepath.lower().endswith((".tif", ".tiff")):
                img = Image.open(filepath)
                for i, page in enumerate(ImageSequence.Iterator(img)):
                    temp_page_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{filename}_page_{i}.png")
                    page.save(temp_page_path)
                    paths = warp_and_extract_cells(template_path, temp_page_path, cell_structure, filename, i)
                    result_imgs.extend(paths)

    # Handle selections
    selected = request.form.getlist("selected")
    print("[DEBUG] Selected images:", selected)

    if selected:
        for img_path in selected:
            parts = img_path.split("/")
            if len(parts) < 4:
                continue
            _, filename, page_folder, filename_img = parts
            try:
                cell_num = int(filename_img.split("_")[1].split(".")[0])
                cell_name = CELL_LABELS[cell_num - 1]
            except:
                continue
            ensure_page_folders(f"{filename}/{page_folder}")
            src = os.path.join("static", img_path)
            dst = os.path.join("static", "saved", filename, page_folder, cell_name, filename_img)
            shutil.copyfile(src, dst)

        # Save unselected
        all_temp_imgs = []
        for root, _, files in os.walk("static/temp"):
            for f in files:
                full_path = os.path.join(root, f)
                relative = os.path.relpath(full_path, "static")
                all_temp_imgs.append(relative)

        normalized_selected = {os.path.normpath(p) for p in selected}
        unselected = {os.path.normpath(p) for p in all_temp_imgs} - normalized_selected

        for img_path in unselected:
            parts = img_path.split(os.sep)
            try:
                _, filename, page_folder, filename_img = parts
            except ValueError:
                print(f"[ERROR] Unrecognized image path format: {img_path}")
                continue

            ensure_page_folders(f"{filename}/{page_folder}")
            src = os.path.join("static", *parts)
            dst = os.path.join("static", "saved", filename, page_folder, "unselected", filename_img)

            try:
                shutil.copyfile(src, dst)
            except Exception as e:
                print(f"[ERROR] Failed to save unselected {filename_img}: {e}")

        message = "Images saved successfully."

    return render_template("index.html", result_imgs=result_imgs, message=message)

if __name__ == "__main__":
    app.run(debug=True)
