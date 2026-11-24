import re
from datetime import date
from decimal import Decimal
from functools import wraps
import click
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint, inspect, text
from config import Config
from extensions import db

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="STUDENT")
    active = db.Column(db.Boolean, default=True, nullable=False)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    @property
    def is_active(self):
        return self.active

class ClassRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    grade = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(10), nullable=False, default="A")
    academic_year = db.Column(db.String(20), nullable=False)
    __table_args__ = (UniqueConstraint("grade", "section", "academic_year"),)
    @property
    def label(self):
        return f"Class {self.grade}-{self.section} ({self.academic_year})"

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    grades = db.Column(db.String(30), default="1-10")
    active = db.Column(db.Boolean, default=True)

class StaffProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    employee_id = db.Column(db.String(40), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    designation = db.Column(db.String(80), default="Teacher")
    user = db.relationship("User", backref=db.backref("staff_profile", uselist=False))

class TeachingAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("staff_profile.id"), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey("class_room.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    teacher = db.relationship("StaffProfile")
    classroom = db.relationship("ClassRoom")
    subject = db.relationship("Subject")
    __table_args__ = (UniqueConstraint("teacher_id", "classroom_id", "subject_id"),)

class StudentProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    admission_no = db.Column(db.String(40), unique=True, nullable=False)
    roll_no = db.Column(db.String(40))
    full_name = db.Column(db.String(120), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey("class_room.id"), nullable=False)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(30))
    phone = db.Column(db.String(30))
    address = db.Column(db.Text)
    father_name = db.Column(db.String(120)); father_phone = db.Column(db.String(30))
    father_email = db.Column(db.String(120)); father_occupation = db.Column(db.String(120))
    mother_name = db.Column(db.String(120)); mother_phone = db.Column(db.String(30))
    mother_email = db.Column(db.String(120)); mother_occupation = db.Column(db.String(120))
    guardian_name = db.Column(db.String(120)); guardian_phone = db.Column(db.String(30))
    guardian_relation = db.Column(db.String(60))
    user = db.relationship("User", backref=db.backref("student_profile", uselist=False))
    classroom = db.relationship("ClassRoom")

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profile.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("staff_profile.id"), nullable=False)
    attendance_date = db.Column(db.Date, default=date.today, nullable=False)
    status = db.Column(db.String(10), nullable=False)
    student = db.relationship("StudentProfile")
    __table_args__ = (UniqueConstraint("student_id", "attendance_date"),)

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey("class_room.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    exam_date = db.Column(db.Date)
    max_marks = db.Column(db.Float, default=100)
    room = db.Column(db.String(50))
    classroom = db.relationship("ClassRoom")
    subject = db.relationship("Subject")

class Mark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exam.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profile.id"), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    exam = db.relationship("Exam")
    student = db.relationship("StudentProfile")
    __table_args__ = (UniqueConstraint("exam_id", "student_id"),)

class FeeRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profile.id"), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    total_fee = db.Column(db.Numeric(10, 2), nullable=False)
    student = db.relationship("StudentProfile")

class FeePayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fee_record_id = db.Column(db.Integer, db.ForeignKey("fee_record.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.Date, default=date.today)
    receipt_no = db.Column(db.String(50))
    fee_record = db.relationship("FeeRecord", backref="payments")

def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return deco

def assigned(classroom_id, subject_id=None):
    teacher = getattr(current_user, "staff_profile", None)
    if not teacher: return False
    q = TeachingAssignment.query.filter_by(teacher_id=teacher.id, classroom_id=classroom_id)
    if subject_id is not None: q = q.filter_by(subject_id=subject_id)
    return q.first() is not None

@app.context_processor
def inject_teacher_nav():
    """Gives every template the logged-in teacher's classes for the sidebar."""
    if current_user.is_authenticated and current_user.role == "TEACHER":
        p = getattr(current_user, "staff_profile", None)
        if p:
            seen = {}
            for a in TeachingAssignment.query.filter_by(teacher_id=p.id).all():
                seen.setdefault(a.classroom_id, a.classroom)
            return {"nav_classes": list(seen.values()), "nav_teacher": p}
    return {"nav_classes": [], "nav_teacher": None}

def current_teacher():
    """The logged-in teacher's profile. Every teacher page works only on this teacher's own data."""
    profile = getattr(current_user, "staff_profile", None)
    if not profile:
        abort(403, description="No teacher profile is linked to this account. Ask the admin.")
    return profile

def class_students(cid):
    """Students of a class ordered by the number at the end of the roll no, then name."""
    def key(s):
        m = re.search(r"(\d+)$", (s.roll_no or "").strip())
        return (int(m.group(1)) if m else 10**9, s.full_name)
    return sorted(StudentProfile.query.filter_by(classroom_id=cid).all(), key=key)

def grade_for(p):
    if p >= 91: return "A1"
    if p >= 81: return "A2"
    if p >= 71: return "B1"
    if p >= 61: return "B2"
    if p >= 51: return "C1"
    if p >= 41: return "C2"
    if p >= 33: return "D"
    return "E"

@app.route("/")
def home():
    if current_user.is_authenticated:
        if current_user.role == "ADMIN":
            return redirect(url_for("admin_dashboard"))
        elif current_user.role == "TEACHER":
            return redirect(url_for("teacher_dashboard"))
        elif current_user.role == "STUDENT":
            return redirect(url_for("student_dashboard"))

    return redirect(url_for("login"))



@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "ADMIN":
            return redirect(url_for("admin_dashboard"))
        elif current_user.role == "TEACHER":
            return redirect(url_for("teacher_dashboard"))
        elif current_user.role == "STUDENT":
            return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        selected_role = request.form.get("role", "").strip().upper()


        user = User.query.filter_by(
            username=username,
            active=True
        ).first()

        if (
            user
            and selected_role in ["ADMIN", "TEACHER", "STUDENT"]
            and user.role == selected_role
            and user.check_password(password)
        ):
            login_user(user)

            if user.role == "ADMIN":
                return redirect(url_for("admin_dashboard"))
            elif user.role == "TEACHER":
                return redirect(url_for("teacher_dashboard"))
            elif user.role == "STUDENT":
                return redirect(url_for("student_dashboard"))

        flash(
            "Invalid username, password or selected login type.",
            "danger"
        )

    return render_template("login.html")



@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("login"))

@app.route("/admin")
@login_required
@role_required("ADMIN")
def admin_dashboard():

    recent_students = StudentProfile.query.order_by(
        StudentProfile.id.desc()
    ).limit(5).all()

    return render_template(
        "admin_dashboard.html",
        students=StudentProfile.query.count(),
        teachers=StaffProfile.query.count(),
        classes=ClassRoom.query.count(),
        subjects=Subject.query.count(),
        recent_students=recent_students
    )

@app.route("/teacher")
@login_required
@role_required("TEACHER")
def teacher_dashboard():
    teacher = current_teacher()

    assignments = TeachingAssignment.query.filter_by(
        teacher_id=teacher.id
    ).all()

    # Count each assigned class only once.
    classroom_ids = list({
        assignment.classroom_id
        for assignment in assignments
    })

    counts = {
        cid: StudentProfile.query.filter_by(
            classroom_id=cid
        ).count()
        for cid in classroom_ids
    }

    total_students = StudentProfile.query.filter(
        StudentProfile.classroom_id.in_(classroom_ids)
    ).count() if classroom_ids else 0

    exam_count = Exam.query.filter(
        Exam.classroom_id.in_(classroom_ids)
    ).count() if classroom_ids else 0

    stats = {
        "classes": len(classroom_ids),
        "assignments": len(assignments),
        "students": total_students,
        "exams": exam_count
    }

    return render_template(
        "teacher_dashboard.html",
        teacher=teacher,
        assignments=assignments,
        counts=counts,
        stats=stats
    )


@app.route("/student")
@login_required
@role_required("STUDENT")
def student_dashboard():
    s = getattr(current_user, "student_profile", None)
    if not s:
        return render_template("student_dashboard.html", student=None, marks=[], attendance=[], fees=[], subjects=[])
    marks = Mark.query.join(Exam).filter(Mark.student_id==s.id).all()
    attendance = Attendance.query.filter_by(student_id=s.id).order_by(Attendance.attendance_date.desc()).limit(50).all()
    fee_rows=[]
    for f in FeeRecord.query.filter_by(student_id=s.id).all():
        paid=sum((x.amount for x in f.payments), Decimal("0.00"))
        fee_rows.append((f,paid,f.total_fee-paid))
    # Subjects for student's class
    assignments = TeachingAssignment.query.filter_by(classroom_id=s.classroom_id).all()
    assigned_subjects = list({a.subject for a in assignments if a.subject})
    if not assigned_subjects:
        assigned_subjects = [sub for sub in Subject.query.filter_by(active=True).all() if grade_in_range(sub.grades, s.classroom.grade)]
    assigned_subjects.sort(key=lambda x: x.name)
    return render_template("student_dashboard.html", student=s, marks=marks, attendance=attendance, fees=fee_rows, grade_for=grade_for, subjects=assigned_subjects)

@app.route("/admin/classes", methods=["GET","POST"])
@login_required
@role_required("ADMIN")
def classes_page():
    if request.method=="POST":
        try:
            grade=int(request.form["grade"])
            if not 1 <= grade <= 10: raise ValueError()
            db.session.add(ClassRoom(grade=grade, section=request.form["section"].strip().upper(), academic_year=request.form["year"].strip()))
            db.session.commit(); flash("Class added.", "success")
        except Exception:
            db.session.rollback(); flash("Could not add class (check grade/year and duplicates).", "danger")
    return render_template("classes.html", classes=ClassRoom.query.order_by(ClassRoom.grade).all())

@app.route("/admin/subjects", methods=["GET","POST"])
@login_required
@role_required("ADMIN")
def subjects_page():
    if request.method=="POST":
        try:
            db.session.add(Subject(name=request.form["name"].strip(), grades=request.form.get("grades","1-10")))
            db.session.commit(); flash("Subject added.", "success")
        except Exception:
            db.session.rollback(); flash("Subject already exists or invalid.", "danger")
    return render_template("subjects.html", subjects=Subject.query.all())

@app.route("/admin/assignments", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def assignments_page():
    if request.method == "POST":
        try:
            db.session.add(TeachingAssignment(
                teacher_id=int(request.form["teacher_id"]),
                classroom_id=int(request.form["classroom_id"]),
                subject_id=int(request.form["subject_id"]),
            ))
            db.session.commit()
            flash("Teaching assignment added.", "success")
        except Exception:
            db.session.rollback()
            flash("Could not assign (it may already exist, or a teacher/class/subject is missing).", "danger")
        return redirect(url_for("assignments_page"))
    return render_template(
        "assignments.html",
        teachers=StaffProfile.query.order_by(StaffProfile.full_name).all(),
        classes=ClassRoom.query.order_by(ClassRoom.grade).all(),
        subjects=Subject.query.order_by(Subject.name).all(),
        assignments=TeachingAssignment.query.order_by(TeachingAssignment.id.desc()).all(),
    )

@app.route("/admin/assign", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def bulk_assign_page():
    teachers = StaffProfile.query.order_by(StaffProfile.full_name).all()
    classes = ClassRoom.query.order_by(ClassRoom.grade, ClassRoom.section).all()
    subjects = Subject.query.order_by(Subject.name).all()

    if request.method == "POST":
        try:
            teacher_id = int(request.form["teacher_id"])
            classroom_ids = [int(x) for x in request.form.getlist("classroom_ids")]
            subject_ids = [int(x) for x in request.form.getlist("subject_ids")]
        except (KeyError, ValueError):
            flash("Please select a teacher, at least one class, and at least one subject.", "danger")
            return redirect(url_for("bulk_assign_page"))

        teacher = db.session.get(StaffProfile, teacher_id)
        if not teacher or not classroom_ids or not subject_ids:
            flash("Please select a teacher, at least one class, and at least one subject.", "danger")
            return redirect(url_for("bulk_assign_page"))

        created = 0
        already_existed = 0
        for cid in classroom_ids:
            for sid in subject_ids:
                existing = TeachingAssignment.query.filter_by(
                    teacher_id=teacher.id, classroom_id=cid, subject_id=sid
                ).first()
                if existing:
                    already_existed += 1
                else:
                    db.session.add(TeachingAssignment(
                        teacher_id=teacher.id, classroom_id=cid, subject_id=sid
                    ))
                    created += 1
        db.session.commit()
        flash(f"{created} created, {already_existed} already existed.", "success")
        return redirect(url_for("bulk_assign_page", teacher_id=teacher.id))

    selected_tid = request.args.get("teacher_id", type=int)
    selected_teacher = db.session.get(StaffProfile, selected_tid) if selected_tid else None
    teacher_assignments = []
    student_counts = {}
    if selected_teacher:
        teacher_assignments = TeachingAssignment.query.filter_by(teacher_id=selected_teacher.id).all()
        cids = {a.classroom_id for a in teacher_assignments}
        student_counts = {cid: StudentProfile.query.filter_by(classroom_id=cid).count() for cid in cids}

    class_id = request.args.get("class_id", type=int)
    view_class = db.session.get(ClassRoom, class_id) if class_id else None
    class_student_count = 0
    class_assignments = []
    if view_class:
        class_student_count = StudentProfile.query.filter_by(classroom_id=view_class.id).count()
        class_assignments = TeachingAssignment.query.filter_by(classroom_id=view_class.id).all()

    return render_template(
        "admin_assign.html",
        teachers=teachers,
        classes=classes,
        subjects=subjects,
        selected_teacher=selected_teacher,
        teacher_assignments=teacher_assignments,
        student_counts=student_counts,
        view_class=view_class,
        class_student_count=class_student_count,
        class_assignments=class_assignments,
    )

@app.route("/admin/assignments/<int:aid>/delete", methods=["POST"])
@login_required
@role_required("ADMIN")
def delete_assignment(aid):
    assignment = db.session.get(TeachingAssignment, aid)
    if not assignment:
        abort(404)
    teacher_id = assignment.teacher_id
    db.session.delete(assignment)
    db.session.commit()
    flash("Assignment removed.", "success")
    referrer = request.referrer
    if referrer and ("admin" in referrer):
        return redirect(referrer)
    return redirect(url_for("bulk_assign_page", teacher_id=teacher_id))

@app.route("/admin/fees", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def fees_page():
    if request.method == "POST":
        try:
            total = Decimal(request.form["total_fee"])
            if total < 0: raise ValueError()
            db.session.add(FeeRecord(
                student_id=int(request.form["student_id"]),
                academic_year=request.form["year"].strip(),
                total_fee=total,
            ))
            db.session.commit()
            flash("Fee record added.", "success")
        except Exception:
            db.session.rollback()
            flash("Could not add fee record. Check the student, year and amount.", "danger")
        return redirect(url_for("fees_page"))
    return render_template(
        "fees_admin.html",
        students=StudentProfile.query.order_by(StudentProfile.full_name).all(),
        records=FeeRecord.query.order_by(FeeRecord.id.desc()).all(),
    )

@app.route("/admin/fees/<int:fid>/pay", methods=["POST"])
@login_required
@role_required("ADMIN")
def fee_payment(fid):
    record = db.session.get(FeeRecord, fid)
    if not record: abort(404)
    try:
        amount = Decimal(request.form["amount"])
        if amount <= 0: raise ValueError()
        db.session.add(FeePayment(fee_record_id=fid, amount=amount,
                                  receipt_no=request.form.get("receipt_no") or None))
        db.session.commit()
        flash("Payment recorded.", "success")
    except Exception:
        db.session.rollback()
        flash("Invalid payment amount.", "danger")
    return redirect(url_for("fees_page"))

@app.route("/admin/students/new", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def add_student_page():
    classes = ClassRoom.query.order_by(ClassRoom.grade, ClassRoom.section).all()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "").strip() or None
        full_name = request.form.get("full_name", "").strip()
        admission_no = request.form.get("admission_no", "").strip()
        roll_no = request.form.get("roll_no", "").strip() or None
        classroom_id_raw = request.form.get("classroom_id", "")
        dob_raw = request.form.get("date_of_birth", "").strip()
        gender = request.form.get("gender", "").strip() or None
        phone = request.form.get("phone", "").strip() or None
        address = request.form.get("address", "").strip() or None

        father_name = request.form.get("father_name", "").strip() or None
        father_phone = request.form.get("father_phone", "").strip() or None
        father_email = request.form.get("father_email", "").strip() or None
        father_occupation = request.form.get("father_occupation", "").strip() or None

        mother_name = request.form.get("mother_name", "").strip() or None
        mother_phone = request.form.get("mother_phone", "").strip() or None
        mother_email = request.form.get("mother_email", "").strip() or None
        mother_occupation = request.form.get("mother_occupation", "").strip() or None

        guardian_name = request.form.get("guardian_name", "").strip() or None
        guardian_phone = request.form.get("guardian_phone", "").strip() or None
        guardian_relation = request.form.get("guardian_relation", "").strip() or None

        # Required fields validation
        if not username:
            flash("Username is required.", "danger")
            return redirect(url_for("add_student_page"))
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return redirect(url_for("add_student_page"))
        if not full_name:
            flash("Full name is required.", "danger")
            return redirect(url_for("add_student_page"))
        if not admission_no:
            flash("Admission number is required.", "danger")
            return redirect(url_for("add_student_page"))
        try:
            classroom_id = int(classroom_id_raw)
            if not db.session.get(ClassRoom, classroom_id):
                raise ValueError()
        except (ValueError, TypeError):
            flash("Valid class selection is required.", "danger")
            return redirect(url_for("add_student_page"))

        # Unique checks
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("add_student_page"))
        if StudentProfile.query.filter_by(admission_no=admission_no).first():
            flash("Admission number already exists.", "danger")
            return redirect(url_for("add_student_page"))
        if roll_no and StudentProfile.query.filter_by(classroom_id=classroom_id, roll_no=roll_no).first():
            flash("Roll number already exists in this class.", "danger")
            return redirect(url_for("add_student_page"))
        if email:
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                flash("Invalid email format.", "danger")
                return redirect(url_for("add_student_page"))
            if User.query.filter_by(email=email).first():
                flash("User email already registered.", "danger")
                return redirect(url_for("add_student_page"))

        # Phone digits only (7 to 15)
        for phone_val, label in [
            (phone, "Student phone"),
            (father_phone, "Father phone"),
            (mother_phone, "Mother phone"),
            (guardian_phone, "Guardian phone"),
        ]:
            if phone_val and not re.fullmatch(r"\d{7,15}", phone_val):
                flash(f"{label} must contain only digits (7 to 15 digits).", "danger")
                return redirect(url_for("add_student_page"))

        # Parent email format
        for email_val, label in [
            (father_email, "Father email"),
            (mother_email, "Mother email"),
        ]:
            if email_val and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email_val):
                flash(f"Invalid {label} format.", "danger")
                return redirect(url_for("add_student_page"))

        dob = None
        if dob_raw:
            try:
                dob = date.fromisoformat(dob_raw)
            except ValueError:
                flash("Invalid date of birth format.", "danger")
                return redirect(url_for("add_student_page"))

        # Transaction
        try:
            user = User(
                username=username,
                email=email,
                role="STUDENT"
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            student = StudentProfile(
                user_id=user.id,
                admission_no=admission_no,
                roll_no=roll_no,
                full_name=full_name,
                classroom_id=classroom_id,
                date_of_birth=dob,
                gender=gender,
                phone=phone,
                address=address,
                father_name=father_name,
                father_phone=father_phone,
                father_email=father_email,
                father_occupation=father_occupation,
                mother_name=mother_name,
                mother_phone=mother_phone,
                mother_email=mother_email,
                mother_occupation=mother_occupation,
                guardian_name=guardian_name,
                guardian_phone=guardian_phone,
                guardian_relation=guardian_relation,
            )
            db.session.add(student)
            db.session.commit()
            flash(f"Student created successfully with username '{username}'.", "success")
            return redirect(url_for("users_page"))
        except Exception as e:
            db.session.rollback()
            flash(f"Could not create student: {e}", "danger")
            return redirect(url_for("add_student_page"))

    return render_template("admin_add_student.html", classes=classes)

@app.route("/admin/users", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def users_page():
    classes = ClassRoom.query.all()

    if request.method == "POST":
        try:
            role = request.form["role"]

            if role not in ["TEACHER", "STUDENT"]:
                raise ValueError("Invalid role")

            username = request.form["username"].strip()
            password = request.form["password"]

            if len(password) < 8:
                raise ValueError("Password must be at least 8 characters")

            user = User(
                username=username,
                email=request.form.get("email") or None,
                role=role
            )

            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            if role == "TEACHER":
                db.session.add(StaffProfile(
                    user_id=user.id,
                    employee_id=request.form["employee_id"].strip(),
                    full_name=request.form["full_name"].strip(),
                    phone=request.form.get("phone")
                ))

            else:
                db.session.add(StudentProfile(
                    user_id=user.id,
                    admission_no=request.form["admission_no"].strip(),
                    roll_no=request.form.get("roll_no"),
                    full_name=request.form["full_name"].strip(),
                    classroom_id=int(request.form["classroom_id"]),
                    phone=request.form.get("phone"),
                    address=request.form.get("address"),
                    father_name=request.form.get("father_name"),
                    father_phone=request.form.get("father_phone"),
                    father_email=request.form.get("father_email"),
                    father_occupation=request.form.get("father_occupation"),
                    mother_name=request.form.get("mother_name"),
                    mother_phone=request.form.get("mother_phone"),
                    mother_email=request.form.get("mother_email"),
                    mother_occupation=request.form.get("mother_occupation"),
                    guardian_name=request.form.get("guardian_name"),
                    guardian_phone=request.form.get("guardian_phone"),
                    guardian_relation=request.form.get("guardian_relation")
                ))

            db.session.commit()
            flash("User/profile created successfully.", "success")

        except Exception as e:
            db.session.rollback()
            flash(
                "Creation failed. Check required fields and unique username, admission or employee ID.",
                "danger"
            )

        return redirect(url_for("users_page"))

    search = request.args.get("q", "").strip()

    student_query = StudentProfile.query

    if search:
        student_query = student_query.filter(
            db.or_(
                StudentProfile.full_name.ilike(f"%{search}%"),
                StudentProfile.admission_no.ilike(f"%{search}%")
            )
        )

    students = student_query.order_by(StudentProfile.id.desc()).all()

    return render_template(
        "users.html",
        classes=classes,
        students=students,
        search=search
    )


@app.route("/admin/students/<int:sid>/edit", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def edit_student(sid):
    student = db.session.get(StudentProfile, sid)

    if not student:
        abort(404)

    classes = ClassRoom.query.all()

    if request.method == "POST":
        try:
            student.full_name = request.form["full_name"].strip()
            student.admission_no = request.form["admission_no"].strip()
            student.roll_no = request.form.get("roll_no")
            student.classroom_id = int(request.form["classroom_id"])
            student.phone = request.form.get("phone")
            student.address = request.form.get("address")

            student.father_name = request.form.get("father_name")
            student.father_phone = request.form.get("father_phone")
            student.father_email = request.form.get("father_email")
            student.father_occupation = request.form.get("father_occupation")

            student.mother_name = request.form.get("mother_name")
            student.mother_phone = request.form.get("mother_phone")
            student.mother_email = request.form.get("mother_email")
            student.mother_occupation = request.form.get("mother_occupation")

            student.guardian_name = request.form.get("guardian_name")
            student.guardian_phone = request.form.get("guardian_phone")
            student.guardian_relation = request.form.get("guardian_relation")

            db.session.commit()
            flash("Student and parent information updated successfully.", "success")
            return redirect(url_for("users_page"))

        except Exception:
            db.session.rollback()
            flash("Unable to update student. Check the entered details.", "danger")

    student_teachers = TeachingAssignment.query.filter_by(classroom_id=student.classroom_id).all()
    return render_template(
        "edit_student.html",
        student=student,
        classes=classes,
        student_teachers=student_teachers
    )

@app.route("/teacher/classes")
@login_required
@role_required("TEACHER")
def my_classes_page():
    teacher = current_teacher()
    assignments = TeachingAssignment.query.filter_by(teacher_id=teacher.id).all()
    class_map = {}
    for a in assignments:
        if a.classroom_id not in class_map:
            cnt = StudentProfile.query.filter_by(classroom_id=a.classroom_id).count()
            class_map[a.classroom_id] = {
                "classroom": a.classroom,
                "student_count": cnt,
                "subjects": []
            }
        if a.subject not in class_map[a.classroom_id]["subjects"]:
            class_map[a.classroom_id]["subjects"].append(a.subject)
    classes_data = sorted(class_map.values(), key=lambda x: (x["classroom"].grade, x["classroom"].section))
    return render_template("teacher_classes.html", classes_data=classes_data)

@app.route("/teacher/assignments")
@login_required
@role_required("TEACHER")
def teacher_assignments_page():
    teacher = current_teacher()
    assignments = TeachingAssignment.query.filter_by(teacher_id=teacher.id).all()
    rows = []
    for a in assignments:
        s_count = StudentProfile.query.filter_by(classroom_id=a.classroom_id).count()
        e_count = Exam.query.filter_by(classroom_id=a.classroom_id, subject_id=a.subject_id).count()
        rows.append({
            "assignment": a,
            "student_count": s_count,
            "exam_count": e_count,
        })
    return render_template("teacher_assignments.html", rows=rows)

@app.route("/teacher/students")
@login_required
@role_required("TEACHER")
def my_students_page():
    teacher = current_teacher()
    assignments = TeachingAssignment.query.filter_by(teacher_id=teacher.id).all()
    seen_cids = set()
    teacher_classes = []
    for a in assignments:
        if a.classroom_id not in seen_cids:
            seen_cids.add(a.classroom_id)
            teacher_classes.append(a.classroom)
    teacher_classes.sort(key=lambda c: (c.grade, c.section))

    selected_cid = request.args.get("class", type=int)
    search = request.args.get("q", "").strip()

    if selected_cid:
        if selected_cid not in seen_cids:
            abort(403)
        target_cids = [selected_cid]
    else:
        target_cids = list(seen_cids)

    if not target_cids:
        students = []
    else:
        q_filter = StudentProfile.query.filter(StudentProfile.classroom_id.in_(target_cids))
        if search:
            q_filter = q_filter.filter(
                db.or_(
                    StudentProfile.full_name.ilike(f"%{search}%"),
                    StudentProfile.admission_no.ilike(f"%{search}%"),
                    StudentProfile.roll_no.ilike(f"%{search}%"),
                )
            )
        students = q_filter.all()

        def roll_sort_key(s):
            m = re.search(r"(\d+)$", (s.roll_no or "").strip())
            return (int(m.group(1)) if m else 10**9, s.full_name)

        students.sort(key=roll_sort_key)

    return render_template(
        "teacher_my_students.html",
        students=students,
        teacher_classes=teacher_classes,
        selected_class=selected_cid,
        search=search,
    )

@app.route("/teacher/students/<int:cid>")
@login_required
@role_required("TEACHER")
def teacher_students(cid):
    current_teacher()
    if not assigned(cid): abort(403)
    cls = db.session.get(ClassRoom, cid)
    if not cls: abort(404)
    return render_template("teacher_students.html", classroom=cls, students=class_students(cid))

@app.route("/teacher/attendance/<int:cid>", methods=["GET", "POST"])
@login_required
@role_required("TEACHER")
def attendance_page(cid):
    teacher = current_teacher()
    if not assigned(cid): abort(403)
    cls = db.session.get(ClassRoom, cid)
    if not cls: abort(404)
    students = class_students(cid)

    if request.method == "POST":
        try:
            d = date.fromisoformat(request.form["attendance_date"])
        except (KeyError, ValueError):
            flash("Please choose a valid date.", "danger")
            return redirect(url_for("attendance_page", cid=cid))
        if d > date.today():
            flash("Attendance cannot be marked for a future date.", "danger")
            return redirect(url_for("attendance_page", cid=cid))
        for s in students:
            status = request.form.get(f"status_{s.id}", "Absent")
            if status not in ("Present", "Absent", "Late"): status = "Absent"
            row = Attendance.query.filter_by(student_id=s.id, attendance_date=d).first()
            if row:
                row.status = status
                row.teacher_id = teacher.id
            else:
                db.session.add(Attendance(student_id=s.id, teacher_id=teacher.id,
                                          attendance_date=d, status=status))
        db.session.commit()
        flash(f"Attendance saved for {d.strftime('%d %b %Y')}.", "success")
        return redirect(url_for("attendance_page", cid=cid, date=d.isoformat()))

    try:
        selected = date.fromisoformat(request.args.get("date", ""))
    except ValueError:
        selected = date.today()
    ids = [s.id for s in students]
    existing = {}
    if ids:
        existing = {a.student_id: a.status for a in Attendance.query.filter(
            Attendance.attendance_date == selected, Attendance.student_id.in_(ids)).all()}
    return render_template("attendance.html", classroom=cls, students=students,
                           today=selected, existing=existing, max_date=date.today())

@app.route("/teacher/exams", methods=["GET", "POST"])
@login_required
@role_required("TEACHER")
def exams_page():
    teacher = current_teacher()
    assignments = TeachingAssignment.query.filter_by(teacher_id=teacher.id).all()
    if request.method == "POST":
        try:
            a = db.session.get(TeachingAssignment, int(request.form["assignment_id"]))
            if not a or a.teacher_id != teacher.id: abort(403)
            name = request.form["name"].strip()
            max_marks = float(request.form["max_marks"])
            if not name or max_marks <= 0: raise ValueError()
            raw_date = request.form.get("exam_date")
            raw_room = request.form.get("room", "").strip() or None
            db.session.add(Exam(name=name, classroom_id=a.classroom_id, subject_id=a.subject_id,
                                exam_date=date.fromisoformat(raw_date) if raw_date else None,
                                max_marks=max_marks, room=raw_room))
            db.session.commit()
            flash("Exam created.", "success")
        except (ValueError, KeyError):
            db.session.rollback()
            flash("Please enter a valid exam name, assignment and maximum marks.", "danger")
        return redirect(url_for("exams_page"))

    class_filter = request.args.get("class", type=int) or request.args.get("class_id", type=int)
    subject_filter = request.args.get("subject_id", type=int) or request.args.get("subject", type=int)

    if class_filter and not assigned(class_filter):
        abort(403)
    if subject_filter:
        if class_filter and not assigned(class_filter, subject_filter):
            abort(403)
        elif not any(a.subject_id == subject_filter for a in assignments):
            abort(403)

    exams = []
    if assignments:
        q = Exam.query.filter(db.or_(*[
            db.and_(Exam.classroom_id == a.classroom_id, Exam.subject_id == a.subject_id)
            for a in assignments]))
        if class_filter:
            q = q.filter(Exam.classroom_id == class_filter)
        if subject_filter:
            q = q.filter(Exam.subject_id == subject_filter)
        exams = q.order_by(Exam.id.desc()).all()
    return render_template("exams.html", assignments=assignments, exams=exams,
                           selected_class=class_filter, selected_subject=subject_filter)

@app.route("/teacher/exams/<int:eid>/edit", methods=["GET", "POST"])
@login_required
@role_required("TEACHER")
def edit_exam(eid):
    current_teacher()
    exam = db.session.get(Exam, eid)
    if not exam:
        abort(404)
    if not assigned(exam.classroom_id, exam.subject_id):
        abort(403)

    if request.method == "POST":
        try:
            name = request.form["name"].strip()
            max_marks = float(request.form["max_marks"])
            if not name or max_marks <= 0:
                raise ValueError()
            raw_date = request.form.get("exam_date")
            room = request.form.get("room", "").strip() or None

            highest_mark = db.session.query(db.func.max(Mark.marks_obtained)).filter_by(exam_id=eid).scalar()
            if highest_mark is not None and max_marks < highest_mark:
                flash(f"Maximum marks ({max_marks}) cannot be lower than the highest recorded mark ({highest_mark}).", "danger")
                return redirect(url_for("edit_exam", eid=eid))

            exam.name = name
            exam.exam_date = date.fromisoformat(raw_date) if raw_date else None
            exam.max_marks = max_marks
            exam.room = room
            db.session.commit()
            flash("Exam updated successfully.", "success")
            return redirect(url_for("exams_page"))
        except (ValueError, KeyError):
            db.session.rollback()
            flash("Please enter a valid exam name and maximum marks.", "danger")
            return redirect(url_for("edit_exam", eid=eid))

    return render_template("edit_exam.html", exam=exam)

@app.route("/teacher/exams/<int:eid>/delete", methods=["POST"])
@login_required
@role_required("TEACHER")
def delete_exam(eid):
    current_teacher()
    exam = db.session.get(Exam, eid)
    if not exam:
        abort(404)
    if not assigned(exam.classroom_id, exam.subject_id):
        abort(403)

    if Mark.query.filter_by(exam_id=eid).first() is not None:
        flash("Cannot delete exam because marks have already been recorded.", "danger")
        return redirect(url_for("exams_page"))

    db.session.delete(exam)
    db.session.commit()
    flash("Exam deleted successfully.", "success")
    return redirect(url_for("exams_page"))

@app.route("/teacher/marks/<int:eid>", methods=["GET", "POST"])
@login_required
@role_required("TEACHER")
def marks_page(eid):
    current_teacher()
    exam = db.session.get(Exam, eid)
    if not exam: abort(404)
    if not assigned(exam.classroom_id, exam.subject_id): abort(403)
    students = class_students(exam.classroom_id)
    if request.method == "POST":
        skipped = 0
        for s in students:
            raw = request.form.get(f"mark_{s.id}", "").strip()
            if not raw: continue
            try: val = float(raw)
            except ValueError:
                skipped += 1; continue
            if not 0 <= val <= exam.max_marks:
                skipped += 1; continue
            m = Mark.query.filter_by(exam_id=eid, student_id=s.id).first()
            if m: m.marks_obtained = val
            else: db.session.add(Mark(exam_id=eid, student_id=s.id, marks_obtained=val))
        db.session.commit()
        flash("Marks saved.", "success")
        if skipped:
            flash(f"{skipped} entr{'y was' if skipped == 1 else 'ies were'} skipped (not a number or above max marks).", "warning")
        return redirect(url_for("marks_page", eid=eid))
    old = {m.student_id: m.marks_obtained for m in Mark.query.filter_by(exam_id=eid).all()}
    return render_template("marks.html", exam=exam, students=students, old=old)

@app.cli.command("init-db")
def init_db():
    db.create_all()
    click.echo("Tables created.")

@app.cli.command("add-exam-room-column")
def add_exam_room_column():
    """Add room column to exam table if missing."""
    inspector = inspect(db.engine)
    if "exam" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("exam")]
        if "room" not in columns:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE exam ADD COLUMN room VARCHAR(50) NULL"))
                conn.commit()
            click.echo("Column 'room' added to table 'exam'.")
        else:
            click.echo("Column 'room' already exists on table 'exam'.")
    else:
        click.echo("Table 'exam' does not exist yet. Run init-db first.")

@app.cli.command("seed-school")
def seed_school():
    year="2026-2027"
    for g in range(1,11):
        if not ClassRoom.query.filter_by(grade=g,section="A",academic_year=year).first():
            db.session.add(ClassRoom(grade=g,section="A",academic_year=year))
    for name in ["English","Hindi","Mathematics","Science","Social Science","Computer Science"]:
        if not Subject.query.filter_by(name=name).first():
            db.session.add(Subject(name=name,grades="1-10"))
    db.session.commit()
    click.echo("Added Classes 1–10 (section A) and starter subjects. Customize CBSE subjects to match your school.")

@app.cli.command("create-admin")
@click.option("--username", default=None, help="Admin username")
@click.option("--email", default=None, help="Email (optional)")
@click.option("--password", default=None, help="Password (min 8 chars)")
def create_admin(username, email, password):
    if User.query.filter_by(role="ADMIN").first():
        click.echo("Admin already exists.")
        return

    if not username:
        username = click.prompt("Admin username")
        if email is None:
            email = click.prompt("Email (optional)", default="", show_default=False)
    if not password:
        password = click.prompt(
            "Password",
            hide_input=True,
            confirmation_prompt=True
        )

    if len(password) < 8:
        raise click.ClickException(
            "Password must be at least 8 characters."
        )

    u = User(
        username=username,
        email=email or None,
        role="ADMIN"
    )
    u.set_password(password)

    db.session.add(u)
    db.session.commit()

    click.echo("Admin account created.")


@app.cli.command("reset-student-passwords")
def reset_student_passwords():
    students = User.query.filter_by(role="STUDENT").all()

    for student in students:
        student.set_password("Student@123")

    db.session.commit()

    click.echo(
        f"Updated passwords for {len(students)} students."
    )


@app.cli.command("seed-parent-info")
def seed_parent_info():
    """Add fictional parent information for demo students."""

    father_names = [
        "Ramesh Kumar",
        "Suresh Reddy",
        "Rajesh Sharma",
        "Venkat Rao",
        "Arun Kumar"
    ]

    mother_names = [
        "Lakshmi Devi",
        "Anitha Sharma",
        "Sunitha Rao",
        "Padma Kumari",
        "Geetha Reddy"
    ]

    students = StudentProfile.query.order_by(StudentProfile.id).all()

    for i, student in enumerate(students):
        if not student.father_name:
            student.father_name = father_names[i % len(father_names)]

        if not student.mother_name:
            student.mother_name = mother_names[i % len(mother_names)]

        if not student.father_phone:
            student.father_phone = f"90000000{student.id:02d}"

        if not student.mother_phone:
            student.mother_phone = f"90000001{student.id:02d}"

        if not student.father_email:
            student.father_email = f"father{student.id}@example.com"

        if not student.mother_email:
            student.mother_email = f"mother{student.id}@example.com"

        if not student.father_occupation:
            student.father_occupation = "Business"

        if not student.mother_occupation:
            student.mother_occupation = "Homemaker"

        if not student.guardian_name:
            student.guardian_name = student.father_name

        if not student.guardian_phone:
            student.guardian_phone = student.father_phone

        if not student.guardian_relation:
            student.guardian_relation = "Father"

    db.session.commit()

    click.echo(f"Parent information added for {len(students)} students.")


CBSE_SUBJECTS = [
    ("English", "1-10"), ("Hindi", "1-10"), ("Mathematics", "1-10"),
    ("EVS", "1-5"), ("Science", "3-10"), ("Social Science", "3-10"),
    ("Computer", "1-5"), ("Computer Science", "6-10"), ("Sanskrit", "6-10"),
    ("Art", "1-10"), ("Moral Science", "1-8"), ("Physical Education", "1-10"),
]

def grade_in_range(grades, g):
    """True if class g falls in a range string such as '3-10'."""
    try:
        lo, hi = [int(x) for x in grades.split("-")]
    except ValueError:
        return True
    return lo <= g <= hi

def ensure_subjects():
    """Create any missing CBSE subjects; returns {name: Subject}."""
    out = {}
    for name, grades in CBSE_SUBJECTS:
        sub = Subject.query.filter_by(name=name).first()
        if not sub:
            sub = Subject(name=name, grades=grades)
            db.session.add(sub)
            db.session.flush()
        out[name] = sub
    return out

@app.cli.command("seed-subjects")
def seed_subjects():
    """Add the full CBSE subject list for classes 1-10 (existing subjects are kept, not deleted)."""
    added = 0
    for name, grades in CBSE_SUBJECTS:
        existing = Subject.query.filter_by(name=name).first()
        if existing:
            existing.grades = grades
        else:
            db.session.add(Subject(name=name, grades=grades))
            added += 1
    db.session.commit()
    click.echo(f"Subjects ready. Added {added} new, updated grade ranges on the rest.")


@app.cli.command("seed-teachers")
@click.option("--year", default="2026-2027", show_default=True, help="Academic year of the classes.")
@click.option("--per", type=click.Choice(["class", "band"]), default="class", show_default=True,
              help="class = a different teacher for every subject in every class; "
                   "band = one teacher per subject for classes 1-2, 3-5, 6-8 and 9-10.")
def seed_teachers(year, per):
    """Demo teachers with their own IDs (TCH001...), one shared password, assigned class-wise by subject."""
    password_hash = generate_password_hash("Teacher@123")
    first_names = ["Anil", "Sunita", "Ravi", "Meena", "Kiran", "Deepa", "Suresh", "Lata", "Vijay", "Padma",
                   "Mohan", "Rekha", "Sanjay", "Geeta", "Prakash", "Uma", "Naveen", "Shobha", "Ramesh", "Hema"]
    last_names = ["Sharma", "Reddy", "Rao", "Kumar", "Nair", "Iyer", "Gupta", "Verma", "Das", "Patel",
                  "Singh", "Naidu", "Joshi", "Mehta"]
    subjects = ensure_subjects()

    # Each unit = one teacher: (the classes they teach, their subject)
    units = []
    if per == "class":
        for g in range(1, 11):
            for name, rng in CBSE_SUBJECTS:
                if grade_in_range(rng, g):
                    units.append(([g], name))
    else:
        for lo, hi in [(1, 2), (3, 5), (6, 8), (9, 10)]:
            grades = list(range(lo, hi + 1))
            for name, rng in CBSE_SUBJECTS:
                if all(grade_in_range(rng, g) for g in grades):
                    units.append((grades, name))

    new_teachers = new_assignments = skipped = 0
    for n, (grades, subject_name) in enumerate(units, start=1):
        emp = f"TCH{n:03d}"
        staff = StaffProfile.query.filter_by(employee_id=emp).first()
        if not staff:
            if User.query.filter_by(username=emp).first():
                skipped += 1          # username already used by another account
                continue
            user = User(username=emp, email=None, password_hash=password_hash, role="TEACHER")
            db.session.add(user)
            db.session.flush()
            staff = StaffProfile(
                user_id=user.id, employee_id=emp,
                full_name=f"{first_names[n % len(first_names)]} {last_names[(n * 3) % len(last_names)]}",
                phone=f"9100{n:06d}", designation=f"{subject_name} Teacher",
            )
            db.session.add(staff)
            db.session.flush()
            new_teachers += 1

        for g in grades:
            classes = ClassRoom.query.filter_by(grade=g, academic_year=year).all()
            if not classes:           # class not created yet -> create section A so the teacher has a class
                c = ClassRoom(grade=g, section="A", academic_year=year)
                db.session.add(c)
                db.session.flush()
                classes = [c]
            for c in classes:
                if not TeachingAssignment.query.filter_by(
                        teacher_id=staff.id, classroom_id=c.id, subject_id=subjects[subject_name].id).first():
                    db.session.add(TeachingAssignment(teacher_id=staff.id, classroom_id=c.id,
                                                      subject_id=subjects[subject_name].id))
                    new_assignments += 1

    db.session.commit()
    click.echo(f"Created {new_teachers} teachers and {new_assignments} class-subject assignments "
               f"({per} mode, {len(units)} teachers in total); skipped {skipped}.")
    click.echo("Login: username = teacher ID (TCH001, TCH002 ...), password = Teacher@123")


@app.cli.command("seed-freshers")
@click.option("--sections", default="ABC", show_default=True, help="Sections to create, e.g. A or ABC.")
@click.option("--per-class", default=30, show_default=True, help="Students per class-section.")
def seed_freshers(sections, per_class):
    """Demo students for Classes 1-10 (2026-2027) with logins, parents, marks, attendance and fees."""
    year = "2026-2027"
    sections = "".join(dict.fromkeys(sections.upper().replace(",", "").replace(" ", "")))
    password_hash = generate_password_hash("Student@123")
    first_names = ["Aarav", "Aadhya", "Aanya", "Arjun", "Avni", "Diya", "Dhruv", "Ishaan", "Ira", "Kavya",
                   "Krishna", "Manav", "Meera", "Mihir", "Neha", "Pranav", "Riya", "Rohan", "Sai", "Saanvi",
                   "Tanvi", "Varun", "Vedant", "Vihaan", "Anika", "Charan", "Nandini", "Bhavya", "Kiran", "Lakshmi"]
    last_names = ["Reddy", "Sharma", "Rao", "Kumar", "Patel", "Nair", "Gupta", "Verma", "Iyer", "Das"]
    fathers = ["Ramesh", "Suresh", "Rajesh", "Venkat", "Arun", "Mahesh", "Naresh"]
    mothers = ["Lakshmi", "Anitha", "Sunitha", "Padma", "Geetha", "Sudha", "Rekha"]
    subject_grades = {"Mathematics": "1-10", "English": "1-10", "EVS": "1-5", "Science": "3-10"}

    subjects = {}
    for name, grades in subject_grades.items():
        sub = Subject.query.filter_by(name=name).first()
        if not sub:
            sub = Subject(name=name, grades=grades)
            db.session.add(sub)
            db.session.flush()
        subjects[name] = sub

    teacher = StaffProfile.query.first()   # attendance rows need a teacher on record
    created = skipped = counter = 0

    for grade in range(1, 11):
        # Classes 1-2 use EVS; Classes 3-10 use Science
        test_subjects = ["Mathematics", "English", "EVS" if grade <= 2 else "Science"]

        for sec_index, sec in enumerate(sections):
            cls = ClassRoom.query.filter_by(grade=grade, section=sec, academic_year=year).first()
            if not cls:
                cls = ClassRoom(grade=grade, section=sec, academic_year=year)
                db.session.add(cls)
                db.session.flush()

            exams = {}
            for name in test_subjects:
                ex = Exam.query.filter_by(name="Unit Test 1", classroom_id=cls.id,
                                          subject_id=subjects[name].id).first()
                if not ex:
                    ex = Exam(name="Unit Test 1", classroom_id=cls.id, subject_id=subjects[name].id,
                              exam_date=date(2026, 4, 15), max_marks=50)
                    db.session.add(ex)
                    db.session.flush()
                exams[name] = ex

            for i in range(1, per_class + 1):
                counter += 1
                roll = f"2026-{grade}{sec}-{i:02d}"
                if User.query.filter_by(username=roll).first() or \
                   StudentProfile.query.filter_by(admission_no=roll).first():
                    skipped += 1
                    continue

                user = User(username=roll, email=None, password_hash=password_hash, role="STUDENT")
                db.session.add(user)
                db.session.flush()

                idx = (i - 1) + sec_index * 3 + grade
                last = last_names[idx % len(last_names)]
                father = f"{fathers[idx % len(fathers)]} {last}"
                mother = f"{mothers[idx % len(mothers)]} {last}"
                phone_no = counter % 1000
                student = StudentProfile(
                    user_id=user.id, admission_no=roll, roll_no=roll,
                    full_name=f"{first_names[(i - 1 + grade) % len(first_names)]} {last}",
                    classroom_id=cls.id,
                    father_name=father, father_phone=f"8000000{phone_no:03d}",
                    mother_name=mother, mother_phone=f"8000001{phone_no:03d}",
                    guardian_name=father, guardian_phone=f"8000000{phone_no:03d}",
                    guardian_relation="Father",
                )
                db.session.add(student)
                db.session.flush()

                for n, name in enumerate(test_subjects):
                    db.session.add(Mark(exam_id=exams[name].id, student_id=student.id,
                                        marks_obtained=30 + ((i * 7 + grade * 3 + n * 5) % 20)))

                if teacher:
                    for day in (2, 3, 4):
                        db.session.add(Attendance(student_id=student.id, teacher_id=teacher.id,
                                                  attendance_date=date(2026, 4, day), status="Present"))

                fee = FeeRecord(student_id=student.id, academic_year=year, total_fee=Decimal("30000.00"))
                db.session.add(fee)
                db.session.flush()
                db.session.add(FeePayment(fee_record_id=fee.id, amount=Decimal("25000.00"),
                                          payment_date=date(2026, 4, 2), receipt_no=f"RCPT-{roll}"))
                created += 1

        db.session.commit()   # commit per class so a long run is never lost half-way

    click.echo(f"Created {created} students across Classes 1-10 (sections {sections}); skipped {skipped} existing.")
    click.echo("Login: username = roll number (e.g. 2026-5A-01 or 2026-10A-07), password = Student@123")
    if not teacher:
        click.echo("No teacher exists yet, so attendance was not added for these students.")