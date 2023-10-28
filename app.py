from hack import app, create_db, db
from flask import render_template, redirect, url_for, flash
from flask_login import current_user, login_user, logout_user, login_required
from hack.forms import LoginForm, RegForm
from hack.models import User
from werkzeug.security import generate_password_hash, check_password_hash

create_db(app)

@app.route('/')
def home():
    return render_template('index.html')

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
            mess = 'Account already exists'
        else:
            new_user = User(email=email, username=username, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
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
