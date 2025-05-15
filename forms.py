from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, FloatField, validators, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User
from wtforms.fields import SelectField


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

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Старый пароль', validators=[DataRequired()])
    new_password = PasswordField('Новый пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите новый пароль', validators=[DataRequired(), EqualTo('new_password', message='Пароли должны совпадать')])
    submit = SubmitField('Сменить пароль')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Запросить сброс пароля')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user is None:
            raise ValidationError('Нет аккаунта с таким email.')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Новый пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль', 
        validators=[DataRequired(), EqualTo('password', message='Пароли должны совпадать')])
    submit = SubmitField('Сбросить пароль')


class ProfileForm(FlaskForm):
    full_name = StringField('Полное имя', validators=[DataRequired()])
    address = StringField('Адрес', validators=[DataRequired()])
    phone = StringField('Телефон', validators=[DataRequired()])
    submit = SubmitField('Сохранить')

class ProductForm(FlaskForm):
    class Meta:
        csrf = False
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
    search = StringField('Поиск по названию')
    min_price = StringField('Минимальная цена')
    max_price = StringField('Максимальная цена')
    category = SelectField('Категория', choices=[
        ('all', 'Все категории')
    ])
    brand = SelectField('Бренд', choices=[
        ('all', 'Все бренды')
    ])
    sort_by = SelectField('Сортировка', choices=[
        ('name_asc', 'По названию (А-Я)'),
        ('name_desc', 'По названию (Я-А)'),
        ('price_asc', 'Сначала дешевле'),
        ('price_desc', 'Сначала дороже')
    ])
    submit = SubmitField('Применить')