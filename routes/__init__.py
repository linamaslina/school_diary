# routes/__init__.py

def register_blueprints(app):
    from .auth_routes import auth_bp
    from .general_routes import general_bp
    from .admin_routes import admin_bp
    from .student_routes import student_bp
    from .teacher_routes import teacher_bp
    from .parent_routes import parent_bp
    from .director_routes import director_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(general_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(parent_bp)
    app.register_blueprint(director_bp)
