from flask import Flask
from school_diary.extensions import db, bcrypt, migrate
from .models import * 
from flask_wtf import CSRFProtect

from school_diary.routes import register_blueprints

from flask import Flask
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from school_diary.extensions import db, bcrypt, migrate
from .models import *
from school_diary.routes import register_blueprints

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
    app.config['SECRET_KEY'] = 'secretkey'
    app.config['WTF_CSRF_ENABLED'] = True

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    csrf = CSRFProtect(app)

    # ✅ Фикс за CSRF token да се появи в HTML
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf())

    # ✅ Фикс за филтъра да не хвърля грешка
    @app.template_filter('day_of_week_display')
    def day_of_week_display(day):
        days = {
            1: "Понеделник",
            2: "Вторник",
            3: "Сряда",
            4: "Четвъртък",
            5: "Петък",
            6: "Събота",
            7: "Неделя"
        }
        return days.get(day, "Unknown")

    register_blueprints(app)

    return app
