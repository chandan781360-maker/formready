from flask import Flask, render_template, request, send_from_directory, jsonify, send_file
from PIL import Image
#from rembg import remove
from pdf2image import convert_from_bytes
import os
import uuid
import io
import base64
import zipfile
import time

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================================================
# AUTO DELETE UPLOADS (SAFE + LEGAL)
# =========================================================

def cleanup_uploads(folder=UPLOAD_FOLDER, max_age_minutes=30):
    now = time.time()
    max_age = max_age_minutes * 60

    if not os.path.exists(folder):
        return

    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)

        if not os.path.isfile(file_path):
            continue

        if now - os.path.getmtime(file_path) > max_age:
            try:
                os.remove(file_path)
            except:
                pass

# =========================================================
# BASIC ROUTES
# =========================================================

@app.route("/")
def index():
    return render_template("index.html", show_subtitle=True)

@app.route("/documents")
def documents():
    return render_template("documents.html")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/download/<filename>")
def download_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

# =========================================================
# PHOTO
# =========================================================

@app.route("/photo", methods=["GET", "POST"])
def photo():
    cleanup_uploads()

    filename = size_kb = width = height = file_type = None

    if request.method == "POST":
        file = request.files.get("file")
        if file:
            ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
            filename = f"{uuid.uuid4().hex}.{ext}"
            path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)

            img = Image.open(path)
            width, height = img.size
            size_kb = round(os.path.getsize(path) / 1024, 1)
            file_type = ext

    return render_template(
        "photo.html",
        filename=filename,
        size_kb=size_kb,
        width=width,
        height=height,
        type=file_type
    )

# =========================================================
# SIGNATURE
# =========================================================

@app.route("/signature", methods=["GET", "POST"])
def signature():
    cleanup_uploads()

    filename = size_kb = width = height = file_type = None

    if request.method == "POST":
        file = request.files.get("file")
        if file:
            ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
            filename = f"{uuid.uuid4().hex}.{ext}"
            path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)

            img = Image.open(path)
            width, height = img.size
            size_kb = round(os.path.getsize(path) / 1024, 1)
            file_type = ext

    return render_template(
        "signature.html",
        filename=filename,
        size_kb=size_kb,
        width=width,
        height=height,
        type=file_type
    )

# =========================================================
# BACKGROUND REMOVAL (PHOTO + SIGNATURE)
# =========================================================
@app.route("/bg-process", methods=["POST"])
def bg_process():
    return jsonify({"error": "Background removal temporarily disabled"}), 503

@app.route("/signature-bg-process", methods=["POST"])
def signature_bg_process():
    return jsonify({"error": "Background removal temporarily disabled"}), 503


# =========================================================
# FINAL PHOTO / SIGNATURE PROCESS
# =========================================================

@app.route("/photo-preview", methods=["POST"])
def photo_preview():
    cleanup_uploads()

    file = request.files.get("image_file")
    img = Image.open(file.stream).convert("RGB")

    width = request.form.get("width", type=int)
    height = request.form.get("height", type=int)
    target_kb = int(request.form.get("kb", 50))
    fmt = request.form.get("format", "jpg").lower()

    if width and height:
        img = img.resize((width, height), Image.LANCZOS)

    quality = 90
    final_data = None
    final_size_kb = None

    while quality >= 20:
        buf = io.BytesIO()
        if fmt == "png":
            img.save(buf, "PNG", optimize=True)
        else:
            img.save(buf, "JPEG", quality=quality, optimize=True)

        size_kb = len(buf.getvalue()) / 1024
        if size_kb <= target_kb:
            final_data = buf.getvalue()
            final_size_kb = round(size_kb, 1)
            break

        quality -= 5

    if final_data is None:
        final_data = buf.getvalue()
        final_size_kb = round(len(final_data) / 1024, 1)

    name = f"{uuid.uuid4().hex}.{fmt}"
    path = os.path.join(UPLOAD_FOLDER, name)

    with open(path, "wb") as f:
        f.write(final_data)

    return jsonify({
        "preview_url": f"/uploads/{name}",
        "download_url": f"/download/{name}",
        "width": img.width,
        "height": img.height,
        "size_kb": final_size_kb,
        "type": fmt
    })

# =========================================================
# DOCUMENT UI ROUTES
# =========================================================

@app.route("/doc-image-pdf")
def doc_image_pdf():
    return render_template("doc_image_pdf.html")

@app.route("/doc-pdf-image")
def doc_pdf_image():
    return render_template("doc_pdf_image.html")

@app.route("/doc-compress")
def doc_compress():
    return render_template("doc_compress.html")

@app.route("/doc-increase")
def doc_increase():
    return render_template("doc_increase.html")

@app.route("/documents-result")
def documents_result():
    cleanup_uploads()

    download_url = request.args.get("download")
    if not download_url:
        return "Invalid request", 400

    filename = download_url.split("/")[-1]
    path = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(path):
        return "File not found", 404

    size_kb = round(os.path.getsize(path) / 1024, 1)
    file_type = filename.split(".")[-1].upper()

    return render_template(
        "documents_result.html",
        download_url=download_url,
        filename=filename,
        size_kb=size_kb,
        file_type=file_type
    )

# =========================================================
# LEGAL / INFO PAGES
# =========================================================

@app.route("/about")
def about(): return render_template("about.html")

@app.route("/contact")
def contact(): return render_template("contact.html")

@app.route("/privacy")
def privacy(): return render_template("privacy.html")

@app.route("/terms")
def terms(): return render_template("terms.html")

@app.route("/disclaimer")
def disclaimer(): return render_template("disclaimer.html")

# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


