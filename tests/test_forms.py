import pytest
from flask import Flask
from wtforms_sqlalchemy.fields import QuerySelectField
from werkzeug.datastructures import MultiDict
from school_diary.forms import (
    LoginForm, AddUserForm, SchoolForm, RegisterForm, ClassroomForm,
    GradeForm, ScheduleForm, AutoAddScheduleForm, ScheduleFilterForm,
    StudentProfileForm, ParentForm, TeacherAndDirectorProfileForm
)

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'testsecret'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        yield app

def test_login_form_valid(app):
    form = LoginForm(username="user", password="pass")
    assert form.validate()

def test_login_form_invalid_missing_password(app):
    form = LoginForm(username="user", password="")
    assert not form.validate()

def test_add_user_form_valid(app):
    form = AddUserForm()
    form.role.choices = [("student", "Ученик")]
    form.process(data={
        "role": "student",
        "first_name": "Ана",
        "middle_name": "",
        "last_name": "Петрова",
        "email": "ana@example.com",
        "phone_number": "0888123456",
        "date_of_birth": "2005-10-15"
    })
    assert form.validate()


def test_add_user_form_invalid_email(app):
    with app.test_request_context(method='POST'):
        form = AddUserForm(formdata=MultiDict({
            "role": "student",
            "first_name": "Иван",
            "last_name": "Иванов",
            "email": "invalid-email"
        }))
        form.role.choices = [("student", "Ученик")]

        is_valid = form.validate()
        assert not is_valid
        assert "email" in form.errors



def test_school_form_valid(app):
    form = SchoolForm(data={
        "name": "СУ Иван Вазов",
        "address": "ул. Пирин 1",
        "city": "Пловдив",
        "classrooms": "1А,2Б"
    })
    assert form.validate()

def test_register_form_password_mismatch(app):
    form = RegisterForm(data={
        "password": "pass123",
        "confirm_password": "wrongpass",
        "role": "student",
        "first_name": "Мария",
        "middle_name": "Петрова",
        "last_name": "Георгиева"
    })
    assert not form.validate()

def test_classroom_form_valid(app):
    form = ClassroomForm(data={"grade": 5, "letter": "А"})
    assert form.validate()

def test_grade_form_invalid_grade_too_low(app):
    form = GradeForm()
    form.student.choices = [(1, "Иван Иванов")]
    form.course.choices = [(1, "Математика")]
    
    form.process(data={"student": 1, "course": 1, "value": 1.5})
    
    assert not form.validate()
    assert "value" in form.errors 

def test_grade_form_valid(app):
    form = GradeForm()
    form.student.choices = [(1, "Иван Иванов"), (2, "Петър Петров")]
    form.course.choices = [(1, "Математика"), (2, "Физика")]

    form.process(formdata=MultiDict({
        "student": "1",
        "course": "1",
        "value": "5.5"
    }))

    assert form.validate()


def test_schedule_form_missing_teacher(app):
    form = ScheduleForm()
    form.classroom.choices = [(1, '1А')]
    form.course.choices = [(1, 'Математика')]
    form.teacher.choices = [(1, 'Учител 1')]
    
    form.process(data={
        'day_of_week': 1, 
        'hour': 3,
        'classroom': 1,
        'course': 1,
    })
    assert not form.validate()
    assert 'teacher' in form.errors


def test_student_profile_form_valid(app):
    form = StudentProfileForm(data={
        "first_name": "Теодор",
        "middle_name": "Иванов",
        "last_name": "Георгиев",
        "email": "test@test.bg"
    })
    assert form.validate()

def test_parent_form_invalid_email(app):
    form = ParentForm(data={
        "first_name": "Майка",
        "last_name": "Родителова",
        "email": "невалиден-имейл"
    })
    assert not form.validate()

def test_teacher_profile_password_mismatch(app):
    with app.test_request_context(method='POST'):
        form = TeacherAndDirectorProfileForm(formdata=MultiDict({
            "first_name": "Мария",
            "middle_name": "Иванова",
            "last_name": "Петрова",
            "email": "maria@school.bg",
            "password": "12345678",
            "confirm_password": "00000000"
        }))

        is_valid = form.validate()
        assert not is_valid
        assert "confirm_password" in form.errors

def test_register_form_valid_data(app):
    with app.test_request_context(method='POST'):
        form = RegisterForm(formdata=MultiDict({
            "username": "ivanivanov",
            "password": "pass1234",
            "confirm_password": "pass1234",
            "role": "student",
            "first_name": "Иван",
            "middle_name": "Петров",
            "last_name": "Иванов",
            "phone_number":"0888577454",
            "email": "ivan@test.bg"
        }))
       
        form.role.choices = [("student", "Ученик"), ("teacher", "Учител")]

        assert form.validate(), f"Form errors: {form.errors}"


def test_register_form_missing_required_fields(app):
    form = RegisterForm(data={
        "password": "pass123",
        "confirm_password": "pass123"
        # липсват role, имена и email
    })
    assert not form.validate()
    assert "role" in form.errors
    assert "first_name" in form.errors

def test_classroom_form_invalid_grade(app):
    form = ClassroomForm(data={"grade": 15, "letter": "А"})  # Невалиден клас (над 12)
    assert not form.validate()
    assert "grade" in form.errors

def test_auto_add_schedule_form_missing_data(app):
    form = AutoAddScheduleForm(data={
        # липсват всички задължителни полета
    })
    assert not form.validate()
    assert "classroom" in form.errors
    assert "course" in form.errors
    assert "teacher" in form.errors

def test_student_profile_form_invalid_email(app):
    form = StudentProfileForm(data={
        "first_name": "Алекс",
        "middle_name": "Иванов",
        "last_name": "Симеонов",
        "email": "невалиден@имейл"
    })
    assert not form.validate()
    assert "email" in form.errors
