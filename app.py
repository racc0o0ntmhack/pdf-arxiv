# app.py
from flask import Flask  # type: ignore
from config import Config, ensure_directories
from routes import register_routes

# Flask tətbiqini yarat
app = Flask(__name__)

# Konfiqurasiyaları yüklə
app.config.from_object(Config)

# Lazım olan qovluqları yarat
ensure_directories()

# Bütün routeları qeydiyyatdan keçir
register_routes(app)

# Proqramı işə sal
if __name__ == '__main__':
    app.run(
        debug=Config.DEBUG,
        host=Config.HOST,
        port=Config.PORT
    )