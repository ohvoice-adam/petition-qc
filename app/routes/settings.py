from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text

from app import db
from app.models import Settings, admin_required

bp = Blueprint("settings", __name__)


@bp.route("/", methods=["GET", "POST"])
@login_required
@admin_required
def index():
    """Application settings page."""
    if request.method == "POST":
        target_city = request.form.get("target_city")
        if target_city:
            Settings.set("target_city", target_city.upper())

        signature_goal = request.form.get("signature_goal", "").strip()
        if signature_goal:
            try:
                goal = int(signature_goal)
                if goal >= 0:
                    Settings.set_signature_goal(goal)
            except ValueError:
                flash("Signature goal must be a number", "error")
                return redirect(url_for("settings.index"))

        flash("Settings saved", "success")
        return redirect(url_for("settings.index"))

    # Get current settings
    current_city = Settings.get_target_city()
    signature_goal = Settings.get_signature_goal()

    # Get distinct cities from voter file
    cities = get_distinct_cities()

    return render_template(
        "settings/index.html",
        current_city=current_city,
        cities=cities,
        signature_goal=signature_goal,
    )


def get_distinct_cities() -> list[dict]:
    """Get distinct cities from the voter file."""
    result = db.session.execute(text("""
        SELECT DISTINCT city, COUNT(*) as count
        FROM voters
        WHERE city IS NOT NULL AND city != ''
        GROUP BY city
        ORDER BY count DESC
    """))

    cities = []
    for row in result:
        cities.append({
            "value": row.city,
            "label": row.city.title(),
            "count": row.count,
        })

    return cities
