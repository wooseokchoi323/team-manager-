from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import os, json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tm-secret-2024")

_url = os.environ.get("DATABASE_URL", "sqlite:///tm.db")
if _url.startswith("postgres://"): _url = _url.replace("postgres://", "postgresql://", 1)
app.config.update(SQLALCHEMY_DATABASE_URI=_url, SQLALCHEMY_TRACK_MODIFICATIONS=False)
db = SQLAlchemy(app)

# ── Models ─────────────────────────────────────
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True)
    role = db.Column(db.String(30), default="팀원")
    color = db.Column(db.String(7), default="#3B82F6")
    a_tasks = db.relationship("Task", foreign_keys="Task.assignee_id", backref="assignee", lazy=True)
    c_tasks = db.relationship("Task", foreign_keys="Task.creator_id", backref="creator", lazy=True)
    comments = db.relationship("Comment", backref="author", lazy=True)
    def to_dict(self): return {"id":self.id,"name":self.name,"role":self.role,"color":self.color}

class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="todo")
    priority = db.Column(db.String(10), default="medium")
    progress = db.Column(db.Integer, default=0)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship("Comment", backref="task", lazy=True, cascade="all, delete-orphan")
    @property
    def is_overdue(self): return self.due_date and self.due_date < date.today() and self.status != "done"
    def to_dict(self):
        return {"id":self.id,"title":self.title,"status":self.status,"priority":self.priority,
                "progress":self.progress,"assignee_id":self.assignee_id,
                "assignee_name":self.assignee.name if self.assignee else "",
                "assignee_color":self.assignee.color if self.assignee else "#6B7280",
                "due_date":self.due_date.isoformat() if self.due_date else None}

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def me():
    uid = session.get("user_id", 1)
    return db.session.get(User, uid) or User.query.first()

def init():
    db.create_all()
    if User.query.count(): return
    users = [
        User(name="김팀장", email="lead@team.com", role="팀장", color="#8B5CF6"),
        User(name="이개발", email="dev@team.com", role="개발자", color="#3B82F6"),
        User(name="박디자인", email="design@team.com", role="디자이너", color="#EC4899"),
        User(name="최기획", email="plan@team.com", role="기획자", color="#F59E0B"),
        User(name="정QA", email="qa@team.com", role="QA", color="#10B981"),
    ]
    for u in users: db.session.add(u)
    db.session.commit()
    today = date.today()
    tasks = [
        Task(title="메인 페이지 UI 개발", description="반응형 메인 페이지 퍼블리싱 작업", status="in_progress", priority="high", progress=65, assignee_id=2, creator_id=1, due_date=today+timedelta(3)),
        Task(title="로그인/회원가입 구현", description="JWT 기반 인증 시스템 구현", status="done", priority="urgent", progress=100, assignee_id=2, creator_id=1, due_date=today-timedelta(2)),
        Task(title="메인 화면 디자인 시안", description="Figma UI/UX 시안 제작", status="done", priority="high", progress=100, assignee_id=3, creator_id=1, due_date=today-timedelta(5)),
        Task(title="UX 플로우 설계", description="전체 서비스 UX 플로우 다이어그램 작성", status="in_progress", priority="medium", progress=40, assignee_id=4, creator_id=1, due_date=today+timedelta(7)),
        Task(title="QA 테스트 케이스 작성", description="기능별 테스트 시나리오 및 체크리스트", status="todo", priority="medium", progress=0, assignee_id=5, creator_id=1, due_date=today+timedelta(10)),
        Task(title="API 명세서 문서화", description="REST API Swagger 문서화", status="todo", priority="low", progress=0, assignee_id=4, creator_id=2, due_date=today+timedelta(14)),
        Task(title="DB 스키마 설계", description="ERD 작성 및 테이블 최적화", status="done", priority="high", progress=100, assignee_id=2, creator_id=1, due_date=today-timedelta(10)),
        Task(title="모바일 반응형 UI", description="전체 페이지 모바일 최적화 적용", status="todo", priority="medium", progress=0, assignee_id=3, creator_id=1, due_date=today+timedelta(5)),
    ]
    for t in tasks: db.session.add(t)
    db.session.commit()

PMAP = {"urgent":"긴급","high":"높음","medium":"보통","low":"낮음"}
SMAP = {"todo":"할 일","in_progress":"진행 중","done":"완료"}

@app.route("/")
def dashboard():
    u = me(); users = User.query.all(); tasks = Task.query.all(); today = date.today()
    total = len(tasks)
    done_c = sum(1 for t in tasks if t.status == "done")
    inp_c = sum(1 for t in tasks if t.status == "in_progress")
    todo_c = total - done_c - inp_c
    rate = round(done_c / total * 100) if total else 0
    my_c = sum(1 for t in tasks if t.assignee_id == u.id)
    overdue = [t for t in tasks if t.is_overdue]
    upcoming = sorted([t for t in tasks if t.due_date and today <= t.due_date <= today + timedelta(7) and t.status != "done"], key=lambda x: x.due_date)
    stats = []
    for usr in users:
        ut = [t for t in tasks if t.assignee_id == usr.id]
        stats.append({"user": usr, "total": len(ut),
                      "done": sum(1 for t in ut if t.status == "done"),
                      "inp": sum(1 for t in ut if t.status == "in_progress"),
                      "prog": round(sum(t.progress for t in ut) / len(ut)) if ut else 0})
    recent = Task.query.order_by(Task.created_at.desc()).limit(5).all()
    return render_template("dashboard.html", u=u, users=users, today=today,
        total=total, done_c=done_c, inp_c=inp_c, todo_c=todo_c, rate=rate,
        my_c=my_c, overdue=overdue, upcoming=upcoming, stats=stats, recent=recent, PMAP=PMAP, SMAP=SMAP)

@app.route("/kanban")
def kanban():
    u = me(); users = User.query.all()
    fu = request.args.get("user", "all"); fp = request.args.get("priority", "all")
    q = Task.query
    if fu != "all": q = q.filter_by(assignee_id=int(fu))
    if fp != "all": q = q.filter_by(priority=fp)
    tasks = q.order_by(Task.created_at.desc()).all()
    return render_template("kanban.html", u=u, users=users, today=date.today(), fu=fu, fp=fp,
        todo=[t for t in tasks if t.status == "todo"],
        inp=[t for t in tasks if t.status == "in_progress"],
        done=[t for t in tasks if t.status == "done"],
        PMAP=PMAP, SMAP=SMAP)

@app.route("/calendar")
def calendar_view():
    u = me(); users = User.query.all()
    tasks = Task.query.filter(Task.due_date.isnot(None)).all()
    sc = {"done": "#10B981", "in_progress": "#F59E0B", "todo": "#6B7280"}
    events = [{"id": t.id, "title": t.title, "start": t.due_date.isoformat(),
               "backgroundColor": sc.get(t.status, "#3B82F6"), "borderColor": sc.get(t.status, "#3B82F6"),
               "extendedProps": {"status": t.status, "priority": t.priority,
                                 "assignee": t.assignee.name if t.assignee else "",
                                 "progress": t.progress, "tid": t.id}} for t in tasks]
    return render_template("calendar.html", u=u, users=users, events=json.dumps(events))

@app.route("/my-tasks")
def my_tasks():
    u = me(); users = User.query.all(); fs = request.args.get("status", "all")
    q = Task.query.filter_by(assignee_id=u.id)
    if fs != "all": q = q.filter_by(status=fs)
    tasks = q.order_by(Task.due_date.asc()).all()
    all_my = Task.query.filter_by(assignee_id=u.id).all()
    return render_template("my_tasks.html", u=u, users=users, tasks=tasks, fs=fs, today=date.today(),
        tc=sum(1 for t in all_my if t.status == "todo"),
        ic=sum(1 for t in all_my if t.status == "in_progress"),
        dc=sum(1 for t in all_my if t.status == "done"),
        PMAP=PMAP, SMAP=SMAP)

@app.route("/team")
def team():
    u = me(); users = User.query.all(); tasks = Task.query.all()
    td = []
    for usr in users:
        ut = [t for t in tasks if t.assignee_id == usr.id]
        td.append({"user": usr, "all": ut,
                   "todo": [t for t in ut if t.status == "todo"],
                   "inp": [t for t in ut if t.status == "in_progress"],
                   "done": [t for t in ut if t.status == "done"],
                   "prog": round(sum(t.progress for t in ut) / len(ut)) if ut else 0,
                   "overdue": [t for t in ut if t.is_overdue]})
    return render_template("team.html", u=u, users=users, td=td, PMAP=PMAP, SMAP=SMAP)

@app.route("/tasks/add", methods=["GET", "POST"])
def add_task():
    u = me(); users = User.query.all()
    if request.method == "POST":
        dd = datetime.strptime(request.form["due_date"], "%Y-%m-%d").date() if request.form.get("due_date") else None
        t = Task(title=request.form["title"], description=request.form.get("description", ""),
                 status=request.form.get("status", "todo"), priority=request.form.get("priority", "medium"),
                 progress=int(request.form.get("progress", 0)),
                 assignee_id=int(request.form["assignee_id"]) if request.form.get("assignee_id") else None,
                 creator_id=u.id, due_date=dd)
        db.session.add(t); db.session.commit()
        return redirect(request.form.get("next", "/"))
    return render_template("task_form.html", u=u, users=users, task=None, action="add")

@app.route("/tasks/<int:tid>")
def task_detail(tid):
    u = me(); users = User.query.all(); task = Task.query.get_or_404(tid)
    cmts = Comment.query.filter_by(task_id=tid).order_by(Comment.created_at).all()
    return render_template("task_detail.html", u=u, users=users, task=task, cmts=cmts, today=date.today(), PMAP=PMAP, SMAP=SMAP)

@app.route("/tasks/<int:tid>/edit", methods=["GET", "POST"])
def edit_task(tid):
    u = me(); users = User.query.all(); task = Task.query.get_or_404(tid)
    if request.method == "POST":
        task.title = request.form["title"]; task.description = request.form.get("description", "")
        task.status = request.form.get("status", "todo"); task.priority = request.form.get("priority", "medium")
        task.progress = int(request.form.get("progress", 0))
        task.assignee_id = int(request.form["assignee_id"]) if request.form.get("assignee_id") else None
        task.due_date = datetime.strptime(request.form["due_date"], "%Y-%m-%d").date() if request.form.get("due_date") else None
        task.updated_at = datetime.utcnow(); db.session.commit()
        return redirect(url_for("task_detail", tid=task.id))
    return render_template("task_form.html", u=u, users=users, task=task, action="edit")

@app.route("/tasks/<int:tid>/delete", methods=["POST"])
def delete_task(tid):
    t = Task.query.get_or_404(tid); db.session.delete(t); db.session.commit()
    return redirect(url_for("kanban"))

@app.route("/tasks/<int:tid>/comment", methods=["POST"])
def add_comment(tid):
    u = me(); c = request.form.get("content", "").strip()
    if c: db.session.add(Comment(task_id=tid, user_id=u.id, content=c)); db.session.commit()
    return redirect(url_for("task_detail", tid=tid))

@app.route("/api/tasks/<int:tid>/status", methods=["POST"])
def api_status(tid):
    t = Task.query.get_or_404(tid); d = request.get_json()
    if "status" in d:
        t.status = d["status"]
        if d["status"] == "done": t.progress = 100
        elif d["status"] == "todo" and t.progress == 100: t.progress = 0
    if "progress" in d: t.progress = d["progress"]
    t.updated_at = datetime.utcnow(); db.session.commit()
    return jsonify({"ok": True, "task": t.to_dict()})

@app.route("/api/tasks")
def api_tasks(): return jsonify([t.to_dict() for t in Task.query.all()])

@app.route("/switch/<int:uid>")
def switch_user(uid):
    session["user_id"] = uid
    return redirect(request.referrer or "/")

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    # 해당 팀원의 업무는 미배정으로 변경
    Task.query.filter_by(user_id=user_id).update({'user_id': None})
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': '팀원이 삭제되었습니다.'})
    
@app.route("/users/add", methods=["POST"])
def add_user():
    n = request.form.get("name", "").strip()
    if n:
        db.session.add(User(name=n, email=request.form.get("email", n+"@team.com"),
                            role=request.form.get("role", "팀원"), color=request.form.get("color", "#3B82F6")))
        db.session.commit()
    return redirect(url_for("team"))

with app.app_context():
    db.create_all()
    # 초기 팀원 데이터 생성
    if User.query.count() == 0:
        users = [
            User(name='김팀장', role='팀장', color='#6366f1'),
            User(name='이개발', role='개발자', color='#3b82f6'),
            User(name='박디자인', role='디자이너', color='#ec4899'),
            User(name='최기획', role='기획자', color='#f59e0b'),
            User(name='정QA', role='QA', color='#10b981'),
        ]
        for u in users:
            db.session.add(u)
        db.session.commit()

@app.route('/settings')
def settings():
    users = User.query.all()
    return render_template('settings.html', users=users)

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    Task.query.filter_by(user_id=user_id).update({'user_id': None})
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': '팀원이 삭제되었습니다.'})

if __name__ == "__main__":
    with app.app_context(): init()
    app.run(debug=True, host="0.0.0.0", port=5000)
