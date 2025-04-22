# Zavrsni - Logic Gate Cell Extractor

## ✅ TODO


---

## 💡 Description

This is a Flask-based web app that:
- Accepts single or multiple `.tiff` image uploads (multi-page or single-page)
- Aligns them to a clean template
- Extracts cells from specific positions
- Lets users select logic gate types (AND, OR, etc.)
- Saves results into labeled folders

---

## 🚀 How to Run

### 1. Clone the repo

```bash
git clone https://github.com/Mmacan2/zavrsni.git
cd zavrsni
```

### 2. (Optional) Create a virtual environment

```bash
python -m venv venv
.env\Scriptsctivate  # on Windows
source venv/bin/activate  # on macOS/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Flask app

```bash
python app.py
```

App will run at:  
📍 `http://127.0.0.1:5000/`

---

## 📁 Folder Structure

| Folder | Purpose |
|--------|---------|
| `uploads/` | Stores uploaded TIFFs & intermediate PNGs |
| `static/temp/` | Temporary cropped cell previews |
| `static/saved/` | Final classified cell images |
| `clean_template/` | Reference form for alignment |
| `templates/` | Contains `index.html` (UI) |

---

## 🧾 Notes

- Make sure `clean_template/clean_form.tiff` exists — it's used for alignment.
- Uploaded files and results are cleaned from `.gitignore` (you won’t accidentally commit test data).
- The app supports batch uploads of TIFFs and handles multipage splitting.

---

## 👨‍💻 Author

Mario Macan – [github.com/Mmacan2](https://github.com/Mmacan2)
