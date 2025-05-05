from flask import Flask, render_template, session, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, login_manager
from forms import RegistrationForm, LoginForm, ProductForm, SearchForm
from models import User, Product, OrderItem, Order
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()

    return app

app = create_app()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#Начальная страница
@app.route('/', methods=['GET', 'POST'])
def index():
    form = SearchForm()
    products = Product.query

    # Использование request.args для GET-параметров
    if request.args.get('search'):
        products = products.filter(Product.name.ilike(f"%{request.args.get('search')}%"))
    if request.args.get('min_price'):
        products = products.filter(Product.price >= float(request.args.get('min_price')))
    if request.args.get('max_price'):
        products = products.filter(Product.price <= float(request.args.get('max_price')))

    products = products.all()
    return render_template('index.html', products=products, form=form)

#Товары
@app.route('/product/<int:id>')
def product(id):
    product = Product.query.get_or_404(id)
    return render_template('product.html', product=product)

#Добавление в корзину и корзина
@app.route('/add_to_cart/<int:id>')
@login_required
def add_to_cart(id):
    if 'cart' not in session:
        session['cart'] = {}

    # Увеличиваем количество или добавляем товар
    if str(id) in session['cart']:
        session['cart'][str(id)] += 1
    else:
        session['cart'][str(id)] = 1

    session.modified = True
    return redirect(url_for('cart'))


@app.route('/cart')
@login_required
def cart():
    cart_items = session.get('cart', {})
    products = Product.query.filter(Product.id.in_(cart_items.keys())).all()
    total = sum(product.price * cart_items[str(product.id)] for product in products)
    return render_template('cart.html',
                           products=products,
                           cart_items=cart_items,  # Добавьте это
                           total=total)


@app.route('/update_quantity/<int:id>/<int:quantity>', methods=['POST'])
@login_required
def update_quantity(id, quantity):
    if 'cart' not in session:
        return jsonify({'error': 'Корзина не найдена'}), 404

    product_id = str(id)

    if product_id not in session['cart']:
        return jsonify({'error': 'Товар не найден в корзине'}), 404

    # Устанавливаем новое количество
    session['cart'][product_id] = quantity
    session.modified = True

    # Пересчет общей суммы
    total = sum(
        Product.query.get(int(pid)).price * qty
        for pid, qty in session['cart'].items()
    )

    return jsonify({
        'new_quantity': quantity,
        'total': total
    })

@app.route('/clear_cart', methods=['POST'])  # Используем POST для безопасности
@login_required
def clear_cart():
    if 'cart' in session:
        session.pop('cart')  # Полностью удаляем корзину
        session.modified = True
        flash('Корзина успешно очищена', 'success')
    return redirect(url_for('cart'))

# app.py - исправленный маршрут remove_from_cart
@app.route('/remove_from_cart/<int:id>', methods=['POST'])  # Изменено на POST
@login_required
def remove_from_cart(id):
    if 'cart' in session and str(id) in session['cart']:
        del session['cart'][str(id)]  # Исправлено для работы со словарем
        session.modified = True
        flash('Товар удален из корзины', 'success')
    return redirect(url_for('cart'))


#Регистрация, вход и выход из аккаунта
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            hashed_password = generate_password_hash(form.password.data)
            user = User(
                username=form.username.data,
                email=form.email.data,
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()
            flash('Регистрация прошла успешно! Пожалуйста, войдите в систему.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Ошибка регистрации. Адрес электронной почты или логин уже существуют.', 'danger')
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Ищем пользователя по email или username
        user = User.query.filter(
            (User.email == form.identifier.data) |
            (User.username == form.identifier.data)
        ).first()

        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Вход в систему прошел успешно!', 'success')
            return redirect(url_for('index'))
        flash('Неверный адрес электронной почты, логин или пароль', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))




#Оплата
@app.route('/payment/<int:order_id>')
@login_required
def payment(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('payment.html', order=order)

@app.route('/confirm_payment/<int:order_id>')
@login_required
def confirm_payment(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = 'Доставлен'
    db.session.commit()
    flash('Ваш заказ принят.', 'success')  # Изменено на нужный текст
    return redirect(url_for('order_history'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if 'cart' not in session or not session['cart']:
        flash('Корзина пуста', 'danger')
        return redirect(url_for('cart'))

        # Получение товаров из корзины
    cart_items = session['cart']
    products = Product.query.filter(Product.id.in_(cart_items)).all()

    # Проверка наличия товаров
    if not products:
        flash('Ошибка: товары не найдены', 'danger')
        return redirect(url_for('cart'))

    # Расчет суммы заказа
    total = sum(product.price for product in products)

    if request.method == 'POST':
        address = request.form.get('address')
        if not address.strip():
            flash('Укажите адрес доставки', 'danger')
            return redirect(url_for('checkout'))

        try:
            order = Order(
                user_id=current_user.id,
                total=total,
                address=address.strip(),
                status='pending',
                created_at=datetime.now()
            )
            db.session.add(order)

            for product in products:
                item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=1
                )
                db.session.add(item)

            db.session.commit()
            session.pop('cart', None)
            return redirect(url_for('payment', order_id=order.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'warning')

    products = Product.query.filter(Product.id.in_(session['cart'])).all()
    return render_template('checkout.html', products=products, total=total)

@app.route('/order_history')
@login_required
def order_history():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('order_history.html', orders=orders)

#Админ панель и функции
@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        try:
            filename = secure_filename(form.image.data.filename)
            file_path = os.path.join(app.root_path, 'static/uploads', filename)
            form.image.data.save(file_path)

            product = Product(
                name=form.name.data,
                description=form.description.data,
                price=float(form.price.data),
                image=f'uploads/{filename}'
            )
            db.session.add(product)
            db.session.commit()
            return redirect(url_for('index'))
        except Exception as e:
            flash('Ошибка при создании продукта', 'danger')
    return render_template('add_product.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)