import cv2
import numpy as np
from PIL import Image, ImageSequence

def align_scanned_pages_to_template(template_path, scanned_stack_path, output_path):
    # Load clean template in grayscale
    clean_img_gray = np.array(Image.open(template_path).convert("L"))

    # Extract keypoints from the clean template using SIFT
    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(clean_img_gray, None)

    # Load all scanned pages (ensure each is unique)
    scanned_pages = [page.copy() for page in ImageSequence.Iterator(Image.open(scanned_stack_path))]
    total_pages = len(scanned_pages)
    aligned_pages = []

    for i, scanned_pil in enumerate(scanned_pages):
        print(f"📄 Aligning page {i+1} of {total_pages}...")

        # Convert scanned page to grayscale and color
        scanned_img_gray = np.array(scanned_pil.convert("L"))
        scanned_img_color = np.array(scanned_pil.convert("RGB"))

        # Detect keypoints on scanned image
        kp2, des2 = sift.detectAndCompute(scanned_img_gray, None)

        # Match descriptors using FLANN
        index_params = dict(algorithm=1, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        matches = flann.knnMatch(des1, des2, k=2)

        # Apply Lowe's ratio test
        good = [m for m, n in matches if m.distance < 0.7 * n.distance]

        if len(good) < 10:
            aligned_pages.append(scanned_pil.convert("RGB"))
            continue

        # Extract matched keypoints
        src_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)

        # Compute homography and warp scanned image
        H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        warped = cv2.warpPerspective(scanned_img_color, H, (clean_img_gray.shape[1], clean_img_gray.shape[0]))

        # Append warped image
        aligned_pages.append(Image.fromarray(warped))

    # Save all aligned pages to multi-page TIFF
    aligned_pages[0].save(output_path, save_all=True, append_images=aligned_pages[1:])
    print(f"\n✅ All pages aligned. Output saved to: {output_path}")

