from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from app import db
from app.models import Collector, DataEnterer, Organization

bp = Blueprint("collectors", __name__)


@bp.route("/")
@login_required
def index():
    """List all collectors."""
    collectors = Collector.query.order_by(Collector.last_name, Collector.first_name).all()
    return render_template("collectors/index.html", collectors=collectors)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    """Create a new collector."""
    organizations = Organization.query.order_by(Organization.name).all()

    if request.method == "POST":
        org_id = request.form.get("organization_id")
        collector = Collector(
            first_name=request.form.get("first_name"),
            last_name=request.form.get("last_name"),
            phone=request.form.get("phone"),
            email=request.form.get("email"),
            organization_id=int(org_id) if org_id else None,
        )
        db.session.add(collector)
        db.session.commit()

        flash("Collector added successfully", "success")
        return redirect(url_for("collectors.index"))

    return render_template("collectors/new.html", organizations=organizations)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    """Edit a collector."""
    collector = db.session.get(Collector, id)
    organizations = Organization.query.order_by(Organization.name).all()

    if not collector:
        flash("Collector not found", "error")
        return redirect(url_for("collectors.index"))

    if request.method == "POST":
        org_id = request.form.get("organization_id")
        collector.first_name = request.form.get("first_name")
        collector.last_name = request.form.get("last_name")
        collector.phone = request.form.get("phone")
        collector.email = request.form.get("email")
        collector.organization_id = int(org_id) if org_id else None
        db.session.commit()

        flash("Collector updated successfully", "success")
        return redirect(url_for("collectors.index"))

    return render_template("collectors/edit.html", collector=collector, organizations=organizations)


# Data Enterers routes
@bp.route("/enterers")
@login_required
def enterers():
    """List all data enterers."""
    enterers = DataEnterer.query.order_by(DataEnterer.last_name, DataEnterer.first_name).all()
    return render_template("collectors/enterers.html", enterers=enterers)


@bp.route("/enterers/new", methods=["GET", "POST"])
@login_required
def new_enterer():
    """Create a new data enterer."""
    if request.method == "POST":
        enterer = DataEnterer(
            first_name=request.form.get("first_name"),
            last_name=request.form.get("last_name"),
            phone=request.form.get("phone"),
            email=request.form.get("email"),
        )
        db.session.add(enterer)
        db.session.commit()

        flash("Data enterer added successfully", "success")
        return redirect(url_for("collectors.enterers"))

    return render_template("collectors/new_enterer.html")
