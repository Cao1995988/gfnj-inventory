#!/usr/bin/env python3
"""共福农机库存管理系统 - Flask 应用"""

import json
import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'gfnj-secret-key-2026-fixed')
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.db')


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")

    db.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        display_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'clerk',
        enabled INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        address TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT DEFAULT '',
        spec TEXT DEFAULT '',
        unit TEXT DEFAULT '个',
        purchase_price REAL DEFAULT 0,
        sale_price REAL DEFAULT 0,
        stock REAL DEFAULT 0,
        safety_stock REAL DEFAULT 0,
        supplier_id INTEGER,
        barcodes TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    );

    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT UNIQUE NOT NULL,
        customer_name TEXT DEFAULT '',
        customer_phone TEXT DEFAULT '',
        method TEXT DEFAULT 'cash',
        total REAL DEFAULT 0,
        paid REAL DEFAULT 0,
        status TEXT DEFAULT 'paid',
        notes TEXT DEFAULT '',
        operator TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sales(id)
    );

    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT UNIQUE NOT NULL,
        supplier_id INTEGER,
        supplier_name TEXT DEFAULT '',
        total REAL DEFAULT 0,
        notes TEXT DEFAULT '',
        operator TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    );

    CREATE TABLE IF NOT EXISTS purchase_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (purchase_id) REFERENCES purchases(id)
    );

    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT DEFAULT '',
        total_debt REAL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    );

    CREATE TABLE IF NOT EXISTS credit_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        customer_name TEXT NOT NULL,
        amount REAL NOT NULL,
        notes TEXT DEFAULT '',
        operator TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    );

    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_table TEXT NOT NULL,
        target_id INTEGER,
        action TEXT NOT NULL,
        op TEXT NOT NULL,
        user_id INTEGER,
        user_name TEXT DEFAULT '',
        before_data TEXT,
        after_data TEXT,
        order_no TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    );
    ''')

    # Check if data already exists
    cur = db.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] > 0:
        db.close()
        return

    # Load seed data from API JSON files
    api_dir = '/tmp'
    seed_users = []
    seed_products = []
    seed_logs = []
    seed_customers = []

    try:
        with open(os.path.join(api_dir, 'api_users.json')) as f:
            data = json.load(f)
            seed_users = data.get('data', [])
    except Exception:
        pass

    try:
        with open(os.path.join(api_dir, 'api_products.json')) as f:
            data = json.load(f)
            seed_products = data.get('data', [])
    except Exception:
        pass

    try:
        with open(os.path.join(api_dir, 'api_logs.json')) as f:
            data = json.load(f)
            seed_logs = data.get('data', [])
    except Exception:
        pass

    try:
        with open(os.path.join(api_dir, 'api_customers.json')) as f:
            data = json.load(f)
            seed_customers = data.get('data', [])
    except Exception:
        pass

    # Insert users
    for u in seed_users:
        db.execute(
            "INSERT OR IGNORE INTO users (id, username, password, display_name, role, enabled, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (u['id'], u['username'], '', u['display_name'], u['role'], u['enabled'], u['created_at'])
        )
    # Update passwords: owner -> gfnj@2026, clerk -> 123456
    db.execute("UPDATE users SET password = 'gfnj@2026' WHERE username = 'owner'")
    db.execute("UPDATE users SET password = '123456' WHERE username = 'clerk'")
    # Other users get default password
    db.execute("UPDATE users SET password = '123456' WHERE password = ''")

    # Insert products
    for p in seed_products:
        db.execute(
            "INSERT OR IGNORE INTO products (id, code, name, category, spec, unit, purchase_price, sale_price, stock, safety_stock, supplier_id, barcodes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (p['id'], p['code'], p['name'], p.get('category', ''), p.get('spec', ''), p.get('unit', '个'),
             p.get('purchase_price', 0), p.get('sale_price', 0), p.get('stock', 0), p.get('safety_stock', 0),
             p.get('supplier_id'), p.get('barcodes', ''), p.get('created_at', ''), p.get('updated_at', ''))
        )

    # Insert customers
    for c in seed_customers:
        db.execute(
            "INSERT OR IGNORE INTO customers (id, name, phone, total_debt, created_at) VALUES (?, ?, ?, ?, ?)",
            (c['id'], c['name'], c.get('phone', ''), c.get('total_debt', 0), c.get('created_at', ''))
        )

    # Insert logs
    for l in seed_logs:
        db.execute(
            "INSERT OR IGNORE INTO logs (id, target_table, target_id, action, op, user_id, user_name, before_data, after_data, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (l['id'], l.get('target_table', ''), l.get('target_id'), l.get('action', ''), l.get('op', ''),
             l.get('user_id'), l.get('user_name', ''), l.get('before_data'), l.get('after_data'), l.get('created_at', ''))
        )

    db.commit()
    db.close()


# ---------- Auth helpers ----------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'ok': False, 'msg': '请先登录'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


def owner_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'ok': False, 'msg': '请先登录'}), 401
            return redirect(url_for('login_page'))
        if session.get('role') != 'owner':
            if request.path.startswith('/api/'):
                return jsonify({'ok': False, 'msg': '仅店长可操作'}), 403
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def add_log(target_table, target_id, action, before=None, after=None, order_no=''):
    db = get_db()
    db.execute(
        "INSERT INTO logs (target_table, target_id, action, op, user_id, user_name, before_data, after_data, order_no) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (target_table, target_id, action, session.get('display_name', ''),
         session.get('user_id'), session.get('display_name', ''),
         json.dumps(before, ensure_ascii=False) if before else None,
         json.dumps(after, ensure_ascii=False) if after else None,
         order_no)
    )
    db.commit()


# ---------- Page routes ----------

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND enabled = 1",
            (username,)
        ).fetchone()
        if not user:
            return render_template('login.html', error='账号不存在或已停用')
        if user['password'] != password:
            return render_template('login.html', error='密码错误')
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['display_name'] = user['display_name']
        session['role'] = user['role']
        next_url = request.args.get('next', '/')
        return redirect(next_url)
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/')
@login_required
def index():
    return render_template('index.html',
                           user={'name': session['display_name'], 'role': session['role']})


@app.route('/products')
@login_required
def products():
    return render_template('products.html',
                           user={'name': session['display_name'], 'role': session['role']})


@app.route('/qrcodes')
@login_required
def qrcodes():
    return render_template('qrcodes.html',
                           user={'name': session['display_name'], 'role': session['role']})


@app.route('/scan')
@login_required
def scan():
    return render_template('scan.html',
                           user={'name': session['display_name'], 'role': session['role']})


@app.route('/sales')
@login_required
def sales():
    return render_template('sales.html',
                           user={'name': session['display_name'], 'role': session['role']})


@app.route('/purchases')
@login_required
def purchases():
    return render_template('purchases.html',
                           user={'name': session['display_name'], 'role': session['role']})


@app.route('/suppliers')
@login_required
def suppliers():
    return render_template('suppliers.html',
                           user={'name': session['display_name'], 'role': session['role']})


@app.route('/customers')
@login_required
def customers():
    return render_template('customers.html',
                           user={'name': session['display_name'], 'role': session['role']})



@app.route('/outbound')
@login_required
def outbound():
    return render_template('outbound.html',
                           user={'name': session['display_name'], 'role': session['role']})

@app.route('/api/outbounds', methods=['GET', 'POST'])
@login_required
def api_outbounds():
    db = get_db()
    if request.method == 'GET':
        rows = db.execute("""
            SELECT o.*, u.display_name as operator_name
            FROM outbounds o LEFT JOIN users u ON o.operator_id = u.id
            ORDER BY o.id DESC
        """).fetchall()
        return jsonify({'ok': True, 'data': [dict(r) for r in rows]})

    data = request.get_json()
    items = data.get('items', [])
    if not items:
        return jsonify({'ok': False, 'msg': '请添加出库明细'})

    order_no = gen_order_no('CK', 'outbounds')
    total = sum(item.get('subtotal', 0) for item in items)

    db.execute(
        "INSERT INTO outbounds (order_no, customer_name, customer_phone, total, notes, operator_id) VALUES (?,?,?,?,?,?)",
        (order_no, data.get('customer_name', ''), data.get('customer_phone', ''),
         total, data.get('notes', ''), session.get('user_id'))
    )
    outbound_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    for item in items:
        db.execute(
            "INSERT INTO outbound_items (outbound_id, product_id, quantity, price, subtotal) VALUES (?,?,?,?,?)",
            (outbound_id, item['product_id'], item.get('quantity', 0),
             item.get('price', 0), item.get('subtotal', 0))
        )
        db.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (item.get('quantity', 0), item['product_id'])
        )

    db.commit()
    add_log('outbounds', outbound_id, 'create', after={
        'order_no': order_no, 'items': items, 'total': total
    }, order_no=order_no)
    return jsonify({'ok': True, 'data': {'id': outbound_id, 'order_no': order_no}})

@app.route('/api/outbounds/<int:oid>', methods=['GET', 'DELETE'])
@login_required
def api_outbound(oid):
    db = get_db()
    outbound = db.execute("SELECT * FROM outbounds WHERE id = ?", (oid,)).fetchone()
    if not outbound:
        return jsonify({'ok': False, 'msg': '出库单不存在'}), 404

    if request.method == 'GET':
        outbound = dict(outbound)
        items = db.execute(
            "SELECT oi.*, p.name as product_name, p.code as product_code, p.unit FROM outbound_items oi JOIN products p ON oi.product_id = p.id WHERE oi.outbound_id = ?",
            (oid,)
        ).fetchall()
        outbound['items'] = [dict(it) for it in items]
        return jsonify({'ok': True, 'data': outbound})

    # DELETE: restore stock
    items = db.execute("SELECT * FROM outbound_items WHERE outbound_id = ?", (oid,)).fetchall()
    for item in items:
        db.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (item['quantity'], item['product_id']))
    db.execute("DELETE FROM outbounds WHERE id = ?", (oid,))
    db.commit()
    add_log('outbounds', oid, 'delete', before=dict(outbound), order_no=outbound['order_no'])
    return jsonify({'ok': True})

@app.route('/logs')
@login_required
def logs():
    return render_template('logs.html',
                           user={'name': session['display_name'], 'role': session['role']})


@app.route('/users')
@login_required
@owner_required
def users():
    return render_template('users.html',
                           user={'name': session['display_name'], 'role': session['role']})


# ---------- Product detail page (WeChat scan entry) ----------

@app.route('/p/<code>')
@login_required
def product_detail(code):
    db = get_db()
    p = db.execute("SELECT * FROM products WHERE code = ?", (code,)).fetchone()
    if not p:
        return redirect('/')
    return render_template('product_detail.html',
                           product=dict(p),
                           user={'name': session['display_name'], 'role': session['role']})


# ---------- API routes ----------

@app.route('/api/dashboard')
@login_required
def api_dashboard():
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')

    # Product count
    product_count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    # Low stock count
    low_stock = db.execute(
        "SELECT COUNT(*) FROM products WHERE stock <= safety_stock AND safety_stock > 0"
    ).fetchone()[0]

    # Today sales
    today_sales = db.execute(
        "SELECT COALESCE(SUM(total), 0) FROM sales WHERE date(created_at) = ?",
        (today,)
    ).fetchone()[0]

    # Total credit
    total_credit = db.execute(
        "SELECT COALESCE(SUM(total - paid), 0) FROM sales WHERE status = 'credit'"
    ).fetchone()[0]

    # Today in
    today_in = db.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM purchase_items pi JOIN purchases p ON pi.purchase_id = p.id WHERE date(p.created_at) = ?",
        (today,)
    ).fetchone()[0]

    # Today out
    today_out = db.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM sale_items si JOIN sales s ON si.sale_id = s.id WHERE date(s.created_at) = ?",
        (today,)
    ).fetchone()[0]

    # Stock list for chart
    stock_list = db.execute(
        "SELECT name, stock, unit FROM products ORDER BY stock DESC"
    ).fetchall()
    stock_data = [{'name': r['name'], 'stock': r['stock'], 'unit': r['unit']} for r in stock_list]

    return jsonify({
        'ok': True,
        'data': {
            'product_count': product_count,
            'low_stock': low_stock,
            'today_sales': today_sales,
            'total_credit': total_credit,
            'today_in': today_in,
            'today_out': today_out,
            'stock_list': stock_data,
        }
    })


@app.route('/api/products', methods=['GET', 'POST'])
@login_required
def api_products():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'msg': '请求数据无效'}), 400
        code = data.get('code', '').strip()
        name = data.get('name', '').strip()
        if not code or not name:
            return jsonify({'ok': False, 'msg': '编码和名称不能为空'}), 400

        # Check duplicate code
        existing = db.execute("SELECT id FROM products WHERE code = ?", (code,)).fetchone()
        if existing:
            return jsonify({'ok': False, 'msg': '编码已存在'}), 400

        db.execute(
            "INSERT INTO products (code, name, category, spec, unit, purchase_price, sale_price, stock, safety_stock, supplier_id, barcodes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (code, name, data.get('category', ''), data.get('spec', ''),
             data.get('unit', '个'), data.get('purchase_price', 0), data.get('sale_price', 0),
             data.get('stock', 0), data.get('safety_stock', 0),
             data.get('supplier_id'), data.get('barcodes', ''))
        )
        db.commit()
        new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        add_log('products', new_id, 'create', after={
            'code': code, 'name': name, 'stock': data.get('stock', 0)
        })
        return jsonify({'ok': True, 'data': {'id': new_id}})

    # GET: list products with optional search
    q = request.args.get('q', '').strip()
    low = request.args.get('low', '')
    sql = """
        SELECT p.*, s.name as supplier_name
        FROM products p
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (p.code LIKE ? OR p.name LIKE ? OR p.category LIKE ? OR p.barcodes LIKE ?)"
        like = f'%{q}%'
        params.extend([like, like, like, like])
    if low:
        sql += " AND p.stock <= p.safety_stock AND p.safety_stock > 0"
    sql += " ORDER BY p.id DESC"
    rows = db.execute(sql, params).fetchall()
    products = [dict(r) for r in rows]
    return jsonify({'ok': True, 'data': products})


@app.route('/api/products/<int:pid>', methods=['PUT', 'DELETE'])
@login_required
def api_product_by_id(pid):
    db = get_db()
    if request.method == 'DELETE':
        p = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        if not p:
            return jsonify({'ok': False, 'msg': '商品不存在'}), 404
        before = dict(p)
        db.execute("DELETE FROM products WHERE id = ?", (pid,))
        db.commit()
        add_log('products', pid, 'delete', before=before)
        return jsonify({'ok': True})

    if request.method == 'PUT':
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'msg': '请求数据无效'}), 400
        p = db.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        if not p:
            return jsonify({'ok': False, 'msg': '商品不存在'}), 404
        before = dict(p)
        db.execute(
            "UPDATE products SET code=?, name=?, category=?, spec=?, unit=?, purchase_price=?, sale_price=?, stock=?, safety_stock=?, supplier_id=?, barcodes=?, updated_at=datetime('now','localtime') WHERE id=?",
            (data.get('code', p['code']), data.get('name', p['name']),
             data.get('category', p['category']), data.get('spec', p['spec']),
             data.get('unit', p['unit']), data.get('purchase_price', p['purchase_price']),
             data.get('sale_price', p['sale_price']), data.get('stock', p['stock']),
             data.get('safety_stock', p['safety_stock']), data.get('supplier_id'),
             data.get('barcodes', p['barcodes']), pid)
        )
        db.commit()
        after = {
            'code': data.get('code', p['code']),
            'name': data.get('name', p['name']),
            'stock': data.get('stock', p['stock']),
            'barcodes': data.get('barcodes', p['barcodes'])
        }
        add_log('products', pid, 'update', before=before, after=after)
        return jsonify({'ok': True})

    return jsonify({'ok': False, 'msg': 'Method not allowed'}), 405


@app.route('/api/products/by-code/<path:code>')
@login_required
def api_product_by_code(code):
    db = get_db()
    # Try exact match first
    p = db.execute("SELECT * FROM products WHERE code = ?", (code,)).fetchone()
    if p:
        return jsonify({'ok': True, 'data': dict(p)})
    # Try barcode match
    p = db.execute(
        "SELECT * FROM products WHERE barcodes LIKE ?",
        (f'%{code}%',)
    ).fetchone()
    if p:
        return jsonify({'ok': True, 'data': dict(p)})
    return jsonify({'ok': False, 'msg': f'未找到编码 {code} 对应的商品'}), 404


@app.route('/api/suppliers', methods=['GET', 'POST'])
@login_required
def api_suppliers():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('name', '').strip():
            return jsonify({'ok': False, 'msg': '名称不能为空'}), 400
        db.execute(
            "INSERT INTO suppliers (name, contact, phone, address, notes) VALUES (?, ?, ?, ?, ?)",
            (data['name'].strip(), data.get('contact', ''), data.get('phone', ''),
             data.get('address', ''), data.get('notes', ''))
        )
        db.commit()
        new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        add_log('suppliers', new_id, 'create', after={'name': data['name'].strip()})
        return jsonify({'ok': True, 'data': {'id': new_id}})

    rows = db.execute("SELECT * FROM suppliers ORDER BY id DESC").fetchall()
    return jsonify({'ok': True, 'data': [dict(r) for r in rows]})


@app.route('/api/suppliers/<int:sid>', methods=['PUT', 'DELETE'])
@login_required
def api_supplier_by_id(sid):
    db = get_db()
    if request.method == 'DELETE':
        s = db.execute("SELECT * FROM suppliers WHERE id = ?", (sid,)).fetchone()
        if not s:
            return jsonify({'ok': False, 'msg': '供应商不存在'}), 404
        before = dict(s)
        db.execute("DELETE FROM suppliers WHERE id = ?", (sid,))
        db.commit()
        add_log('suppliers', sid, 'delete', before=before)
        return jsonify({'ok': True})

    if request.method == 'PUT':
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'msg': '请求数据无效'}), 400
        s = db.execute("SELECT * FROM suppliers WHERE id = ?", (sid,)).fetchone()
        if not s:
            return jsonify({'ok': False, 'msg': '供应商不存在'}), 404
        before = dict(s)
        db.execute(
            "UPDATE suppliers SET name=?, contact=?, phone=?, address=?, notes=? WHERE id=?",
            (data.get('name', s['name']), data.get('contact', s['contact']),
             data.get('phone', s['phone']), data.get('address', s['address']),
             data.get('notes', s['notes']), sid)
        )
        db.commit()
        add_log('suppliers', sid, 'update', before=before,
                after={'name': data.get('name', s['name'])})
        return jsonify({'ok': True})

    return jsonify({'ok': False, 'msg': 'Method not allowed'}), 405


@app.route('/api/customers', methods=['GET'])
@login_required
def api_customers():
    db = get_db()
    rows = db.execute(
        "SELECT c.*, COALESCE(SUM(cp.amount), 0) as total_paid FROM customers c LEFT JOIN credit_payments cp ON c.id = cp.customer_id GROUP BY c.id ORDER BY c.id DESC"
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        # total_debt = sum of unpaid credit sales
        debt = db.execute(
            "SELECT COALESCE(SUM(total - paid), 0) FROM sales WHERE status = 'credit' AND customer_name = ?",
            (r['name'],)
        ).fetchone()[0]
        d['total_debt'] = debt
        result.append(d)
    return jsonify({'ok': True, 'data': result})


@app.route('/api/customers/<int:cid>/settle', methods=['POST'])
@login_required
def api_customer_settle(cid):
    db = get_db()
    data = request.get_json()
    if not data:
        return jsonify({'ok': False, 'msg': '请求数据无效'}), 400
    amount = float(data.get('amount', 0))
    if amount <= 0:
        return jsonify({'ok': False, 'msg': '还款金额必须大于0'}), 400
    c = db.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()
    if not c:
        return jsonify({'ok': False, 'msg': '客户不存在'}), 404
    db.execute(
        "INSERT INTO credit_payments (customer_id, customer_name, amount, notes, operator) VALUES (?, ?, ?, ?, ?)",
        (cid, c['name'], amount, data.get('notes', ''), session.get('display_name', ''))
    )
    db.commit()
    add_log('credits', cid, 'settle', after={
        'customer': c['name'], 'amount': amount, 'notes': data.get('notes', '')
    })
    return jsonify({'ok': True, 'data': {'id': db.execute("SELECT last_insert_rowid()").fetchone()[0]}})


@app.route('/api/customers/<int:cid>/history', methods=['GET'])
@login_required
def api_customer_history(cid):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM credit_payments WHERE customer_id = ? ORDER BY created_at DESC",
        (cid,)
    ).fetchall()
    return jsonify({'ok': True, 'data': [dict(r) for r in rows]})


@app.route('/api/logs')
@login_required
def api_logs():
    db = get_db()
    table = request.args.get('table', '').strip()
    action = request.args.get('action', '').strip()
    date = request.args.get('date', '').strip()
    sql = "SELECT * FROM logs WHERE 1=1"
    params = []
    if table:
        sql += " AND target_table = ?"
        params.append(table)
    if action:
        sql += " AND action = ?"
        params.append(action)
    if date:
        sql += " AND date(created_at) = ?"
        params.append(date)
    sql += " ORDER BY created_at DESC LIMIT 500"
    rows = db.execute(sql, params).fetchall()
    return jsonify({'ok': True, 'data': [dict(r) for r in rows]})


@app.route('/api/users', methods=['GET', 'POST'])
@login_required
@owner_required
def api_users():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'msg': '请求数据无效'}), 400
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        if not username or not password:
            return jsonify({'ok': False, 'msg': '账号和密码不能为空'}), 400
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            return jsonify({'ok': False, 'msg': '账号已存在'}), 400
        db.execute(
            "INSERT INTO users (username, password, display_name, role, enabled) VALUES (?, ?, ?, ?, ?)",
            (username, password, data.get('display_name', username), data.get('role', 'clerk'), data.get('enabled', 1))
        )
        db.commit()
        new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        add_log('users', new_id, 'create', after={'username': username, 'role': data.get('role', 'clerk')})
        return jsonify({'ok': True, 'data': {'id': new_id}})

    rows = db.execute("SELECT id, username, display_name, role, enabled, created_at FROM users ORDER BY id").fetchall()
    return jsonify({'ok': True, 'data': [dict(r) for r in rows]})


@app.route('/api/users/<int:uid>', methods=['PUT', 'DELETE'])
@login_required
def api_user_by_id(uid):
    db = get_db()
    if request.method == 'DELETE':
        u = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if not u:
            return jsonify({'ok': False, 'msg': '用户不存在'}), 404
        if u['username'] == 'owner':
            return jsonify({'ok': False, 'msg': '不能删除店长账号'}), 400
        before = {'id': u['id'], 'username': u['username'], 'display_name': u['display_name'], 'role': u['role']}
        db.execute("DELETE FROM users WHERE id = ?", (uid,))
        db.commit()
        add_log('users', uid, 'delete', before=before)
        return jsonify({'ok': True})

    if request.method == 'PUT':
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'msg': '请求数据无效'}), 400
        u = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        if not u:
            return jsonify({'ok': False, 'msg': '用户不存在'}), 404
        before = {'id': u['id'], 'username': u['username'], 'display_name': u['display_name'], 'role': u['role'], 'enabled': u['enabled']}
        updates = []
        params = []
        for field in ['display_name', 'role', 'enabled']:
            if field in data:
                updates.append(f"{field} = ?")
                params.append(data[field])
        if data.get('password', '').strip():
            updates.append("password = ?")
            params.append(data['password'].strip())
        if updates:
            params.append(uid)
            db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
            db.commit()
        after = {k: data.get(k, u[k]) for k in ['display_name', 'role', 'enabled']}
        add_log('users', uid, 'update', before=before, after=after)
        return jsonify({'ok': True})

    return jsonify({'ok': False, 'msg': 'Method not allowed'}), 405


@app.route('/api/sales', methods=['GET', 'POST'])
@login_required
def api_sales():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'msg': '请求数据无效'}), 400
        items = data.get('items', [])
        if not items:
            return jsonify({'ok': False, 'msg': '请至少添加一个商品'}), 400

        customer_name = data.get('customer_name', '').strip()
        customer_phone = data.get('customer_phone', '').strip()
        method = data.get('method', 'cash')
        paid = float(data.get('paid', 0))
        notes = data.get('notes', '')

        # Generate order number
        today = datetime.now().strftime('%Y%m%d')
        count = db.execute(
            "SELECT COUNT(*) FROM sales WHERE order_no LIKE ?",
            (f'SALE-{today}-%',)
        ).fetchone()[0]
        order_no = f'SALE-{today}-{count + 1:04d}'

        total = 0
        for item in items:
            product_id = item.get('product_id')
            product_name = item.get('product_name', '')
            quantity = float(item.get('quantity', 0))
            price = float(item.get('price', 0))
            subtotal = quantity * price
            total += subtotal

        status = 'credit' if method == 'credit' and paid < total else 'paid'

        db.execute(
            "INSERT INTO sales (order_no, customer_name, customer_phone, method, total, paid, status, notes, operator) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (order_no, customer_name, customer_phone, method, total, paid, status, notes, session.get('display_name', ''))
        )
        sale_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        for item in items:
            product_id = item.get('product_id')
            product_name = item.get('product_name', '')
            quantity = float(item.get('quantity', 0))
            price = float(item.get('price', 0))
            subtotal = quantity * price
            db.execute(
                "INSERT INTO sale_items (sale_id, product_id, product_name, quantity, price, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                (sale_id, product_id, product_name, quantity, price, subtotal)
            )
            # Deduct stock
            db.execute(
                "UPDATE products SET stock = stock - ?, updated_at = datetime('now','localtime') WHERE id = ?",
                (quantity, product_id)
            )

        # Track customer for credit sales
        if method == 'credit' and customer_name:
            existing_customer = db.execute(
                "SELECT id FROM customers WHERE name = ?",
                (customer_name,)
            ).fetchone()
            if not existing_customer:
                db.execute(
                    "INSERT INTO customers (name, phone, total_debt) VALUES (?, ?, ?)",
                    (customer_name, customer_phone, total - paid)
                )

        db.commit()
        add_log('sales', sale_id, 'create', after={
            'order_no': order_no, 'total': total, 'paid': paid, 'method': method, 'items': len(items)
        }, order_no=order_no)
        return jsonify({'ok': True, 'data': {'id': sale_id, 'order_no': order_no}})

    # GET: list sales
    rows = db.execute("SELECT * FROM sales ORDER BY created_at DESC").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        items = db.execute("SELECT * FROM sale_items WHERE sale_id = ?", (r['id'],)).fetchall()
        d['items'] = [dict(i) for i in items]
        result.append(d)
    return jsonify({'ok': True, 'data': result})


@app.route('/api/sales/<int:sid>', methods=['GET', 'DELETE'])
@login_required
def api_sale_by_id(sid):
    db = get_db()
    if request.method == 'DELETE':
        s = db.execute("SELECT * FROM sales WHERE id = ?", (sid,)).fetchone()
        if not s:
            return jsonify({'ok': False, 'msg': '销售单不存在'}), 404
        before = dict(s)
        # Restore stock
        items = db.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sid,)).fetchall()
        for item in items:
            db.execute(
                "UPDATE products SET stock = stock + ?, updated_at = datetime('now','localtime') WHERE id = ?",
                (item['quantity'], item['product_id'])
            )
        db.execute("DELETE FROM sale_items WHERE sale_id = ?", (sid,))
        db.execute("DELETE FROM sales WHERE id = ?", (sid,))
        db.commit()
        add_log('sales', sid, 'delete', before=before, order_no=before['order_no'])
        return jsonify({'ok': True})

    s = db.execute("SELECT * FROM sales WHERE id = ?", (sid,)).fetchone()
    if not s:
        return jsonify({'ok': False, 'msg': '销售单不存在'}), 404
    d = dict(s)
    items = db.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sid,)).fetchall()
    d['items'] = [dict(i) for i in items]
    return jsonify({'ok': True, 'data': d})


@app.route('/api/purchases', methods=['GET', 'POST'])
@login_required
def api_purchases():
    db = get_db()
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'msg': '请求数据无效'}), 400
        items = data.get('items', [])
        if not items:
            return jsonify({'ok': False, 'msg': '请至少添加一个商品'}), 400

        supplier_id = data.get('supplier_id')
        supplier_name = data.get('supplier_name', '')
        notes = data.get('notes', '')

        # Generate order number
        today = datetime.now().strftime('%Y%m%d')
        count = db.execute(
            "SELECT COUNT(*) FROM purchases WHERE order_no LIKE ?",
            (f'PUR-{today}-%',)
        ).fetchone()[0]
        order_no = f'PUR-{today}-{count + 1:04d}'

        total = 0
        for item in items:
            quantity = float(item.get('quantity', 0))
            price = float(item.get('price', 0))
            total += quantity * price

        db.execute(
            "INSERT INTO purchases (order_no, supplier_id, supplier_name, total, notes, operator) VALUES (?, ?, ?, ?, ?, ?)",
            (order_no, supplier_id, supplier_name, total, notes, session.get('display_name', ''))
        )
        purchase_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        for item in items:
            product_id = item.get('product_id')
            product_name = item.get('product_name', '')
            quantity = float(item.get('quantity', 0))
            price = float(item.get('price', 0))
            subtotal = quantity * price
            db.execute(
                "INSERT INTO purchase_items (purchase_id, product_id, product_name, quantity, price, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
                (purchase_id, product_id, product_name, quantity, price, subtotal)
            )
            # Add stock
            db.execute(
                "UPDATE products SET stock = stock + ?, updated_at = datetime('now','localtime') WHERE id = ?",
                (quantity, product_id)
            )

        db.commit()
        add_log('purchases', purchase_id, 'create', after={
            'order_no': order_no, 'total': total, 'items': len(items)
        }, order_no=order_no)
        return jsonify({'ok': True, 'data': {'id': purchase_id, 'order_no': order_no}})

    # GET
    rows = db.execute("SELECT * FROM purchases ORDER BY created_at DESC").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        items = db.execute("SELECT * FROM purchase_items WHERE purchase_id = ?", (r['id'],)).fetchall()
        d['items'] = [dict(i) for i in items]
        result.append(d)
    return jsonify({'ok': True, 'data': result})


@app.route('/api/purchases/<int:pid>', methods=['GET', 'DELETE'])
@login_required
def api_purchase_by_id(pid):
    db = get_db()
    if request.method == 'DELETE':
        p = db.execute("SELECT * FROM purchases WHERE id = ?", (pid,)).fetchone()
        if not p:
            return jsonify({'ok': False, 'msg': '入库单不存在'}), 404
        before = dict(p)
        # Restore stock
        items = db.execute("SELECT * FROM purchase_items WHERE purchase_id = ?", (pid,)).fetchall()
        for item in items:
            db.execute(
                "UPDATE products SET stock = stock - ?, updated_at = datetime('now','localtime') WHERE id = ?",
                (item['quantity'], item['product_id'])
            )
        db.execute("DELETE FROM purchase_items WHERE purchase_id = ?", (pid,))
        db.execute("DELETE FROM purchases WHERE id = ?", (pid,))
        db.commit()
        add_log('purchases', pid, 'delete', before=before, order_no=before['order_no'])
        return jsonify({'ok': True})

    p = db.execute("SELECT * FROM purchases WHERE id = ?", (pid,)).fetchone()
    if not p:
        return jsonify({'ok': False, 'msg': '入库单不存在'}), 404
    d = dict(p)
    items = db.execute("SELECT * FROM purchase_items WHERE purchase_id = ?", (pid,)).fetchall()
    d['items'] = [dict(i) for i in items]
    return jsonify({'ok': True, 'data': d})


@app.route('/api/scan/stockmove', methods=['POST'])
@login_required
def api_scan_stockmove():
    db = get_db()
    data = request.get_json()
    if not data:
        return jsonify({'ok': False, 'msg': '请求数据无效'}), 400
    direction = data.get('direction', 'in')
    items = data.get('items', [])
    if not items:
        return jsonify({'ok': False, 'msg': '请至少添加一个商品'}), 400

    results = []
    for item in items:
        code = item.get('code', '').strip()
        quantity = float(item.get('quantity', 1))
        p = db.execute("SELECT * FROM products WHERE code = ?", (code,)).fetchone()
        if not p:
            results.append({'code': code, 'ok': False, 'msg': '商品不存在'})
            continue

        before_stock = p['stock']
        if direction == 'out':
            if p['stock'] < quantity:
                results.append({
                    'code': code, 'ok': False, 'msg': f'库存不足 (当前{p["stock"]})',
                    'name': p['name']
                })
                continue
            new_stock = p['stock'] - quantity
        else:
            new_stock = p['stock'] + quantity

        db.execute(
            "UPDATE products SET stock = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (new_stock, p['id'])
        )
        results.append({
            'code': code, 'ok': True,
            'name': p['name'], 'before': before_stock, 'after': new_stock
        })

        add_log('products', p['id'], 'update',
                before={'stock': before_stock, 'name': p['name']},
                after={'stock': new_stock, 'direction': direction, 'qty': quantity,
                       'name': p['name'],
                       'note': '扫码入库' if direction == 'in' else '扫码出库'})

    db.commit()
    return jsonify({
        'ok': True,
        'data': {
            'operator': session.get('display_name', ''),
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'results': results
        }
    })


# ---------- Error handlers ----------

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'ok': False, 'msg': '接口不存在'}), 404
    return render_template('404.html'), 404


# ---------- Main ----------

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
