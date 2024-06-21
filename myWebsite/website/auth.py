from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from .models import PasswordResetToken, User
import hashlib
from . import db
from flask_login import login_user, login_required, logout_user, current_user
import time, random
import secrets
from flask_mail import Message
from datetime import datetime, timedelta

auth = Blueprint('auth', __name__)


class Authenticate:
    
    def hashPass(password):
        password_bytes = password.encode('utf-8')
        sha256_hash = hashlib.sha256()
        sha256_hash.update(password_bytes)
        hashed_password = sha256_hash.hexdigest()
        return hashed_password

    def generate_token():
        return secrets.token_urlsafe(32)
    
    def set_password_reset_token(user, token):
        expiration_date = datetime.now() + timedelta(hours=24)  # Expire in 24 hours
        reset_token = PasswordResetToken(user_id=user.id, token=token, expiration_date=expiration_date)
        db.session.add(reset_token)
        db.session.commit()

    def get_password_reset_token(token):
        reset_token = PasswordResetToken.query.filter_by(token=token).first()
        if reset_token and reset_token.expiration_date > datetime.now():
            return reset_token.user_id
        elif reset_token.expiration_date < datetime.now():
            db.session.delete(reset_token)
            
        return None
    
    def send_password_reset_email(user, reset_link):
        msg = Message('Password Reset Request',
                    sender='chatappreset@gmail.com',
                    recipients=[user.email])
        msg.body = f"Hi {user.first_name},\n" \
                    f"A password reset request has been made for your account.\n" \
                    f"Click on the link below to reset your password:\n" \
                    f"{reset_link}\n" \
                    f"This link will expire in 24 hours.\n" \
                    f"If you did not request a password reset, please ignore this email.\n"
        current_app.mail.send(msg)
    
    

@auth.route('/login', methods=['get', 'post'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            time.sleep(random.randint(1,10)/10)
            if Authenticate.hashPass(password) == user.password:
                flash('Logged in!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.add_contact'))
            else:
                flash('Incorrect password. Try again', category='error')
        else:
            flash('no account with this email', category='error')

    return render_template("login.html", user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth.route('/sign-up', methods=['get', 'post'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        user = User.query.filter_by(email=email).first()
        if user:
            flash('email already exists.', category='error')
        elif len(email) < 4:
            flash('Enter a valid e-mail.', category='error')
        elif len(first_name) < 2:
            flash('Enter a valid username.', category='error')
        elif len(password1) < 8:
            flash('Password must have at least 8 characters', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        else:
            #add user to DB
            new_user = User(email=email, first_name=first_name, password=Authenticate.hashPass(password1))
            db.session.add(new_user)
            db.session.commit()
            flash('Account created!', category='success')
            login_user(new_user, remember=True)
            return redirect(url_for('views.add_contact'))

    return render_template("sign_up.html", user=current_user)


@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token=Authenticate.generate_token()
            Authenticate.set_password_reset_token(user, token)
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            Authenticate.send_password_reset_email(user, reset_link)
            flash('A password reset link has been sent to your email address.', category='success')
            return redirect(url_for('auth.login'))
        else:
            flash('No account associated with this email address.', category='error')
    return render_template("forgot_password.html", user=current_user)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('views.add_contact'))
    user_id = Authenticate.get_password_reset_token(token)
    if user_id:
        user = User.query.get(user_id)
        if not user:
            flash('Invalid or expired reset token.', category='error')
            return redirect(url_for('auth.forgot_password'))

        if request.method == 'POST':
            password1 = request.form.get('password')
            password2 = request.form.get('password2')
            if len(password1) < 8:
                flash('Password must have at least 8 characters', category='error')
            elif password1 != password2:
                flash('Passwords don\'t match.', category='error')
            else:
                user.password = Authenticate.hashPass(password1)
                db.session.commit()
                flash('Your password has been updated.', category='success')
                return redirect(url_for('auth.login'))
            
        return render_template('reset_password.html', token=token, user=current_user)
    
    else:
        flash('Invalid or expired reset token.', category='error')
        return redirect(url_for('auth.forgot_password'))