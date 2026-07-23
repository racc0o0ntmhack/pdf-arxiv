# routes/auth.py
from flask import Blueprint, request, redirect, url_for, session  # type: ignore[import]
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Admin girişi"""
    password = request.form.get('password')
    # Şifrəni özünüzə uyğun dəyişin
    if password == '"Mən hələ öz dərinliyimdə olan, məni kəşf edəcək o ağıllı adamı tapmamışam.!45"':
        session['logged_in'] = True
        session['login_time'] = datetime.now().isoformat()
    return redirect(url_for('main.index'))

@auth_bp.route('/logout')
def logout():
    """Admin çıxışı"""
    session.pop('logged_in', None)
    session.pop('login_time', None)
    return redirect(url_for('main.index'))