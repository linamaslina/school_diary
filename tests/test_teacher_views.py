import pytest
from flask import url_for
from school_diary.models import User, Teacher, Student, Classroom, Grade, Absence, Schedule, Course, School
from school_diary.extensions import db, bcrypt
from datetime import datetime
import uuid

@pytest.fixture
def teacher_user(app, client):
    school = School(name='Тестово училище', city='София', address="ул.Орехова")
    db.session.add(school)
    db.session.commit()

    user = User(
        username='teacher1',
        password=bcrypt.generate_password_hash('password').decode('utf-8'),
        first_name='Иван',
        middle_name='Петров',
        last_name='Иванов',
        email='teacher1@example.com',
        phone_number='0888123456',
        role='teacher'
    )
    db.session.add(user)
    db.session.commit()

    teacher = Teacher(user_id=user.id, school_id=school.id)
    db.session.add(teacher)
    db.session.commit()

    return user, teacher


@pytest.fixture
def login_teacher(client, teacher_user):
    user, _ = teacher_user
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['role'] = 'teacher'
    yield
    with client.session_transaction() as sess:
        sess.clear()

def create_classroom_and_student(teacher, student_index=1):
    classroom = Classroom(grade=1, letter='A', school_id=teacher.school_id)
    db.session.add(classroom)
    db.session.commit()

    unique_email = f"student_{uuid.uuid4()}@test.bg"
    student_user = User(
        username=f'student{student_index}',
        password=bcrypt.generate_password_hash('pass').decode('utf-8'),
        first_name=f'Студент{student_index}',
        middle_name='М',
        email=unique_email,
        last_name='Тест',
        role='student'
    )
    db.session.add(student_user)
    db.session.commit()

    student = Student(user_id=student_user.id, classroom_id=classroom.id)
    db.session.add(student)
    db.session.commit()

    return classroom, student

def test_teacher_dashboard_access(client, login_teacher):
    response = client.get('/teacher')
    assert response.status_code == 200
    assert ('Табло на преподавател'.encode('utf-8') in response.data) or (b'teacher_dashboard.html' in response.data)

def test_manage_profile_get(client, login_teacher, teacher_user):
    user, _ = teacher_user
    response = client.get('/teacher/profile')
    assert response.status_code == 200
    assert user.first_name.encode('utf-8') in response.data

def test_manage_profile_post_update(client, login_teacher, teacher_user):
    user, _ = teacher_user
    new_email = 'newemail@example.com'

    response = client.post('/teacher/profile', data={
        'first_name': user.first_name,
        'middle_name': user.middle_name,
        'last_name': user.last_name,
        'email': new_email,
        'phone_number': user.phone_number,
        'password': ''
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Профилът беше обновен'.encode('utf-8') in response.data

    user_in_db = User.query.get(user.id)
    assert user_in_db.email == new_email

def test_manage_students(client, login_teacher, teacher_user):
    _, teacher = teacher_user
    classroom, _ = create_classroom_and_student(teacher, 1)
    teacher.classrooms.append(classroom)
    db.session.commit()

    response = client.get('/teacher/students')
    assert response.status_code == 200
    assert 'Ученици'.encode('utf-8') in response.data

def test_manage_grades_post(client, login_teacher, teacher_user):
    _, teacher = teacher_user
    classroom, student = create_classroom_and_student(teacher, 2)

    course = Course(name='Математика')
    course.schools.append(teacher.school)
    
    db.session.add(course)
    db.session.commit()

    response = client.post('/teacher/grades', data={
        'student_id': student.id,
        'date': '2025-06-16',
        'course_id': course.id,
        'value': '5.50'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Оценката беше записана успешно'.encode('utf-8') in response.data

    grade = Grade.query.filter_by(student_id=student.id, teacher_id=teacher.id, course_id=course.id).first()
    assert grade is not None
    assert grade.value == 5.5

def test_manage_absences_post(client, login_teacher, teacher_user):
    _, teacher = teacher_user
    classroom, student = create_classroom_and_student(teacher, 3)

    course = Course(name='Български')
    course.schools.append(teacher.school)
    db.session.add(course)
    db.session.commit()

    response = client.post('/teacher/absences', data={
        'student_id': student.id,
        'date': '2025-06-16',
        'course_id': course.id,
        'reason': 'Болест',
        'excused': 'y'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Отсъствието беше записано успешно'.encode('utf-8') in response.data

    absence = Absence.query.filter_by(student_id=student.id, teacher_id=teacher.id, course_id=course.id).first()
    assert absence is not None
    assert absence.reason == 'Болест'
    assert absence.excused is True

def test_get_students_api(client, login_teacher, teacher_user):
    _, teacher = teacher_user
    classroom, student = create_classroom_and_student(teacher, 4)

    response = client.get(f'/teacher/get_students?classroom_id={classroom.id}')
    json_data = response.get_json()
    assert response.status_code == 200
    assert 'students' in json_data
    assert any(s['first_name'] == student.user.first_name for s in json_data['students'])

def test_get_courses_for_student_date(client, login_teacher, teacher_user):
    _, teacher = teacher_user
    classroom, student = create_classroom_and_student(teacher, 5)

    course = Course(name='Физика')
    course.schools.append(teacher.school)
    db.session.add(course)
    db.session.commit()

    schedule = Schedule(classroom_id=classroom.id, course_id=course.id, day_of_week=1, hour=1, teacher_id=teacher.id)
    db.session.add(schedule)
    db.session.commit()

    response = client.get(f'/teacher/get_courses_for_student_date?student_id={student.id}&date=2025-06-16')
    json_data = response.get_json()
    assert response.status_code == 200
    assert 'courses' in json_data
    assert len(json_data['courses']) == 1
    assert json_data['courses'][0]['name'] == 'Физика'

def test_student_detail(client, login_teacher, teacher_user):
    user, teacher = teacher_user  # използваме учителя

    # Създаваме ученик в същото училище и клас като учителя
    classroom, student = create_classroom_and_student(teacher, 6)
    teacher.classrooms.append(classroom)
    db.session.commit()

    response = client.get(f'student/{student.id}')
    assert response.status_code == 200
    assert 'Подробности за ученик'.encode('utf-8') in response.data


def test_excuse_absence_post(client, login_teacher, teacher_user):
    _, teacher = teacher_user
    unique_email = f"student_{uuid.uuid4()}@test.bg"
    student_user = User(username='student6', password=bcrypt.generate_password_hash('pass').decode('utf-8'),
                        first_name='Студент6', middle_name='М', email=unique_email, last_name='Тест', role='student')
    db.session.add(student_user)
    db.session.commit()
    student = Student(user_id=student_user.id)
    db.session.add(student)
    db.session.commit()

    course = Course(name='История')
    course.schools.append(teacher.school)
    db.session.add(course)
    db.session.commit()

    absence = Absence(
        student_id=student.id,
        teacher_id=teacher.id,
        course_id=course.id,
        date=datetime.today(),
        reason='Болест',
        excused=False
    )
    db.session.add(absence)
    db.session.commit()

    response = client.post(f'absences/{absence.id}/justify', follow_redirects=True)
    assert response.status_code == 200
    absence_in_db = Absence.query.get(absence.id)
    assert absence_in_db.excused is True

def test_schedule_get(client, login_teacher, teacher_user):
    response = client.get('/teacher/schedule')
    assert response.status_code == 200
    assert 'програма'.encode('utf-8') in response.data
