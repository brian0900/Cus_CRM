from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from config import Config
from werkzeug.security import check_password_hash
import requests
from flask_mail import Mail, Message
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
mail = Mail(app)

# 資料模型（明碼儲存）
class Users(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password_plain = db.Column(db.String(255))  # 明碼密碼

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    contact = db.Column(db.String(100))
    note = db.Column(db.Text)

class Case(db.Model):
    __tablename__ = 'cases'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    type = db.Column(db.Enum('maintain', 'new'))
    title = db.Column(db.String(200))
    status = db.Column(db.String(50))
    start_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    pay_date = db.Column(db.Date)  # 新增繳費日期
    fee = db.Column(db.Numeric(10, 2))
    note = db.Column(db.Text)
    client = db.relationship('Client', backref='cases')

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

@app.route("/login", methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        users = Users.query.filter_by(username=request.form['username']).first()
        if users and users.password_plain == request.form['password']:
            login_user(users)
            return redirect(url_for('index'))
        else:
            error = "帳號或密碼錯誤"
    return render_template("login.html", error=error)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/clients")
@login_required
def show_clients():
    clients = Client.query.all()
    return render_template("clients.html", clients=clients)

@app.route("/cases")
@login_required
def show_cases():
    cases = Case.query.all()
    return render_template("cases.html", cases=cases)

@app.route("/clients/edit/<int:client_id>", methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'POST':
        client.name = request.form['name']
        client.phone = request.form['phone']
        client.email = request.form['email']
        client.contact = request.form['contact']
        client.note = request.form['note']
        db.session.commit()
        return redirect(url_for('show_clients'))
    return render_template("edit_client.html", client=client)

@app.route("/clients/delete/<int:client_id>", methods=['POST'])
@login_required
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    return redirect(url_for('show_clients'))

@app.route("/clients/add", methods=['GET', 'POST'])
@login_required
def add_client():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        contact = request.form['contact']
        note = request.form['note']
        new_client = Client(name=name, phone=phone, email=email, contact=contact, note=note)
        db.session.add(new_client)
        db.session.commit()
        return redirect(url_for('show_clients'))
    return render_template("add_client.html")

@app.route("/cases/add", methods=['GET', 'POST'])
@login_required
def add_case():
    clients = Client.query.all()
    if request.method == 'POST':
        title = request.form['title']
        client_id = request.form['client_id']
        type_ = request.form['type']
        status = request.form['status']
        start_date = request.form['start_date'] or None
        due_date = request.form['due_date'] or None
        fee = request.form['fee'] or None
        note = request.form['note']
        new_case = Case(
            title=title,
            client_id=client_id,
            type=type_,
            status=status,
            start_date=start_date,
            due_date=due_date,
            fee=fee,
            note=note
        )
        db.session.add(new_case)
        db.session.commit()
        # 統一推播內容
        notify_msg = f"新案件通知\n案件名稱：{title}\n客戶ID：{client_id}\n狀態：{status}"
        # Email通知
        send_email("新案件通知", [app.config['NOTIFY_EMAIL']], notify_msg)
        # Telegram通知
        send_telegram(notify_msg)
        return redirect(url_for('show_cases'))
    return render_template("add_case.html", clients=clients)

@app.route("/cases/edit/<int:case_id>", methods=['GET', 'POST'])
@login_required
def edit_case(case_id):
    case = Case.query.get_or_404(case_id)
    clients = Client.query.all()
    if request.method == 'POST':
        case.title = request.form['title']
        case.client_id = request.form['client_id']
        case.type = request.form['type']
        case.status = request.form['status']
        case.start_date = request.form['start_date'] or None
        case.due_date = request.form['due_date'] or None
        case.fee = request.form['fee'] or None
        case.note = request.form['note']
        db.session.commit()
        return redirect(url_for('show_cases'))
    return render_template("edit_case.html", case=case, clients=clients)

@app.route("/cases/delete/<int:case_id>", methods=['POST'])
@login_required
def delete_case(case_id):
    case = Case.query.get_or_404(case_id)
    db.session.delete(case)
    db.session.commit()
    return redirect(url_for('show_cases'))

@app.route("/notify_test", methods=['GET', 'POST'])
@login_required
def notify_test():
    msg = ""
    if request.method == 'POST':
        test_content = request.form.get('content', '這是推播測試訊息')
        try:
            send_email("推播測試", [app.config['MAIL_USERNAME']], test_content)
            send_telegram(f"推播測試\n{test_content}")
            msg = "推播測試已發送（Email與Telegram）"
        except Exception as e:
            msg = f"推播測試失敗：{e}"
    return render_template("notify_test.html", msg=msg)

@app.route("/due_notify_test")
@login_required
def due_notify_test():
    notify_due_cases()
    return "到期案件通知已發送"

def send_email(subject, recipients, body):
    try:
        msg = Message(subject=subject, recipients=recipients, body=body, sender=app.config['MAIL_DEFAULT_SENDER'])
        mail.send(msg)
    except Exception as e:
        print("Email通知失敗:", e)

def send_telegram(text):
    token = app.config['TG_BOT_TOKEN']
    chat_id = app.config['TG_CHAT_ID']
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        resp = requests.post(url, data=payload, timeout=5)
        print("Telegram回應：", resp.text)  # 除錯用
    except Exception as e:
        print("Telegram通知失敗:", e)

def notify_due_cases():
    days = app.config['CASE_DUE_NOTIFY_DAYS']
    today = datetime.today().date()
    due_date = today + timedelta(days=days)
    cases = Case.query.filter(Case.due_date == due_date).all()
    for case in cases:
        msg = f"案件即將到期提醒\n案件名稱：{case.title}\n到期日：{case.due_date}\n客戶ID：{case.client_id}"
        send_email("案件到期提醒", [app.config['NOTIFY_EMAIL']], msg)
        send_telegram(msg)

def auto_extend_due_date():
    today = datetime.today().date()
    # 找出 pay_date 是今天的案件
    cases = Case.query.filter(Case.pay_date == today).all()
    for case in cases:
        # 延後一個月
        if case.due_date:
            case.due_date = case.due_date + relativedelta(months=1)
        else:
            case.due_date = today + relativedelta(months=1)
        db.session.commit()
        print(f"案件 {case.id} 到期日已自動延展至 {case.due_date}")

def start_scheduler():
    scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Taipei'))
    scheduler.add_job(func=notify_due_cases, trigger='cron', hour=8, minute=0)
    scheduler.add_job(func=auto_extend_due_date, trigger='cron', hour=1, minute=0)  # 每天凌晨1點自動延展
    scheduler.start()

start_scheduler()

if __name__ == "__main__":
    app.run(debug=True)
