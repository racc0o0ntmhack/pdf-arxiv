try:
    from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify  # type: ignore[import]
except ImportError as e:
    raise ImportError("Flask is not installed. Install it with `pip install flask`.") from e
import os
import json
from datetime import datetime
import shutil

# ============================================
# 1. FLASK TƏNZİMLƏMƏLƏRİ
# ============================================

app = Flask(__name__)
app.secret_key = 'pdf_arxiv_secret_key_2024'

# Fayl yükləmə qovluğu
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Maksimum fayl ölçüsü (2GB)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024

# Verilənlər bazası faylı
DB_FILE = 'database.json'


# ============================================
# 2. VERİLƏNLƏR BAZASI FUNKSİYALARI
# ============================================

def load_db():
    """JSON verilənlər bazasını yüklə"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if "folders" not in data:
                    return {"folders": {"Ümumi": {"is_secret": False, "sub": {}}}, "files": {}}
                return data
            except:
                pass
    return {"folders": {"Ümumi": {"is_secret": False, "sub": {}}}, "files": {}}

def save_db(data):
    """JSON verilənlər bazasını yadda saxla"""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_all_paths(current_dict, parent_path=""):
    """Bütün qovluq yollarını əldə et"""
    paths = []
    for key, sub_data in current_dict.items():
        full_path = f"{parent_path} / {key}" if parent_path else key
        is_secret = sub_data.get("is_secret", False) if isinstance(sub_data, dict) else False
        paths.append({"path": full_path, "is_secret": is_secret})
        
        sub_dict = sub_data.get("sub", {}) if isinstance(sub_data, dict) else sub_data
        if isinstance(sub_dict, dict) and sub_dict:
            paths.extend(get_all_paths(sub_dict, full_path))
    return paths

def add_folder_recursive(d, path_list, new_folder, is_secret):
    """Qovluğu rekursiv olaraq əlavə et"""
    if not path_list:
        return
    first = path_list[0]
    if first in d:
        if len(path_list) == 1:
            if "sub" in d[first]:
                if new_folder not in d[first]["sub"]:
                    d[first]["sub"][new_folder] = {"is_secret": is_secret, "sub": {}}
            else:
                if new_folder not in d[first]:
                    d[first][new_folder] = {"is_secret": is_secret, "sub": {}}
        else:
            target = d[first]["sub"] if "sub" in d[first] else d[first]
            add_folder_recursive(target, path_list[1:], new_folder, is_secret)


# ============================================
# 3. ROUTELAR (SƏHİFƏLƏR)
# ============================================

@app.route('/')
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
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
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
                file_path = os.path.join(UPLOAD_FOLDER, filename)
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


@app.route('/login', methods=['POST'])
def login():
    """Admin girişi"""
    password = request.form.get('password')
    # Şifrəni özünüzə uyğun dəyişin
    if password == '"Mən hələ öz dərinliyimdə olan, məni kəşf edəcək o ağıllı adamı tapmamışam.!45"':
        session['logged_in'] = True
        session['login_time'] = datetime.now().isoformat()
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """Admin çıxışı"""
    session.pop('logged_in', None)
    session.pop('login_time', None)
    return redirect(url_for('index'))


@app.route('/upload', methods=['POST'])
def upload():
    """PDF faylları yüklə"""
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    pdf_files = request.files.getlist('pdf_files')
    db = load_db()
    uploaded = 0
    
    for pdf_file in pdf_files:
        if pdf_file and pdf_file.filename and pdf_file.filename.endswith('.pdf'):
            filename = pdf_file.filename
            
            # Eyni adlı fayl varsa, timestamp əlavə et
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                filename = f"{base}_{counter}{ext}"
                counter += 1
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(filepath)
            
            if filename not in db["files"]:
                db["files"][filename] = {
                    "path": "Ümumi",
                    "upload_date": datetime.now().isoformat()
                }
            uploaded += 1

    save_db(db)
    return redirect(url_for('index'))


@app.route('/rename_file/<filename>', methods=['POST'])
def rename_file(filename):
    """Faylın adını dəyiş"""
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    new_title = request.form.get('new_title', '').strip()
    if new_title:
        db = load_db()
        ext = os.path.splitext(filename)[1]
        safe_new_name = new_title + ext
        
        old_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        new_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_new_name)
        
        if os.path.exists(old_path) and not os.path.exists(new_path):
            os.rename(old_path, new_path)
            
            if filename in db["files"]:
                db["files"][safe_new_name] = db["files"].pop(filename)
                save_db(db)
                
    return redirect(url_for('index'))


@app.route('/delete_file/<filename>', methods=['POST'])
def delete_file(filename):
    """Faylı sil"""
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        
    db = load_db()
    if filename in db["files"]:
        del db["files"][filename]
        save_db(db)
        
    return redirect(url_for('index'))


@app.route('/delete_selected', methods=['POST'])
def delete_selected():
    """Seçilmiş faylları toplu sil"""
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    selected_files_json = request.form.get('selected_files')
    if selected_files_json:
        try:
            filenames = json.loads(selected_files_json)
            db = load_db()
            for filename in filenames:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                if filename in db["files"]:
                    del db["files"][filename]
            save_db(db)
        except:
            pass
        
    return redirect(url_for('index'))


@app.route('/add_folder', methods=['POST'])
def add_folder():
    """Yeni qovluq yarat"""
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    parent_path = request.form.get('parent_path')
    new_folder_name = request.form.get('new_folder_name').strip()
    is_secret = True if request.form.get('is_secret') == 'on' else False

    if new_folder_name:
        db = load_db()
        if parent_path == "ROOT_NEW_MAIN":
            if new_folder_name not in db["folders"]:
                db["folders"][new_folder_name] = {"is_secret": is_secret, "sub": {}}
        else:
            path_list = [p.strip() for p in parent_path.split('/')]
            add_folder_recursive(db["folders"], path_list, new_folder_name, is_secret)
        save_db(db)

    return redirect(url_for('index'))


@app.route('/update_file/<filename>', methods=['POST'])
def update_file(filename):
    """Faylı başqa qovluğa daşı"""
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    new_path = request.form.get('file_path')
    db = load_db()
    if filename in db["files"]:
        db["files"][filename]["path"] = new_path
        save_db(db)

    return redirect(url_for('index'))


@app.route('/read/<path:filename>')
def read_pdf(filename):
    """PDF-i oxumaq üçün səhifə - PDF.js ilə"""
    db = load_db()
    files_db = db.get("files", {})
    all_paths_info = get_all_paths(db.get("folders", {}))
    is_logged_in = session.get('logged_in', False)

    # Faylın gizli olub-olmadığını yoxla
    file_info = files_db.get(filename, {})
    file_path_cat = file_info.get("path", "Ümumi")

    is_secret = False
    for p in all_paths_info:
        if p["path"] == file_path_cat and p["is_secret"]:
            is_secret = True
            break

    if is_secret and not is_logged_in:
        return "Bu fayl gizlidir və oxuna bilməz!", 403

    # PDF faylının mövcudluğunu yoxla
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        return "Fayl tapılmadı!", 404

    # PDF.js ilə oxumaq üçün
    return render_template('reader_pdfjs.html', filename=filename)


@app.route('/download/<path:filename>')
def download(filename):
    """PDF faylını yüklə"""
    db = load_db()
    files_db = db.get("files", {})
    all_paths_info = get_all_paths(db.get("folders", {}))
    is_logged_in = session.get('logged_in', False)

    # Faylın gizli olub-olmadığını yoxla
    file_info = files_db.get(filename, {})
    file_path_cat = file_info.get("path", "Ümumi")

    is_secret = False
    for p in all_paths_info:
        if p["path"] == file_path_cat and p["is_secret"]:
            is_secret = True
            break

    if is_secret and not is_logged_in:
        return "Bu fayl gizlidir və endirilə bilməz!", 403

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    return "Fayl tapılmadı!", 404


# ============================================
# 4. PROQRAMI İŞƏ SAL
# ============================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)