from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_required
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'login'

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate.init_app(app, db)
login.init_app(app)
from auth import  bp
app.register_blueprint(bp)


@app.route('/', methods=['GET'])
def home():
   
    return '<h1>Share Neighbour</h1>'






if __name__ == "__main__":
    app.run(debug=True)