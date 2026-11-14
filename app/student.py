from flask import Blueprint, jsonify, render_template
from flask_login import current_user
from sqlalchemy import func, insert, literal, select

from . import db
from.auth import role_required
from .models import Course, Enrollment

bp = Blueprint('student', __name__)

def course_json(course, my_course_ids):
    return {
        "id": course.id,
        "name": course.name,
        "teacher": course.teacher.display_name,
        "enrolled": course.enrolled_count,
        "capacity": course.capacity,
        "full": course.is_full,
        "enrolled_in": course.id in my_course_ids,
    }

def my_course_ids():
    #long line, tldr gets the set of course ids that the current user is enrolled in
    return set(db.session.scalars(db.select(Enrollment.course_id).where(Enrollment.student_id == current_user.id)))

@bp.get("/student")
@role_required("student")
def student_dashboard():
    return render_template("student_dashboard.html")

@bp.get("/api/my-courses")
@role_required("student")
def my_courses():
    # Gets the courses that the current user is enrolled in
    ids = my_course_ids()
    courses = db.session.scalars(db.select(Course).order_by(Course.name)).all()
    return jsonify([course_json(c, ids) for c in courses])

@bp.get("/api/courses")
@role_required("student")
def all_courses():
    #self explanatory. gets all courses
    ids = my_course_ids()
    courses = db.session.scalars(db.select(Course).order_by(Course.name)).all()
    return jsonify([course_json(c, ids) for c in courses])

@bp.post("/api/enroll/<int:course_id>")
@role_required("student")
def enroll(course_id):
    if db.session.get(Course, course_id) is None:
        return jsonify({"error": "Course not found"}), 404
    if course_id in my_course_ids():
        return jsonify({"error": "Already enrolled"}), 409
    db.session.execute(db.select(Course.id).where(Course.id == course_id).with_for_update()) #locks the course row
    enrolled = (select(func.count()).select_from(Enrollment).where(Enrollment.course_id == Course.id).scalar_subquery())
    result = db.session.execute(insert(Enrollment).from_select(["student_id", "course_id"], select(literal(current_user.id), Course.id).where(Course.id == course_id, enrolled < Course.capacity)))
    db.session.commit()
    if result.rowcount == 0:
        return jsonify({"error": "Course is full"}), 409
    return jsonify(message="Enrolled successfully"), 200

@bp.delete("/api/enroll/<int:course_id>")
@role_required("student")
def drop(course_id):
    result = result = db.session.execute(db.delete(Enrollment).where(Enrollment.student_id == current_user.id, Enrollment.course_id == course_id))
    db.session.commit()
    if result.rowcount == 0:
        return jsonify({"error": "Not enrolled in this course"}), 404
    return jsonify(message="Dropped successfully"), 200
    