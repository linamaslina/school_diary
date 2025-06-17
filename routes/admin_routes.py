from flask import Blueprint
from flask import Blueprint
from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_migrate import Migrate
from school_diary.models import User, Student, School, Parent, Teacher, Director, Classroom, Course, Grade, Absence
from school_diary.forms import LoginForm, AddUserForm, SchoolForm, ClassroomForm, RegisterForm
from unidecode import unidecode
from sqlalchemy import func

import random, string
import uuid
from school_diary.extensions import bcrypt, db
from school_diary.utils import generate_unique_username, generate_password

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/dashboard')
def admin_dashboard_view():
    return render_template('dashboards/admin_dashboard_view.html')

@admin_bp.route('/add_user', methods=['GET', 'POST'])
def add_user():

    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))

    form = AddUserForm()
    students = Student.query.all()
    classrooms = Classroom.query.all()
    schools = School.query.all()
    courses = Course.query.all()

    if form.validate_on_submit():

        # Хеширане на паролата
        password=generate_password()
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        generated_username = generate_unique_username(
            form.first_name.data.strip(),
            form.middle_name.data.strip(),
            form.last_name.data.strip()
        )
        # Създаване на основния потребител
        user = User(
            username=generated_username,
            password=hashed_pw,
            role=form.role.data,
            first_name=form.first_name.data.strip(),
            middle_name=form.middle_name.data.strip(),
            last_name=form.last_name.data.strip(),
            email=form.email.data.strip() if form.email.data else None,
            phone_number=form.phone_number.data.strip() if form.phone_number.data else None,
            date_of_birth=form.date_of_birth.data
        )
        db.session.add(user)
        db.session.flush()  # Нужно за да получим user.id преди commit

        role = form.role.data

        if role == 'student':
            classroom_id = request.form.get('classroom_id')
            
            student = Student(user_id=user.id, classroom_id=classroom_id, share_code=uuid.uuid4().hex[:10].upper())
            db.session.add(student)

        elif role == 'parent':
            parent = Parent(user_id=user.id)
            db.session.add(parent)

            share_code = request.form.get('share_code', '').strip().upper()
            student = Student.query.filter_by(share_code=share_code).first()

            if not student:
                flash('Невалиден код на ученик.', 'danger')
                return render_template('add_user.html', form=form, schools=schools, classrooms=classrooms, courses=courses)

            if len(student.parents) >= 2:
                flash('Ученикът вече има двама родители.', 'danger')
                return render_template('add_user.html', form=form, schools=schools, classrooms=classrooms, courses=courses)

            parent.children.append(student)


        elif role == 'teacher':
            school_id = request.form.get('teacher_school_id')
            course_ids = request.form.getlist('teacher_course_ids')
            teacher = Teacher(user_id=user.id, school_id=school_id)
            teacher.courses = Course.query.filter(Course.id.in_(course_ids)).all()
            db.session.add(teacher)

        elif role == 'director':
            school_id = request.form.get('school_id')
            school = School.query.get(school_id)

            if not school:
                flash('Училището не съществува.', 'danger')
                return render_template('add_user.html', form=form, students=students, schools=schools, classrooms=classrooms)

            if school.director:
                flash('Това училище вече има директор.', 'danger')
                return render_template('add_user.html', form=form, students=students, schools=schools, classrooms=classrooms)

            director = Director(user_id=user.id, school_id=school.id)
            db.session.add(director)

        db.session.commit()
        flash(f'Потребителят е добавен успешно. Парола: {password}', 'success')
        return redirect(url_for('admin.manage_users'))

    return render_template('add_user.html', form=form, students=students, schools=schools, classrooms=classrooms, courses=courses)

@admin_bp.route('/admin/users')
def manage_users():
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@admin_bp.route('/user/<int:user_id>')
def view_user(user_id):
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))

    user = User.query.get_or_404(user_id)
    details = {}

    if user.role == 'student':
        student = Student.query.filter_by(user_id=user.id).first()
        details['student'] = student

    elif user.role == 'teacher':
        teacher = Teacher.query.filter_by(user_id=user.id).first()
        details['teacher'] = teacher
        details['class_teacher_of'] = teacher.class_teacher_of

    elif user.role == 'parent':
        parent = Parent.query.filter_by(user_id=user.id).first()
        details['parent'] = parent
        details['children'] = parent.children

    elif user.role == 'director':
        director = Director.query.filter_by(user_id=user.id).first()
        details['director'] = director
        details['school'] = director.school

    return render_template('view_user.html', user=user, **details)

@admin_bp.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))
    
    user = User.query.get(user_id)
    if user:
        # Премахваме свързаните профили (ако има такива)
        student = Student.query.filter_by(user_id=user.id).first()
        if student:
            db.session.delete(student)
        
        parent = Parent.query.filter_by(user_id=user.id).first()
        if parent:
            db.session.delete(parent)
        
        teacher = Teacher.query.filter_by(user_id=user.id).first()
        if teacher:
            db.session.delete(teacher)
        
        director = Director.query.filter_by(user_id=user.id).first()
        if director:
            db.session.delete(director)

        # Изтриваме самия user
        db.session.delete(user)
        db.session.commit()
        flash('Потребителят и свързаните с него данни бяха изтрити успешно!', 'success')
    else:
        flash('Потребителят не беше намерен.', 'warning')

    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if session.get('role') != 'admin':
        flash("Нямате достъп до тази страница.", "danger")
        return redirect(url_for('auth.login'))

    user = User.query.get_or_404(user_id)
    form = AddUserForm(obj=user)

    # Ролята не може да се променя
    form.role.render_kw = {'readonly': True, 'disabled': True}

    schools = School.query.all()
    classrooms = Classroom.query.all()
    courses = Course.query.all()
    students = Student.query.all()

    # Зареждаме свързаните обекти според роля
    student = Student.query.filter_by(user_id=user.id).first()
    parent = Parent.query.filter_by(user_id=user.id).first()
    teacher = Teacher.query.filter_by(user_id=user.id).first()
    director = Director.query.filter_by(user_id=user.id).first()

    share_code = student.share_code if student else None
    selected_student_ids = [s.id for s in parent.children] if parent else []
    selected_course_ids = [c.id for c in teacher.courses] if teacher else []

    # Инициализираме стойности за teacher_school_id и teacher_course_ids
    teacher_school_id = teacher.school_id if teacher else None
    teacher_course_ids = [c.id for c in teacher.courses] if teacher else []

    if form.validate_on_submit():
        # Обновяваме основните данни на потребителя
        user.first_name = form.first_name.data.strip()
        user.middle_name = form.middle_name.data.strip()
        user.last_name = form.last_name.data.strip()
        user.email = form.email.data.strip()
        user.phone_number = form.phone_number.data.strip()
        user.date_of_birth = form.date_of_birth.data


        # Обработка според роля
        if user.role == 'student':
            classroom_id = request.form.get('classroom_id')
            if not classroom_id:
                flash('Моля, изберете клас.', 'warning')
                return redirect(request.url)

            if not student:
                student = Student(user_id=user.id)
                db.session.add(student)
            student.classroom_id = int(classroom_id)

        elif user.role == 'parent':
            if not parent:
                parent = Parent(user_id=user.id)
                db.session.add(parent)

            selected_ids = request.form.getlist('student_ids')
            valid_students = []
            for sid in selected_ids:
                s = Student.query.get(int(sid))
                if s:
                    # Проверка дали студентът има до 2 родители, или текущият родител вече е сред тях
                    if len(s.parents) < 2 or parent in s.parents:
                        valid_students.append(s)
                    else:
                        flash(f"{s.user.first_name} {s.user.last_name} вече има двама родители.", "danger")
                else:
                    flash(f"Студент с ID {sid} не е намерен.", "warning")

            parent.children = valid_students

        elif user.role == 'teacher':
            # Взимане на стойности от формата
            school_id = request.form.get('teacher_school_id')
            course_ids = request.form.getlist('teacher_course_ids')

            # Проверка дали училище е избрано
            if not school_id:
                flash('Моля, изберете училище.', 'warning')
                return redirect(request.url)

            # Създаване на обект Teacher ако не съществува
            if not teacher:
                teacher = Teacher(user_id=user.id)
                db.session.add(teacher)

            teacher.school_id = int(school_id)

            # Зареждане на всички предмети за избраното училище
            school = School.query.get(int(school_id))
            school_courses = school.courses if school else []

            # Проверка дали избраните предмети са валидни
            if course_ids:
                valid_courses = Course.query.filter(Course.id.in_(course_ids)).all()
                valid_course_ids = {str(c.id) for c in school_courses}  # само предметите от това училище
                # Филтриране на избраните предмети, така че да са от това училище
                filtered_courses = [c for c in valid_courses if str(c.id) in valid_course_ids]
                teacher.courses = filtered_courses
            else:
                teacher.courses = []

        elif user.role == 'director':
            school_id = request.form.get('school_id')

            if not school_id:
                flash('Моля, изберете училище.', 'warning')
                return redirect(request.url)

            school = School.query.get(int(school_id))
            if not school:
                flash('Училището не съществува.', 'danger')
                return redirect(url_for('admin.manage_users'))

            # Проверка дали вече има друг директор на това училище, различен от текущия
            existing_director = Director.query.filter(
                Director.school_id == school.id,
                Director.id != (director.id if director else -1)
            ).first()

            if existing_director:
                flash('Това училище вече има друг директор.', 'danger')
                return redirect(url_for('admin.manage_users'))

            if not director:
                director = Director(user_id=user.id)
                db.session.add(director)
            director.school_id = school.id

        db.session.commit()
        flash("Потребителят беше обновен успешно!", "success")
        return redirect(url_for('admin.manage_users'))
    
    for course in courses:
        course.first_school_id = course.schools[0].id if course.schools else None
    
    return render_template(
        'edit_user.html',
        form=form,
        user=user,
        classrooms=classrooms,
        students=students,
        student=student,
        parent=parent,
        director=director,
        selected_student_ids=selected_student_ids,
        selected_course_ids=selected_course_ids,
        share_code=share_code,
        schools=schools,
        courses=courses,
        teacher=teacher,
        teacher_school_id=teacher_school_id,
        teacher_course_ids=teacher_course_ids,
    )

@admin_bp.route('/admin/schools/add', methods=['GET', 'POST'])
def add_school():
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))

    form = SchoolForm()

    if form.validate_on_submit():
        existing_school = School.query.filter_by(name=form.name.data.strip(), city=form.city.data.strip()).first()
        if existing_school:
            flash("❗ Училище с това име вече съществува в този град.", "danger")
            return render_template('add_school.html', form=form)

        school = School(
            name=form.name.data.strip(),
            address=form.address.data.strip(),
            city=form.city.data.strip()
        )
        db.session.add(school)
        db.session.flush()  # за да получим school.id преди commit

        # Обработка на класовете (ако има)
        class_str = form.classrooms.data.strip()
        if class_str:
            entries = [e.strip().upper() for e in class_str.split(',')]
            for entry in entries:
                # Валидация: първа част - число (клас), последна - буква (паралелка)
                if len(entry) >= 2 and entry[:-1].isdigit() and entry[-1].isalpha():
                    grade = int(entry[:-1])
                    letter = entry[-1]
                    existing = Classroom.query.filter_by(school_id=school.id, grade=grade, letter=letter).first()
                    if not existing:
                        classroom = Classroom(school_id=school.id, grade=grade, letter=letter)
                        db.session.add(classroom)
                else:
                    flash(f"Невалиден формат за клас: {entry}. Използвайте например 1А, 2Б.", "warning")

        db.session.commit()
        flash('Училището и класовете са добавени успешно.', 'success')
        return redirect(url_for('admin.manage_schools'))

    return render_template('add_school.html', form=form)

@admin_bp.route('/admin/schools/delete/<int:school_id>', methods=['POST'])
def delete_school(school_id):
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))
    
    school = School.query.get_or_404(school_id)
    confirm_school_id = request.args.get('confirm_school_id', type=int)
    if "confirm" in request.form:
        # Изтриване след потвърждение
        db.session.delete(school)
        db.session.commit()
        flash(f"Училището '{school.name}' и всички негови класове бяха изтрити.", "success")
        return redirect(url_for("admin.manage_schools"))

    if school.classrooms:
        flash(f"Училището '{school.name}' има класове. Потвърдете изтриването.", "warning")
        return redirect(url_for("admin.manage_schools", confirm_school_id=school.id))

    # Ако няма класове – изтрий директно
    db.session.delete(school)
    db.session.commit()
    flash(f"Училището '{school.name}' беше изтрито успешно.", "success")
    return redirect(url_for("admin.manage_schools"))

@admin_bp.route('/admin/schools/<int:school_id>/add_class', methods=['GET', 'POST'])
def add_classroom(school_id):
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))

    school = School.query.get_or_404(school_id)

    if request.method == 'POST':
        grade = int(request.form['grade'])
        letter = request.form['letter']
        classroom = Classroom(grade=grade, letter=letter, school_id=school.id)
        db.session.add(classroom)
        db.session.commit()
        flash(' Класът е добавен успешно.', 'success')
        return redirect(url_for('admin.manage_schools'))

    return render_template('add_classroom.html', school=school)

@admin_bp.route('/admin/manage_schools', methods=['GET', 'POST'])
def manage_schools():
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        city = request.form['city']
        school = School(name=name, address=address, city=city)
        db.session.add(school)
        db.session.commit()
        flash('Училището е добавено.', 'success')
        return redirect(url_for('admin.manage_schools'))

    schools = School.query.all()
    confirm_school_id = request.args.get('confirm_school_id', type=int)
    return render_template('manage_schools.html', schools=schools, confirm_school_id=confirm_school_id)

@admin_bp.route('/courses', methods=['GET', 'POST'])
def manage_courses():
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        course_name = request.form.get('name')
        if course_name:
            existing = Course.query.filter_by(name=course_name).first()
            if existing:
                flash('Този предмет вече съществува.', 'warning')
            else:
                course = Course(name=course_name)
                db.session.add(course)
                db.session.commit()
                flash('Предметът беше добавен успешно!', 'success')
        return redirect(url_for('admin.manage_courses'))

    courses = Course.query.order_by(Course.name).all()
    return render_template('manage_courses.html', courses=courses)

@admin_bp.route('/courses/delete/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))

    course = Course.query.get(course_id)
    if course:
        db.session.delete(course)
        db.session.commit()
        flash('Предметът беше изтрит успешно.', 'success')
    else:
        flash('Предметът не беше намерен.', 'warning')
    return redirect(url_for('admin.manage_courses'))

@admin_bp.route('/statistics')
def view_statistics():
    if session.get('role') != 'admin':
        flash("Нямате достъп", "danger")
        return redirect(url_for('auth.login'))

    # Общи статистики
    all_grades = db.session.query(Grade).all()
    all_absences = db.session.query(Absence).all()

    # Групиране по училище
    grades_by_school = db.session.query(
        School.name, func.count(Grade.id)
    ).join(Classroom, School.id == Classroom.school_id
    ).join(Student, Student.classroom_id == Classroom.id
    ).join(Grade, Grade.student_id == Student.id
    ).group_by(School.name).all()

    absences_by_school = db.session.query(
        School.name, func.count(Absence.id)
    ).join(Classroom, School.id == Classroom.school_id
    ).join(Student, Student.classroom_id == Classroom.id
    ).join(Absence, Absence.student_id == Student.id
    ).group_by(School.name).all()

    # Групиране по предмет
    grades_by_course = db.session.query(
        Course.name, func.count(Grade.id)
    ).join(Grade.course
    ).group_by(Course.name).all()

    grades_avg_by_school = (
    db.session.query(
        School.name,
        func.avg(Grade.value).label('avg_grade')
    )
    .join(Classroom, School.id == Classroom.school_id)
    .join(Student, Student.classroom_id == Classroom.id)
    .join(Grade, Grade.student_id == Student.id)
    .group_by(School.name)
    .all()
    )

    grades_avg_by_course = (
    db.session.query(
        Course.name,
        func.avg(Grade.value).label('avg_grade')
    )
    .join(Grade.course)
    .group_by(Course.name)
    .all()
    )
    return render_template('statistics.html',
                           total_grades=len(all_grades),
                           total_absences=len(all_absences),
                           grades_by_school=grades_by_school,
                           absences_by_school=absences_by_school,
                           grades_by_course=grades_by_course,
                           grades_avg_by_school=grades_avg_by_school,
                           grades_avg_by_course=grades_avg_by_course
                           )