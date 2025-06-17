from school_diary import create_app
from school_diary.extensions import bcrypt, db
from school_diary.models import User, Student, Parent, Teacher, Director, School, Course, Classroom, Grade, Absence
from datetime import date

app = create_app() 

def populate_data():
    print("🚀 Добавяне на примерни данни...")

    # 1. Училище
    school = School(name='СОУ "Св. Климент Охридски"', address='ул. Примерна 10', city='София')
    db.session.add(school)
    db.session.commit()

    # 2. Администратор
    admin_user = User(
        username='admin',
        password=bcrypt.generate_password_hash('admin').decode('utf-8'),
        first_name='Веселина',
        middle_name='Николова',
        last_name='Послийска',
        email='admin@example.com',
        phone_number='+359888111222',
        date_of_birth=date(1980, 3, 15),
        role='admin'
    )
    db.session.add(admin_user)

    # 3. Директор
    director_user = User(
        username='director',
        password=bcrypt.generate_password_hash('director').decode('utf-8'),
        first_name='Иван',
        middle_name='Петров',
        last_name='Петров',
        email='director@example.com',
        phone_number='+359888333444',
        date_of_birth=date(1975, 7, 20),
        role='director'
    )
    db.session.add(director_user)
    db.session.commit()

    director = Director(user_id=director_user.id, school_id=school.id)
    db.session.add(director)

    # 4. Класове
    classroom_7a = Classroom(school_id=school.id, grade=7, letter='А')
    classroom_7b = Classroom(school_id=school.id, grade=7, letter='Б')
    db.session.add_all([classroom_7a, classroom_7b])
    db.session.commit()

    # 5. Предмети
    math = Course(name='Математика')
    physics = Course(name='Физика')
    biology = Course(name='Биология')
    chemistry = Course(name='Химия')
    history = Course(name='История')
    db.session.add_all([math, physics, biology, chemistry, history])
    db.session.commit()

    school.courses.extend([math, physics, biology, chemistry, history])
    classroom_7a.courses.extend([math, physics, chemistry])
    classroom_7b.courses.extend([math, biology, history])
    db.session.commit()

    # 6. Учител - класен ръководител на 7А
    teacher_user = User(
        username='teacher1',
        password=bcrypt.generate_password_hash('teacher1').decode('utf-8'),
        first_name='Петър',
        middle_name='Георгиев',
        last_name='Георгиев',
        email='petar.georgiev@example.com',
        phone_number='+359887555666',
        date_of_birth=date(1985, 11, 5),
        role='teacher'
    )
    db.session.add(teacher_user)
    db.session.commit()

    teacher = Teacher(
        user_id=teacher_user.id,
        school_id=school.id,
        classroom_id=classroom_7a.id  # връзка към класа като класен ръководител
    )
    teacher.courses.extend([math, physics])
    teacher.classrooms.append(classroom_7a)
    db.session.add(teacher)

    # Свързваме classroom <-> class_teacher
    classroom_7a.class_teacher = teacher
    db.session.commit()

    # 7. Ученици
    student_user1 = User(
        username='student1',
        password=bcrypt.generate_password_hash('student1').decode('utf-8'),
        first_name='Мария',
        middle_name='Иванова',
        last_name='Иванова',
        email='maria.ivanova@example.com',
        phone_number='+359889111222',
        date_of_birth=date(2009, 4, 10),
        role='student'
    )
    db.session.add(student_user1)
    db.session.commit()

    student1 = Student(user_id=student_user1.id, classroom_id=classroom_7a.id)
    db.session.add(student1)

    student_user2 = User(
        username='student2',
        password=bcrypt.generate_password_hash('student2').decode('utf-8'),
        first_name='Георги',
        middle_name='Димитров',
        last_name='Димитров',
        email='georgi.dimitrov@example.com',
        phone_number='+359889333444',
        date_of_birth=date(2009, 8, 25),
        role='student'
    )
    db.session.add(student_user2)
    db.session.commit()

    student2 = Student(user_id=student_user2.id, classroom_id=classroom_7b.id)
    db.session.add(student2)

    # 8. Родител
    parent_user = User(
        username='parent1',
        password=bcrypt.generate_password_hash('parent1').decode('utf-8'),
        first_name='Анна',
        middle_name='Петрова',
        last_name='Петрова',
        email='anna.petrova@example.com',
        phone_number='+359887777888',
        date_of_birth=date(1980, 2, 18),
        role='parent'
    )
    db.session.add(parent_user)
    db.session.commit()

    parent = Parent(user_id=parent_user.id)
    parent.children.append(student1)
    db.session.add(parent)

    # 9. Оценки
    grade1 = Grade(
        student_id=student1.id,
        course_id=math.id,
        value=5.50,
        teacher_id=teacher.id,
        date=date.today()
    )
    grade2 = Grade(
        student_id=student2.id,
        course_id=biology.id,
        value=4.25,
        teacher_id=teacher.id,  # може да не е реално учител, но примерът е тестов
        date=date.today()
    )
    db.session.add_all([grade1, grade2])

    # 10. Отсъствия
    absence1 = Absence(
        student_id=student1.id,
        course=biology,
        date=date.today(),
        reason='Здравословни причини',
        excused=True
    )
    absence2 = Absence(
        student_id=student2.id,
        course=math,
        date=date.today(),
        reason='Без уважителна причина',
        excused=False
    )
    db.session.add_all([absence1, absence2])

    # 11. Записваме всички промени
    db.session.commit()
    print("✅ Примерните данни са добавени успешно.")
    
if __name__ == '__main__':
    with app.app_context():
        populate_data()
