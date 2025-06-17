import pytest
from flask import url_for
from school_diary.models import Director, User, Teacher, Student, Classroom, Course, Parent, Schedule
from school_diary.extensions import db, bcrypt
import uuid
from uuid import uuid4

def test_login_get(client):
    response = client.get('/')
    assert response.status_code == 200
    assert 'Вход'.encode('utf-8') in response.data or b'username' in response.data

def test_login_invalid_credentials(client, app):
    response = client.post('/', data={
        'username': 'nonexistent',
        'password': 'wrongpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Вход'.encode('utf-8') in response.data


def test_login_success(client, app):
    from school_diary.models import User
    from school_diary.extensions import db, bcrypt

    with app.app_context():
        user = User(
            username='testuser',
            email='testuser@test.bg',
            password=bcrypt.generate_password_hash('pass123').decode('utf-8'),
            first_name='Test',
            middle_name='M',
            last_name='User',
            role='student'
        )
        db.session.add(user)
        db.session.commit()

    response = client.post('/', data={
        'username': 'testuser',
        'password': 'pass123'
    }, follow_redirects=False)

    assert response.status_code == 302
    assert '/dashboard' in response.headers['Location']

def test_register_get(client):
    response = client.get('/register')
    assert response.status_code == 200
    assert 'Регистрация'.encode('utf-8') in response.data or b'email' in response.data

def test_register_invalid_submission(client):
    response = client.post('/register', data={
        'email': 'test@invalid.bg'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'Регистрация'.encode('utf-8') in response.data
    assert 'Грешка'.encode('utf-8') in response.data or 'невалиден'.encode('utf-8') in response.data

def test_register_student_success(client, app):
    with app.app_context():
        from school_diary.forms import RegisterForm
        from school_diary.utils import generate_unique_username

        data = {
            'first_name': 'Ivan',
            'middle_name': 'Petrov',
            'last_name': 'Ivanov',
            'email': f'ivan_{uuid.uuid4().hex[:6]}@test.bg',
            'phone_number': '0888888888',
            'password': 'strongpass',
            'confirm_password': 'strongpass',
            'role': 'student'
        }

        response = client.post('/register', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert 'Вашето потребителско име е:'.encode('utf-8') in response.data

def test_logout_clears_session(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 123
        sess['role'] = 'student'

    response = client.get('/logout', follow_redirects=False)
    assert response.status_code == 302
    assert '/' in response.headers['Location']

    with client.session_transaction() as sess:
        assert 'user_id' not in sess
        assert 'role' not in sess
