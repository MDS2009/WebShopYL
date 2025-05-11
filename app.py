from flask import Flask, render_template, session, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from extensions import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

from forms import RegistrationForm, LoginForm, ProductForm, SearchForm
from models import User, Product, OrderItem, Order, Favourite


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    Migrate(app, db)

    with app.app_context():
        db.create_all()

    return app

app = create_app()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#Начальная страница
@app.route('/')
def index():
    search_query = request.args.get('search', '')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    category = request.args.get('category')

    query = Product.query

    if search_query:
        query = query.filter(Product.name.ilike(f'%{search_query}%'))
    if min_price:
        query = query.filter(Product.price >= float(min_price))
    if max_price:
        query = query.filter(Product.price <= float(max_price))
    if category:
        query = query.filter_by(category=category)

    products = query.all()
    return render_template('index.html', products=products)
#Товары
@app.route('/product/<int:id>')
def product(id):
    product = Product.query.get_or_404(id)
    return render_template('product.html', product=product)

@app.route('/favourite/<int:product_id>', methods=['POST'])
@login_required
def add_to_favourite(product_id):
    favourite = Favourite(user_id=current_user.id, product_id=product_id)
    db.session.add(favourite)
    db.session.commit()
    return redirect(url_for('product', id=product_id))

@app.route('/favourites')
@login_required
def favourites():
    favourites = Favourite.query.filter_by(user_id=current_user.id).all()
    products = [Product.query.get(fav.product_id) for fav in favourites]
    return render_template('favourites.html', products=products)

# Админ-панель
@app.route('/admin/products')
@login_required
def admin_products():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    products = Product.query.order_by(Product.id.desc()).all()
    return render_template('admin/products.html', products=products)


@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
def admin_add_product():
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    form = ProductForm()
    if form.validate_on_submit():
        try:
            image = form.image.data
            filename = secure_filename(image.filename)
            upload_dir = os.path.join(app.root_path, 'static/uploads')
            os.makedirs(upload_dir, exist_ok=True)
            image.save(os.path.join(upload_dir, filename))

            product = Product(
                name=form.name.data,
                description=form.description.data,
                price=form.price.data,
                image=f'uploads/{filename}'
            )
            db.session.add(product)
            db.session.commit()
            flash('Товар успешно добавлен', 'success')
            return redirect(url_for('admin_products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    return render_template('admin/add_product.html', form=form)


@app.route('/admin/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_edit_product(id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    form.image.validators = []  # Убираем обязательность изображения

    if form.validate_on_submit():
        try:
            product.name = form.name.data
            product.description = form.description.data
            product.price = form.price.data

            if form.image.data:
                image = form.image.data
                filename = secure_filename(image.filename)
                upload_dir = os.path.join(app.root_path, 'static/uploads')
                image.save(os.path.join(upload_dir, filename))
                product.image = f'uploads/{filename}'
            else:
                product.image = product.image  # Сохраняем старое изображение

            db.session.commit()
            flash('Товар обновлен', 'success')
            return redirect(url_for('admin_products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    return render_template('admin/edit_product.html', form=form, product=product)


@app.route('/admin/products/delete/<int:id>', methods=['POST'])
@login_required
def admin_delete_product(id):
    if not current_user.is_admin:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    product = Product.query.get_or_404(id)
    try:
        db.session.delete(product)
        db.session.commit()
        flash('Товар удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления: {str(e)}', 'danger')
    return redirect(url_for('admin_products'))


# Маршрут для админа
@app.route('/admin/approve_sellers')
@login_required
def approve_sellers():
    if not current_user.is_admin:
        abort(403)

    pending_sellers = User.query.filter_by(
        account_type='seller',
        is_approved=False
    ).all()

    return render_template('admin/approve_sellers.html',
                           sellers=pending_sellers)


# Одобрение продавца
@app.route('/admin/approve/<int:user_id>')
@login_required
def approve_seller(user_id):
    if not current_user.is_admin:
        abort(403)

    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()

    send_verification_code(user)  # Отправка кода продавцу
    flash('Продавец одобрен! Код отправлен.', 'success')
    return redirect(url_for('approve_sellers'))


# Генерация и отправка кода
def send_verification_code(user):
    # Реализация отправки email/SMS с кодом
    print(f'Код подтверждения для {user.email}: {user.verification_code}')

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
        user = User.query.filter(
            (User.email == form.identifier.data) |
            (User.username == form.identifier.data)
        ).first()

        # Проверка для продавцов
        if user and user.account_type == 'seller':
            if not user.is_approved:
                flash('Аккаунт продавца еще не одобрен', 'danger')
                return redirect(url_for('login'))

            if not user.code_used and \
                    request.form.get('verification_code') != user.verification_code:
                flash('Неверный код подтверждения', 'danger')
                return redirect(url_for('login'))

            user.code_used = True  # Код можно использовать только один раз
            db.session.commit()

        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('index'))

        flash('Неверные данные', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/check_account_type')
def check_account_type():
    login = request.args.get('login')
    user = User.query.filter(
        (User.email == login) | (User.username == login)
    ).first()

    return jsonify({
        'is_seller': user and user.account_type == 'seller' and user.is_approved
    })


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

if __name__ == '__main__':
    app.run(debug=True)