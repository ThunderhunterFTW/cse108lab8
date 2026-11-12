from flask_login import UserMixin

from . import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    display_name = db.Column(db.String(120), nullable=False)

    __table_args__ = (
        db.CheckConstraint("role IN ('student', 'teacher', 'admin')", name="valid_user_role"),
    )

    def __str__(self):
        return f"{self.display_name} ({self.username})"


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False)
    time = db.Column(db.String(120), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    teacher = db.relationship("User", foreign_keys=[teacher_id])
    enrollments = db.relationship("Enrollment", back_populates="course", passive_deletes="all")

    __table_args__ = (db.CheckConstraint("capacity >= 0", name="nonnegative_capacity"),)

    def __str__(self):
        return self.name


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id", ondelete="RESTRICT"), nullable=False)
    grade = db.Column(db.Integer, nullable=True)
    student = db.relationship("User", foreign_keys=[student_id])
    course = db.relationship("Course", back_populates="enrollments")

    __table_args__ = (
        db.UniqueConstraint("student_id", "course_id", name="unique_student_course"),
        db.CheckConstraint("grade IS NULL OR (grade >= 0 AND grade <= 100)", name="valid_grade"),
    )

    def __str__(self):
        return f"{self.student} - {self.course}"
