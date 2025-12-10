# poly_app/utils/ui_auth.py
from functools import wraps

from flask import session, redirect, url_for, flash

from poly_app.db_mysql import query_one

ADMIN_USER_IDS = {2}  # user_id 2 will be admin (created in seeds)


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = query_one(
        """
        SELECT u.id,
               u.email,
               u.status,
               u.total_spent,
               u.total_books_read,
               p.username,
               p.country,
               p.date_of_birth
        FROM users u
        JOIN user_profile p ON p.user_id = u.id
        WHERE u.id = %s
        """,
        (user_id,),
    )
    return user


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("ui.login"))
        return view_func(*args, **kwargs)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("Please log in as an administrator.", "warning")
            return redirect(url_for("ui.login"))
        if user_id not in ADMIN_USER_IDS:
            flash("You are not authorized to view this page.", "danger")
            return redirect(url_for("ui.index"))
        return view_func(*args, **kwargs)
    return wrapper
