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
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        search_lower = search_query.lower()
        products = [p for p in products if search_lower in p.lower()]
    
    ITEMS_PER_PAGE = 5
    page = request.args.get('page', 1, type=int)
    total = len(products)
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    products_page = products[start:end]
    
    page_range = []
    for p in range(1, total_pages + 1):
        if p == 1 or p == total_pages or (p >= page - 1 and p <= page + 1):
            page_range.append(p)
        elif p == page - 2 or p == page + 2:
            page_range.append('...')
    
    return render_template('dashboard.html', 
                          products=products_page, 
                          search_query=search_query,
                          page=page,
                          total_pages=total_pages,
                          total=total,
                          page_range=page_range)


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

if __name__ == '__main__':
    print("启动密码管理器 Web 应用...")
    print("请访问 http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
