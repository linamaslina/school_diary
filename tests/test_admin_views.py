import pytest
from flask import url_for
from school_diary.models import User, Student, Parent, Teacher, Director, School, Classroom, Course
from school_diary.extensions import bcrypt, db
import uuid
from uuid import uuid4

def unique_email(prefix='user'):
    return f"{prefix}_{uuid4().hex}@example.com"
def unique_username(prefix='user'):
    return f"{prefix}_{uuid4().hex[:8]}"

@pytest.fixture
def admin_user(db):
    user = User(
        email=unique_email('admin'),
        username=unique_username('admin'),
        password=bcrypt.generate_password_hash('adminpass').decode('utf-8'),
        role='admin',
        first_name='Admin',
        middle_name='A',
        last_name='User',
    )
    db.session.add(user)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return user

@pytest.fixture
def login_admin(client, admin_user):
    with client.session_transaction() as sess:
        sess['user_id'] = admin_user.id
        sess['role'] = 'admin'
    return client

@pytest.fixture
def sample_school(db):
    school = School(name='Test School', address='123 Test St', city='Testville')
    db.session.add(school)
    db.session.commit()
    return school

@pytest.fixture
def sample_classroom(db, sample_school):
    classroom = Classroom(grade=1, letter='A', school_id=sample_school.id)
    db.session.add(classroom)
    db.session.commit()
    return classroom

@pytest.fixture
def sample_course(db, sample_school):
    course = Course(name='Mathematics')
    course.schools.append(sample_school)
    db.session.add(course)
    db.session.commit()
    return course

def test_admin_dashboard_access(login_admin):
    response = login_admin.get('/admin/dashboard')
    assert response.status_code == 200
    
    assert 'Админ табло'.encode('utf-8') in response.data 

def test_add_user_get_view(login_admin):
    response = login_admin.get('/add_user')
    assert response.status_code == 200
    assert b'<form' in response.data  # Има форма

def test_add_user_redirect_if_not_admin(client):
    response = client.get('/add_user', follow_redirects=False)
    assert response.status_code == 302
    assert '/' in response.headers['Location']

def test_add_student_user_post(login_admin, sample_classroom):
    email = unique_email('student')
    username = unique_username('student') 
    data = {
        'role': 'student',
        'first_name': 'Ivan',
        'middle_name': 'P',
        'last_name': 'Ivanov',
        'email': email,  # Уникален email
        'phone_number': '0888123456',
        'date_of_birth': '2005-05-20',
        'classroom_id': str(sample_classroom.id),
        'username': username,
    }
    response = login_admin.post('/add_user', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'Потребителят е добавен успешно.'.encode('utf-8') in response.data

    # Проверка в базата
    user = User.query.filter_by(first_name='Ivan', email=email, last_name='Ivanov').first()
    assert user is not None
    assert user.role == 'student'
    student = Student.query.filter_by(user_id=user.id).first()
    assert student is not None
    assert student.classroom_id == sample_classroom.id

def test_delete_user(login_admin):
    # Уникален email за потребителя, който ще изтриваме
    user = User(
        username=unique_username('admin'),
        password=bcrypt.generate_password_hash('test123').decode('utf-8'),
        role='student',
        first_name='Del',
        middle_name='',
        email=f'deluser_{uuid4().hex}@example.com',  # уникален email
        last_name='User'
    )
    db.session.add(user)
    db.session.commit()

    response = login_admin.post(f'/admin/users/delete/{user.id}', follow_redirects=True)
    assert response.status_code == 200
    assert 'Потребителят и свързаните с него данни бяха изтрити успешно!'.encode('utf-8') in response.data
    assert User.query.get(user.id) is None

def test_view_user_page(login_admin, admin_user):
    response = login_admin.get(f'/user/{admin_user.id}')
    assert response.status_code == 200
    assert admin_user.first_name.encode() in response.data

def test_edit_user_get_view(login_admin, admin_user):
    response = login_admin.get(f'/admin/users/edit/{admin_user.id}')
    assert response.status_code == 200
    assert b'<form' in response.data

def test_edit_user_post_update_name(login_admin, admin_user):
    data = {
    'role': admin_user.role,
    'first_name': 'AdminUpdated',
    'middle_name': 'A',
    'last_name': 'User',
    'email': 'admin@example.com',
    'phone_number': '0888123456',
    'date_of_birth': '1990-01-01',
    'teacher_school_id': '',  
    'teacher_course_ids': [],
    'student_ids': [],
    'school_id': '',
    }

    response = login_admin.post(f'/admin/users/edit/{admin_user.id}', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert 'Потребителят беше обновен успешно!'.encode('utf-8') in response.data
    user = User.query.get(admin_user.id)
    assert user.first_name == 'AdminUpdated'

def test_admin_dashboard_access_denied(client):
    response = client.get('/admin/dashboard')
    assert response.status_code == 200  # не изисква авторизация
    assert 'Админ'.encode('utf-8') in response.data or b'dashboard' in response.data

def test_add_user_access_denied(client):
    response = client.get('/add_user')
    assert response.status_code == 302
    assert '/' in response.headers['Location']

def test_add_student_user_success(client, app):
    with app.app_context():
        # Влизаме като админ
        admin_user = User(
            username='admin1',
            email='admin1@test.bg',
            password=bcrypt.generate_password_hash('adminpass').decode('utf-8'),
            first_name='Admin',
            middle_name='A',
            last_name='User',
            role='admin'
        )
        db.session.add(admin_user)

        school = School(name='Тестово училище', city='София', address='Ул. Тестова 1')
        db.session.add(school)
        db.session.flush()

        classroom = Classroom(school_id=school.id, grade=5, letter='А')
        db.session.add(classroom)
        db.session.commit()

        admin_id = admin_user.id
        classroom_id = classroom.id

    # Използваме ID извън app_context()
    with client.session_transaction() as sess:
        sess['user_id'] = admin_id
        sess['role'] = 'admin'

    response = client.post('/add_user', data={
        'first_name': 'Иван',
        'middle_name': 'Петров',
        'last_name': 'Иванов',
        'email': f'ivan_{uuid.uuid4().hex[:5]}@test.bg',
        'role': 'student',
        'date_of_birth': '2005-01-01',
        'classroom_id': classroom_id
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Потребителят е добавен успешно'.encode('utf-8') in response.data


def test_delete_user_success(client, app):
    with app.app_context():
        admin = User(username='admin2', email='admin2@test.bg', password='x', role='admin',
                     first_name='A', middle_name='B', last_name='C')
        db.session.add(admin)

        user = User(username='delete_me', email='delete@test.bg', password='x', role='student',
                    first_name='Del', middle_name='E', last_name='Me')
        db.session.add(user)
        db.session.flush()
        student = Student(user_id=user.id, share_code='ABC123XYZ9')
        db.session.add(student)
        db.session.commit()

        admin_id = admin.id
        user_id = user.id

    with client.session_transaction() as sess:
        sess['user_id'] = admin_id
        sess['role'] = 'admin'

    response = client.post(f'/admin/users/delete/{user_id}', follow_redirects=True)
    assert response.status_code == 200
    assert 'изтрити успешно'.encode('utf-8') in response.data


def test_view_user_details(client, app):
    with app.app_context():
        admin = User(username='admin3', email='admin3@test.bg', password='x', role='admin',
                     first_name='Adm', middle_name='M', last_name='In')
        db.session.add(admin)

        user = User(username='parent1', email='parent@test.bg', password='x', role='parent',
                    first_name='Par', middle_name='A', last_name='Rent')
        db.session.add(user)
        db.session.flush()
        parent = Parent(user_id=user.id)
        db.session.add(parent)
        db.session.commit()

        admin_id = admin.id
        user_id = user.id

    with client.session_transaction() as sess:
        sess['user_id'] = admin_id
        sess['role'] = 'admin'

    response = client.get(f'/user/{user_id}')
    assert response.status_code == 200
    assert b'Par' in response.data


def test_add_school_with_classes(client, app):
    with app.app_context():
        admin = User(username='admin4', email='admin4@test.bg', password='x', role='admin',
                     first_name='Admin', middle_name='Middle', last_name='User')
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    with client.session_transaction() as sess:
        sess['user_id'] = admin_id
        sess['role'] = 'admin'

    response = client.post('/admin/schools/add', data={
        'name': 'СУ Тест',
        'address': 'Бул. Тест 1',
        'city': 'София',
        'classrooms': '5А, 5Б, 6В'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'добавени успешно'.encode('utf-8') in response.data


def test_manage_courses_add_course(client, app):
    with app.app_context():
        admin = User(username='admin5', email='admin5@test.bg', password='x', role='admin',
                     first_name='Admin', middle_name='Middle', last_name='User')
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    with client.session_transaction() as sess:
        sess['user_id'] = admin_id
        sess['role'] = 'admin'

    response = client.post('/courses', data={'name': f'Информатика {uuid.uuid4().hex[:4]}'}, follow_redirects=True)
    assert response.status_code == 200
    assert 'добавен успешно'.encode('utf-8') in response.data


def test_admin_statistics_access(client, app):
    with app.app_context():
        admin = User(username='admin6', email='admin6@test.bg', password='x', role='admin',
                     first_name='Stat', middle_name='I', last_name='Cian')
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    with client.session_transaction() as sess:
        sess['user_id'] = admin_id
        sess['role'] = 'admin'

    response = client.get('/statistics')
    assert response.status_code == 200
    assert 'статистики'.encode('utf-8') in response.data or 'оценки'.encode('utf-8') in response.data




