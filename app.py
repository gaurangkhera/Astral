from hack import app, create_db, db
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from hack.forms import LoginForm, RegForm, UseResourceForm
from hack.models import User, Post, Like, Comment, Resource, Page, ResourceUsage
from werkzeug.security import generate_password_hash, check_password_hash
from uuid import uuid4
from werkzeug.utils import secure_filename
import datetime

app.config['UPLOAD_FOLDER'] = 'hack/static/uploads'
create_db(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/repository')
def repository():
    posts=Post.query.all()
    return render_template('repository.html', posts=posts)

@app.route('/dashboard')
@login_required
def dashboard():
    resource_usage_data = ResourceUsage.query.filter_by(user_id=current_user.id).all()
    dates = [data.date.strftime('%Y-%m-%d') for data in resource_usage_data]
    usages = [data.usage for data in resource_usage_data]
    low_resources = [resource for resource in current_user.resources if resource.quantity <= 5]
    print(low_resources)
    return render_template('dashboard.html', dates=dates, usages=usages, low_resources=low_resources)

@app.route('/dashboard/add-resources', methods=['GET', 'POST'])
@login_required
def add_resources():
    if request.method == 'POST':
        resource_names = request.form.getlist('resource-name[]')
        resource_quantities = request.form.getlist('resource-quantity[]')
        for name, quantity in zip(resource_names, resource_quantities):
            if name and quantity:
                resource = Resource(name=name, quantity=int(quantity), user=current_user.id)
                db.session.add(resource)
                db.session.commit()
        flash('Resources added successfully.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_resources.html')

@app.route('/dashboard/resource/<id>', methods=['GET', 'POST'])
@login_required
def resource(id):
    resource = Resource.query.filter_by(id=id, user=current_user.id).first_or_404()
    form = UseResourceForm()
    resource_usage_data = ResourceUsage.query.filter_by(resource_id=resource.id, user_id=current_user.id).all()
    dates = [data.date.strftime('%Y-%m-%d') for data in resource_usage_data]
    usages = [data.usage for data in resource_usage_data]
    if form.validate_on_submit():
        procured_quantity = form.qty.data
        resource.quantity += procured_quantity
        db.session.add(resource)
        db.session.commit()    
        flash('Quantity updated successfully.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('resource.html', resource=resource, resource_usage_data=resource_usage_data, dates=dates, usages=usages, form=form)

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

@app.route('/dashboard/resource/<id>/use-resource/', methods=['GET', 'POST'])
def use_resource(id):
    resource = Resource.query.filter_by(id=id).first_or_404()
    form = UseResourceForm()
    if form.validate_on_submit():
        usage = form.qty.data
        new_usage = ResourceUsage(usage=usage, resource_id=resource.id, user_id=current_user.id)
        if usage > resource.quantity:
            flash(f"You don't have this much {resource.name.lower()}!", 'error')
            return redirect(url_for('dashboard'))
        if usage == resource.quantity:
            db.session.delete(resource)
            db.session.commit()
            flash(f"You've used up all of your {resource.name.lower()}!", 'error')
            return redirect(url_for('dashboard'))
        resource.quantity -= usage
        db.session.add(resource)
        db.session.add(new_usage)
        db.session.commit()
        flash('Usage recorded successfully.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('use_resource.html', resource=resource, form=form)

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
    new_comment = Comment(content=comment, author=current_user.username, post=post.id)
    db.session.add(post)
    db.session.add(new_comment)
    db.session.commit()
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

@app.route('/journal', methods=['GET', 'POST'])
@login_required
def journal():
    if request.method == 'POST':
        content = request.form['content']
        page = Page(content=content, user=current_user.id)
        db.session.add(page)
        db.session.add(current_user)
        db.session.commit()
        flash('Successfully filled today\'s journal.', 'success')
        return redirect(url_for('journal'))
    already_written = Page.query.filter_by(user=current_user.id, created_at=datetime.datetime.now().strftime('%b %d')).first()
    return render_template('journal.html', already_written=already_written)

@app.route('/journal/page/<id>', methods=['GET', 'POST'])
@login_required
def page(id):
    page = Page.query.filter_by(id=id, user=current_user.id).first_or_404()
    return render_template('page.html', page=page)

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
