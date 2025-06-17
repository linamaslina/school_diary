from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, SelectMultipleField, FloatField, BooleanField, DateField, EmailField
from wtforms_sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, Optional, Length, EqualTo, InputRequired, NumberRange, Email
from school_diary.models import Course, Classroom, Teacher

from datetime import date, datetime

class LoginForm(FlaskForm):
    username = StringField('Потребителско име', validators=[DataRequired()])
    password = PasswordField('Парола', validators=[DataRequired()])
    submit = SubmitField('Вход')

class AddUserForm(FlaskForm):
    role = SelectField('Роля', choices=[])
    first_name = StringField('Име', validators=[DataRequired()])
    middle_name = StringField('Презиме')
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = EmailField('Имейл', validators=[Optional(), Email()])
    phone_number = StringField('Телефон', validators=[Optional(), Length(min=5, max=20)])
    date_of_birth = DateField('Дата на раждане', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Добави')

    def __init__(self, include_admin=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if include_admin:
            self.role.choices = [
                ('admin', 'Админ'),
                ('student', 'Ученик'),
                ('parent', 'Родител'),
                ('teacher', 'Учител'),
                ('director', 'Директор'),
            ]
        else:
            self.role.choices = [
                ('student', 'Ученик'),
                ('parent', 'Родител'),
                ('teacher', 'Учител'),
                ('director', 'Директор'),
            ]

class SchoolForm(FlaskForm):
    name = StringField("Име на училище", validators=[DataRequired()])
    address = StringField("Адрес", validators=[DataRequired()])
    city= StringField("Град", validators=[DataRequired()])
    classrooms = StringField('Класове (напр. 1А, 1Б, 2В)', validators=[])  # поле без задължителна валидация
    submit = SubmitField("Създай училище")

class ClassroomForm(FlaskForm):
    grade = IntegerField("Клас (1–12)", validators=[DataRequired(), NumberRange(min=1, max=12)])
    letter = SelectField("Паралелка", choices=[('А', 'А'), ('Б', 'Б'), ('В', 'В'), ('Г', 'Г'), ('Д', 'Д'), ('Е', 'Е'), ('Ж', 'Ж'), ('З', 'З'), ('И', 'И'), ('К', 'К')])
    submit = SubmitField("Добави клас")

class RegisterForm(FlaskForm):
    # username = StringField('Потребителско име', validators=[DataRequired()])
    password = PasswordField('Парола', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Потвърди парола', validators=[
        DataRequired(),
        EqualTo('password', message='Паролите не съвпадат.')
    ])
    role = SelectField('Роля', choices=[
        ('student', 'Ученик'),
        ('parent', 'Родител'),
        ('teacher', 'Учител'),
        ('director', 'Директор')
    ], validators=[DataRequired()])
    first_name = StringField('Име', validators=[DataRequired()])
    middle_name = StringField('Презиме', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Телефон', validators=[DataRequired(), Length(min=6, max=20)])
    submit = SubmitField('Регистрация')

class GradeForm(FlaskForm):
    student = SelectField("Ученик", coerce=int)
    course = SelectField("Предмет", coerce=int)
    value = FloatField("Оценка", validators=[InputRequired(), NumberRange(min=2.0, max=6.0)])
    submit = SubmitField("Запиши оценка")

class ScheduleForm(FlaskForm):
    day_of_week = SelectField(
        'Ден от седмицата',
        choices=[
            (1, 'Понеделник'),
            (2, 'Вторник'),
            (3, 'Сряда'),
            (4, 'Четвъртък'),
            (5, 'Петък'),
        ],
        coerce=int,  # ↔️ парсва стойността към int
        validators=[DataRequired()]
    )
    hour = IntegerField('Час', validators=[DataRequired(), NumberRange(min=1, max=7)])
    classroom = SelectField('Клас', coerce=int, validators=[DataRequired()])
    course = SelectField('Предмет', coerce=int, validators=[DataRequired()])
    teacher = SelectField('Учител', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Запази')

class AutoAddScheduleForm(FlaskForm):
    classroom = QuerySelectField('Клас', query_factory=lambda: Classroom.query.all(), get_label=lambda classroom: f"{classroom.grade} {classroom.letter}")
    course = QuerySelectField('Предмет', query_factory=lambda: Course.query.all(), get_label='name')
    teacher = QuerySelectField('Учител', query_factory=lambda: Teacher.query.all(), get_label=lambda t: f"{t.user.first_name} {t.user.last_name}")
    hours_per_week = IntegerField('Часове на седмица', validators=[DataRequired(), NumberRange(min=1, max=30)])
    same_day_allowed = BooleanField('Позволи всички часове в един ден')
    max_per_day = IntegerField('Макс. часове в един ден', validators=[NumberRange(min=1, max=8)])
    submit = SubmitField('Генерирай')

class AddTeacherForm(FlaskForm):
    first_name = StringField('Име', validators=[DataRequired()])
    middle_name = StringField('Презиме', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Имейл', validators=[Email()])
    username = StringField('Потребителско име', validators=[DataRequired()])
    password = PasswordField('Парола', validators=[DataRequired()])
    courses = SelectMultipleField('Предмети', coerce=int) 
    classroom = SelectField("Класен ръководител на клас (по избор)", coerce=int, choices=[], validators=[Optional()])
    submit = SubmitField('Запиши')

    def __init__(self, school_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if school_id:
            self.courses.choices = [(c.id, c.name) for c in Course.query.filter_by(school_id=school_id).all()]

class ScheduleFilterForm(FlaskForm):
    classroom = QuerySelectField("Избери клас", get_label=lambda t:f"{t.grade}{t.letter}", allow_blank=False)
    submit = SubmitField("Покажи разписанието")

class StudentProfileForm(FlaskForm):
    first_name = StringField('Име', validators=[DataRequired(), Length(max=70)])
    middle_name = StringField('Презиме', validators=[DataRequired(), Length(max=70)])
    last_name = StringField('Фамилия', validators=[DataRequired(), Length(max=70)])
    email = StringField('Имейл', validators=[DataRequired(), Email(), Length(max=150)])
    phone_number = StringField('Телефон', validators=[Optional(), Length(max=20)])
    date_of_birth = DateField('Дата на раждане', format='%Y-%m-%d', validators=[Optional()])
    password = PasswordField('Нова парола', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Потвърди нова парола', validators=[Optional(), EqualTo('password', message='Паролите не съвпадат.')])
    submit = SubmitField('Запази промените')

class ParentForm(FlaskForm):
    first_name = StringField('Име', validators=[DataRequired()])
    middle_name = StringField('Презиме', validators=[Optional()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Имейл', validators=[DataRequired(), Email()])
    phone_number = StringField('Телефон', validators=[Optional()])
    date_of_birth = DateField('Дата на раждане', format='%Y-%m-%d', validators=[Optional()])
    password = PasswordField('Нова парола', validators=[Optional()])
    confirm_password = PasswordField('Потвърди нова парола', validators=[Optional(), EqualTo('password', message='Паролите не съвпадат.')])
    # НОВО: поле за добавяне на дете по код
    share_code = StringField('Код за споделяне на дете', validators=[Optional()])

    submit = SubmitField('Запази промените')

class TeacherAndDirectorProfileForm(FlaskForm):
    first_name = StringField('Име', validators=[DataRequired()])
    middle_name = StringField('Презиме', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    email = StringField('Имейл', validators=[DataRequired(), Email()])
    phone_number = StringField('Телефон', validators=[Optional(), Length(min=5, max=20)])
    password = PasswordField('Нова парола', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Потвърди парола', validators=[Optional(), EqualTo("password", message='Паролите не съвпадат')])
    submit = SubmitField('Запази')