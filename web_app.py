"""
Web版密码管理器，提供浏览器界面来管理密码
"""

import os
import io
import time
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from functools import wraps
from password_manager import PasswordManager
from exporter import CSVExporter

app = Flask(__name__)
app.secret_key = os.urandom(24)

DEFAULT_MASTER_PASSWORD = "000000"
DB_PATH = "password_manager/data/passwords.enc"
SESSION_TIMEOUT = 60

# 初始化密码管理器
pm = PasswordManager(DB_PATH)


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        
        login_time = session.get('login_time', 0)
        if time.time() - login_time > SESSION_TIMEOUT:
            session.clear()
            flash('登录已超时，请重新登录', 'error')
            return redirect(url_for('login'))
        
        session['login_time'] = time.time()
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    """首页 - 重定向到登录或主界面"""
    if session.get('authenticated'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    # 初始化数据库（如果不存在）
    pm.db.initialize_database(DEFAULT_MASTER_PASSWORD)

    if request.method == 'POST':
        password = request.form.get('password', '')

        if pm.authenticate(password):
            session['authenticated'] = True
            session['login_time'] = time.time()
            flash('登录成功！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(f'密码错误。初始密码为 {DEFAULT_MASTER_PASSWORD}', 'error')

    return render_template('login.html', default_password=DEFAULT_MASTER_PASSWORD)


@app.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """主界面 - 显示所有产品"""
    products = pm.list_products()
    return render_template('dashboard.html', products=products)


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_password():
    """添加密码页面"""
    if request.method == 'POST':
        product_name = request.form.get('product_name', '').strip()
        account = request.form.get('account', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        remark = request.form.get('remark', '').strip()

        if not product_name or not account or not password:
            flash('产品名称、账号和密码为必填项', 'error')
            return render_template('add_password.html')

        if pm.add_password(product_name, account, password, email, phone, remark):
            flash(f'密码 "{product_name}" 添加成功！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('添加失败，产品名称可能已存在', 'error')

    return render_template('add_password.html')


@app.route('/view/<product_name>')
@login_required
def view_password(product_name):
    """查看密码详情"""
    product_info = pm.get_password(product_name)
    if product_info:
        return render_template('view_password.html', name=product_name, info=product_info)
    else:
        flash('产品不存在', 'error')
        return redirect(url_for('dashboard'))


@app.route('/edit/<product_name>', methods=['GET', 'POST'])
@login_required
def edit_password(product_name):
    """编辑密码页面"""
    product_info = pm.get_password(product_name)
    if not product_info:
        flash('产品不存在', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        account = request.form.get('account', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        remark = request.form.get('remark', '').strip()

        # 只更新非空字段
        update_data = {}
        if account:
            update_data['account'] = account
        if password:
            update_data['password'] = password
        if email:
            update_data['email'] = email
        if phone:
            update_data['phone'] = phone
        if remark:
            update_data['remark'] = remark

        if update_data:
            if pm.update_password(product_name, **update_data):
                flash('密码更新成功！', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('更新失败', 'error')
        else:
            flash('没有更改任何内容', 'info')

    return render_template('edit_password.html', name=product_name, info=product_info)


@app.route('/delete/<product_name>', methods=['POST'])
@login_required
def delete_password(product_name):
    """删除密码"""
    if pm.delete_password(product_name):
        flash(f'密码 "{product_name}" 已删除', 'success')
    else:
        flash('删除失败', 'error')
    return redirect(url_for('dashboard'))


@app.route('/export')
@login_required
def export_csv():
    """导出CSV文件"""
    exporter = CSVExporter(pm)

    # 创建内存中的CSV文件
    output = io.StringIO()
    data = pm.get_all_products()

    if data:
        import csv
        fieldnames = ['产品名称', '账号', '密码', '邮箱', '手机号', '备注']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for product_name, info in data.items():
            writer.writerow({
                '产品名称': product_name,
                '账号': info.get('account', ''),
                '密码': info.get('password', ''),
                '邮箱': info.get('email', ''),
                '手机号': info.get('phone', ''),
                '备注': info.get('remark', '')
            })

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='passwords.csv'
    )


@app.route('/import', methods=['GET', 'POST'])
@login_required
def import_csv():
    """批量导入CSV文件"""
    if request.method == 'POST':
        # 检查是否有文件
        if 'csv_file' not in request.files:
            flash('请选择CSV文件', 'error')
            return redirect(request.url)

        file = request.files['csv_file']

        # 检查文件名
        if file.filename == '':
            flash('请选择CSV文件', 'error')
            return redirect(request.url)

        if not file.filename.endswith('.csv'):
            flash('请上传CSV格式的文件', 'error')
            return redirect(request.url)

        try:
            # 读取CSV文件
            import csv
            stream = io.StringIO(file.stream.read().decode('utf-8-sig'))
            reader = csv.DictReader(stream)

            # 支持的字段名（兼容中英文）
            field_mapping = {
                '产品名称': 'product_name',
                '账号': 'account',
                '密码': 'password',
                '邮箱': 'email',
                '手机号': 'phone',
                '备注': 'remark',
                # 英文兼容
                'product_name': 'product_name',
                'account': 'account',
                'password': 'password',
                'email': 'email',
                'phone': 'phone',
                'remark': 'remark'
            }

            success_count = 0
            skip_count = 0
            error_count = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):  # 从第2行开始（第1行是表头）
                try:
                    # 提取数据
                    product_name = row.get('产品名称', '').strip() or row.get('product_name', '').strip()
                    account = row.get('账号', '').strip() or row.get('account', '').strip()
                    password = row.get('密码', '') or row.get('password', '')
                    email = row.get('邮箱', '').strip() or row.get('email', '').strip()
                    phone = row.get('手机号', '').strip() or row.get('phone', '').strip()
                    remark = row.get('备注', '').strip() or row.get('remark', '').strip()

                    # 验证必填字段
                    if not product_name or not account or not password:
                        error_count += 1
                        errors.append(f'第{row_num}行: 产品名称、账号、密码为必填项')
                        continue

                    # 检查产品是否已存在
                    if pm.get_password(product_name):
                        skip_count += 1
                        errors.append(f'第{row_num}行: 产品 "{product_name}" 已存在，已跳过')
                        continue

                    # 添加密码
                    if pm.add_password(product_name, account, password, email, phone, remark):
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(f'第{row_num}行: 添加失败')

                except Exception as e:
                    error_count += 1
                    errors.append(f'第{row_num}行: 处理时出错 - {str(e)}')

            # 显示导入结果
            if success_count > 0:
                flash(f'成功导入 {success_count} 条密码记录', 'success')
            if skip_count > 0:
                flash(f'跳过 {skip_count} 条已存在的记录', 'info')
            if error_count > 0:
                flash(f'导入失败 {error_count} 条记录', 'error')
                # 显示前5个错误
                for error in errors[:5]:
                    flash(error, 'error')

            return redirect(url_for('dashboard'))

        except Exception as e:
            flash(f'读取CSV文件失败: {str(e)}', 'error')
            return redirect(request.url)

    return render_template('import_passwords.html')


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """更改主密码页面"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # 验证当前密码
        if not pm.authenticate(current_password):
            flash('当前密码错误', 'error')
            return render_template('change_password.html')

        if new_password != confirm_password:
            flash('两次输入的新密码不一致', 'error')
            return render_template('change_password.html')

        if not new_password:
            flash('新密码不能为空', 'error')
            return render_template('change_password.html')

        if pm.change_master_password(new_password):
            session['master_password'] = new_password
            flash('主密码更改成功！请牢记新密码', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('密码更改失败', 'error')

    return render_template('change_password.html')


# 创建模板目录和HTML模板
def create_templates():
    """创建HTML模板文件"""
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)

    # 基础模板
    base_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}密码管理器{% endblock %}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
            text-align: center;
        }
        h2 {
            color: #555;
            margin-bottom: 20px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        input[type="text"],
        input[type="password"],
        textarea {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus,
        input[type="password"]:focus,
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        textarea {
            resize: vertical;
            min-height: 80px;
        }
        .btn {
            display: inline-block;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .btn-secondary {
            background: #f0f0f0;
            color: #555;
        }
        .btn-secondary:hover {
            background: #e0e0e0;
        }
        .btn-danger {
            background: #e74c3c;
            color: white;
        }
        .btn-danger:hover {
            background: #c0392b;
        }
        .btn-success {
            background: #27ae60;
            color: white;
        }
        .btn-success:hover {
            background: #219a52;
        }
        .btn-group {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        .flash-messages {
            margin-bottom: 20px;
        }
        .flash {
            padding: 12px 15px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .flash.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .flash.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .flash.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .product-list {
            list-style: none;
        }
        .product-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid #eee;
            transition: background 0.2s;
        }
        .product-item:hover {
            background: #f8f9fa;
        }
        .product-name {
            font-weight: 500;
            color: #333;
            font-size: 18px;
        }
        .product-actions {
            display: flex;
            gap: 8px;
        }
        .btn-small {
            padding: 6px 12px;
            font-size: 14px;
        }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #888;
        }
        .info-row {
            display: flex;
            padding: 15px 0;
            border-bottom: 1px solid #eee;
        }
        .info-label {
            width: 120px;
            color: #888;
            font-weight: 500;
        }
        .info-value {
            flex: 1;
            color: #333;
            word-break: break-all;
        }
        .header-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .password-hint {
            text-align: center;
            color: #888;
            margin-top: 15px;
            font-size: 14px;
        }
        .required::after {
            content: ' *';
            color: #e74c3c;
        }
        .top-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
        }
        .nav-links {
            display: flex;
            gap: 15px;
        }
        .nav-links a {
            color: #667eea;
            text-decoration: none;
        }
        .nav-links a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>'''

    # 登录页面
    login_html = '''{% extends "base.html" %}

{% block title %}登录 - 密码管理器{% endblock %}

{% block content %}
<div class="card" style="max-width: 400px; margin: 100px auto;">
    <h1>🔐 密码管理器</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
        <div class="flash-messages">
            {% for category, message in messages %}
            <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        </div>
        {% endif %}
    {% endwith %}

    <form method="POST">
        <div class="form-group">
            <label for="password">主密码</label>
            <input type="password" id="password" name="password" required autofocus>
        </div>
        <button type="submit" class="btn btn-primary" style="width: 100%;">登录</button>
    </form>

    <p class="password-hint">初始密码: {{ default_password }}</p>
</div>
{% endblock %}'''

    # 主界面
    dashboard_html = '''{% extends "base.html" %}

{% block title %}密码列表 - 密码管理器{% endblock %}

{% block content %}
<div class="card">
    <div class="top-bar">
        <h2>📋 密码列表</h2>
        <div class="nav-links">
            <a href="{{ url_for('export_csv') }}">📥 导出CSV</a>
            <a href="{{ url_for('change_password') }}">🔑 更改主密码</a>
            <a href="{{ url_for('logout') }}">退出</a>
        </div>
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
        <div class="flash-messages">
            {% for category, message in messages %}
            <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        </div>
        {% endif %}
    {% endwith %}

    <div class="header-actions">
        <span style="color: #888;">共 {{ products|length }} 个产品</span>
        <div style="display: flex; gap: 10px;">
            <a href="{{ url_for('import_csv') }}" class="btn btn-success">📥 批量导入</a>
            <a href="{{ url_for('add_password') }}" class="btn btn-primary">➕ 添加密码</a>
        </div>
    </div>

    {% if products %}
    <ul class="product-list">
        {% for product in products %}
        <li class="product-item">
            <span class="product-name">{{ product }}</span>
            <div class="product-actions">
                <a href="{{ url_for('view_password', product_name=product) }}" class="btn btn-secondary btn-small">查看</a>
                <a href="{{ url_for('edit_password', product_name=product) }}" class="btn btn-primary btn-small">编辑</a>
                <form method="POST" action="{{ url_for('delete_password', product_name=product) }}" style="display: inline;" onsubmit="return confirm('确定要删除 \"{{ product }}\" 吗？');">
                    <button type="submit" class="btn btn-danger btn-small">删除</button>
                </form>
            </div>
        </li>
        {% endfor %}
    </ul>
    {% else %}
    <div class="empty-state">
        <p>暂无密码记录</p>
        <p style="margin-top: 10px;">点击上方按钮添加第一个密码</p>
    </div>
    {% endif %}
</div>
{% endblock %}'''

    # 添加密码页面
    add_html = '''{% extends "base.html" %}

{% block title %}添加密码 - 密码管理器{% endblock %}

{% block content %}
<div class="card">
    <h2>➕ 添加新密码</h2>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
        <div class="flash-messages">
            {% for category, message in messages %}
            <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        </div>
        {% endif %}
    {% endwith %}

    <form method="POST">
        <div class="form-group">
            <label for="product_name" class="required">产品名称</label>
            <input type="text" id="product_name" name="product_name" required placeholder="例如：Gmail、微信">
        </div>

        <div class="form-group">
            <label for="account" class="required">账号</label>
            <input type="text" id="account" name="account" required placeholder="例如：user@gmail.com">
        </div>

        <div class="form-group">
            <label for="password" class="required">密码</label>
            <input type="text" id="password" name="password" required>
        </div>

        <div class="form-group">
            <label for="email">邮箱</label>
            <input type="text" id="email" name="email" placeholder="可选">
        </div>

        <div class="form-group">
            <label for="phone">手机号</label>
            <input type="text" id="phone" name="phone" placeholder="可选">
        </div>

        <div class="form-group">
            <label for="remark">备注</label>
            <textarea id="remark" name="remark" placeholder="可选"></textarea>
        </div>

        <div class="btn-group">
            <button type="submit" class="btn btn-primary">保存</button>
            <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">取消</a>
        </div>
    </form>
</div>
{% endblock %}'''

    # 查看密码页面
    view_html = '''{% extends "base.html" %}

{% block title %}{{ name }} - 密码详情{% endblock %}

{% block content %}
<div class="card">
    <h2>🔍 {{ name }}</h2>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
        <div class="flash-messages">
            {% for category, message in messages %}
            <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        </div>
        {% endif %}
    {% endwith %}

    <div class="info-row">
        <div class="info-label">产品名称</div>
        <div class="info-value">{{ name }}</div>
    </div>

    <div class="info-row">
        <div class="info-label">账号</div>
        <div class="info-value">{{ info.account }}</div>
    </div>

    <div class="info-row">
        <div class="info-label">密码</div>
        <div class="info-value" style="font-family: monospace; background: #f8f9fa; padding: 10px; border-radius: 4px;">{{ info.password }}</div>
    </div>

    {% if info.email %}
    <div class="info-row">
        <div class="info-label">邮箱</div>
        <div class="info-value">{{ info.email }}</div>
    </div>
    {% endif %}

    {% if info.phone %}
    <div class="info-row">
        <div class="info-label">手机号</div>
        <div class="info-value">{{ info.phone }}</div>
    </div>
    {% endif %}

    {% if info.remark %}
    <div class="info-row">
        <div class="info-label">备注</div>
        <div class="info-value">{{ info.remark }}</div>
    </div>
    {% endif %}

    <div class="btn-group">
        <a href="{{ url_for('edit_password', product_name=name) }}" class="btn btn-primary">编辑</a>
        <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">返回列表</a>
    </div>
</div>
{% endblock %}'''

    # 编辑密码页面
    edit_html = '''{% extends "base.html" %}

{% block title %}编辑 {{ name }} - 密码管理器{% endblock %}

{% block content %}
<div class="card">
    <h2>✏️ 编辑 {{ name }}</h2>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
        <div class="flash-messages">
            {% for category, message in messages %}
            <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        </div>
        {% endif %}
    {% endwith %}

    <form method="POST">
        <div class="form-group">
            <label for="account">账号</label>
            <input type="text" id="account" name="account" value="{{ info.account }}" placeholder="不填则保持不变">
        </div>

        <div class="form-group">
            <label for="password">密码</label>
            <input type="text" id="password" name="password" placeholder="不填则保持不变">
        </div>

        <div class="form-group">
            <label for="email">邮箱</label>
            <input type="text" id="email" name="email" value="{{ info.email or '' }}" placeholder="不填则保持不变">
        </div>

        <div class="form-group">
            <label for="phone">手机号</label>
            <input type="text" id="phone" name="phone" value="{{ info.phone or '' }}" placeholder="不填则保持不变">
        </div>

        <div class="form-group">
            <label for="remark">备注</label>
            <textarea id="remark" name="remark" placeholder="不填则保持不变">{{ info.remark or '' }}</textarea>
        </div>

        <div class="btn-group">
            <button type="submit" class="btn btn-primary">保存更改</button>
            <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">取消</a>
        </div>
    </form>
</div>
{% endblock %}'''

    # 更改主密码页面
    change_pwd_html = '''{% extends "base.html" %}

{% block title %}更改主密码 - 密码管理器{% endblock %}

{% block content %}
<div class="card">
    <h2>🔑 更改主密码</h2>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
        <div class="flash-messages">
            {% for category, message in messages %}
            <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        </div>
        {% endif %}
    {% endwith %}

    <form method="POST">
        <div class="form-group">
            <label for="current_password">当前主密码</label>
            <input type="password" id="current_password" name="current_password" required>
        </div>

        <div class="form-group">
            <label for="new_password">新主密码</label>
            <input type="password" id="new_password" name="new_password" required>
        </div>

        <div class="form-group">
            <label for="confirm_password">确认新密码</label>
            <input type="password" id="confirm_password" name="confirm_password" required>
        </div>

        <div class="btn-group">
            <button type="submit" class="btn btn-primary">更改密码</button>
            <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">取消</a>
        </div>
    </form>
</div>
{% endblock %}'''

    # 批量导入密码页面
    import_html = '''{% extends "base.html" %}

{% block title %}批量导入 - 密码管理器{% endblock %}

{% block content %}
<div class="card">
    <h2>📥 批量导入密码</h2>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
        <div class="flash-messages">
            {% for category, message in messages %}
            <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        </div>
        {% endif %}
    {% endwith %}

    <div class="info-box" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
        <h4 style="margin-bottom: 10px;">CSV文件格式要求：</h4>
        <ul style="margin-left: 20px; color: #666;">
            <li>文件必须为 CSV 格式（.csv 后缀）</li>
            <li>第一行为表头，包含以下字段：<strong>产品名称、账号、密码、邮箱、手机号、备注</strong></li>
            <li>必填字段：<strong>产品名称、账号、密码</strong></li>
            <li>可选字段：邮箱、手机号、备注</li>
            <li>建议使用 Excel 或导出功能生成的 CSV 文件</li>
        </ul>
        <p style="margin-top: 10px; color: #888; font-size: 14px;">
            提示：如果产品名称已存在，该记录将被跳过
        </p>
    </div>

    <form method="POST" enctype="multipart/form-data">
        <div class="form-group">
            <label for="csv_file">选择CSV文件</label>
            <input type="file" id="csv_file" name="csv_file" accept=".csv" required
                   style="border: 2px dashed #ddd; padding: 30px; text-align: center; width: 100%; border-radius: 8px;">
        </div>

        <div class="btn-group">
            <button type="submit" class="btn btn-primary">开始导入</button>
            <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">取消</a>
        </div>
    </form>
</div>
{% endblock %}'''

    # 写入模板文件
    templates = {
        'base.html': base_html,
        'login.html': login_html,
        'dashboard.html': dashboard_html,
        'add_password.html': add_html,
        'view_password.html': view_html,
        'edit_password.html': edit_html,
        'change_password.html': change_pwd_html,
        'import_passwords.html': import_html
    }

    for filename, content in templates.items():
        filepath = os.path.join(templates_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

    return templates_dir


if __name__ == '__main__':
    # 创建模板
    templates_dir = create_templates()
    print(f"模板目录: {templates_dir}")
    print("启动密码管理器 Web 应用...")
    print("请访问 http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
