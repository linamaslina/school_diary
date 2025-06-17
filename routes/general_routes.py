from flask import Blueprint
from flask import Blueprint
from flask import Blueprint
from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_migrate import Migrate
from school_diary.models import User, Student, School, Parent, Teacher, Director, Classroom, Course
from school_diary.forms import LoginForm, AddUserForm, SchoolForm, ClassroomForm, RegisterForm
from unidecode import unidecode
import random, string
import uuid
from school_diary.extensions import bcrypt, db
from school_diary.utils import generate_unique_username, generate_password


general_bp = Blueprint('general', __name__)

@general_bp.route('/dashboard')
def dashboard():
    role = session.get('role')

    if role == 'admin':
        return redirect(url_for('admin.admin_dashboard_view'))
    elif role == 'director':
        return redirect(url_for('director.director_dashboard'))
    elif role == 'teacher':
        return redirect(url_for('teacher.teacher_dashboard'))
    elif role == 'parent':
        return redirect(url_for('parent.parent_dashboard'))
    elif role == 'student':
        return redirect(url_for('student.student_dashboard'))
    else:
        return redirect(url_for('auth.login'))
    
@general_bp.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404