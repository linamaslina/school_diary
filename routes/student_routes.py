from flask import Blueprint
from flask import Blueprint
from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_migrate import Migrate
from school_diary.models import User, Student, School, Parent, Teacher, Director, Classroom, Course, Grade, Absence, Schedule 
from school_diary.forms import StudentProfileForm
from unidecode import unidecode
import random, string

import uuid
from school_diary.extensions import bcrypt, db

from school_diary.utils import generate_unique_username, generate_password


student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard/student')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('auth.login'))
    
    student = Student.query.filter_by(user_id=session.get('user_id')).first()
    if not student:
        flash("Нямате достъп до таблото.", "danger")
        return redirect(url_for('auth.login'))
    classroom = student.classroom 
    return render_template('dashboards/student_dashboard.html', classroom=classroom)

# Примерен route за оценките
@student_bp.route('/grades')
def manage_grades():
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))  # ако потребителят не е логнат

    # Вземаме профила на учителя
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return "Ученическият профил не е намерен.", 404
    grades = Grade.query.filter_by(student_id=student.id).all()

    return render_template('student/grades.html', grades=grades)

# Примерен route за отсъствията
@student_bp.route('/absences')
def manage_absences():
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))  # ако потребителят не е логнат

    # Вземаме профила на учителя
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return "Ученическият профил не е намерен.", 404
    absences = Absence.query.filter_by(student_id=student.id).all()

    data = [{
        'date': a.date.strftime('%d.%m.%Y'),
        'reason': a.reason
    } for a in absences]

    return render_template('student/absences.html', absences=data)

@student_bp.route("/schedule")
def view_schedule():
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))

    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return "Ученическият профил не е намерен.", 404

    classroom = student.classroom

    schedule_entries = []
    schedule_matrix = None

    if classroom:
        schedule_entries = Schedule.query.filter_by(classroom_id=classroom.id).all()
        if schedule_entries:
            schedule_matrix = {hour: {day: None for day in range(1, 6)} for hour in range(1, 8)}
            for entry in schedule_entries:
                schedule_matrix[entry.hour][entry.day_of_week] = entry

    return render_template(
        "student/schedule.html",
        classroom=classroom,
        schedule_matrix=schedule_matrix
    )




@student_bp.route('/profile')
def profile():
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))  # ако потребителят не е логнат

    # Вземаме профила на учителя
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return "Ученическият профил не е намерен.", 404
    user = student.user

    form = StudentProfileForm(obj=user)

    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.middle_name = form.middle_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data
        user.phone_number = form.phone_number.data
        user.date_of_birth = form.date_of_birth.data

        # Смяна на паролата, ако е въведена
        if form.password.data:
            user.password = bcrypt.generate_password_hash(form.password.data)

        db.session.commit()
        flash('Профилът беше обновен успешно.', 'success')
        return redirect(url_for('student.profile'))

    return render_template('student/profile.html', form=form, student=student)

