from app import app, db
from models import User

with app.app_context():
    user = User.query.filter_by(email='d.mart123@outlook.com').first()

    if user:
        user.is_admin = True
        db.session.commit()
        print(f"Админ-права выданы для {user.username}!")
    else:
        print("Пользователь не найден.")