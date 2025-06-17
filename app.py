from school_diary import create_app
from school_diary.extensions import db

app = create_app()

@app.before_request
def create_tables():
    if not hasattr(app, 'db_created'):
        db.create_all()
        app.db_created = True

if __name__ == '__main__':
    app.run(debug=True)
