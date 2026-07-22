from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
import os
import json

app = Flask(__name__)
app.secret_key = 'pdf_arxiv_secret_key'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DB_FILE = 'database.json'

def load_db():
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
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Qovluqları yolları və gizlilik statusu ilə birlikdə oxuyan funksiya
def get_all_paths(current_dict, parent_path=""):
    paths = []
    for key, sub_data in current_dict.items():
        full_path = f"{parent_path} / {key}" if parent_path else key
        is_secret = sub_data.get("is_secret", False) if isinstance(sub_data, dict) else False
        paths.append({"path": full_path, "is_secret": is_secret})
        
        sub_dict = sub_data.get("sub", {}) if isinstance(sub_data, dict) else sub_data
        if isinstance(sub_dict, dict) and sub_dict:
            paths.extend(get_all_paths(sub_dict, full_path))
    return paths

# İyerarxik lüğətdə qovluq tapmaq və ya əlavə etmək
def add_folder_recursive(d, path_list, new_folder, is_secret):
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

@app.route('/')
def index():
    is_logged_in = session.get('logged_in', False)
    search_query = request.args.get('q', '').lower()
    selected_cat = request.args.get('category', '')

    db = load_db()
    folders = db["folders"]
    files_db = db["files"]

    all_paths_info = get_all_paths(folders)
    
    # Əgər admin deyilsə, gizli qovluqları siyahıdan çıxarırıq
    if not is_logged_in:
        valid_paths = [p["path"] for p in all_paths_info if not p["is_secret"]]
    else:
        valid_paths = [p["path"] for p in all_paths_info]

    files_list = []
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.endswith('.pdf'):
                if filename not in files_db:
                    files_db[filename] = {"path": "Ümumi"}
                
                f_info = files_db[filename]
                f_path = f_info.get("path", "Ümumi")
                
                # Faylın yerləşdiyi qovluq gizlidirsə və admin deyiliksə, göstərmirik
                is_file_secret = False
                for p in all_paths_info:
                    if p["path"] == f_path and p["is_secret"]:
                        is_file_secret = True
                        break
                
                if is_file_secret and not is_logged_in:
                    continue

                files_list.append({
                    "title": os.path.splitext(filename)[0],
                    "filename": filename,
                    "path": f_path
                })
    save_db({"folders": folders, "files": files_db})

    if search_query:
        files_list = [f for f in files_list if search_query in f['title'].lower()]
    if selected_cat:
        files_list = [f for f in files_list if f['path'] == selected_cat or f['path'].startswith(selected_cat + " / ")]

    return render_template('index.html', 
                           files=files_list, 
                           folder_paths=valid_paths, 
                           all_paths_info=all_paths_info,
                           is_logged_in=is_logged_in,
                           selected_cat=selected_cat,
                           search_query=search_query)

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('password') == '"Mən hələ öz dərinliyimdə olan, məni kəşf edəcək o ağıllı adamı tapmamışam.!45"':
        session['logged_in'] = True
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    pdf_files = request.files.getlist('pdf_files')
    for pdf_file in pdf_files:
        if pdf_file and pdf_file.filename:
            filename = pdf_file.filename
            pdf_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    return redirect(url_for('index'))

@app.route('/add_folder', methods=['POST'])
def add_folder():
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
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    new_path = request.form.get('file_path')
    db = load_db()
    if filename in db["files"]:
        db["files"][filename]["path"] = new_path
        save_db(db)

    return redirect(url_for('index'))

@app.route('/download/<path:filename>')
def download(filename):
    db = load_db()
    files_db = db.get("files", {})
    all_paths_info = get_all_paths(db.get("folders", {}))
    is_logged_in = session.get('logged_in', False)

    # Faylın gizli qovluqda olub- olmadığını yoxlayırıq
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

if __name__ == '__main__':
    app.run(debug=True)