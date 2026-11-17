import unittest

from app import create_app, db
from app.models import Course, Enrollment, User
from app.seed import seed_demo


class TeacherTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "k", "SQLALCHEMY_DATABASE_URI": "sqlite://",
                               "WTF_CSRF_ENABLED": False})
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        seed_demo()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, username):
        return self.client.post("/login", data={"username": username, "password": "demo-password"})

    def course(self, name):
        return db.session.execute(db.select(Course).filter_by(name=name)).scalar_one()

    def enrollment(self, course_name, username):
        return db.session.execute(
            db.select(Enrollment).join(User, Enrollment.student_id == User.id)
            .where(Enrollment.course_id == self.course(course_name).id, User.username == username)
        ).scalar_one()

    def test_teacher_routed_to_dashboard_and_sees_only_own_courses(self):
        self.login("ahepworth")
        self.assertIn("/teacher", self.client.get("/").headers["Location"])
        self.assertEqual(self.client.get("/teacher").status_code, 200)
        data = self.client.get("/api/teacher/courses").get_json()
        self.assertEqual({c["name"]: (c["enrolled"], c["capacity"]) for c in data},
                         {"CS 106": (4, 10), "CS 162": (4, 4)})

    def test_roster_lists_students_and_grades(self):
        self.login("ahepworth")
        r = self.client.get(f"/api/teacher/courses/{self.course('CS 162').id}/students").get_json()
        self.assertEqual(r["course"]["name"], "CS 162")
        self.assertEqual({s["name"]: s["grade"] for s in r["students"]},
                         {"Aditya Ranganath": 99, "Nancy Little": 87, "Yi Wen Chen": 92, "John Stuart": 67})

    def test_edit_and_clear_grade(self):
        self.login("ahepworth")
        e = self.enrollment("CS 162", "nlittle")
        r = self.client.patch(f"/api/teacher/enrollments/{e.id}", json={"grade": 100})
        self.assertEqual(r.status_code, 200)
        db.session.expire_all()
        self.assertEqual(db.session.get(Enrollment, e.id).grade, 100)
        self.assertEqual(self.client.patch(f"/api/teacher/enrollments/{e.id}", json={"grade": None}).status_code, 200)
        db.session.expire_all()
        self.assertIsNone(db.session.get(Enrollment, e.id).grade)

    def test_invalid_grades_rejected(self):
        self.login("ahepworth")
        e = self.enrollment("CS 162", "nlittle")
        for bad in (101, -1, 85.5, "90", True, [1]):
            r = self.client.patch(f"/api/teacher/enrollments/{e.id}", json={"grade": bad})
            self.assertEqual(r.status_code, 400, bad)
        self.assertEqual(self.client.patch(f"/api/teacher/enrollments/{e.id}", json={}).status_code, 400)
        self.assertEqual(self.client.patch("/api/teacher/enrollments/9999", json={"grade": 90}).status_code, 404)
        db.session.expire_all()
        self.assertEqual(db.session.get(Enrollment, e.id).grade, 87)

    def test_teacher_cannot_touch_another_teachers_course(self):
        self.login("ahepworth")
        math = self.course("Math 101").id
        self.assertEqual(self.client.get(f"/api/teacher/courses/{math}/students").status_code, 403)
        self.assertEqual(self.client.get("/api/teacher/courses/9999/students").status_code, 404)
        e = self.enrollment("Math 101", "jsantos")
        self.assertEqual(self.client.patch(f"/api/teacher/enrollments/{e.id}", json={"grade": 0}).status_code, 403)
        db.session.expire_all()
        self.assertEqual(db.session.get(Enrollment, e.id).grade, 92)

    def test_roles_enforced(self):
        self.assertEqual(self.client.get("/api/teacher/courses").status_code, 302)
        self.login("mnorris")
        for path in ("/teacher", "/api/teacher/courses"):
            self.assertEqual(self.client.get(path).status_code, 403)
        self.assertEqual(self.client.patch("/api/teacher/enrollments/1", json={"grade": 90}).status_code, 403)

    def test_csrf_enforced_on_grade_edit(self):
        self.login("ahepworth")
        e = self.enrollment("CS 162", "nlittle")
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.assertEqual(self.client.patch(f"/api/teacher/enrollments/{e.id}", json={"grade": 90}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
