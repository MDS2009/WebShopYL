import strip
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, FloatField, validators
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from wtforms import TextAreaField, validators
import re

from models import User


class RegistrationForm(FlaskForm):
    username = StringField(
        'Логин',
        validators=[
            validators.DataRequired(),
            validators.Length(min=3, max=25),
            # Запрет на спецсимволы и пробел в начале
            validators.Regexp(
                regex=r'^[a-zA-Z0-9]',
                message='Логин должен начинаться с буквы или цифры'
            )
        ],
        render_kw={"placeholder": "Только буквы, цифры и _"}
    )
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
    name = StringField('Название', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    description = TextAreaField('Описание', validators=[
        DataRequired(),
        Length(max=500)
    ])
    price = FloatField('Цена', validators=[
        DataRequired(),
        validators.NumberRange(min=0.01)
    ])
    image = FileField('Изображение', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Только изображения!'),
        DataRequired()  # Обязательное поле для нового товара
    ])
    submit = SubmitField('Сохранить')

class SearchForm(FlaskForm):
    search = StringField('Поиск')
    min_price = StringField('Возрастание цены')
    max_price = StringField('Убывание цены')
    submit = SubmitField('Фильтр')