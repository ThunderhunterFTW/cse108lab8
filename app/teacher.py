from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user

from . import db
from .auth import role_required
from .models import Course, Enrollment

bp = Blueprint('teacher', __name__)

def course_json(course):
    return {
        "id": course.id,
        "name": course.name,
        "teacher": course.teacher.display_name,
        "time": course.time,
        "enrolled": course.enrolled_count,
        "capacity": course.capacity,
    }

def owned_course(course_id):
    # returns (course, error_response). Only the teacher of a course may see or change it
    course = db.session.get(Course, course_id)
    if course is None:
        return None, (jsonify({"error": "Course not found"}), 404)
    if course.teacher_id != current_user.id:
        return None, (jsonify({"error": "You do not teach this course"}), 403)
    return course, None

@bp.get("/teacher")
@role_required("teacher")
def dashboard():
    return render_template("teacher.html")

@bp.get("/api/teacher/courses")
@role_required("teacher")
def my_courses():
    # Gets the courses that the current user teaches
    courses = db.session.scalars(db.select(Course).where(Course.teacher_id == current_user.id).order_by(Course.name)).all()
    return jsonify([course_json(c) for c in courses])

@bp.get("/api/teacher/courses/<int:course_id>/students")
@role_required("teacher")
def roster(course_id):
    course, error = owned_course(course_id)
    if error:
        return error
    enrollments = sorted(course.enrollments, key=lambda e: e.student.display_name)
    return jsonify({
        "course": course_json(course),
        "students": [{"enrollment_id": e.id, "name": e.student.display_name, "grade": e.grade} for e in enrollments],
    })

@bp.patch("/api/teacher/enrollments/<int:enrollment_id>")
@role_required("teacher")
def set_grade(enrollment_id):
    enrollment = db.session.get(Enrollment, enrollment_id)
    if enrollment is None:
        return jsonify({"error": "Enrollment not found"}), 404
    if enrollment.course.teacher_id != current_user.id:
        return jsonify({"error": "You do not teach this course"}), 403
    data = request.get_json(silent=True) or {}
    if "grade" not in data:
        return jsonify({"error": "Grade is required"}), 400
    grade = data["grade"]
    # null clears the grade; bool is a subclass of int so reject it explicitly
    if grade is not None and (type(grade) is not int or not 0 <= grade <= 100):
        return jsonify({"error": "Grade must be a whole number from 0 to 100"}), 400
    enrollment.grade = grade
    db.session.commit()
    return jsonify(enrollment_id=enrollment.id, grade=enrollment.grade)
