from hack import db,login_manager
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import UserMixin
from uuid import uuid4
import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

def get_uuid():
    return uuid4().hex

class User(db.Model,UserMixin):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    username = db.Column(db.String, nullable=False, unique=True)
    email = db.Column(db.String(64),index=True)
    password = db.Column(db.Text)
    membership = db.Column(db.String, default='Free')
    posts = db.relationship('Post', backref='authorPost', lazy=True)
    comments = db.relationship('Comment', backref='authorComment', lazy=True)
    likes = db.relationship('Like', backref='authorLike', lazy=True)
    pages = db.relationship('Page', backref='authorPage', lazy=True)
    resources = db.relationship('Resource', backref='authorResource', lazy=True)
    resource_usage = db.relationship('ResourceUsage', backref='authorResourceUsage', lazy=True)

class ResourceUsage(db.Model):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    date = db.Column(db.DateTime, default=datetime.datetime.now)
    usage = db.Column(db.Integer, nullable=False)
    resource_id = db.Column(db.String, db.ForeignKey('resource.id'), nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('user.id'), nullable=False)   

class Post(db.Model):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    image = db.Column(db.String(255))
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    post_type = db.Column(db.String(20))
    likes = db.relationship('Like', backref='postLike', lazy=True)
    comments = db.relationship('Comment', backref='postComment', lazy=True)
    author = db.Column(db.String, db.ForeignKey('user.username'))

class Page(db.Model):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    content = db.Column(db.Text)
    user = db.Column(db.String, db.ForeignKey('user.id'))
    created_at = db.Column(db.String, default=datetime.datetime.now().strftime('%b %d'))

class Resource(db.Model):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    name = db.Column(db.String(255))
    quantity = db.Column(db.Integer)
    user = db.Column(db.String, db.ForeignKey('user.id'))

class Like(db.Model):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    user_id = db.Column(db.String, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.String, db.ForeignKey('post.id'), nullable=False)

class Comment(db.Model):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    content = db.Column(db.Text)
    post = db.Column(db.String, db.ForeignKey('post.id'))
    author = db.Column(db.String, db.ForeignKey('user.username'))
