from flask import Flask, render_template, request
import cv2
import numpy as np
import os
from PIL import Image, ImageSequence
from utils import extract_template_boxes, group_into_rows
from align import align_scanned_pages_to_template
import shutil

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

CELL_LABELS = ["AND", "OR", "NAND", "NOR", "XOR", "XNOR", "pojacalo", "invertor"]

# Ensure folders exist
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

def warp_and_extract_cells(target_path, boxes_2d, upload_id, page_index=0):
    aligned_img = cv2.imread(target_path)
    result_paths = []

    for i in range(8):
        try:
            x, y, w, h = boxes_2d[13][1 + i]
            pad = 12
            cy1, cy2 = y + pad, y + h - pad
            cx1, cx2 = x + pad, x + w - pad
            if cy2 > cy1 and cx2 > cx1:
                cropped = aligned_img[cy1:cy2, cx1:cx2]
            else:
                cropped = aligned_img[y:y+h, x:x+w]

            if cropped is None or cropped.size == 0:
                raise ValueError("Empty cropped image")

            gate_name = CELL_LABELS[i]
            gate_folder = os.path.join("static", "temp", upload_id, f"page_{page_index}", gate_name)
            os.makedirs(gate_folder, exist_ok=True)
            filename = f"{gate_name}.png"
            save_path = os.path.join(gate_folder, filename)
            cv2.imwrite(save_path, cropped)
            result_paths.append(os.path.relpath(save_path, "static").replace("\\", "/"))
        except Exception as e:
            print(f"[ERROR] Cell {i+1} on page {page_index} failed: {e}")
            result_paths.append("__placeholder__")

    return result_paths

@app.route("/", methods=["GET", "POST"])
def index():
    grouped_imgs = []
    message = None
    upload_id = None

    if request.method == "POST" and "files" in request.files:
        uploaded_files = request.files.getlist("files")
        upload_id = get_next_upload_id()
        template_path = "clean_template/clean_form.tiff"
        boxes = extract_template_boxes(template_path)
        cell_structure = group_into_rows(boxes)

        # ✅ Get checkbox value from form
        do_align = "do_align" in request.form
        print("⚙️ Alignment enabled:", do_align)

        global_page_index = 0

        for file in uploaded_files:
            upload_dir = os.path.abspath(app.config["UPLOAD_FOLDER"])
            os.makedirs(upload_dir, exist_ok=True)

            filepath = os.path.join(upload_dir, file.filename)
            file.save(filepath)

            if filepath.lower().endswith((".tif", ".tiff")):
                if do_align:
                    base_name = os.path.splitext(file.filename)[0]
                    aligned_path = os.path.join(upload_dir, f"{upload_id}_{base_name}_aligned.tiff")
                    align_scanned_pages_to_template(
                        template_path=template_path,
                        scanned_stack_path=filepath,
                        output_path=aligned_path
                    )
                else:
                    aligned_path = filepath  # use original if no alignment

                img = Image.open(aligned_path)
                for page in ImageSequence.Iterator(img):
                    temp_page_path = os.path.join(upload_dir, f"{upload_id}_page_{global_page_index}.png")
                    page.convert("RGB").save(temp_page_path)
                    paths = warp_and_extract_cells(temp_page_path, cell_structure, upload_id, global_page_index)
                    grouped_imgs.append(paths)
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

                final_name = f"{upload_id}_{page_folder}_{cell_name}.png"
                final_dst = os.path.join("static", "final", "unselected", final_name)
                shutil.copyfile(src, final_dst)
            except Exception as e:
                print(f"[ERROR] Failed to save unselected {img_path}: {e}")

        message = "Images saved successfully."

    return render_template("index.html", result_imgs=grouped_imgs, message=message)

if __name__ == "__main__":
    app.run(debug=True)
