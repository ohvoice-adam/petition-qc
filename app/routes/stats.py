from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models import Settings
from app.services import StatsService

bp = Blueprint("stats", __name__)


@bp.route("/")
@login_required
def index():
    """Main statistics dashboard."""
    progress = StatsService.get_progress_stats()
    signature_goal = Settings.get_signature_goal()
    return render_template("stats/index.html", progress=progress, signature_goal=signature_goal)


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


@bp.route("/books")
@login_required
def books():
    """Per-book signature counts and validity rates."""
    sort = request.args.get("sort", "book_number")
    if sort not in ("book_number", "entry_time"):
        sort = "book_number"

    direction = request.args.get("dir", "desc")
    if direction not in ("asc", "desc"):
        direction = "desc"

    book_stats = StatsService.get_book_stats(sort=sort, direction=direction)
    return render_template(
        "stats/books.html",
        books=book_stats,
        sort=sort,
        direction=direction,
    )
