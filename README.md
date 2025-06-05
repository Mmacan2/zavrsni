# 🧠 Logic Gate Cell Extractor

A Flask-based web and desktop app that aligns scanned or photographed logical circuit forms and extracts logic gate symbols for manual classification.

---

## 🚀 Features

- Upload one or more `.tiff` files (supports multi-page TIFFs)
- Automatically aligns forms to a clean reference template
- Extracts 8 logic gate cells per page
- Lets users preview and manually label each cell (e.g., AND, OR, XOR)
- Saves results into class-labeled folders
- Run as a web app or desktop GUI using `pywebview`

---

## 🧩 Project Structure

| Path                      | Purpose                                        |
|---------------------------|------------------------------------------------|
| `app.py`                 | Flask app with upload, alignment, preview UI  |
| `align.py`               | Aligns scanned TIFFs to a clean template       |
| `desktop.py`             | Runs the app in a native desktop window        |
| `utils.py`               | Functions for extracting and grouping cells    |
| `templates/index.html`   | Frontend web interface                         |
| `static/ref_gates/`      | Reference gate images (AND, OR, etc.)          |
| `static/temp/`           | Cropped previews before classification         |
| `static/final/`          | Final classified (and unclassified) cells      |
| `uploads/`               | Stores uploaded raw and aligned TIFFs          |
| `clean_template/`        | Contains clean form for alignment              |
| `upload_counter.txt`     | Tracks unique session IDs                      |

---

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-user/logic-gate-classifier.git
cd logic-gate-classifier
```

### 2. Create a virtual environment (optional but recommended)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## 🌐 Run as Web App (Flask)

```bash
python app.py
```

Then open your browser at:  
📍 http://localhost:5000

---

## 💻 Run as Desktop App

```bash
python desktop.py
```

This launches the same interface in a desktop window using [pywebview](https://pywebview.flowrl.com/).

---

## ⚙️ Standalone Alignment Script

You can align scanned TIFFs without running the app:

```bash
python align.py clean_template/clean_form.tiff input.tiff output_aligned.tiff
```

---

## Cleanup
# Remove uploaded TIFFs and intermediate PNGs
Remove-Item -Recurse -Force uploads\*

# Remove all temporary cropped cells
Remove-Item -Recurse -Force static\temp\*

# Remove all saved classified/unselected cells
Remove-Item -Recurse -Force static\saved\*

# Cleanup all intermediate and processed files
Remove-Item -Recurse -Force uploads\*, static\temp\*, static\saved\*, static\final\*

---

## 📌 Notes

- Alignment is optional (can be toggled in the UI).
- Only `.tiff` files are supported for now (multi-page or single-page).
- Make sure `clean_template/clean_form.tiff` exists before running.
- Gate previews must be manually classified unless you build automation.

---

## 👨‍💻 Author

**Mario Macan**  
🔗 [github.com/Mmacan2](https://github.com/Mmacan2)
