from datetime import date

from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from flask_login import login_required, current_user

from app import db
from app.models import Book, Batch, Collector

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def index():
    """Home page - session setup for data entry."""
    collectors = Collector.query.order_by(Collector.last_name, Collector.first_name).all()

    # Get current session info if set
    book_id = session.get("book_id")
    batch_id = session.get("batch_id")
    book_number = session.get("book_number")

    return render_template(
        "main/index.html",
        collectors=collectors,
        book_id=book_id,
        batch_id=batch_id,
        book_number=book_number,
    )


@bp.route("/start-session", methods=["POST"])
@login_required
def start_session():
    """Start a new data entry session."""
    book_number = request.form.get("book_number")
    collector_id = request.form.get("collector_id")
    date_entered = request.form.get("date_entered") or date.today().isoformat()

    if not book_number or not collector_id:
        flash("Please enter book number and select a collector", "error")
        return redirect(url_for("main.index"))

    # Find or create the book
    book = Book.query.filter_by(book_number=book_number).first()
    if not book:
        book = Book(book_number=book_number, collector_id=collector_id)
        db.session.add(book)
        db.session.commit()

    # Create a new batch for this session
    batch = Batch(
        book_id=book.id,
        book_number=book_number,
        collector_id=collector_id,
        enterer_id=current_user.id,
        enterer_first=current_user.first_name,
        enterer_last=current_user.last_name,
        enterer_email=current_user.email,
        date_entered=date_entered,
    )
    db.session.add(batch)
    db.session.commit()

    # Store session info
    session["book_id"] = book.id
    session["batch_id"] = batch.id
    session["book_number"] = book_number
    session["date_entered"] = date_entered

    flash(f"Started session for Book {book_number}", "success")
    return redirect(url_for("signatures.entry"))


@bp.route("/end-session", methods=["POST"])
@login_required
def end_session():
    """End the current data entry session."""
    session.pop("book_id", None)
    session.pop("batch_id", None)
    session.pop("book_number", None)
    session.pop("date_entered", None)

    flash("Session ended", "info")
    return redirect(url_for("main.index"))
