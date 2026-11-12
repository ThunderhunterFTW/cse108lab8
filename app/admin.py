from flask import abort, redirect, url_for
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from sqlalchemy import func
from werkzeug.security import generate_password_hash
from wtforms import PasswordField, ValidationError
from wtforms.validators import Length, Optional

from . import db
from .models import Course, Enrollment, User


class AdminAccess:
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == "admin"

    def inaccessible_callback(self, name, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login"))
        abort(403)


class ProtectedIndex(AdminAccess, AdminIndexView):
    pass


class ProtectedModelView(AdminAccess, ModelView):
    can_view_details = True
    page_size = 50


class UserAdmin(ProtectedModelView):
    column_list = ("id", "username", "display_name", "role")
    column_details_exclude_list = ("password_hash",)
    form_columns = ("username", "display_name", "role", "password")
    form_choices = {"role": [("student", "Student"), ("teacher", "Teacher"), ("admin", "Admin")]}
    form_extra_fields = {
        "password": PasswordField(
            "New password", validators=[Optional(), Length(min=8)],
            description="Required when creating a user; leave blank to keep an existing password.",
        )
    }

    def on_model_change(self, form, model, is_created):
        if is_created and not form.password.data:
            raise ValidationError("A password is required for a new user.")
        if not is_created:
            with db.session.no_autoflush:
                if model.role != "teacher" and db.session.scalar(
                    db.select(func.count()).select_from(Course).where(Course.teacher_id == model.id)
                ):
                    raise ValidationError("Reassign this user's courses before changing their role.")
                if model.role != "student" and db.session.scalar(
                    db.select(func.count()).select_from(Enrollment).where(Enrollment.student_id == model.id)
                ):
                    raise ValidationError("Remove this user's enrollments before changing their role.")
        if form.password.data:
            model.password_hash = generate_password_hash(form.password.data)


class CourseAdmin(ProtectedModelView):
    column_list = ("id", "name", "teacher", "time", "capacity")
    form_columns = ("name", "teacher", "time", "capacity")

    def on_model_change(self, form, model, is_created):
        if model.teacher.role != "teacher":
            raise ValidationError("The course teacher must have the teacher role.")
        if not is_created:
            with db.session.no_autoflush:
                count = db.session.scalar(
                    db.select(func.count()).select_from(Enrollment).where(Enrollment.course_id == model.id)
                )
            if model.capacity < count:
                raise ValidationError("Capacity cannot be lower than the current enrollment count.")


class EnrollmentAdmin(ProtectedModelView):
    column_list = ("id", "student", "course", "grade")
    form_columns = ("student", "course", "grade")

    def on_model_change(self, form, model, is_created):
        if model.student.role != "student":
            raise ValidationError("The enrolled user must have the student role.")
        with db.session.no_autoflush:
            count = db.session.scalar(
                db.select(func.count()).select_from(Enrollment).where(
                    Enrollment.course_id == model.course.id,
                    Enrollment.id != model.id if model.id is not None else Enrollment.id.is_not(None),
                )
            )
        if count >= model.course.capacity:
            raise ValidationError("The course is full.")


def setup_admin(app):
    admin = Admin(app, name="ACME University", index_view=ProtectedIndex())
    admin.add_view(UserAdmin(User, db))
    admin.add_view(CourseAdmin(Course, db))
    admin.add_view(EnrollmentAdmin(Enrollment, db))
