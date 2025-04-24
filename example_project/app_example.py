from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from extensions import db, login_manager
from forms import RegistrationForm, LoginForm, ProductForm, SearchForm
from models import User, Product, OrderItem, Order
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
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

@app.route('/')
def index():
    form = SearchForm()
    query = Product.query

    if form.validate_on_submit():
        if form.search.data:
            query = query.filter(Product.name.ilike(f'%{form.search.data}%'))
        if form.min_price.data:
            query = query.filter(Product.price >= float(form.min_price.data))
        if form.max_price.data:
            query = query.filter(Product.price <= float(form.max_price.data))

    products = query.all()
    return render_template('index.html', products=products, form=form)

@app.route('/product/<int:id>')
def product(id):
    product = Product.query.get_or_404(id)
    return render_template('product.html', product=product)

@app.route('/add_to_cart/<int:id>')
@login_required
def add_to_cart(id):
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append(id)
    session.modified = True
    return redirect(url_for('cart'))

@app.route('/cart')
@login_required
def cart():
    cart_items = session.get('cart', [])
    products = Product.query.filter(Product.id.in_(cart_items)).all()
    total = sum(product.price for product in products)
    return render_template('cart.html', products=products, total=total)

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
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Email or username already exists.', 'danger')
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
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        flash('Invalid email/username or password', 'danger')
    return render_template('login.html', form=form)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/remove_from_cart/<int:id>')
@login_required
def remove_from_cart(id):
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item != id]
        session.modified = True
        flash('Item removed from cart', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if 'cart' not in session or len(session['cart']) == 0:
        return redirect(url_for('cart'))

    if request.method == 'POST':
        try:
            order = Order(
                user_id=current_user.id,
                total=sum(Product.query.get(p).price for p in session['cart'])
            )
            db.session.add(order)

            for product_id in session['cart']:
                item = OrderItem(
                    order_id=order.id,
                    product_id=product_id,
                    quantity=1
                )
                db.session.add(item)

            db.session.commit()
            session.pop('cart')
            return redirect(url_for('payment', order_id=order.id))

        except Exception as e:
            db.session.rollback()
            flash('Error creating order', 'danger')

    products = Product.query.filter(Product.id.in_(session['cart'])).all()
    return render_template('checkout.html', products=products)

@app.route('/payment/<int:order_id>')
@login_required
def payment(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('payment.html', order=order)

@app.route('/confirm_payment/<int:order_id>')
@login_required
def confirm_payment(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = 'completed'
    db.session.commit()
    flash('Payment successful!', 'success')
    return redirect(url_for('order_history'))


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
            flash('Error saving product', 'danger')
    return render_template('add_product.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)