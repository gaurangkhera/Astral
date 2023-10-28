from hack import app, create_db, db
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from hack.forms import LoginForm, RegForm
from hack.models import User, Post, Like, Comment
from werkzeug.security import generate_password_hash, check_password_hash
from uuid import uuid4
from werkzeug.utils import secure_filename

app.config['UPLOAD_FOLDER'] = 'hack/static/uploads'
create_db(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/repository')
def repository():
    posts=Post.query.all()
    return render_template('repository.html', posts=posts)

@app.route('/contribute-data', methods=['GET', 'POST'])
@login_required
def contribute():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        post_type = request.form['category']
        image = request.files['image']
        filename = str(uuid4()) + '_' + secure_filename(image.filename)
        image.save(app.config['UPLOAD_FOLDER'] + '/' + filename)
        new_post = Post(title=title, content=content, post_type=post_type, image=filename, author=current_user.username)
        db.session.add(new_post)
        db.session.commit()
        flash('Thanks for contributing to our repository.', 'success')
        return redirect(url_for('repository'))
    return render_template('contribute.html')

@app.route('/posts/<id>')
def post(id):
    post = Post.query.filter_by(id=id).first_or_404()
    has_user_liked = False if not current_user.is_authenticated else True if Like.query.filter_by(user_id=current_user.id, post_id=post.id).first() else False
    return render_template('post.html', post=post, has_user_liked=has_user_liked)

@app.route('/addcomment/<id>', methods=['POST'])
@login_required
def add_comment(id):
    post = Post.query.filter_by(id=id).first_or_404()
    comment = request.get_json()['comment']
    new_comment = Comment(content=comment, author=current_user.username)
    return jsonify({'success': True})

@app.route('/likepost/<id>', methods=['POST'])
@login_required
def like_post(id):
    try:
        post = Post.query.filter_by(id=id).first_or_404()
        like = Like(user_id=current_user.id, post_id=post.id)
        db.session.add(like)
        db.session.add(post)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(e)
        return jsonify({'success': False})

@app.route('/reg', methods=['GET', 'POST'])
def reg():
    form = RegForm()
    mess = ''
    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Account already exists.', 'error')
        else:
            new_user = User(email=email, username=username, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('Account created successfully', 'success')
            return redirect('/')
    return render_template('reg.html', form=form, mess=mess)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    mess=''
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Email not found.', 'error')
        else:
            if check_password_hash(user.password, password):
                login_user(user, remember=True)
                return redirect(url_for('home'))
            else:
                flash('Incorrect password.', 'error')
    return render_template('login.html', mess=mess, form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, port=6969)
