import pytest
from school_diary.models import Director, User, Teacher, Student, Classroom, Course, School
from school_diary.extensions import db, bcrypt
from flask import session
import uuid
from uuid import uuid4

@pytest.fixture
def student_user(db):
    unique_username=f"director_{uuid4().hex[:8]}"
    unique_email = f"director_{uuid.uuid4()}@test.bg"
    user = User(
        username=unique_username,
        email=unique_email,
        role='student',
        first_name='Stu',
        middle_name="Gud",
        last_name='Dent',
        password=bcrypt.generate_password_hash('student').decode('utf-8')
    )
    db.session.add(user)
    db.session.commit()

    school = School(name='Test School', address="Street", city="City")
    db.session.add(school)
    db.session.commit()

    class_ = Classroom(grade=5, letter='A', school_id=school.id)
    db.session.add(class_)
    db.session.commit()

    student = Student(user_id=user.id, classroom_id=class_.id)
    db.session.add(student)
    db.session.commit()

    return user


# Тестове за redirect при липса на логин
@pytest.mark.parametrize('url', [
    '/dashboard/student',
    '/grades',
    '/absences',
    '/schedule',
    '/profile'
])
def test_student_views_redirect_if_not_logged_in(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert '/' in response.headers['Location']

def login_as_student(client, db, student_user):
    with client.session_transaction() as sess:
        sess['user_id'] = student_user.id
        sess['role'] = 'student'

def test_student_dashboard_logged_in(client, db, student_user):
    login_as_student(client, db, student_user)
    response = client.get('/dashboard/student')
    assert response.status_code == 200
    assert 'Табло'.encode('utf-8') in response.data or b'classroom' in response.data 

def test_student_grades_logged_in(client, db, student_user):
    login_as_student(client, db, student_user)
    response = client.get('/grades')
    assert response.status_code == 200
    assert 'Моите оценки'.encode('utf-8') in response.data or b'grades' in response.data

def test_student_absences_logged_in(client, db, student_user):
    login_as_student(client, db, student_user)
    response = client.get('/absences')
    assert response.status_code == 200
    assert 'Моите отсъствия'.encode('utf-8') in response.data or b'date' in response.data

def test_student_schedule_logged_in(client, db, student_user):
    login_as_student(client, db, student_user)
    response = client.get('/schedule')
    assert response.status_code == 200
    assert 'Седмична програма'.encode('utf-8') in response.data or b'schedule_matrix' in response.data

def test_student_profile_logged_in(client, db, student_user):
    login_as_student(client, db, student_user)
    response = client.get('/profile')
    assert response.status_code == 200
    assert 'Профил'.encode('utf-8') in response.data or b'form' in response.data
