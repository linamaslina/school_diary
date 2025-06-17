from school_diary.extensions import db
import uuid
from datetime import date

# Много към много: родител-ученик
parent_student = db.Table(
    'parent_student',
    db.Column('parent_id', db.Integer, db.ForeignKey('parent.id')),
    db.Column('student_id', db.Integer, db.ForeignKey('student.id'))
)

# Много към много: учител-предмет
teacher_course = db.Table(
    'teacher_course',
    db.Column('teacher_id', db.Integer, db.ForeignKey('teacher.id')),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'))
)

# Много към много: учител-клас
teacher_classrooms = db.Table(
    'teacher_classrooms',
    db.Column('teacher_id', db.Integer, db.ForeignKey('teacher.id')),
    db.Column('classroom_id', db.Integer, db.ForeignKey('classroom.id'))
)

# Много към много: клас-предмет
classroom_course = db.Table(
    'classroom_course',
    db.Column('classroom_id', db.Integer, db.ForeignKey('classroom.id')),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'))
)

# Много към много: училище-предмет
school_courses = db.Table(
    'school_courses',
    db.Column('school_id', db.Integer, db.ForeignKey('school.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)

# Основен потребител
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(70), nullable=False)
    middle_name = db.Column(db.String(70), nullable=False)
    last_name = db.Column(db.String(70), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin, teacher, student, parent, director и др.

    email = db.Column(db.String(150), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True) 

# Ученик
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'))
    share_code = db.Column(db.String(10), unique=True, nullable=False, default=lambda: uuid.uuid4().hex[:10].upper())

    user = db.relationship('User', backref='student_profile')
    classroom = db.relationship('Classroom', back_populates='students')
    grades = db.relationship('Grade', back_populates='student', lazy=True)
    absences = db.relationship('Absence', back_populates='student', lazy=True)

# Родител
class Parent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref='parent_profile')
    children = db.relationship('Student', secondary=parent_student, backref='parents')

# Учител
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=True)  # ново поле

    user = db.relationship('User', backref='teacher_profile')
    school = db.relationship('School', back_populates='teachers')
    courses = db.relationship('Course', secondary=teacher_course, back_populates='teachers')
    classrooms = db.relationship('Classroom', secondary=teacher_classrooms, back_populates='teachers')
    grades = db.relationship('Grade', back_populates='teacher', lazy=True)
    absences_recorded = db.relationship('Absence', back_populates='teacher', lazy=True)
    class_teacher_of = db.relationship('Classroom', back_populates='class_teacher', foreign_keys=[classroom_id])

# Директор
class Director(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'))

    user = db.relationship('User', backref='director_profile')
    school = db.relationship('School', back_populates='director')

# Училище
class School(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)

    classrooms = db.relationship('Classroom', back_populates='school', cascade="all, delete-orphan", lazy=True)
    teachers = db.relationship('Teacher', back_populates='school', lazy=True)
    director = db.relationship('Director', back_populates='school', uselist=False)
    courses = db.relationship('Course', secondary=school_courses, back_populates='schools')

# Предмет
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    teachers = db.relationship('Teacher', secondary=teacher_course, back_populates='courses')
    classrooms = db.relationship('Classroom', secondary=classroom_course, back_populates='courses')
    schools = db.relationship('School', secondary=school_courses, back_populates='courses')
    grades = db.relationship('Grade', back_populates='course', lazy=True)

# Клас
class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    letter = db.Column(db.String(1), nullable=False)

    __table_args__ = (db.UniqueConstraint('school_id', 'grade', 'letter', name='unique_class_per_school'),)

    school = db.relationship('School', back_populates='classrooms')
    students = db.relationship('Student', back_populates='classroom', lazy=True)
    courses = db.relationship('Course', secondary=classroom_course, back_populates='classrooms')
    teachers = db.relationship('Teacher', secondary=teacher_classrooms, back_populates='classrooms')
    schedule = db.relationship('Schedule', back_populates='classroom', cascade='all, delete-orphan')
    class_teacher = db.relationship('Teacher', back_populates='class_teacher_of', uselist=False)

# Оценка
class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    value = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)

    student = db.relationship('Student', back_populates='grades')
    teacher = db.relationship('Teacher', back_populates='grades')
    course = db.relationship('Course', back_populates='grades')

# Отсъствие
class Absence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False) 
    date = db.Column(db.Date, nullable=False, default=date.today)
    reason = db.Column(db.String(255))
    excused = db.Column(db.Boolean, default=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))

    course = db.relationship('Course')
    student = db.relationship('Student', back_populates='absences')
    teacher = db.relationship('Teacher', back_populates='absences_recorded')

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))
    day_of_week = db.Column(db.Integer)  # 1=Понеделник, ..., 5=Петък
    hour = db.Column(db.Integer)  # 1–7

    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    classroom = db.relationship('Classroom', back_populates='schedule')
    course = db.relationship('Course', backref='schedule_entries')
    teacher = db.relationship('Teacher', backref='schedule_entries')
