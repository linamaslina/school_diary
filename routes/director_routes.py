from flask import Blueprint
from sqlalchemy import or_
from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from flask_migrate import Migrate
from school_diary.models import User, Student, Teacher, Director, Classroom, Course, Schedule, teacher_course, Parent, Grade, parent_student, Absence
from school_diary.forms import ScheduleForm, AutoAddScheduleForm, ScheduleFilterForm, TeacherAndDirectorProfileForm, AddTeacherForm
from unidecode import unidecode
import random, string
from school_diary.extensions import bcrypt, db
import uuid
from school_diary.utils import auto_add_schedule
from sqlalchemy import cast, String, literal

director_bp = Blueprint('director', __name__)

@director_bp.route('/director')
def director_dashboard():
    user_id = session.get('user_id')
    role = session.get('role')  # или 'role', но трябва да е еднакво навсякъде
    if not user_id or role != 'director':
        return redirect(url_for('auth.login'))  # или 'login', ако не ползваш blueprint за auth
    return render_template('dashboards/director_dashboard.html')

@director_bp.route('/teachers')
def director_teachers():
    if session.get('role') != 'director':
        return redirect(url_for('auth.login'))

    director = Director.query.filter_by(user_id=session['user_id']).first()
    if not director:
        flash("Нямате достъп.", "danger")
        return redirect(url_for('auth.login'))

    teachers = Teacher.query.filter_by(school_id=director.school_id).all()
    return render_template('director/teachers.html', teachers=teachers)

@director_bp.route('/director/students')
def director_students():
    if session.get('role') != 'director':
        flash("Нямате достъп до тази страница.", "danger")
        return redirect(url_for('auth.login'))

    user_id = session.get('user_id')
    if not user_id:
        flash("Не сте влезли в системата.", "danger")
        return redirect(url_for('auth.login'))

    director = Director.query.filter_by(user_id=user_id).first()
    if not director:
        flash("Директорският профил не е намерен.", "danger")
        return redirect(url_for('auth.login'))

    # # Търсене и филтриране
    # search = request.args.get('search', '').strip().lower()
    classroom_id = request.args.get('classroom_id', type=int)

    students_query = Student.query.join(User).join(Classroom).filter(Classroom.school_id == director.school_id)

    # if search:
    #     students_query = students_query.filter(
    #         or_(
    #             User.first_name.ilike(f"%{search}%"),
    #             User.middle_name.ilike(f"%{search}%"),
    #             User.last_name.ilike(f"%{search}%"),
    #             User.username.ilike(f"%{search}%")
    #         )
    #     )

    if classroom_id:
        students_query = students_query.filter(Student.classroom_id == classroom_id)

    students = students_query.all()

    classrooms = Classroom.query.filter_by(school_id=director.school_id).order_by(Classroom.grade, Classroom.letter).all()

    return render_template('director/students.html', students=students, classrooms=classrooms)

@director_bp.route('/director/student/<int:student_id>')
def view_details_student(student_id):
    if session.get('role') != 'director':
        flash("Нямате достъп до тази страница.", "danger")
        return redirect(url_for('auth.login'))

    user_id = session.get('user_id')
    if not user_id:
        flash("Не сте влезли в системата.", "danger")
        return redirect(url_for('auth.login'))
    
    student = Student.query.get_or_404(student_id)

    # Брой извинени и неизвинени отсъствия
    excused_count = Absence.query.filter_by(student_id=student.id, excused=True).count()
    unexcused_count = Absence.query.filter_by(student_id=student.id, excused=False).count()

    # Вземи избрания предмет за филтриране на оценки от GET параметър
    course_id = request.args.get('course_id', type=int)

    # Вземи предметите на класа на ученика за филтър
    courses = student.classroom.courses if student.classroom else []

    # Вземи оценки, евентуално филтрирани по предмет
    if course_id:
        grades = Grade.query.filter_by(student_id=student.id, course_id=course_id).all()
    else:
        grades = Grade.query.filter_by(student_id=student.id).all()

    class_teacher = None
    if student.classroom and student.classroom.class_teacher:
        class_teacher = student.classroom.class_teacher.user

    return render_template('director/view_student.html',
                           student=student,
                           excused_count=excused_count,
                           unexcused_count=unexcused_count,
                           courses=courses,
                           grades=grades,
                           selected_course=course_id,
                           class_teacher=class_teacher)


@director_bp.route('/director/courses', methods=['GET', 'POST'])
def director_courses():
    if 'user_id' not in session:
        flash("Моля, влезте в системата.", "danger")
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    print("User ID from session:", user_id)

    director = Director.query.filter_by(user_id=user_id).first()
    if not director:
        flash("Нямате достъп до тази страница.", "danger")
        return redirect(url_for('auth.login'))

    school = director.school
    if not school:
        flash("Няма намерено училище за този директор.", "danger")
        return redirect(url_for('auth.login'))
    try:
        if request.method == 'POST':
            selected_course_id = request.form.get('course_id')
            course = Course.query.get(selected_course_id)
            if course:
                if course not in school.courses:
                    school.courses.append(course)
                    db.session.commit()
                    flash('Предметът беше добавен към училището.', 'success')
                else:
                    flash('Предметът вече е добавен.', 'warning')
            return redirect(url_for('director.director_courses'))
    except:
        flash("Invalid ourse_id")

    all_courses = Course.query.all()
    school_courses = school.courses
    available_courses = [c for c in all_courses if c not in school_courses]

    return render_template(
        'director/courses.html',
        school_courses=school_courses,
        available_courses=available_courses
    )

@director_bp.route('/teachers/edit/<int:teacher_id>', methods=['GET', 'POST'])
def edit_teacher_by_director(teacher_id):
    if session.get('role') != 'director':
        return redirect(url_for('auth.login'))

    director = Director.query.filter_by(user_id=session['user_id']).first()
    teacher = Teacher.query.filter_by(id=teacher_id, school_id=director.school_id).first_or_404()
    user = User.query.get(teacher.user_id)

    form = AddTeacherForm(obj=user)

    # Зареждане на предметите в училището
    school_courses = director.school.courses  # През връзката от модела
    form.courses.choices = [(c.id, c.name) for c in school_courses]

    # Зареждане на класовете от същото училище
    classrooms = Classroom.query.filter_by(school_id=director.school_id).all()
    form.classroom.choices = [(0, '–– Не е класен ––')] + [
        (c.id, f"{c.grade}{c.letter}") for c in classrooms
    ]

    # Попълване на данни при GET
    if request.method == 'GET':
        form.courses.data = [c.id for c in teacher.courses]
        form.classroom.data = teacher.classroom_id if teacher.classroom_id else 0

    if form.validate_on_submit():
        # Обновяване на предметите
        teacher.courses.clear()
        for course_id in form.courses.data:
            course = Course.query.get(course_id)
            if course:
                teacher.courses.append(course)

        selected_classroom_id = form.classroom.data

        # Ако има избран клас за класен ръководител
        if selected_classroom_id and selected_classroom_id != 0:
            classroom = Classroom.query.get(selected_classroom_id)

            if classroom and classroom.school_id == director.school_id:
                # Премахваме предишен класен от този клас, ако има
                if classroom.teacher_id and classroom.teacher_id != teacher.id:
                    old_teacher = Teacher.query.get(classroom.teacher_id)
                    if old_teacher:
                        old_teacher.classroom_id = None

                # Премахваме текущия учител като класен от предишен клас
                if teacher.classroom_id and teacher.classroom_id != classroom.id:
                    old_class = Classroom.query.get(teacher.classroom_id)
                    if old_class:
                        old_class.teacher_id = None

                # Задаваме новия класен
                teacher.classroom_id = classroom.id
                classroom.teacher_id = teacher.id
        else:
            # Ако е избрано "Не е класен"
            if teacher.classroom_id:
                old_classroom = Classroom.query.get(teacher.classroom_id)
                if old_classroom:
                    old_classroom.teacher_id = None
                teacher.classroom_id = None

        db.session.commit()
        flash("Данните на преподавателя бяха обновени успешно.", "success")
        return redirect(url_for('director.director_teachers'))

    return render_template('director/edit_teacher.html', form=form, teacher=teacher, readonly=True)

@director_bp.route('/students/edit/<int:student_id>', methods=['GET', 'POST'])
def edit_student_by_director(student_id):
    if session.get('role') != 'director':
        return redirect(url_for('auth.login'))

    director = Director.query.filter_by(user_id=session['user_id']).first()
    student = Student.query.get_or_404(student_id)

    # Проверка дали ученикът е в неговото училище
    if student.classroom.school_id != director.school_id:
        flash("Нямате права да редактирате този ученик.", "danger")
        return redirect(url_for('director.director_students'))

    if request.method == 'POST':
        new_classroom_id = request.form.get('classroom_id')
        if new_classroom_id:
            student.classroom_id = new_classroom_id
        db.session.commit()
        flash("Ученикът беше успешно редактиран.", "success")
        return redirect(url_for('director.director_students'))

    classrooms = Classroom.query.filter_by(school_id=director.school_id).order_by(Classroom.grade, Classroom.letter).all()
    return render_template('director/edit_student.html', student=student, classrooms=classrooms, readonly=True)

@director_bp.route('/courses/remove/<int:course_id>', methods=['POST'])
def remove_course_from_school(course_id):
    if session.get('role') != 'director':
        return redirect(url_for('auth.login'))

    director = Director.query.filter_by(user_id=session['user_id']).first()
    if not director or not director.school:
        flash('Няма намерено училище за този директор.', 'danger')
        return redirect(url_for('auth.login'))

    school = director.school
    course = Course.query.get(course_id)
    if course and course in school.courses:
        school.courses.remove(course)
        db.session.commit()
        flash(f'Предметът "{course.name}" беше премахнат от училището.', 'success')
    else:
        flash('Предметът не е намерен или не е свързан с училището.', 'warning')

    return redirect(url_for('director.director_courses'))

@director_bp.route('/editschedule', methods=['GET', 'POST'])
def view_schedule():
    if session.get('role') != 'director':
        return redirect(url_for('auth.login'))

    director = Director.query.filter_by(user_id=session['user_id']).first()
    if not director:
        flash("Нямате достъп.", "danger")
        return redirect(url_for('auth.login'))

    classrooms = Classroom.query.filter_by(school_id=director.school_id).order_by(Classroom.grade, Classroom.letter)

    form = ScheduleFilterForm()
    form.classroom.query = classrooms

    schedule_entries = []
    if form.validate_on_submit():
        selected_classroom = form.classroom.data
        schedule_entries = Schedule.query.filter_by(classroom_id=selected_classroom.id).order_by(
            Schedule.day_of_week, Schedule.hour
        ).all()
    else:
        selected_classroom = None

    # Словар за ден от седмицата
    day_names = {
        1: "Понеделник",
        2: "Вторник",
        3: "Сряда",
        4: "Четвъртък",
        5: "Петък"
    }

    return render_template("director/view_schedule.html",
                           form=form,
                           selected_classroom=selected_classroom,
                           schedule=schedule_entries,
                           day_names=day_names)

@director_bp.route('/schedule/add', methods=['GET', 'POST'])
def add_schedule():
    if session.get('role') != 'director':
        return redirect(url_for('auth.login'))

    director = Director.query.filter_by(user_id=session['user_id']).first()
    if not director:
        flash("Нямате достъп.", "danger")
        return redirect(url_for('auth.login'))

    form = ScheduleForm()

    # Зареждаме само класове, предмети и учители от училището на директора
    form.classroom.choices = [(c.id, f"{c.grade}{c.letter}") for c in Classroom.query.filter_by(school_id=director.school_id).all()]
    form.course.choices = [(c.id, c.name) for c in Course.query.all()]
    form.teacher.choices = [(t.id, f"{t.user.first_name} {t.user.last_name}") for t in Teacher.query.filter_by(school_id=director.school_id).all()]

    if form.validate_on_submit():
        # Проверка за конфликт в разписанието:
        conflict = Schedule.query.filter_by(
            day_of_week=form.day_of_week.data,
            hour=form.hour.data,
            classroom_id=form.classroom.data
        ).first()

        if conflict:
            flash("Вече има зададен час за този клас по това време.", "danger")
            return render_template('director/add_schedule.html', form=form)

        conflict_teacher = Schedule.query.filter_by(
            day_of_week=form.day_of_week.data,
            hour=form.hour.data,
            teacher_id=form.teacher.data
        ).first()

        if conflict_teacher:
            flash("Този учител вече преподава по това време.", "danger")
            return render_template('director/add_schedule.html', form=form)

        new_entry = Schedule(
            day_of_week=form.day_of_week.data,
            hour=form.hour.data,
            classroom_id=form.classroom.data,
            course_id=form.course.data,
            teacher_id=form.teacher.data
        )
        db.session.add(new_entry)
        db.session.commit()
        flash("Часът беше добавен успешно!", "success")
        return redirect(url_for('director.view_schedule'))

    return render_template('director/add_schedule.html', form=form, director=director)

@director_bp.route('/auto_add_schedule', methods=['GET', 'POST'])
def auto_add_schedule_view():
    if session.get('role') != 'director':
        return redirect(url_for('auth.login'))

    director = Director.query.filter_by(user_id=session.get('user_id')).first()
    if not director:
        flash("Нямате достъп.", "danger")
        return redirect(url_for('auth.login'))

    form = AutoAddScheduleForm()

    # Ограничаваме формата до учителите и класовете в училището на директора
    form.classroom.query = Classroom.query.filter_by(school_id=director.school_id).all()
    form.teacher.query = Teacher.query.filter_by(school_id=director.school_id).all()
    form.course.query = Course.query.all()  # може да се филтрира по училище при нужда

    if form.validate_on_submit():
        added = auto_add_schedule(
            classroom_id=form.classroom.data.id,
            course_id=form.course.data.id,
            teacher_id=form.teacher.data.id,
            hours_per_week=form.hours_per_week.data,
            same_day_allowed=form.same_day_allowed.data,
            max_per_day=form.max_per_day.data or 6  # по подразбиране 6
        )
        flash(f'Успешно добавени {added} учебни часа.', 'success')
        return redirect(url_for('director.view_schedule'))

    return render_template('director/auto_add_schedule.html', form=form, director=director)

@director_bp.route('/edit_schedule/<int:schedule_id>', methods=['GET', 'POST'])
def edit_schedule(schedule_id):
    if session.get('role') != 'director':
        return redirect(url_for('auth.login'))

    director = Director.query.filter_by(user_id=session.get('user_id')).first()
    if not director:
        flash("Нямате достъп.", "danger")
        return redirect(url_for('auth.login'))

    schedule = Schedule.query.get_or_404(schedule_id)
    form = ScheduleForm(obj=schedule)

    # Попълваме dropdown-ите с правилните данни
    form.classroom.choices = [(c.id, f"{c.grade}{c.letter}") for c in Classroom.query.filter_by(school_id=director.school_id).all()]
    form.teacher.choices = [(t.id, f"{t.user.first_name} {t.user.last_name}") for t in Teacher.query.filter_by(school_id=director.school_id).all()]
    form.course.choices = [(c.id, c.name) for c in Course.query.all()]

    if form.validate_on_submit():
        schedule.day_of_week = form.day_of_week.data
        schedule.hour = form.hour.data
        schedule.classroom_id = form.classroom.data
        schedule.course_id = form.course.data
        schedule.teacher_id = form.teacher.data
        db.session.commit()
        flash("Часът беше успешно редактиран.", "success")
        return redirect(url_for('director.view_schedule'))

    # Задаваме текущите стойности на избора, за да се виждат при GET
    form.classroom.data = schedule.classroom_id
    form.course.data = schedule.course_id
    form.teacher.data = schedule.teacher_id

    return render_template('director/edit_schedule.html', form=form, schedule=schedule, director=director)

@director_bp.route('/delete_schedule/<int:schedule_id>', methods=['GET'])
def delete_schedule(schedule_id):
    if session.get('role') != 'director':
        return redirect(url_for('auth.login'))

    director = Director.query.filter_by(user_id=session['user_id']).first()
    if not director:
        flash("Нямате достъп.", "danger")
        return redirect(url_for('auth.login'))

    schedule = Schedule.query.get_or_404(schedule_id)
    db.session.delete(schedule)
    db.session.commit()
    flash("Часът беше изтрит.", "success")
    return redirect(url_for('director.view_schedule'))

@director_bp.route('/parents')
def director_parents():
    if session.get('role') != 'director':
        return redirect(url_for('auth.login'))

    director = Director.query.filter_by(user_id=session['user_id']).first()
    if not director:
        flash("Нямате достъп.", "danger")
        return redirect(url_for('auth.login'))

    # Взимаме всички родители, които имат деца в училището на директора
    parents = (
        Parent.query
        .join(Parent.children)
        .join(Student.classroom)
        .filter(Classroom.school_id == director.school_id)
        .distinct()
        .all()
    )

    return render_template('director/parents.html', parents=parents)

@director_bp.route('/director/get_teachers_by_course/<int:course_id>')
def get_teachers_by_course(course_id):
    school_id = request.args.get('school_id', type=int)

    if not school_id:
        return jsonify([])

    # Филтриране по предмет И училище
    teachers = Teacher.query \
        .join(teacher_course) \
        .filter(teacher_course.c.course_id == course_id, Teacher.school_id == school_id) \
        .all()
    teachers_data = [{'id': t.id, 'name': f"{t.user.first_name} {t.user.last_name}"} for t in teachers]
    return jsonify(teachers_data)

@director_bp.route('/director/statistics')
def view_statistics():
    if session.get('role') != 'director':
        return redirect(url_for('auth.login'))

    director = Director.query.filter_by(user_id=session['user_id']).first()
    if not director:
        flash("Нямате достъп.", "danger")
        return redirect(url_for('auth.login'))

    # Групиране на оценки по предмет
    grades_by_course = db.session.query(
        Course.name,
        db.func.avg(Grade.value)
    ).join(Grade).join(Student).join(Classroom).filter(
        Classroom.school_id == director.school_id
    ).group_by(Course.name).all()

    # Групиране на оценки по учител
    grades_by_teacher = db.session.query(
        User.first_name,
        User.last_name,
        db.func.avg(Grade.value)
    ).join(Teacher, Teacher.user_id == User.id).join(Grade).join(Student).join(Classroom).filter(
        Classroom.school_id == director.school_id
    ).group_by(User.id).all()

    # По класове
    grades_by_class = db.session.query(
        (cast(Classroom.grade, String) + literal(' ') + Classroom.letter).label('class_name'),
        db.func.avg(Grade.value)
    ).join(Student, Student.classroom_id == Classroom.id)\
    .join(Grade, Grade.student_id == Student.id)\
    .filter(Classroom.school_id == director.school_id)\
    .group_by('class_name')\
    .all()


    # Обобщено: средна оценка за училището
    avg_grade = db.session.query(db.func.avg(Grade.value)).join(Student).join(Classroom).filter(
        Classroom.school_id == director.school_id
    ).scalar()

    return render_template('director/statistics.html' ,grades_by_course=grades_by_course,
                           grades_by_teacher=grades_by_teacher, avg_grade=avg_grade,grades_by_class=grades_by_class)

@director_bp.route('/director/profile', methods=['GET', 'POST'])
def manage_profile():
    user_id = session.get('user_id')
    if not user_id:
        flash("Моля, влезте в профила си.", "warning")
        return redirect(url_for('auth.login'))

    director = Director.query.filter_by(user_id=user_id).first()
    if not director:
        flash("Нямате достъп до тази страница.", "danger")
        return redirect(url_for('auth.login'))

    user = director.user
    form = TeacherAndDirectorProfileForm(obj=user)

    if form.validate_on_submit():
        if form.email.data != user.email:
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user:
                flash('Имейлът вече е зает от друг потребител.', 'danger')
                return redirect(url_for('director.manage_profile'))

        if form.password.data:
            user.password = bcrypt.generate_password_hash(form.password.data)

        user.first_name = form.first_name.data
        user.middle_name = form.middle_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data
        user.phone_number = form.phone_number.data

        db.session.commit()
        flash('Профилът беше обновен.', 'success')
        return redirect(url_for('director.manage_profile'))

    return render_template('director/profile.html', user=user, director=director, form=form)
