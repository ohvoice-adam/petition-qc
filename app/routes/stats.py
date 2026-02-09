from flask import Blueprint, render_template
from flask_login import login_required

from app.services import StatsService

bp = Blueprint("stats", __name__)


@bp.route("/")
@login_required
def index():
    """Main statistics dashboard."""
    progress = StatsService.get_progress_stats()
    return render_template("stats/index.html", progress=progress)


@bp.route("/enterers")
@login_required
def enterers():
    """Data enterer performance statistics."""
    enterer_stats = StatsService.get_enterer_stats()
    return render_template("stats/enterers.html", stats=enterer_stats)


@bp.route("/organizations")
@login_required
def organizations():
    """Organization performance statistics."""
    org_stats = StatsService.get_organization_stats()
    return render_template("stats/organizations.html", stats=org_stats)
