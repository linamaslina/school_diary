import random
import string
from unidecode import unidecode
from school_diary.models import User, Schedule, Course, Teacher
from unidecode import unidecode
import random, string
from school_diary.extensions import bcrypt, db
import random

def generate_unique_username(first_name, middle_name, last_name):
    base_username = f"{unidecode(first_name.lower())}.{unidecode(middle_name[0].lower())}.{unidecode(last_name.lower())}"
    
    while True:
        suffix = str(random.randint(100, 999))
        username = f"{base_username}{suffix}"
        if not User.query.filter_by(username=username).first():
            return username

def generate_password(length=10):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))

def get_teachers_for_course_and_school(course_id, school_id):
    # Връща всички учители, които преподават course_id и са в school_id
    return Teacher.query.filter(
        Teacher.school_id == school_id,
        Teacher.courses.any(id=course_id)  # assuming Teacher има many-to-many към Course чрез "courses"
    ).all()


def auto_add_schedule(classroom_id, course_id, teacher_id, hours_per_week, same_day_allowed=False, max_per_day=7):
    days = [1, 2, 3, 4, 5]  # Понеделник до Петък
    hours = list(range(1, 8))  # Часове от 1 до 7
    all_slots = [(d, h) for d in days for h in hours]
    random.shuffle(all_slots)  # Разбъркваме всички слотове

    used_slots = set(
        (s.day_of_week, s.hour)
        for s in Schedule.query.filter_by(classroom_id=classroom_id).all()
    )

    teacher_slots = set(
        (s.day_of_week, s.hour)
        for s in Schedule.query.filter_by(teacher_id=teacher_id).all()
    )

    course_teacher_slots = set(
        (s.day_of_week, s.hour)
        for s in Schedule.query.filter_by(teacher_id=teacher_id, course_id=course_id).all()
    )

    # Колко часа вече има добавени в този ден за класа
    classroom_day_hours = {
        day: sum(1 for s in Schedule.query.filter_by(classroom_id=classroom_id).all() if s.day_of_week == day)
        for day in days
    }

    added = 0

    for day, hour in all_slots:
        slot = (day, hour)

        if slot in used_slots or slot in teacher_slots or slot in course_teacher_slots:
            continue

        # Проверка дали броят часове за деня не е достигнат
        if classroom_day_hours[day] >= max_per_day:
            continue

        # Ако не е позволено всичко в един ден и вече има поне 1 час този ден – пропускаме
        if not same_day_allowed and classroom_day_hours[day] > 0:
            continue

        new_schedule = Schedule(
            classroom_id=classroom_id,
            course_id=course_id,
            teacher_id=teacher_id,
            day_of_week=day,
            hour=hour
        )
        db.session.add(new_schedule)

        used_slots.add(slot)
        teacher_slots.add(slot)
        course_teacher_slots.add(slot)
        classroom_day_hours[day] += 1

        added += 1
        if added == hours_per_week:
            break

    db.session.commit()
    return added

    
