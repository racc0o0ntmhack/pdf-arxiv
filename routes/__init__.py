# routes/__init__.py
from routes.main import main_bp
from routes.auth import auth_bp
from routes.files import files_bp
from routes.folders import folders_bp
from routes.reader import reader_bp

def register_routes(app):
    """Bütün routeları qeydiyyatdan keçir"""
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(folders_bp)
    app.register_blueprint(reader_bp)