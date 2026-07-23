# routes/folders.py
from flask import Blueprint, request, redirect, url_for, session  # type: ignore[import]
from database import load_db, save_db, add_folder_recursive
import os
from config import Config

folders_bp = Blueprint('folders', __name__)

@folders_bp.route('/add_folder', methods=['POST'])
def add_folder():
    """Yeni qovluq yarat"""
    if not session.get('logged_in'):
        return redirect(url_for('main.index'))
    
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

    return redirect(url_for('main.index'))

@folders_bp.route('/update_file/<filename>', methods=['POST'])
def update_file(filename):
    """Faylı başqa qovluğa daşı"""
    if not session.get('logged_in'):
        return redirect(url_for('main.index'))
    
    new_path = request.form.get('file_path')
    db = load_db()
    if filename in db["files"]:
        db["files"][filename]["path"] = new_path
        save_db(db)

    return redirect(url_for('main.index'))