import re
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import check_password_hash

from app import create_app, db
from app.models import Course, Enrollment, User
from app.seed import seed_demo


class AdminFlowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": False,
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        seed_demo()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def login(self, username):
        return self.client.post("/login", data={
            "username": username, "password": "demo-password",
        }, follow_redirects=True)

    def test_seed_and_repeat_protection(self):
        courses = db.session.execute(db.select(Course)).scalars().all()
        self.assertEqual(
            {course.name: (len(course.enrollments), course.capacity) for course in courses},
            {"Math 101": (4, 8), "Physics 121": (5, 10), "CS 106": (4, 10), "CS 162": (4, 4)},
        )
        result = self.app.test_cli_runner().invoke(args=["seed-demo"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("empty database", result.output)

    def test_authentication_and_admin_access(self):
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.assertEqual(self.client.get("/admin/user/").status_code, 302)
        response = self.client.post("/login", data={"username": "admin", "password": "wrong"})
        self.assertIn(b"Invalid username or password", response.data)
        self.login("mnorris")
        for path in ("/admin/", "/admin/user/", "/admin/course/new/", "/admin/enrollment/"):
            self.assertEqual(self.client.get(path).status_code, 403)
        self.client.post("/logout")
        response = self.login("admin")
        self.assertIn(b"Administration", response.data)
        self.assertEqual(self.client.get("/admin/user/").status_code, 200)

    def test_admin_crud_and_password_hash(self):
        self.login("admin")
        response = self.client.post("/admin/user/new/", data={
            "username": "newstudent", "display_name": "New Student",
            "role": "student", "password": "test-password",
        }, follow_redirects=True)
        self.assertNotIn(b"Failed to create record", response.data)
        student = db.session.execute(db.select(User).filter_by(username="newstudent")).scalar_one()
        self.assertTrue(check_password_hash(student.password_hash, "test-password"))
        self.assertNotIn(b"test-password", self.client.get("/admin/user/").data)
        details = self.client.get(f"/admin/user/details/?id={student.id}")
        self.assertNotIn(student.password_hash.encode(), details.data)
        self.client.post(f"/admin/user/edit/?id={student.id}", data={
            "username": "newstudent", "display_name": "Updated Student",
            "role": "student", "password": "",
        }, follow_redirects=True)
        db.session.expire_all()
        self.assertEqual(student.display_name, "Updated Student")
        self.assertTrue(check_password_hash(student.password_hash, "test-password"))
        teacher = db.session.execute(db.select(User).filter_by(username="ahepworth")).scalar_one()
        self.client.post("/admin/course/new/", data={
            "name": "Test 100", "teacher": str(teacher.id), "time": "Monday", "capacity": "1",
        }, follow_redirects=True)
        course = db.session.execute(db.select(Course).filter_by(name="Test 100")).scalar_one()
        response = self.client.post("/admin/enrollment/new/", data={
            "student": str(student.id), "course": str(course.id), "grade": "85",
        }, follow_redirects=True)
        self.assertNotIn(b"Failed to create record", response.data)
        enrollment = db.session.execute(db.select(Enrollment).filter_by(
            student_id=student.id, course_id=course.id
        )).scalar_one()
        self.client.post(f"/admin/enrollment/edit/?id={enrollment.id}", data={
            "student": str(student.id), "course": str(course.id), "grade": "95",
        }, follow_redirects=True)
        db.session.expire_all()
        self.assertEqual(db.session.get(Enrollment, enrollment.id).grade, 95)
        for model, path, record_id in (
            (Enrollment, "enrollment", enrollment.id),
            (Course, "course", course.id),
            (User, "user", student.id),
        ):
            self.client.post(f"/admin/{path}/delete/", data={"id": str(record_id)}, follow_redirects=True)
            self.assertIsNone(db.session.get(model, record_id))

    def test_admin_rejects_full_course_and_role_change(self):
        self.login("admin")
        student = db.session.execute(db.select(User).filter_by(username="mnorris")).scalar_one()
        course = db.session.execute(db.select(Course).filter_by(name="CS 162")).scalar_one()
        response = self.client.post("/admin/enrollment/new/", data={
            "student": str(student.id), "course": str(course.id), "grade": "",
        }, follow_redirects=True)
        self.assertIn(b"The course is full", response.data)
        self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(Enrollment).where(
            Enrollment.course_id == course.id
        )), 4)
        response = self.client.post(f"/admin/user/edit/?id={student.id}", data={
            "username": student.username, "display_name": student.display_name,
            "role": "teacher", "password": "",
        }, follow_redirects=True)
        self.assertIn(b"Remove this user", response.data)
        db.session.expire_all()
        self.assertEqual(db.session.get(User, student.id).role, "student")

    def test_existing_full_course_enrollment_can_be_edited_and_references_are_protected(self):
        self.login("admin")
        course = db.session.execute(db.select(Course).filter_by(name="CS 162")).scalar_one()
        enrollment = course.enrollments[0]
        response = self.client.post(f"/admin/enrollment/edit/?id={enrollment.id}", data={
            "student": str(enrollment.student_id), "course": str(course.id), "grade": "90",
        }, follow_redirects=True)
        self.assertNotIn(b"Failed to update record", response.data)
        db.session.expire_all()
        self.assertEqual(db.session.get(Enrollment, enrollment.id).grade, 90)
        response = self.client.post("/admin/course/delete/", data={"id": str(course.id)}, follow_redirects=True)
        self.assertIn(b"FOREIGN KEY constraint failed", response.data)
        self.assertIsNotNone(db.session.get(Course, course.id))

    def test_csrf_required_for_admin_mutations(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        login_page = self.client.get("/login")
        token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', login_page.data).group(1).decode()
        self.client.post("/login", data={
            "username": "admin", "password": "demo-password", "csrf_token": token,
        })
        self.assertEqual(self.client.post("/admin/user/delete/", data={"id": "1"}).status_code, 400)
        page = self.client.get("/admin/user/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'name="csrf_token"', page.data)
        create_page = self.client.get("/admin/user/new/")
        token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', create_page.data).group(1).decode()
        response = self.client.post("/admin/user/new/", data={
            "username": "csrfuser", "display_name": "CSRF User", "role": "student",
            "password": "test-password", "csrf_token": token,
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        user = db.session.execute(db.select(User).filter_by(username="csrfuser")).scalar_one()
        response = self.client.post("/admin/user/delete/", data={
            "id": str(user.id), "csrf_token": token,
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(db.session.get(User, user.id))


class PersistenceTests(unittest.TestCase):
    def test_cli_seed_persists_across_app_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {
                "TESTING": True,
                "SECRET_KEY": "test-key",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{Path(directory) / 'test.db'}",
            }
            first = create_app(config)
            runner = first.test_cli_runner()
            self.assertEqual(runner.invoke(args=["init-db"]).exit_code, 0)
            self.assertEqual(runner.invoke(args=["seed-demo"]).exit_code, 0)
            second = create_app(config)
            with second.app_context():
                self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(Enrollment)), 17)
                self.assertIsNotNone(db.session.execute(db.select(User).filter_by(username="admin")).scalar_one_or_none())
                db.session.remove()
            with first.app_context():
                db.engine.dispose()
            with second.app_context():
                db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
