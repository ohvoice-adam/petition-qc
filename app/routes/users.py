from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.models import User, UserRole, admin_required

bp = Blueprint("users", __name__)


@bp.route("/")
@login_required
@admin_required
def index():
    """List all users."""
    users = User.query.order_by(User.last_name, User.first_name).all()
    return render_template("users/index.html", users=users)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def new():
    """Create a new user."""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        role = request.form.get("role", UserRole.ENTERER)

        if User.query.filter_by(email=email).first():
            flash("Email already registered", "error")
            return render_template("users/new.html", roles=UserRole.CHOICES)

        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(f"User {user.full_name} created successfully", "success")
        return redirect(url_for("users.index"))

    return render_template("users/new.html", roles=UserRole.CHOICES)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit(id):
    """Edit a user."""
    user = db.session.get(User, id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("users.index"))

    if request.method == "POST":
        user.email = request.form.get("email")
        user.first_name = request.form.get("first_name")
        user.last_name = request.form.get("last_name")
        user.role = request.form.get("role", UserRole.ENTERER)
        user.is_active = request.form.get("is_active") == "on"

        # Only update password if provided
        new_password = request.form.get("password")
        if new_password:
            user.set_password(new_password)

        db.session.commit()

        flash(f"User {user.full_name} updated successfully", "success")
        return redirect(url_for("users.index"))

    return render_template("users/edit.html", user=user, roles=UserRole.CHOICES)


@bp.route("/<int:id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_active(id):
    """Toggle user active status."""
    user = db.session.get(User, id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("users.index"))

    # Prevent deactivating yourself
    if user.id == current_user.id:
        flash("You cannot deactivate your own account", "error")
        return redirect(url_for("users.index"))

    user.is_active = not user.is_active
    db.session.commit()

    status = "activated" if user.is_active else "deactivated"
    flash(f"User {user.full_name} {status}", "success")
    return redirect(url_for("users.index"))
