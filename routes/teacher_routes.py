from flask import Blueprint
from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from datetime import date
from flask_migrate import Migrate
from school_diary.models import User, Student, School, Parent, Teacher, Director, Classroom, Course, Absence, Grade, Schedule
from school_diary.forms import TeacherAndDirectorProfileForm
from unidecode import unidecode
import random, string
from school_diary.extensions import bcrypt, db

import uuid
from school_diary.utils import generate_unique_username, generate_password
from datetime import date, datetime

DAYS_OF_WEEK = {
    1: 'Понеделник',
    2: 'Вторник',
    3: 'Сряда',
    4: 'Четвъртък',
    5: 'Петък'
}

teacher_bp = Blueprint('teacher', __name__)

@teacher_bp.route('/teacher')
def teacher_dashboard():
    user_id = session.get('user_id')
    role = session.get('role')  # или 'role', но трябва да е еднакво навсякъде
    if not user_id or role != 'teacher':
        return redirect(url_for('auth.login'))  # или 'login', ако не ползваш blueprint за auth
    return render_template('dashboards/teacher_dashboard.html')

@teacher_bp.route('/teacher/profile', methods=['GET', 'POST'])
def manage_profile():
    user_id = session.get('user_id')
    if not user_id:
        flash("Моля, влезте в профила си.", "warning")
        return redirect(url_for('auth.login'))

    teacher = Teacher.query.filter_by(user_id=user_id).first()
    if not teacher:
        flash("Нямате достъп до тази страница.", "danger")
        return redirect(url_for('auth.login'))

    user = teacher.user

    form = TeacherAndDirectorProfileForm(obj=user)  # зареждаме данните от user в формата

    if form.validate_on_submit():
        # валидираме вече CSRF токена автоматично
        if form.email.data != user.email:
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user:
                flash('Имейлът вече е зает от друг потребител.', 'danger')
                return redirect(url_for('teacher.manage_profile'))

        if form.password.data:
            user.password = bcrypt.generate_password_hash(form.password.data)

        user.first_name = form.first_name.data
        user.middle_name = form.middle_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data
        user.phone_number = form.phone_number.data

        db.session.commit()
        flash('Профилът беше обновен.', 'success')
        return redirect(url_for('teacher.manage_profile'))

    return render_template('teacher/profile.html', user=user, teacher=teacher, form=form)


@teacher_bp.route('/teacher/students')
def manage_students():
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth_bp.login'))  # ако потребителят не е логнат

    # Вземаме профила на учителя
    teacher = Teacher.query.filter_by(user_id=user_id).first()
    if not teacher:
        return "Учителският профил не е намерен.", 404

    # Събираме учениците от всички класове, в които участва учителят
    students = []
    for classroom in teacher.classrooms:
        students.extend(classroom.students)

    # Премахваме дублиращи се ученици (ако учителят преподава в повече от един клас с общи ученици)
    unique_students = list({student.id: student for student in students}.values())

    return render_template('teacher/students.html', students=unique_students)

@teacher_bp.route('/teacher/grades', methods=['GET', 'POST'])
def manage_grades():
    teacher = Teacher.query.filter_by(user_id=session.get('user_id')).first()
    if not teacher:
        flash("Нямате достъп.", "danger")
        return redirect(url_for('auth.login'))

    classrooms = Classroom.query.filter_by(school_id=teacher.school_id).all()

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        date_str = request.form.get('date')
        course_id = request.form.get('course_id')
        value = request.form.get('value')

        if not (student_id and date_str and course_id and value):
            flash("Моля, попълнете всички полета.", "warning")
            return redirect(url_for('teacher.manage_grades'))

        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            grade_value = float(value)
        except ValueError:
            flash("Невалидна дата или стойност на оценка.", "warning")
            return redirect(url_for('teacher.manage_grades'))

        grade = Grade(
            student_id=student_id,
            teacher_id=teacher.id,
            course_id=course_id,
            value=grade_value,
            date=date_obj
        )
        db.session.add(grade)
        db.session.commit()
        flash("Оценката беше записана успешно.", "success")
        return redirect(url_for('teacher.manage_grades'))

    return render_template('teacher/grades.html', classrooms=classrooms)

@teacher_bp.route('/teacher/absences', methods=['GET', 'POST'])
def manage_absences():
    # Взимаме учителя по user_id от сесията
    teacher = Teacher.query.filter_by(user_id=session.get('user_id')).first()
    if not teacher:
        flash("Нямате достъп.", "danger")
        return redirect(url_for('auth.login'))

    # Взимаме класовете на училището, в което учителят работи (или само тези, за които преподава)
    classrooms = Classroom.query.filter_by(school_id=teacher.school_id).all()

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        date_str = request.form.get('date')
        course_id = request.form.get('course_id')
        reason = request.form.get('reason')
        excused = bool(request.form.get('excused'))

        if not (student_id and date_str and course_id):
            flash("Моля, попълнете всички задължителни полета.", "warning")
            return redirect(url_for('teacher.manage_absences'))

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Невалидна дата.", "warning")
            return redirect(url_for('teacher.manage_absences'))

        # Записваме отсъствието
        absence = Absence(
            student_id=student_id,
            date=date,
            course_id=course_id,
            reason=reason,
            excused=excused,
            teacher_id=teacher.id
        )
        db.session.add(absence)
        db.session.commit()

        flash("Отсъствието беше записано успешно.", "success")
        return redirect(url_for('teacher.manage_absences'))

    return render_template('teacher/absences.html', classrooms=classrooms)

@teacher_bp.route('/teacher/get_students')
def get_students():
    teacher = Teacher.query.filter_by(user_id=session.get('user_id')).first()
    if not teacher:
        return {"error": "Нямате достъп."}, 403

    classroom_id = request.args.get('classroom_id', type=int)
    if not classroom_id:
        return {"students": []}

    students = Student.query.filter_by(classroom_id=classroom_id).all()

    students_data = []
    for s in students:
        if s.user:  # Проверяваме дали има свързан потребител
            students_data.append({
                "id": s.id,
                "first_name": s.user.first_name,
                "last_name": s.user.last_name
            })

    return jsonify({"students": students_data})

@teacher_bp.route('/teacher/get_courses_for_student_date')
def get_courses_for_student_date():
    teacher = Teacher.query.filter_by(user_id=session.get('user_id')).first()
    if not teacher:
        return {"error": "Нямате достъп."}, 403

    student_id = request.args.get('student_id')
    date_str = request.args.get('date')

    if not student_id or not date_str:
        return {"courses": [], "hours": []}

    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return {"courses": [], "hours": []}

    student = Student.query.get(student_id)
    if not student:
        return {"courses": [], "hours": []}

    # Търсим в Schedule по classroom_id, ден от седмицата (0=понеделник, но твоят модел е 1=понеделник, затова намалям с 1)
    day_of_week = date.isoweekday()  # връща 1-7, където 1=понеделник

    schedules = Schedule.query.filter_by(classroom_id=student.classroom_id, day_of_week=day_of_week).all()

    courses = []
    hours = []
    for sched in schedules:
        courses.append({"id": sched.course_id, "name": sched.course.name})
        hours.append(sched.hour)

    return {"courses": courses, "hours": hours}

@teacher_bp.route('/student/<int:student_id>')
def student_detail(student_id):
    user_id = session.get('user_id')
    teacher = Teacher.query.filter_by(user_id=user_id).first()
    if not teacher:
        return "Учителският профил не е намерен.", 404
    
    student = Student.query.get_or_404(student_id)

    grades = Grade.query.filter_by(student_id=student.id).all()
    absences = Absence.query.filter_by(student_id=student.id).all()

    return render_template(
        'teacher/student_detail.html',
        student=student,
        grades=grades,
        absences=absences
    )

@teacher_bp.route('/absences/<int:absence_id>/justify', methods=['POST'])
def justify_absence(absence_id):
    teacher = Teacher.query.filter_by(user_id=session.get('user_id')).first()
    if not teacher:
        flash("Нямате достъп.", "danger")
        return redirect(url_for('auth.login'))
    # Зареди отсъствието от базата
    absence = Absence.query.get_or_404(absence_id)

    # Логика за извиняване на отсъствието
    absence.excused = True
    db.session.commit()
    flash('Отсъствието беше успешно извинено.', 'success')
    # Връщаме се към страницата с детайли на ученика или към списъка с отсъствия
    return redirect(request.referrer or url_for('teacher.manage_absences'))

@teacher_bp.route("/teacher/schedule")
def teacher_schedule():
    teacher = Teacher.query.filter_by(user_id=session.get('user_id')).first()
    if not teacher:
        flash("Не сте учител.", "danger")
        return redirect(url_for("auth.login"))

    schedule_entries = Schedule.query.filter_by(teacher_id=teacher.id).all()

    # Създаваме таблица: {час: {ден: entry}}
    schedule = {hour: {day: None for day in range(1, 6)} for hour in range(1, 8)}

    for entry in schedule_entries:
        schedule[entry.hour][entry.day_of_week] = entry

    return render_template(
        "teacher/schedule.html",
        schedule=schedule
    )