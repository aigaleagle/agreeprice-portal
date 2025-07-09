from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'shri_aigal'  # Needed for sessions and flash

# Initialize the DB with FK support
def init_db():
    conn = sqlite3.connect('products.db')
    c = conn.cursor()

    # Enable FK support
    c.execute('PRAGMA foreign_keys = ON')

    # Create seller_registration table
    c.execute('''
        CREATE TABLE IF NOT EXISTS seller_registration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            company_no TEXT NOT NULL,
            email TEXT NOT NULL,
            gst_no TEXT NOT NULL,
            phone_no TEXT NOT NULL,
            profile_image BLOB NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Create product table with FK
    c.execute('''
        CREATE TABLE IF NOT EXISTS product (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            quantity TEXT NOT NULL,
            price REAL NOT NULL,
            date TEXT NOT NULL,
            seller_id INTEGER NOT NULL,
            FOREIGN KEY (seller_id) REFERENCES seller_registration(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()


# Home page
@app.route('/')
def index():
    return render_template('index.html')


# Seller dashboard
@app.route('/seller')
def seller():
    if 'user_id' not in session:
        flash('You must be logged in.', 'error')
        return redirect(url_for('login'))
    return render_template('seller.html')


# Submit product
@app.route('/submit', methods=['POST'])
def submit():
    if 'user_id' not in session:
        flash('You must be logged in to add products.', 'error')
        return redirect(url_for('login'))

    product = request.form['product']
    quantity = request.form['quantity']
    price = request.form['price']
    date = request.form['date']

    try:
        price_val = float(price)
        if price_val <= 0:
            flash('Error: Price must be positive.', 'error')
            return redirect(url_for('seller'))
    except ValueError:
        flash('Error: Invalid price.', 'error')
        return redirect(url_for('seller'))

    try:
        conn = sqlite3.connect('products.db')
        conn.execute('PRAGMA foreign_keys = ON')
        c = conn.cursor()
        c.execute('''
            INSERT INTO product (product_name, quantity, price, date, seller_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (product, quantity, price_val, date, session['user_id']))
        conn.commit()
        conn.close()
        flash('Product saved successfully!', 'success')
    except Exception as e:
        flash('Error saving product: ' + str(e), 'error')

    return redirect(url_for('seller'))


# Viewer page
@app.route('/viewer')
def viewer():
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template('viewer.html', today=today)


# Get products by date
@app.route('/get_products', methods=['POST'])
def get_products():
    date_param = request.form['date']
    conn = sqlite3.connect('products.db')
    c = conn.cursor()
    c.execute('''
        SELECT p.id, p.product_name, p.quantity, p.price, s.company_name 
        FROM product p 
        JOIN seller_registration s ON p.seller_id = s.id
        WHERE p.date = ?
    ''', (date_param,))
    rows = c.fetchall()
    conn.close()
    return jsonify(rows)


# Seller registration page
@app.route('/seller_registration')
def seller_registration():
    return render_template('seller_registration.html')


# Register seller
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        company_name = request.form['companyName']
        company_no = request.form['companyNo']
        email = request.form['email']
        gst_no = request.form['gstNo']
        phone_no = request.form['phoneNo']
        password = request.form['password']
        confirm_password = request.form['confirmPassword']

        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(request.url)

        profile_image = request.files['profileImage']
        if profile_image:
            image_data = profile_image.read()
        else:
            flash('Profile image is required.', 'error')
            return redirect(request.url)

        conn = sqlite3.connect('products.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO seller_registration
            (company_name, company_no, email, gst_no, phone_no, profile_image, password)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (company_name, company_no, email, gst_no, phone_no, sqlite3.Binary(image_data), password))
        conn.commit()
        conn.close()

        flash('Company registered successfully!', 'success')
        return redirect(url_for('seller_login'))

    return render_template('seller_registration.html')


# Seller login page
@app.route('/seller_login')
def seller_login():
    if 'user_id' in session:
        return redirect(url_for('seller'))
    return render_template('seller_login.html')


# Seller login POST
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('seller'))

    if request.method == 'POST':
        company_name = request.form['companyName']
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('products.db')
        c = conn.cursor()
        c.execute('''
            SELECT id, password FROM seller_registration
            WHERE company_name = ? AND email = ?
        ''', (company_name, email))
        user = c.fetchone()
        conn.close()

        if user:
            user_id, stored_password = user
            if stored_password == password:
                session['user_id'] = user_id
                flash('Login successful!', 'success')
                return redirect(url_for('seller'))
            else:
                flash('Invalid password.', 'error')
        else:
            flash('Invalid credentials.', 'error')

        return redirect(request.url)

    return render_template('seller_login.html')


@app.route('/admin_login', methods=['POST'])
def admin_login():
    username = request.form['username']
    password = request.form['password']

    if username == 'shri aigal@admin' and password == 'shri aigal':
        session['admin_logged_in'] = True
        flash('Login successful!', 'success')
    else:
        flash('Invalid username or password.', 'danger')

    return redirect(url_for('admin'))


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin'))


# Admin dashboard
@app.route('/admin')
def admin():
    return render_template('admin.html')


# Manage companies
@app.route('/manage_companies')
def manage_companies():
    conn = sqlite3.connect('products.db')
    c = conn.cursor()
    c.execute('SELECT * FROM seller_registration')
    companies = c.fetchall()
    conn.close()
    return render_template('manage_companies.html', companies=companies)


# Manage products
@app.route('/manage_products')
def manage_products():
    conn = sqlite3.connect('products.db')
    c = conn.cursor()
    c.execute('''
    SELECT p.id, p.product_name, p.quantity, p.price, p.date, 
           s.company_name, s.company_no, s.email
    FROM product p
    JOIN seller_registration s ON p.seller_id = s.id
''')

    products = c.fetchall()
    conn.close()
    return render_template('manage_products.html', products=products)


# Delete company
@app.route('/delete_company/<int:id>')
def delete_company(id):
    conn = sqlite3.connect('products.db')
    conn.execute('PRAGMA foreign_keys = ON')
    c = conn.cursor()
    c.execute('DELETE FROM seller_registration WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Company deleted successfully!')
    return redirect(url_for('manage_companies'))


# Delete product
@app.route('/delete_product/<int:id>')
def delete_product(id):
    conn = sqlite3.connect('products.db')
    c = conn.cursor()
    c.execute('DELETE FROM product WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Product deleted successfully!')
    return redirect(url_for('manage_products'))


# Edit company
@app.route('/edit_company/<int:id>', methods=['GET', 'POST'])
def edit_company(id):
    conn = sqlite3.connect('products.db')
    c = conn.cursor()
    if request.method == 'POST':
        company_name = request.form['company_name']
        company_no = request.form['company_no']
        email = request.form['email']
        gst_no = request.form['gst_no']
        phone_no = request.form['phone_no']
        c.execute('''
            UPDATE seller_registration 
            SET company_name=?, company_no=?, email=?, gst_no=?, phone_no=?
            WHERE id=?
        ''', (company_name, company_no, email, gst_no, phone_no, id))
        conn.commit()
        conn.close()
        flash('Company updated successfully!')
        return redirect(url_for('manage_companies'))
    else:
        c.execute('SELECT * FROM seller_registration WHERE id = ?', (id,))
        company = c.fetchone()
        conn.close()
        return render_template('edit_company.html', company=company)


# Edit product
@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    conn = sqlite3.connect('products.db')
    c = conn.cursor()
    if request.method == 'POST':
        product_name = request.form['product_name']
        quantity = request.form['quantity']
        price = request.form['price']
        date = request.form['date']
        c.execute('''
            UPDATE product 
            SET product_name=?, quantity=?, price=?, date=?
            WHERE id=?
        ''', (product_name, quantity, price, date, id))
        conn.commit()
        conn.close()
        flash('Product updated successfully!')
        return redirect(url_for('manage_products'))
    else:
        c.execute('SELECT * FROM product WHERE id = ?', (id,))
        product = c.fetchone()
        conn.close()
        return render_template('edit_product.html', product=product)


# API updates
@app.route('/update_product/<int:id>', methods=['POST'])
def update_product(id):
    data = request.get_json()
    conn = sqlite3.connect('products.db')
    c = conn.cursor()
    c.execute('''
        UPDATE product
        SET product_name = ?, quantity = ?, price = ?, date = ?
        WHERE id = ?
    ''', (data['product_name'], data['quantity'], data['price'], data['date'], id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/update_company/<int:id>', methods=['POST'])
def update_company(id):
    data = request.get_json()
    conn = sqlite3.connect('products.db')
    c = conn.cursor()
    c.execute('''
        UPDATE seller_registration 
        SET company_name = ?, company_no = ?, email = ?, gst_no = ?, phone_no = ?
        WHERE id = ?
    ''', (data['company_name'], data['company_no'], data['email'], data['gst_no'], data['phone_no'], id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

