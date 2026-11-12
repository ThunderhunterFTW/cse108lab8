import click
from werkzeug.security import generate_password_hash

from . import db
from .models import Course, Enrollment, User


def seed_demo():
    if any(db.session.scalar(db.select(db.func.count()).select_from(model)) for model in (User, Course, Enrollment)):
        raise click.ClickException("Demo data can only be loaded into an empty database.")

    password_hash = generate_password_hash("demo-password")
    people = [
        ("admin", "Demo Admin", "admin"),
        ("rjenkins", "Ralph Jenkins", "teacher"),
        ("swalker", "Susan Walker", "teacher"),
        ("ahepworth", "Ammon Hepworth", "teacher"),
        ("jsantos", "Jose Santos", "student"),
        ("bbrown", "Betty Brown", "student"),
        ("jstuart", "John Stuart", "student"),
        ("lcheng", "Li Cheng", "student"),
        ("nlittle", "Nancy Little", "student"),
        ("mnorris", "Mindy Norris", "student"),
        ("aranganath", "Aditya Ranganath", "student"),
        ("ychen", "Yi Wen Chen", "student"),
    ]
    users = {
        username: User(username=username, display_name=name, role=role, password_hash=password_hash)
        for username, name, role in people
    }
    db.session.add_all(users.values())
    courses = [
        ("Math 101", "rjenkins", "MWF 10:00-10:50 AM", 8,
         [("jsantos", 92), ("bbrown", 65), ("jstuart", 86), ("lcheng", 77)]),
        ("Physics 121", "swalker", "TR 11:00-11:50 AM", 10,
         [("nlittle", 53), ("lcheng", 85), ("mnorris", 94), ("jstuart", 91), ("bbrown", 88)]),
        ("CS 106", "ahepworth", "MWF 2:00-2:50 PM", 10,
         [("aranganath", 93), ("ychen", 85), ("nlittle", 57), ("mnorris", 68)]),
        ("CS 162", "ahepworth", "TR 3:00-3:50 PM", 4,
         [("aranganath", 99), ("nlittle", 87), ("ychen", 92), ("jstuart", 67)]),
    ]
    for name, teacher, time, capacity, students in courses:
        course = Course(name=name, teacher=users[teacher], time=time, capacity=capacity)
        db.session.add(course)
        for student, grade in students:
            db.session.add(Enrollment(student=users[student], course=course, grade=grade))
    db.session.commit()
