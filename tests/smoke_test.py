import os
import sys
import re
from datetime import date, timedelta
from decimal import Decimal

# Force test database
os.environ["DB_NAME"] = "school_erp_test"

# Add workspace to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import (
    app, db, User, ClassRoom, Subject, StaffProfile, TeachingAssignment,
    StudentProfile, Attendance, Exam, Mark, FeeRecord, FeePayment,
    init_db, add_exam_room_column, seed_school, seed_subjects,
    seed_teachers, seed_freshers, create_admin
)

assert "school_erp_test" in app.config["SQLALCHEMY_DATABASE_URI"], "ERROR: Not connected to school_erp_test!"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def run_tests():
    print("=" * 70)
    print("RUNNING SMOKE TEST SUITE ON DATABASE: school_erp_test")
    print("=" * 70)

    # 1. SETUP TEST DATABASE
    with app.app_context():
        log("Recreating tables on school_erp_test...")
        db.drop_all()
        db.create_all()
        log("Tables created successfully.")

        # Test CLI commands
        log("Running add-exam-room-column CLI...")
        app.test_cli_runner().invoke(add_exam_room_column)

        log("Running seed-school...")
        app.test_cli_runner().invoke(seed_school)

        log("Running seed-subjects...")
        app.test_cli_runner().invoke(seed_subjects)

        log("Creating non-interactive admin (admin / Admin@12345)...")
        res = app.test_cli_runner().invoke(create_admin, ["--username", "admin", "--password", "Admin@12345"])
        assert res.exit_code == 0, f"create-admin failed: {res.output}"

        log("Running seed-teachers (class mode)...")
        res = app.test_cli_runner().invoke(seed_teachers, ["--per", "class"])
        assert res.exit_code == 0, f"seed-teachers failed: {res.output}"

        log("Running seed-freshers (sections ABC, 30 per class)...")
        res = app.test_cli_runner().invoke(seed_freshers, ["--sections", "ABC", "--per-class", "30"])
        assert res.exit_code == 0, f"seed-freshers failed: {res.output}"

        # 2. TEST RE-RUNNING SEED COMMANDS TWICE CAUSES NO DUPLICATES
        log("Testing idempotency: re-running seed commands...")
        c_count_before = ClassRoom.query.count()
        s_count_before = Subject.query.count()
        t_count_before = StaffProfile.query.count()
        st_count_before = StudentProfile.query.count()

        app.test_cli_runner().invoke(seed_school)
        app.test_cli_runner().invoke(seed_subjects)
        app.test_cli_runner().invoke(seed_teachers, ["--per", "class"])
        app.test_cli_runner().invoke(seed_freshers, ["--sections", "ABC", "--per-class", "30"])

        assert ClassRoom.query.count() == c_count_before, "Duplicate classrooms created on re-seed!"
        assert Subject.query.count() == s_count_before, "Duplicate subjects created on re-seed!"
        assert StaffProfile.query.count() == t_count_before, "Duplicate teachers created on re-seed!"
        assert StudentProfile.query.count() == st_count_before, "Duplicate students created on re-seed!"
        log("Idempotency test passed: 0 duplicates on re-seed.", "PASS")

    # 3. TEST CSRF REJECTION
    log("Testing CSRF protection...")
    app.config["WTF_CSRF_ENABLED"] = True
    with app.test_client() as client:
        # POST without CSRF token should be rejected (400 Bad Request)
        resp = client.post("/login", data={"username": "admin", "password": "wrong", "role": "ADMIN"})
        assert resp.status_code == 400, f"Expected 400 without CSRF token, got {resp.status_code}"
        log("CSRF rejection test passed: POST without token returned 400.", "PASS")

    # Disable CSRF for subsequent client testing
    app.config["WTF_CSRF_ENABLED"] = False

    # Helper login function
    def login(client, username, password, role):
        return client.post("/login", data={"username": username, "password": password, "role": role}, follow_redirects=True)

    def logout(client):
        return client.get("/logout", follow_redirects=True)

    # 4. TEST ROLE AUTHORIZATION (200 for correct role, 403 for wrong role, 302 for unauthenticated)
    log("Testing role authorization across existing and new pages...")
    admin_urls = [
        "/admin",
        "/admin/students/new",
        "/admin/assign",
        "/admin/users",
        "/admin/classes",
        "/admin/subjects",
        "/admin/assignments",
        "/admin/fees"
    ]

    with app.test_client() as client:
        # Unauthenticated access to admin and teacher pages
        for u in admin_urls:
            r = client.get(u)
            assert r.status_code in [302, 401], f"Unauthenticated access to {u} should redirect to login, got {r.status_code}"

        # Login as student
        login(client, "2026-1A-01", "Student@123", "STUDENT")
        for u in admin_urls:
            r = client.get(u)
            assert r.status_code == 403, f"Student accessing {u} should be 403, got {r.status_code}"

        r = client.get("/teacher")
        assert r.status_code == 403, f"Student accessing /teacher should be 403, got {r.status_code}"
        r = client.get("/teacher/classes")
        assert r.status_code == 403, f"Student accessing /teacher/classes should be 403, got {r.status_code}"
        r = client.get("/student")
        assert r.status_code == 200, f"Student accessing /student should be 200, got {r.status_code}"
        logout(client)

        # Login as teacher
        login(client, "TCH001", "Teacher@123", "TEACHER")
        for u in admin_urls:
            r = client.get(u)
            assert r.status_code == 403, f"Teacher accessing {u} should be 403, got {r.status_code}"
        r = client.get("/student")
        assert r.status_code == 403, f"Teacher accessing /student should be 403, got {r.status_code}"
        logout(client)

        # Login as admin
        login(client, "admin", "Admin@12345", "ADMIN")
        for u in admin_urls:
            r = client.get(u)
            assert r.status_code == 200, f"Admin accessing {u} should be 200, got {r.status_code}"
        r = client.get("/teacher")
        assert r.status_code == 403, f"Admin accessing /teacher should be 403, got {r.status_code}"
        r = client.get("/student")
        assert r.status_code == 403, f"Admin accessing /student should be 403, got {r.status_code}"
        logout(client)

    log("Role authorization test passed for all routes.", "PASS")

    # 5. TEST 3 DIFFERENT TEACHERS (TCH001, TCH020, TCH060)
    log("Testing 3 distinct teachers (TCH001, TCH020, TCH060)...")
    with app.app_context():
        teachers_to_test = ["TCH001", "TCH020", "TCH060"]
        for tch_id in teachers_to_test:
            log(f"Testing teacher {tch_id}...")
            staff = StaffProfile.query.filter_by(employee_id=tch_id).first()
            assert staff is not None, f"Teacher {tch_id} not found!"
            assigned_cids = {a.classroom_id for a in TeachingAssignment.query.filter_by(teacher_id=staff.id).all()}
            assigned_sids = {a.subject_id for a in TeachingAssignment.query.filter_by(teacher_id=staff.id).all()}
            unassigned_cls = ClassRoom.query.filter(~ClassRoom.id.in_(assigned_cids)).first()
            assert unassigned_cls is not None, "Need at least one unassigned classroom for negative testing."

            with app.test_client() as client:
                login(client, tch_id, "Teacher@123", "TEACHER")

                # Verify My Classes page renders and shows their classes
                r = client.get("/teacher/classes")
                assert r.status_code == 200
                html = r.get_data(as_text=True)
                for cid in assigned_cids:
                    cls = db.session.get(ClassRoom, cid)
                    assert cls.label in html, f"Teacher {tch_id} should see class {cls.label}"

                # Verify Teaching Assignments page renders
                r = client.get("/teacher/assignments")
                assert r.status_code == 200

                # Verify My Students page renders and filters
                r = client.get("/teacher/students")
                assert r.status_code == 200
                first_cid = list(assigned_cids)[0]
                r_filter = client.get(f"/teacher/students?class={first_cid}")
                assert r_filter.status_code == 200

                # Create exam with room
                first_assign = TeachingAssignment.query.filter_by(teacher_id=staff.id).first()
                exam_name = f"Midterm {tch_id}"
                room_name = f"Hall-{tch_id}"
                post_exam = client.post("/teacher/exams", data={
                    "assignment_id": first_assign.id,
                    "name": exam_name,
                    "exam_date": date.today().isoformat(),
                    "max_marks": 100,
                    "room": room_name
                }, follow_redirects=True)
                assert post_exam.status_code == 200
                assert exam_name in post_exam.get_data(as_text=True)
                assert room_name in post_exam.get_data(as_text=True)

                created_exam = Exam.query.filter_by(name=exam_name, classroom_id=first_assign.classroom_id).first()
                assert created_exam is not None
                assert created_exam.room == room_name

                # Marks page shows room
                r_marks = client.get(f"/teacher/marks/{created_exam.id}")
                assert r_marks.status_code == 200
                assert room_name in r_marks.get_data(as_text=True)

                # Enter marks
                cls_students = StudentProfile.query.filter_by(classroom_id=first_assign.classroom_id).all()
                assert len(cls_students) > 0
                st1 = cls_students[0]
                post_marks = client.post(f"/teacher/marks/{created_exam.id}", data={
                    f"mark_{st1.id}": "85.5"
                }, follow_redirects=True)
                assert post_marks.status_code == 200

                # Verify mark was saved
                saved_mark = Mark.query.filter_by(exam_id=created_exam.id, student_id=st1.id).first()
                assert saved_mark is not None and saved_mark.marks_obtained == 85.5

                # Negative test: Edit exam - reject max_marks lower than recorded mark (e.g. 50 < 85.5)
                edit_bad = client.post(f"/teacher/exams/{created_exam.id}/edit", data={
                    "name": exam_name,
                    "exam_date": date.today().isoformat(),
                    "max_marks": 50,
                    "room": "Room-Updated"
                }, follow_redirects=True)
                assert "cannot be lower" in edit_bad.get_data(as_text=True).lower()
                db.session.refresh(created_exam)
                assert created_exam.max_marks == 100

                # Edit exam - valid update (max_marks = 95 >= 85.5)
                edit_good = client.post(f"/teacher/exams/{created_exam.id}/edit", data={
                    "name": f"{exam_name} Edited",
                    "exam_date": date.today().isoformat(),
                    "max_marks": 95,
                    "room": f"{room_name}-Updated"
                }, follow_redirects=True)
                assert edit_good.status_code == 200
                db.session.refresh(created_exam)
                assert created_exam.max_marks == 95
                assert created_exam.room == f"{room_name}-Updated"

                # Try to delete exam when marks exist -> blocked
                del_resp = client.post(f"/teacher/exams/{created_exam.id}/delete", follow_redirects=True)
                assert "cannot delete exam" in del_resp.get_data(as_text=True).lower()
                assert db.session.get(Exam, created_exam.id) is not None

                # Create empty exam and confirm delete succeeds
                client.post("/teacher/exams", data={
                    "assignment_id": first_assign.id,
                    "name": f"Empty Exam {tch_id}",
                    "exam_date": date.today().isoformat(),
                    "max_marks": 50,
                    "room": "Room-Empty"
                }, follow_redirects=True)
                empty_exam = Exam.query.filter_by(name=f"Empty Exam {tch_id}").first()
                assert empty_exam is not None
                del_empty = client.post(f"/teacher/exams/{empty_exam.id}/delete", follow_redirects=True)
                assert del_empty.status_code == 200
                assert db.session.get(Exam, empty_exam.id) is None

                # Attendance: save attendance, reload date, edit it
                att_date = date.today()
                post_att = client.post(f"/teacher/attendance/{first_assign.classroom_id}", data={
                    "attendance_date": att_date.isoformat(),
                    f"status_{st1.id}": "Present"
                }, follow_redirects=True)
                assert post_att.status_code == 200
                att_row = Attendance.query.filter_by(student_id=st1.id, attendance_date=att_date).first()
                assert att_row is not None and att_row.status == "Present"

                # Reload and edit attendance
                edit_att = client.post(f"/teacher/attendance/{first_assign.classroom_id}", data={
                    "attendance_date": att_date.isoformat(),
                    f"status_{st1.id}": "Late"
                }, follow_redirects=True)
                assert edit_att.status_code == 200
                db.session.refresh(att_row)
                assert att_row.status == "Late"

                logout(client)

    log("Teacher module tests passed for all 3 teachers.", "PASS")

    # 6. NEGATIVE TESTS
    log("Running negative tests...")
    with app.app_context():
        t1 = StaffProfile.query.filter_by(employee_id="TCH001").first()
        t1_cids = {a.classroom_id for a in TeachingAssignment.query.filter_by(teacher_id=t1.id).all()}
        other_cls = ClassRoom.query.filter(~ClassRoom.id.in_(t1_cids)).first()
        assert other_cls is not None

        with app.test_client() as client:
            login(client, "TCH001", "Teacher@123", "TEACHER")

            # Accessing unassigned class
            r = client.get(f"/teacher/students/{other_cls.id}")
            assert r.status_code == 403, f"Expected 403 for unassigned class, got {r.status_code}"

            r = client.get(f"/teacher/attendance/{other_cls.id}")
            assert r.status_code == 403, f"Expected 403 for unassigned attendance, got {r.status_code}"

            r = client.get(f"/teacher/students?class={other_cls.id}")
            assert r.status_code == 403, f"Expected 403 for unassigned student class filter, got {r.status_code}"

            r = client.get(f"/teacher/exams?class_id={other_cls.id}")
            assert r.status_code == 403, f"Expected 403 for unassigned exam class filter, got {r.status_code}"

            # Unassigned exam returns 403
            other_exam = Exam.query.filter(~Exam.classroom_id.in_(t1_cids)).first()
            if other_exam:
                r_unassigned_exam = client.get(f"/teacher/marks/{other_exam.id}")
                assert r_unassigned_exam.status_code == 403, f"Expected 403 for other teacher exam, got {r_unassigned_exam.status_code}"

                r_unassigned_edit = client.get(f"/teacher/exams/{other_exam.id}/edit")
                assert r_unassigned_edit.status_code == 403, f"Expected 403 for other teacher exam edit, got {r_unassigned_edit.status_code}"

            # Future attendance date rejection
            future_d = (date.today() + timedelta(days=2)).isoformat()
            first_cid = list(t1_cids)[0]
            r_fut = client.post(f"/teacher/attendance/{first_cid}", data={
                "attendance_date": future_d
            }, follow_redirects=True)
            assert "future date" in r_fut.get_data(as_text=True).lower()

            # Mark above maximum marks rejected
            t1_assign = TeachingAssignment.query.filter_by(teacher_id=t1.id).first()
            ex = Exam.query.filter_by(classroom_id=t1_assign.classroom_id, subject_id=t1_assign.subject_id).first()
            if not ex:
                ex = Exam(name="Test Max Exam", classroom_id=t1_assign.classroom_id, subject_id=t1_assign.subject_id, max_marks=50)
                db.session.add(ex)
                db.session.commit()
            st = StudentProfile.query.filter_by(classroom_id=t1_assign.classroom_id).first()
            r_mark_high = client.post(f"/teacher/marks/{ex.id}", data={
                f"mark_{st.id}": str(ex.max_marks + 50)
            }, follow_redirects=True)
            assert "skipped" in r_mark_high.get_data(as_text=True).lower()

            logout(client)

    log("Negative tests passed.", "PASS")

    # 7. ADMIN TESTS (Add Student, Validation Rollback, Bulk Assign, Delete Assignment, Deactivated User)
    log("Running Admin tests...")
    with app.app_context():
        with app.test_client() as client:
            login(client, "admin", "Admin@12345", "ADMIN")

            # 7a. Add student with full parent details
            student_payload = {
                "username": "2026-TEST-ADMIT",
                "password": "Password@123",
                "email": "testadmit@example.com",
                "full_name": "Test Admission Student",
                "admission_no": "ADM-TEST-9999",
                "roll_no": "2026-1A-99",
                "classroom_id": 1,
                "date_of_birth": "2015-05-12",
                "gender": "Male",
                "phone": "9876543210",
                "address": "123 School Lane",
                "father_name": "Father Test",
                "father_phone": "9876543211",
                "father_email": "father_test@example.com",
                "father_occupation": "Scientist",
                "mother_name": "Mother Test",
                "mother_phone": "9876543212",
                "mother_email": "mother_test@example.com",
                "mother_occupation": "Doctor",
                "guardian_name": "Guardian Test",
                "guardian_phone": "9876543213",
                "guardian_relation": "Uncle"
            }

            r_add = client.post("/admin/students/new", data=student_payload, follow_redirects=True)
            assert r_add.status_code == 200
            assert "created successfully" in r_add.get_data(as_text=True).lower()

            # Confirm student can log in
            logout(client)
            login_stu = login(client, "2026-TEST-ADMIT", "Password@123", "STUDENT")
            assert login_stu.status_code == 200
            stu_dash = client.get("/student")
            assert stu_dash.status_code == 200
            dash_html = stu_dash.get_data(as_text=True)
            assert "Father Test" in dash_html
            assert "Mother Test" in dash_html
            assert "Guardian Test" in dash_html
            assert "9876543211" in dash_html
            logout(client)

            # Confirm student is visible to teachers of Class 1
            tch1 = TeachingAssignment.query.filter_by(classroom_id=1).first().teacher
            login(client, tch1.employee_id, "Teacher@123", "TEACHER")
            r_tch_stu = client.get("/teacher/students")
            assert "Test Admission Student" in r_tch_stu.get_data(as_text=True)
            logout(client)

            # 7b. Validation & Rollback tests
            login(client, "admin", "Admin@12345", "ADMIN")

            # Duplicate username
            bad1 = student_payload.copy()
            bad1["admission_no"] = "ADM-DIFF-001"
            bad1["roll_no"] = "2026-1A-98"
            r_dup_user = client.post("/admin/students/new", data=bad1, follow_redirects=True)
            assert "username already exists" in r_dup_user.get_data(as_text=True).lower()
            assert StudentProfile.query.filter_by(admission_no="ADM-DIFF-001").first() is None, "Partial record created on duplicate username!"

            # Duplicate admission number
            bad2 = student_payload.copy()
            bad2["username"] = "diff_user_01"
            r_dup_adm = client.post("/admin/students/new", data=bad2, follow_redirects=True)
            assert "admission number already exists" in r_dup_adm.get_data(as_text=True).lower()
            assert User.query.filter_by(username="diff_user_01").first() is None, "Partial record created on duplicate admission no!"

            # Duplicate roll number in same class
            bad3 = student_payload.copy()
            bad3["username"] = "diff_user_02"
            bad3["admission_no"] = "ADM-DIFF-002"
            # roll_no is already 2026-1A-99 in class 1
            r_dup_roll = client.post("/admin/students/new", data=bad3, follow_redirects=True)
            assert "roll number already exists" in r_dup_roll.get_data(as_text=True).lower()
            assert User.query.filter_by(username="diff_user_02").first() is None

            # Bad phone format (letters or wrong length)
            bad4 = student_payload.copy()
            bad4["username"] = "diff_user_03"
            bad4["admission_no"] = "ADM-DIFF-003"
            bad4["roll_no"] = "2026-1A-97"
            bad4["father_phone"] = "abc12345"
            r_bad_phone = client.post("/admin/students/new", data=bad4, follow_redirects=True)
            assert "digits" in r_bad_phone.get_data(as_text=True).lower()
            assert User.query.filter_by(username="diff_user_03").first() is None

            # Bad email format
            bad5 = student_payload.copy()
            bad5["username"] = "diff_user_04"
            bad5["admission_no"] = "ADM-DIFF-004"
            bad5["roll_no"] = "2026-1A-96"
            bad5["email"] = "not-an-email"
            r_bad_email = client.post("/admin/students/new", data=bad5, follow_redirects=True)
            assert "invalid" in r_bad_email.get_data(as_text=True).lower()
            assert User.query.filter_by(username="diff_user_04").first() is None

            # 7c. Bulk assign 1 teacher to 2 classes x 2 subjects
            tch = StaffProfile.query.filter_by(employee_id="TCH090").first()
            # Clean any existing assignments for TCH090 for this test
            TeachingAssignment.query.filter_by(teacher_id=tch.id).delete()
            db.session.commit()

            c1, c2 = ClassRoom.query.all()[:2]
            s1, s2 = Subject.query.all()[:2]

            post_bulk = client.post("/admin/assign", data={
                "teacher_id": tch.id,
                "classroom_ids": [c1.id, c2.id],
                "subject_ids": [s1.id, s2.id]
            }, follow_redirects=True)
            assert "4 created, 0 already existed" in post_bulk.get_data(as_text=True)

            # Running it again creates 0 and reports 4 existed
            post_bulk2 = client.post("/admin/assign", data={
                "teacher_id": tch.id,
                "classroom_ids": [c1.id, c2.id],
                "subject_ids": [s1.id, s2.id]
            }, follow_redirects=True)
            assert "0 created, 4 already existed" in post_bulk2.get_data(as_text=True)

            # Test removing an assignment
            asgn_to_del = TeachingAssignment.query.filter_by(teacher_id=tch.id, classroom_id=c1.id, subject_id=s1.id).first()
            assert asgn_to_del is not None
            r_del_asgn = client.post(f"/admin/assignments/{asgn_to_del.id}/delete", follow_redirects=True)
            assert r_del_asgn.status_code == 200
            assert db.session.get(TeachingAssignment, asgn_to_del.id) is None
            log("Bulk assign and remove assignment tested successfully.", "PASS")

            # 7d. Deactivated users cannot log in
            user_deact = User.query.filter_by(username="TCH090").first()
            user_deact.active = False
            db.session.commit()

            logout(client)
            r_deact_login = login(client, "TCH090", "Teacher@123", "TEACHER")
            assert "invalid" in r_deact_login.get_data(as_text=True).lower()
            # Restore user
            user_deact.active = True
            db.session.commit()
            log("Deactivated user test passed.", "PASS")

    # 8. STUDENTS FROM CLASS 1-A, 5-A, 9-A TEST
    log("Testing Student Dashboard for Class 1-A, 5-A, and 9-A...")
    sample_students = ["2026-1A-01", "2026-5A-01", "2026-9A-01"]
    with app.app_context():
        with app.test_client() as client:
            for roll in sample_students:
                log(f"Checking student {roll}...")
                login(client, roll, "Student@123", "STUDENT")
                resp = client.get("/student")
                assert resp.status_code == 200
                html = resp.get_data(as_text=True)

                # Check student profile info
                sp = StudentProfile.query.filter_by(admission_no=roll).first()
                assert sp is not None, f"Student {roll} not found in DB"
                assert sp.full_name in html, f"Student name {sp.full_name} not found in HTML"
                assert sp.classroom.label in html, f"Classroom {sp.classroom.label} not found in HTML"
                assert "Parent" in html and "Guardian" in html
                assert (sp.father_name or "") in html
                assert (sp.mother_name or "") in html
                assert "Academic Performance" in html
                assert "Attendance Records" in html
                assert "Fee Details" in html

                logout(client)
    log("Students from Class 1-A, 5-A, and 9-A verified successfully.", "PASS")

    # 9. PY_COMPILE, TEMPLATE PARSING, AND DEBUG PRINTS CHECK
    log("Checking py_compile, Jinja templates, and debug prints...")
    import py_compile
    py_compile.compile("app.py", doraise=True)

    import jinja2, glob
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
    for path in glob.glob('templates/*.html'):
        env.get_template(path.split('/')[-1])

    with open("app.py") as f:
        content = f.read()
        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("print(") or (" print(" in line and not "#" in line[:line.find("print(")]):
                raise AssertionError(f"Debug print found at app.py line {idx}: {line}")

    log("py_compile, templates, and no-debug-prints verified.", "PASS")

    print("=" * 70)
    print("ALL SMOKE TESTS PASSED SUCCESSFULLY ON school_erp_test!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
