# routes/reader.py
from flask import Blueprint, render_template, send_from_directory, session, request  # type: ignore[import]
from database import load_db, get_all_paths, is_file_secret
from config import Config
import os

reader_bp = Blueprint('reader', __name__)

@reader_bp.route('/read/<path:filename>')
def read_pdf(filename):
    """PDF-i oxumaq üçün səhifə"""
    db = load_db()
    is_logged_in = session.get('logged_in', False)

    # Faylın gizli olub-olmadığını yoxla
    if is_file_secret(filename, db) and not is_logged_in:
        return "Bu fayl gizlidir və oxuna bilməz!", 403

    # PDF faylının mövcudluğunu yoxla
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        return "Fayl tapılmadı!", 404

    # PDF.js ilə oxumaq üçün
    return render_template('reader_pdfjs.html', filename=filename)

@reader_bp.route('/download/<path:filename>')
def download(filename):
    """PDF faylını yüklə"""
    db = load_db()
    is_logged_in = session.get('logged_in', False)

    # Faylın gizli olub-olmadığını yoxla
    if is_file_secret(filename, db) and not is_logged_in:
        return "Bu fayl gizlidir və endirilə bilməz!", 403

    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_from_directory(Config.UPLOAD_FOLDER, filename, as_attachment=True)
    return "Fayl tapılmadı!", 404

@reader_bp.route('/static/uploads/<path:filename>')
def serve_upload(filename):
    """Statik upload qovluğundan fayl xidməti"""
    return send_from_directory(Config.UPLOAD_FOLDER, filename)