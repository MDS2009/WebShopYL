from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, FloatField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from models import User


class RegistrationForm(FlaskForm):
    username = StringField('Логин',
                          validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Почта',
                       validators=[DataRequired(), Email()])
    password = PasswordField('Пароль',
                            validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Повторите пароль',
                                    validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Регистрация')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Такой логин уже используется')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Такая почта уже используется')

class LoginForm(FlaskForm):
    identifier = StringField('Почта/Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class ProductForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    description = StringField('Описание')
    price = FloatField('Цена', validators=[DataRequired()])
    image = FileField('Изображение товара', validators=[
        FileAllowed(['jpg', 'png'], 'Только картинки!')
    ])
    submit = SubmitField('Создать продукт')

class SearchForm(FlaskForm):
    search = StringField('Поиск')
    min_price = StringField('Возрастание цены')
    max_price = StringField('Убывание цены')
    submit = SubmitField('Фильтр')