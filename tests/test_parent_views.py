import pytest
from flask import url_for
from school_diary.models import User, Parent, Student, School, Classroom
from school_diary.extensions import db, bcrypt

@pytest.fixture
def parent_user():
    user = User(
        username='parent_test',
        password=bcrypt.generate_password_hash('password').decode('utf-8'),
        first_name='Родител',
        middle_name='На дете',
        last_name='Тест',
        phone_number='08884835534',
        email='parent_test@test.bg',
        role='parent'
    )
    db.session.add(user)
    db.session.commit()

    parent = Parent(user_id=user.id)
    db.session.add(parent)
    db.session.commit()

    return user, parent

@pytest.fixture
def student_child():
    user = User(
        username='student_child',
        password=bcrypt.generate_password_hash('password').decode('utf-8'),
        first_name='Дете',
        middle_name="На родител",
        last_name='Тест',
        phone_number='07784835534',
        email='student_child@test.bg',
        role='student'
    )
    db.session.add(user)
    db.session.commit()

    student = Student(user_id=user.id)
    db.session.add(student)
    db.session.commit()

    return student

def login_as_parent(client, parent_user):
    user, _ = parent_user
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['role'] = 'parent'

def test_parent_dashboard(client, parent_user):
    login_as_parent(client, parent_user)
    response = client.get('/parent')
    assert response.status_code == 200
    assert 'Табло на родител'.encode('utf-8') in response.data or b'parent_dashboard' in response.data

# def test_view_children(client, parent_user, student_child):
#     user, parent = parent_user
    
#     school = School(name="Тестово училище", address="ул. Орехова", city="София")
#     db.session.add(school)
#     db.session.commit()

#     classroom = Classroom(school_id=school.id, grade=5, letter='А')
#     db.session.add(classroom)
#     db.session.commit()

#     student_child.classroom = classroom
#     db.session.commit()

#     parent.children.append(student_child)
#     db.session.add(parent)
#     db.session.commit()
#     db.session.expire_all()

#     login_as_parent(client, parent_user)
#     response = client.get('/parent/children')
#     assert response.status_code == 200
#     assert student_child.user.first_name.encode('utf-8') in response.data

def test_view_grades(client, parent_user, student_child):
    user, parent = parent_user
    parent.children.append(student_child)
    db.session.commit()

    login_as_parent(client, parent_user)
    response = client.get('/parent/grades')
    assert response.status_code == 200
    # Проверка за име на детето
    assert student_child.user.first_name.encode('utf-8') in response.data

def test_view_absences(client, parent_user, student_child):
    user, parent = parent_user
    parent.children.append(student_child)
    db.session.commit()

    login_as_parent(client, parent_user)
    response = client.get('/parent/absences')
    assert response.status_code == 200
    assert student_child.user.first_name.encode('utf-8') in response.data

def test_parent_profile_get(client, parent_user):
    login_as_parent(client, parent_user)
    response = client.get('/parent/profile')
    assert response.status_code == 200
    assert 'Родител'.encode('utf-8') in response.data or b'parent_profile' in response.data

def test_parent_profile_post_add_child(client, parent_user, student_child):
    login_as_parent(client, parent_user)
    
    student_child.share_code = 'SHARE123'
    db.session.commit()

    response = client.post('/parent/profile', data={
        'first_name': 'Updated',
        'middle_name': '',
        'last_name': 'Parent',
        'email': 'parent_updated@test.bg',
        'phone_number': '0888123456',
        'date_of_birth': '1980-01-01',
        'password': '',
        'share_code': 'SHARE123',
    }, follow_redirects=True)
    assert response.status_code == 200
    parent = Parent.query.filter_by(user_id=parent_user[0].id).first()
    assert student_child in parent.children
