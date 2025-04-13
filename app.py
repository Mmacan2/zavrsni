from flask import Flask, render_template, request
import cv2
import numpy as np
import os
from PIL import Image, ImageSequence
from utils import extract_template_boxes, group_into_rows

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs("uploads", exist_ok=True)
os.makedirs("static/cells", exist_ok=True)


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


def warp_and_extract_cells(template_path, target_path, boxes_2d, row=13, start_col=1, count=8, page_index=0):
    aligned_img = cv2.imread(target_path)
    H = compute_homography(template_path, target_path)
    result_paths = []

    for i in range(count):
        col = start_col + i
        try:
            x, y, w, h = boxes_2d[row][col]
            src_pts = np.float32([[x, y], [x + w, y + h]]).reshape(-1, 1, 2)
            dst_pts = cv2.perspectiveTransform(src_pts, H)
            (x1, y1), (x2, y2) = dst_pts[:, 0]
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
            cropped = aligned_img[y1:y2, x1:x2]

            folder = f"static/cells/cell_{i+1}"
            os.makedirs(folder, exist_ok=True)
            save_path = f"{folder}/page_{page_index}.png"
            cv2.imwrite(save_path, cropped)
            result_paths.append(f"cells/cell_{i+1}/page_{page_index}.png")
        except:
            continue

    return result_paths


@app.route("/", methods=["GET", "POST"])
def index():
    result_imgs = []
    if request.method == "POST":
        file = request.files["file"]
        if file:
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)

            template_path = "clean_template/clean_form.tiff"
            boxes = extract_template_boxes(template_path)
            cell_structure = group_into_rows(boxes)

            if filepath.lower().endswith((".tif", ".tiff")):
                img = Image.open(filepath)
                for i, page in enumerate(ImageSequence.Iterator(img)):
                    page_rgb = page.convert("RGB")
                    np_img = np.array(page_rgb)
                    temp_path = f"uploads/temp_page_{i}.png"
                    cv2.imwrite(temp_path, cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR))

                    page_result = warp_and_extract_cells(template_path, temp_path, cell_structure, page_index=i)
                    if page_result:
                        result_imgs.append(page_result)
            else:
                single_page_result = warp_and_extract_cells(template_path, filepath, cell_structure, page_index=0)
                if single_page_result:
                    result_imgs.append(single_page_result)

    return render_template("index.html", result_imgs=result_imgs)


if __name__ == "__main__":
    app.run(debug=True)
