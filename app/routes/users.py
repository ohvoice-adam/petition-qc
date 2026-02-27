from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.models import User, UserRole, Organization, admin_required, organizer_required
from app.utils import is_valid_email

bp = Blueprint("users", __name__)


@bp.route("/")
@login_required
@organizer_required
def index():
    """List all users."""
    users = User.query.order_by(User.last_name, User.first_name).all()
    return render_template("users/index.html", users=users)


@bp.route("/new", methods=["GET", "POST"])
@login_required
@organizer_required
def new():
    """Create a new user."""
    organizations = Organization.query.order_by(Organization.name).all()
    # Organizers cannot assign the Admin role
    available_roles = UserRole.CHOICES if current_user.is_admin else [
        c for c in UserRole.CHOICES if c[0] != UserRole.ADMIN
    ]

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        role = request.form.get("role", UserRole.ENTERER)
        org_id = request.form.get("organization_id")
        organization_id = int(org_id) if org_id else None

        # Organizers cannot assign admin role
        if not current_user.is_admin and role == UserRole.ADMIN:
            flash("You don't have permission to assign the Administrator role.", "error")
            return render_template("users/new.html", roles=available_roles, organizations=organizations)

        if not is_valid_email(email):
            flash("Invalid email address.", "error")
            return render_template("users/new.html", roles=available_roles, organizations=organizations)

        if User.query.filter_by(email=email).first():
            flash("Email already registered", "error")
            return render_template("users/new.html", roles=available_roles, organizations=organizations)

        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            organization_id=organization_id,
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(f"User {user.full_name} created successfully", "success")
        return redirect(url_for("users.index"))

    return render_template("users/new.html", roles=available_roles, organizations=organizations)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@organizer_required
def edit(id):
    """Edit a user."""
    user = db.session.get(User, id)
    organizations = Organization.query.order_by(Organization.name).all()

    if not user:
        flash("User not found", "error")
        return redirect(url_for("users.index"))

    # Organizers cannot edit admin accounts
    if not current_user.is_admin and user.is_admin:
        flash("You don't have permission to edit an Administrator account.", "error")
        return redirect(url_for("users.index"))

    # Organizers cannot assign the Admin role
    available_roles = UserRole.CHOICES if current_user.is_admin else [
        c for c in UserRole.CHOICES if c[0] != UserRole.ADMIN
    ]

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not is_valid_email(email):
            flash("Invalid email address.", "error")
            return render_template("users/edit.html", user=user, roles=available_roles, organizations=organizations)

        role = request.form.get("role", UserRole.ENTERER)
        if not current_user.is_admin and role == UserRole.ADMIN:
            flash("You don't have permission to assign the Administrator role.", "error")
            return render_template("users/edit.html", user=user, roles=available_roles, organizations=organizations)

        user.email = email
        user.first_name = request.form.get("first_name")
        user.last_name = request.form.get("last_name")
        user.role = role
        user.is_active = request.form.get("is_active") == "on"

        org_id = request.form.get("organization_id")
        user.organization_id = int(org_id) if org_id else None

        # Only update password if provided
        new_password = request.form.get("password")
        if new_password:
            user.set_password(new_password)

        db.session.commit()

        flash(f"User {user.full_name} updated successfully", "success")
        return redirect(url_for("users.index"))

    return render_template("users/edit.html", user=user, roles=available_roles, organizations=organizations)


@bp.route("/<int:id>/toggle-active", methods=["POST"])
@login_required
@organizer_required
def toggle_active(id):
    """Toggle user active status."""
    user = db.session.get(User, id)

    if not user:
        flash("User not found", "error")
        return redirect(url_for("users.index"))

    # Organizers cannot toggle admin accounts
    if not current_user.is_admin and user.is_admin:
        flash("You don't have permission to modify an Administrator account.", "error")
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
