from flask import Blueprint
from flask import Flask, render_template, redirect, url_for, request, session, flash
# from flask_migrate import Migrate
from school_diary.models import User, Student, Parent, Teacher, Director
from school_diary.forms import LoginForm, RegisterForm
# from unidecode import unidecode
# import random, string
from school_diary.extensions import bcrypt, db
import uuid
from school_diary.utils import generate_unique_username, generate_password


auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('general.dashboard'))
    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    print("Form submitted:", request.method == "POST")
    print("Form valid:", form.validate_on_submit())
    print("Form errors:", form.errors)
    if form.validate_on_submit():
        # Взимаме паролата от полето password (която вече е потвърдена)
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

        # Генерираме username (игнорираме form.username)
        generated_username = generate_unique_username(
            form.first_name.data.strip(),
            form.middle_name.data.strip(),
            form.last_name.data.strip()
        )

        # Създаваме User с генерираното потребителско име
        user = User(
            username=generated_username,
            password=hashed_pw,
            role=form.role.data,
            first_name=form.first_name.data.strip(),
            middle_name=form.middle_name.data.strip(),
            last_name=form.last_name.data.strip(),
            email=form.email.data.strip(),
            phone_number=form.phone_number.data.strip()
        )
        db.session.add(user)
        db.session.flush()

        role = form.role.data

        if role == 'student':
            share_code = uuid.uuid4().hex[:10].upper()
            student = Student(user_id=user.id, share_code=share_code)
            db.session.add(student)
        elif role == 'parent':
            
            parent = Parent(user_id=user.id)
            db.session.add(parent)
        elif role == 'teacher':
            teacher = Teacher(user_id=user.id)
            db.session.add(teacher)
        elif role == 'director':
            director = Director(user_id=user.id)
            db.session.add(director)

        db.session.commit()

        flash(f'Регистрацията е успешна. Вашето потребителско име е: {generated_username}. Моля, влезте в профила си.', 'success')
        return redirect(url_for('auth.login'))
    else:
        if request.method == 'POST':
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Грешка в полето {getattr(form, field).label.text}: {error}", 'danger')
    return render_template('register.html', form=form)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))