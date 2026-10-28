from flask import Flask, redirect, url_for

from config import Config
from database.init_db import init_db
from routes.api import api_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp


app = Flask(__name__)
app.config.from_object(Config)

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(api_bp)


with app.app_context():
    init_db()


@app.route('/')
def index():
    return redirect(url_for('dashboard.dashboard_home'))


if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000)
