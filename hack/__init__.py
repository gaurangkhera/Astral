import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

app =  Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

app.config['SECRET_KEY'] = 'secret'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://amgpxddb:QAXoXe4bL9QqkYPFid-Ls1OI7QrmUd_8@rain.db.elephantsql.com/amgpxddb"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
Migrate(app,db, render_as_batch=True)

def create_db(app):
    with app.app_context():
        db.create_all()