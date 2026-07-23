# routes/main.py
from flask import Blueprint, render_template, request, session  # type: ignore[import]
from database import load_db, get_all_paths, save_db
from config import Config
import os
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Ana səhifə"""
    is_logged_in = session.get('logged_in', False)
    search_query = request.args.get('q', '').lower()
    selected_cat = request.args.get('category', '')
    sort_order = request.args.get('sort', 'az')

    db = load_db()
    folders = db["folders"]
    files_db = db["files"]

    all_paths_info = get_all_paths(folders)
    
    # İcazəli qovluqları filtrələ
    if not is_logged_in:
        valid_paths = [p["path"] for p in all_paths_info if not p["is_secret"]]
    else:
        valid_paths = [p["path"] for p in all_paths_info]

    # Faylları siyahıya al
    files_list = []
    if os.path.exists(Config.UPLOAD_FOLDER):
        for filename in os.listdir(Config.UPLOAD_FOLDER):
            if filename.endswith('.pdf'):
                if filename not in files_db:
                    files_db[filename] = {"path": "Ümumi", "upload_date": datetime.now().isoformat()}
                
                f_info = files_db[filename]
                f_path = f_info.get("path", "Ümumi")
                
                # Gizli faylları yoxla
                is_file_secret = False
                for p in all_paths_info:
                    if p["path"] == f_path and p["is_secret"]:
                        is_file_secret = True
                        break
                
                if is_file_secret and not is_logged_in:
                    continue

                # Fayl ölçüsünü əldə et
                file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

                files_list.append({
                    "title": os.path.splitext(filename)[0],
                    "filename": filename,
                    "path": f_path,
                    "size": size,
                    "upload_date": f_info.get("upload_date", datetime.now().isoformat())
                })

    save_db({"folders": folders, "files": files_db})

    # Axtarış
    if search_query:
        files_list = [f for f in files_list if search_query in f['title'].lower()]
    
    # Kateqoriya
    if selected_cat:
        files_list = [f for f in files_list if f['path'] == selected_cat or f['path'].startswith(selected_cat + " / ")]
    
    # Sıralama
    if sort_order == 'za':
        files_list = sorted(files_list, key=lambda x: x['title'].lower(), reverse=True)
    elif sort_order == 'newest':
        files_list = sorted(files_list, key=lambda x: x.get('upload_date', ''), reverse=True)
    elif sort_order == 'oldest':
        files_list = sorted(files_list, key=lambda x: x.get('upload_date', ''))
    else:  # az (default)
        files_list = sorted(files_list, key=lambda x: x['title'].lower())

    return render_template('index.html',
                           files=files_list,
                           folder_paths=valid_paths,
                           all_paths_info=all_paths_info,
                           is_logged_in=is_logged_in,
                           selected_cat=selected_cat,
                           search_query=search_query,
                           sort_order=sort_order)