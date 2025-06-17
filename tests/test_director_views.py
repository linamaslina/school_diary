import pytest
from flask import url_for
from school_diary.models import Director, User, Teacher, Student, Classroom, Course, Parent, Schedule, School
from school_diary.extensions import db, bcrypt
import uuid
from uuid import uuid4

@pytest.fixture
def director_user(client, app):
    with app.app_context():
        school = School(name="Test School", city="Test City",  address="123 Test Street")
        db.session.add(school)
        db.session.flush()  # за да получим school.id

        unique_username = f"director_{uuid4().hex[:8]}"
        unique_email = f"director_{uuid.uuid4()}@test.bg"
        user = User(
            username=unique_username,
            email=unique_email,
            role='director',
            first_name='Dir',
            middle_name='Pir',
            last_name='Ector',
            password=bcrypt.generate_password_hash('director').decode('utf-8')
        )
        db.session.add(user)
        db.session.flush()

        director = Director(user_id=user.id, school_id=school.id)
        db.session.add(director)
        db.session.commit()

        db.session.refresh(user)
        db.session.refresh(director)

    return user


def test_access_without_login_redirects(client):
    response = client.get('/director')
    assert response.status_code == 302
    assert '/' in response.headers['Location']


@pytest.mark.parametrize("url2", [
    '/courses/remove/1'
])

def test_access_without_login_redirects2(client, url2):
    response = client.post(url2)
    assert response.status_code == 302
    assert '/' in response.headers['Location']


@pytest.mark.parametrize("url", [
    '/director',
    '/teachers',
    '/director/students',
    '/director/courses',
])
def test_access_with_wrong_role_redirects(client, url):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'student'  # не е директор
    response = client.get(url)
    assert response.status_code == 302
    assert '/' in response.headers['Location']


def login_as_director(client, user):
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['role'] = 'director'

def test_director_dashboard_requires_login(client):
    # Без логин пренасочва към login
    response = client.get('/director')
    assert response.status_code == 302
    assert '/' in response.headers['Location']

def test_director_dashboard_success(client, director_user):
    login_as_director(client, director_user)
    response = client.get('/director')
    assert response.status_code == 200
    assert 'Табло на директор'.encode('utf-8') in response.data  # примерно в html да има нещо с този текст

def test_director_teachers(client, director_user):
    login_as_director(client, director_user)
    response = client.get('/teachers')
    assert response.status_code == 200
    # Може да провериш дали шаблонът е зареден със списък на учители
    assert b'teachers' in response.data or b'<table' in response.data

def test_director_students_search(client, director_user):
    login_as_director(client, director_user)
    response = client.get('/director/students?search=test')
    assert response.status_code == 200
    assert b'students' in response.data

def test_view_details_student_no_access(client):
    # Без логин пренасочва
    response = client.get('/director/student/1')
    assert response.status_code == 302
    assert '/' in response.headers['Location']

def test_view_details_student_success(client, director_user, app):
    login_as_director(client, director_user)
    with app.app_context():
        classroom = Classroom(grade=10, letter='A', school_id=1)
        db.session.add(classroom)

        student_user = User(
            username=f'student_{uuid4().hex[:8]}',
            first_name='Stud',
            middle_name='Gud',
            last_name='Ent',
            role='student',
            email=f'student_{uuid4().hex}@example.com',
            password=bcrypt.generate_password_hash('student').decode('utf-8')
        )
        db.session.add(student_user)
        db.session.flush()  # за да получим user.id

        student = Student(user_id=student_user.id, classroom_id=classroom.id)
        db.session.add(student)

        db.session.commit()

        student_id = student.id  # запазваме id-то, за да го ползваме извън контекста

    response = client.get(f'/director/student/{student_id}')
    assert response.status_code == 200
    assert b'student' in response.data or bytes(student_user.first_name, 'utf-8') in response.data

        

    response = client.get(f'/director/student/{student.id}')
    assert response.status_code == 200
    assert b'student' in response.data or bytes(student_user.first_name, 'utf-8') in response.data

def test_director_courses_get(client, director_user):
    login_as_director(client, director_user)
    response = client.get('/director/courses')
    assert response.status_code == 200
    assert 'Добави предмет'.encode('utf-8') in response.data or b'courses' in response.data

def test_edit_teacher_by_director(client, director_user, app):
    login_as_director(client, director_user)
    with app.app_context():
        # Създаване на учител
        teacher_user = User(
            username=f'teacher_{uuid4().hex[:8]}',
            first_name='Tina',
            middle_name='Testova',
            last_name='Teach',
            role='teacher',
            email=f'teacher_{uuid4().hex}@example.com',
            password=bcrypt.generate_password_hash('test').decode('utf-8')
        )
        db.session.add(teacher_user)
        db.session.flush()

        teacher = Teacher(user_id=teacher_user.id, school_id=Director.query.first().school_id)
        db.session.add(teacher)
        db.session.commit()

        # Достъп до страницата
        response = client.get(f'/teachers/edit/{teacher.id}')
        assert response.status_code == 200
        assert b'Tina' in response.data

def test_view_schedule_requires_login(client):
    response = client.get('/editschedule')
    assert response.status_code == 302
    assert '/' in response.headers['Location']

def test_view_schedule_with_director_access(client, director_user):
    login_as_director(client, director_user)
    response = client.get('/editschedule')
    assert response.status_code == 200
    assert 'ден от седмицата'.encode('utf-8') in response.data or 'клас'.encode('utf-8') in response.data


def test_director_parents_requires_login(client):
    response = client.get('/parents')
    assert response.status_code == 302
    assert '/' in response.headers['Location']

def test_director_parents_success(client, director_user, app):
    login_as_director(client, director_user)
    with app.app_context():
        school = Director.query.filter_by(user_id=director_user.id).first().school
        classroom = Classroom(grade=5, letter='B', school_id=school.id)
        db.session.add(classroom)
        db.session.flush()

        student_user = User(username=f'stu_{uuid4().hex[:6]}', first_name='A', middle_name='B', last_name='C',
                            role='student', email=f'stu_{uuid4().hex}@mail.bg',
                            password=bcrypt.generate_password_hash('123').decode('utf-8'))
        db.session.add(student_user)
        db.session.flush()
        student = Student(user_id=student_user.id, classroom_id=classroom.id)
        db.session.add(student)

        parent_user = User(username=f'par_{uuid4().hex[:6]}', first_name='P', middle_name='M', last_name='L',
                           role='parent', email=f'par_{uuid4().hex}@mail.bg',
                           password=bcrypt.generate_password_hash('123').decode('utf-8'))
        db.session.add(parent_user)
        db.session.flush()
        parent = Parent(user_id=parent_user.id)
        db.session.add(parent)
        db.session.commit()

        parent.children.append(student)
        db.session.commit()

    response = client.get('/parents')
    assert response.status_code == 200
    assert b'P' in response.data or 'родител'.encode('utf-8') in response.data

def test_director_statistics_access(client, director_user):
    login_as_director(client, director_user)
    response = client.get('/director/statistics')
    assert response.status_code == 200
    assert 'Средна оценка'.encode('utf-8') in response.data or 'Оценки по предмети'.encode('utf-8') in response.data


def test_director_courses_post_add_new_course(client, director_user, app):
    login_as_director(client, director_user)
    with app.app_context():
        new_course = Course(name='New Test Course')
        db.session.add(new_course)
        db.session.commit()
        course_id = new_course.id

    response = client.post('/director/courses', data={'course_id': course_id}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Предметът беше добавен към училището.'.encode('utf-8') in response.data

    # Проверка дали наистина е добавен
    with app.app_context():
        director = Director.query.filter_by(user_id=director_user.id).first()
        assert any(c.id == course_id for c in director.school.courses)


def test_director_courses_post_add_existing_course(client, director_user, app):
    login_as_director(client, director_user)
    with app.app_context():
        director = Director.query.filter_by(user_id=director_user.id).first()
        
        # Увери се, че има курс
        course = Course.query.first()
        if not course:
            course = Course(name='Existing Course')
            db.session.add(course)
            db.session.commit()
        
        if course not in director.school.courses:
            director.school.courses.append(course)
            db.session.commit()
        course_id = course.id

    response = client.post('/director/courses', data={'course_id': course_id}, follow_redirects=True)
    assert response.status_code == 200
    assert 'Предметът вече е добавен.'.encode('utf-8') in response.data


def test_remove_course_from_school_success(client, director_user, app):
    login_as_director(client, director_user)
    with app.app_context():
        director = Director.query.filter_by(user_id=director_user.id).first()

        course = Course.query.first()
        if not course:
            course = Course(name='Removable Course')
            db.session.add(course)
            db.session.commit()

        if course not in director.school.courses:
            director.school.courses.append(course)
            db.session.commit()

        course_id = course.id

    response = client.post(f'/courses/remove/{course_id}', follow_redirects=True)
    assert response.status_code == 200
    assert 'беше премахнат от училището'.encode('utf-8') in response.data


def test_remove_course_from_school_no_access(client):
    # Без логин или с не-директорска роля
    response = client.post('/courses/remove/1')
    assert response.status_code == 302  # пренасочва към login

def test_view_details_student_not_found(client, director_user):
    login_as_director(client, director_user)
    response = client.get('/director/student/999999')  # невалиден ID
    assert response.status_code == 404

def test_auto_add_schedule_view_access(client, director_user):
    login_as_director(client, director_user)
    response = client.get('/auto_add_schedule')
    assert response.status_code == 200
    assert 'Автоматично добавяне'.encode('utf-8') in response.data or 'часа седмично'.encode('utf-8') in response.data

def test_edit_schedule_view_get(client, director_user, app):
    login_as_director(client, director_user)
    with app.app_context():
        director = Director.query.filter_by(user_id=director_user.id).first()
        school = director.school

        classroom = Classroom(grade=7, letter='G', school_id=school.id)
        db.session.add(classroom)
        db.session.flush()

        course = Course(name=f'Math_{uuid4().hex[:5]}')
        db.session.add(course)
        db.session.flush()

        teacher_user = User(
            username=f'teacher_{uuid4().hex[:5]}',
            email=f't_{uuid4().hex}@mail.bg',
            password=bcrypt.generate_password_hash('123').decode('utf-8'),
            first_name='Teach', middle_name='E', last_name='R',
            role='teacher'
        )
        db.session.add(teacher_user)
        db.session.flush()
        teacher = Teacher(user_id=teacher_user.id, school_id=school.id)
        db.session.add(teacher)
        db.session.commit()

        schedule = Schedule(day_of_week=1, hour=1, classroom_id=classroom.id,
                            course_id=course.id, teacher_id=teacher.id)
        db.session.add(schedule)
        db.session.commit()

        response = client.get(f'/edit_schedule/{schedule.id}')
        assert response.status_code == 200
        assert 'Редакция на час'.encode('utf-8') in response.data or 'ден от седмицата'.encode('utf-8') in response.data

def test_delete_schedule_success(client, director_user, app):
    login_as_director(client, director_user)
    with app.app_context():
        director = Director.query.filter_by(user_id=director_user.id).first()
        school = director.school

        classroom = Classroom(grade=6, letter='D', school_id=school.id)
        db.session.add(classroom)
        db.session.flush()

        course = Course(name=f'Science_{uuid4().hex[:5]}')
        db.session.add(course)
        db.session.flush()

        teacher_user = User(
            username=f'teach_{uuid4().hex[:5]}',
            email=f'teach_{uuid4().hex}@mail.bg',
            password=bcrypt.generate_password_hash('pass').decode('utf-8'),
            first_name='T', middle_name='E', last_name='R',
            role='teacher'
        )
        db.session.add(teacher_user)
        db.session.flush()
        teacher = Teacher(user_id=teacher_user.id, school_id=school.id)
        db.session.add(teacher)
        db.session.commit()

        schedule = Schedule(day_of_week=2, hour=3, classroom_id=classroom.id,
                            course_id=course.id, teacher_id=teacher.id)
        db.session.add(schedule)
        db.session.commit()

        schedule_id = schedule.id

    response = client.get(f'/delete_schedule/{schedule_id}', follow_redirects=True)
    assert response.status_code == 200
    assert 'изтрит'.encode('utf-8') in response.data

def test_manage_profile_view(client, director_user):
    login_as_director(client, director_user)
    response = client.get('/director/profile')
    assert response.status_code == 200
    assert 'Профил'.encode('utf-8') in response.data or 'Име'.encode('utf-8') in response.data


