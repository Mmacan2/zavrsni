import cv2
import numpy as np
from PIL import Image

def extract_template_boxes(template_img_path, min_height=20, min_area=1000):
    pil_img = Image.open(template_img_path).convert("RGB")
    img = np.array(pil_img)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, bin_img = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    bin_img = cv2.bitwise_not(bin_img)

    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, img.shape[1] // 120))
    vertical = cv2.dilate(cv2.erode(bin_img, vertical_kernel, 3), vertical_kernel, 3)

    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (img.shape[1] // 40, 1))
    horizontal = cv2.dilate(cv2.erode(bin_img, horizontal_kernel, 3), horizontal_kernel, 3)

    mask = cv2.addWeighted(vertical, 0.5, horizontal, 0.5, 0)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.erode(cv2.bitwise_not(mask), kernel, 2)
    _, mask = cv2.threshold(mask, 0, 255, cv2.THRESH_OTSU)

    contours_info = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = contours_info[0] if len(contours_info) == 2 else contours_info[1]

    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if h >= min_height and w * h >= min_area:
            boxes.append((x, y, w, h))

    return sorted(boxes, key=lambda b: (b[1], b[0]))

def group_into_rows(boxes, y_tolerance=15):
    rows = []
    current_row = []
    prev_y = -100

    for box in sorted(boxes, key=lambda b: (b[1], b[0])):
        x, y, w, h = box
        if abs(y - prev_y) > y_tolerance:
            if current_row:
                rows.append(current_row)
            current_row = []
        current_row.append(box)
        prev_y = y
    if current_row:
        rows.append(current_row)
    return [sorted(row, key=lambda b: b[0]) for row in rows]
