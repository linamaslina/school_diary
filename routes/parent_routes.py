from flask import Blueprint
from flask import Blueprint
from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_migrate import Migrate
from school_diary.models import User, Student, School, Parent, Teacher, Director, Classroom, Course
from school_diary.forms import ParentForm
from unidecode import unidecode
import random, string
from school_diary.extensions import bcrypt, db
import uuid
from school_diary.utils import generate_unique_username, generate_password

parent_bp = Blueprint('parent', __name__)

@parent_bp.route('/parent')
def parent_dashboard():
    if session.get('role') != 'parent':
        return redirect(url_for('auth.login'))

    parent = Parent.query.filter_by(user_id=session.get('user_id')).first()
    if not parent:
        flash("Нямате достъп до таблото на родител.", "danger")
        return redirect(url_for('auth.login'))

    return render_template('dashboards/parent_dashboard.html')

@parent_bp.route('/parent/children')
def view_children():
    if session.get('role') != 'parent':
        return redirect(url_for('auth.login'))

    parent = Parent.query.filter_by(user_id=session.get('user_id')).first()
    if not parent:
        flash("Нямате достъп.", "danger")
        return redirect(url_for('auth.login'))

    children = parent.children  # Предполага се, че имаш релация `children = relationship('Student', secondary=...)`
    return render_template('parent/view_children.html', children=children)

@parent_bp.route('/parent/grades')
def view_grades():
    if session.get('role') != 'parent':
        return redirect(url_for('auth.login'))

    parent = Parent.query.filter_by(user_id=session.get('user_id')).first()
    if not parent:
        flash("Нямате достъп до оценки.", "danger")
        return redirect(url_for('auth.login'))

    grades_by_child = {child: child.grades for child in parent.children}
    return render_template('parent/view_grades.html', grades_by_child=grades_by_child)

@parent_bp.route('/parent/absences')
def view_absences():
    if session.get('role') != 'parent':
        return redirect(url_for('auth.login'))

    parent = Parent.query.filter_by(user_id=session.get('user_id')).first()
    if not parent:
        flash("Нямате достъп до отсъствия.", "danger")
        return redirect(url_for('auth.login'))

    absences_by_child = {child: child.absences for child in parent.children}
    return render_template('parent/view_absences.html', absences_by_child=absences_by_child)

@parent_bp.route('/parent/profile', methods=['GET', 'POST'])
def parent_profile():
    if session.get('role') != 'parent':
        return redirect(url_for('auth.login'))

    user = User.query.get(session.get('user_id'))
    parent = Parent.query.filter_by(user_id=user.id).first()
    form = ParentForm(obj=user)

    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.middle_name = form.middle_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data
        user.phone_number = form.phone_number.data
        user.date_of_birth = form.date_of_birth.data

        if form.password.data:
            user.password = bcrypt.generate_password_hash(form.password.data)

        # Проверка и добавяне на дете по споделен код
        if form.share_code.data:
            share_code = form.share_code.data.strip()
            child = Student.query.filter_by(share_code=share_code).first()
            if child:
                if child not in parent.children:
                    parent.children.append(child)
                    flash(f"Успешно добавихте {child.user.first_name} {child.user.last_name} като ваше дете.", 'success')
                else:
                    flash("Това дете вече е добавено.", 'info')
            else:
                flash("Невалиден код за дете.", 'danger')

        db.session.commit()
        flash('Профилът беше обновен успешно.', 'success')
        return redirect(url_for('parent.parent_profile'))

    return render_template('parent/profile.html', form=form, children=parent.children)

