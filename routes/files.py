# routes/files.py
from flask import Blueprint, request, redirect, url_for, session, jsonify  # type: ignore[reportMissingImports]
from database import load_db, save_db
from config import Config
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename  # type: ignore[reportMissingImports]

files_bp = Blueprint('files', __name__)

def allowed_file(filename):
    """Faylın icazə verilən tip olub-olmadığını yoxla"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@files_bp.route('/upload', methods=['POST'])
def upload():
    """PDF faylları yüklə"""
    if not session.get('logged_in'):
        return redirect(url_for('main.index'))
    
    if 'pdf_files' not in request.files:
        return 'Fayl seçilməyib', 400
    
    pdf_files = request.files.getlist('pdf_files')
    db = load_db()
    uploaded = 0
    
    for pdf_file in pdf_files:
        if pdf_file and allowed_file(pdf_file.filename):
            filename = secure_filename(pdf_file.filename)
            
            # Eyni adlı fayl varsa, timestamp əlavə et
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(os.path.join(Config.UPLOAD_FOLDER, filename)):
                filename = f"{base}_{counter}{ext}"
                counter += 1
            
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            pdf_file.save(filepath)
            
            if filename not in db["files"]:
                db["files"][filename] = {
                    "path": "Ümumi",
                    "upload_date": datetime.now().isoformat()
                }
            uploaded += 1

    save_db(db)
    return redirect(url_for('main.index'))

@files_bp.route('/rename_file/<filename>', methods=['POST'])
def rename_file(filename):
    """Faylın adını dəyiş"""
    if not session.get('logged_in'):
        return redirect(url_for('main.index'))
    
    new_title = request.form.get('new_title', '').strip()
    if new_title:
        db = load_db()
        ext = os.path.splitext(filename)[1]
        safe_new_name = new_title + ext
        
        old_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        new_path = os.path.join(Config.UPLOAD_FOLDER, safe_new_name)
        
        if os.path.exists(old_path) and not os.path.exists(new_path):
            os.rename(old_path, new_path)
            
            if filename in db["files"]:
                db["files"][safe_new_name] = db["files"].pop(filename)
                save_db(db)
                
    return redirect(url_for('main.index'))

@files_bp.route('/delete_file/<filename>', methods=['POST'])
def delete_file(filename):
    """Faylı sil"""
    if not session.get('logged_in'):
        return redirect(url_for('main.index'))
    
    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        
    db = load_db()
    if filename in db["files"]:
        del db["files"][filename]
        save_db(db)
        
    return redirect(url_for('main.index'))

@files_bp.route('/delete_selected', methods=['POST'])
def delete_selected():
    """Seçilmiş faylları toplu sil"""
    if not session.get('logged_in'):
        return redirect(url_for('main.index'))
    
    selected_files_json = request.form.get('selected_files')
    if selected_files_json:
        try:
            filenames = json.loads(selected_files_json)
            db = load_db()
            for filename in filenames:
                filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                if filename in db["files"]:
                    del db["files"][filename]
            save_db(db)
        except:
            pass
        
    return redirect(url_for('main.index'))