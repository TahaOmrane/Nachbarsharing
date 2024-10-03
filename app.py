from flask import Flask, render_template
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user
from config import Config

from models import db

migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate.init_app(app, db)
login.init_app(app)

def blueprints():
    from auth import bp
    from main_routes import main
    app.register_blueprint(bp)
    app.register_blueprint(main)

with app.app_context():
    db.create_all()
    blueprints()
    

@login.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))


@app.route('/')
@login_required
def dashboard():
    return render_template('index.html', username=current_user.username)


if __name__ == "__main__":
    app.run(debug=True)