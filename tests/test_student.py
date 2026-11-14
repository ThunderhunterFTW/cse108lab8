import unittest

from app import create_app, db
from app.models import Course, Enrollment, User
from app.seed import seed_demo


class StudentTests(unittest.TestCase):
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

    def login(self, username, client=None):
        return (client or self.client).post("/login", data={"username": username, "password": "demo-password"})

    def course(self, name):
        return db.session.execute(db.select(Course).filter_by(name=name)).scalar_one()

    def count(self, name):
        return db.session.scalar(db.select(db.func.count()).select_from(Enrollment).where(
            Enrollment.course_id == self.course(name).id))

    def test_student_routed_to_dashboard_and_sees_own_courses(self):
        r = self.login("mnorris")
        self.assertEqual(r.headers["Location"], "/")
        self.assertIn("/student", self.client.get("/").headers["Location"])
        self.assertEqual(self.client.get("/student").status_code, 200)
        data = self.client.get("/api/my-courses").get_json()
        self.assertEqual({c["name"] for c in data}, {"Physics 121", "CS 106"})
        physics = next(c for c in data if c["name"] == "Physics 121")
        self.assertEqual((physics["enrolled"], physics["capacity"], physics["teacher"]), (5, 10, "Susan Walker"))

    def test_catalog_lists_all_courses_with_counts(self):
        self.login("mnorris")
        data = {c["name"]: c for c in self.client.get("/api/courses").get_json()}
        self.assertEqual({k: (v["enrolled"], v["capacity"]) for k, v in data.items()},
                         {"Math 101": (4, 8), "Physics 121": (5, 10), "CS 106": (4, 10), "CS 162": (4, 4)})
        self.assertTrue(data["CS 162"]["full"])
        self.assertTrue(data["Physics 121"]["enrolled_in"])
        self.assertFalse(data["Math 101"]["enrolled_in"])

    def test_enroll_and_drop(self):
        self.login("mnorris")
        cid = self.course("Math 101").id
        self.assertEqual(self.client.post(f"/api/enroll/{cid}").status_code, 201)
        self.assertEqual(self.count("Math 101"), 5)
        self.assertEqual(self.client.delete(f"/api/enroll/{cid}").status_code, 200)
        self.assertEqual(self.count("Math 101"), 4)
        self.assertEqual(self.client.delete(f"/api/enroll/{cid}").status_code, 404)

    def test_full_course_and_duplicate_rejected(self):
        self.login("mnorris")
        full = self.course("CS 162").id
        r = self.client.post(f"/api/enroll/{full}")
        self.assertEqual(r.status_code, 409)
        self.assertIn("full", r.get_json()["error"])
        self.assertEqual(self.count("CS 162"), 4)
        r = self.client.post(f"/api/enroll/{self.course('CS 106').id}")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.count("CS 106"), 4)
        self.assertEqual(self.client.post("/api/enroll/9999").status_code, 404)

    def test_last_seat_only_one_succeeds(self):
        course = self.course("Math 101")
        course.capacity = 5
        db.session.commit()
        other = self.app.test_client()
        self.login("mnorris")
        self.login("nlittle", other)
        self.assertEqual(self.client.post(f"/api/enroll/{course.id}").status_code, 201)
        self.assertEqual(other.post(f"/api/enroll/{course.id}").status_code, 409)
        self.assertEqual(self.count("Math 101"), 5)

    def test_student_cannot_drop_someone_elses_enrollment_and_roles_enforced(self):
        self.login("mnorris")
        self.client.delete(f"/api/enroll/{self.course('Physics 121').id}")
        self.assertEqual(self.count("Physics 121"), 4)
        nl = db.session.execute(db.select(User).filter_by(username="nlittle")).scalar_one()
        self.assertEqual(len([e for e in nl.enrollments]), 3)
        self.client.post("/logout")
        self.login("ahepworth")
        for path in ("/student", "/api/courses", "/api/my-courses"):
            self.assertEqual(self.client.get(path).status_code, 403)
        self.assertEqual(self.client.post(f"/api/enroll/{self.course('Math 101').id}").status_code, 403)
        self.client.post("/logout")
        self.assertEqual(self.client.get("/api/courses").status_code, 302)

    def test_csrf_enforced_on_enroll(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.login("mnorris")
        self.assertEqual(self.client.post(f"/api/enroll/{self.course('Math 101').id}").status_code, 400)


if __name__ == "__main__":
    unittest.main()