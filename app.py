from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "performance_review.db"

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "dev-secret-key-change-me"

db = SQLAlchemy(app)


class Staff(db.Model):
    __tablename__ = "staff"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False, unique=True)
    manager_id = db.Column(db.Integer, db.ForeignKey("staff.id"), nullable=True)

    manager = db.relationship("Staff", remote_side=[id], backref="reports", lazy=True)


class ReviewTemplate(db.Model):
    __tablename__ = "review_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class TemplateQuestion(db.Model):
    __tablename__ = "template_questions"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("review_templates.id"), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    answer_by = db.Column(db.String(20), nullable=False)  # reviewer, reviewee, both
    order_index = db.Column(db.Integer, nullable=False, default=0)

    template = db.relationship("ReviewTemplate", backref="questions")


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey("review_templates.id"), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("staff.id"), nullable=False)
    reviewee_id = db.Column(db.Integer, db.ForeignKey("staff.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="In Progress")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    template = db.relationship("ReviewTemplate")
    reviewer = db.relationship("Staff", foreign_keys=[reviewer_id])
    reviewee = db.relationship("Staff", foreign_keys=[reviewee_id])


class ReviewAnswer(db.Model):
    __tablename__ = "review_answers"

    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey("reviews.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("template_questions.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # reviewer, reviewee
    answer_text = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    review = db.relationship("Review", backref="answers")
    question = db.relationship("TemplateQuestion")

    __table_args__ = (UniqueConstraint("review_id", "question_id", "role", name="uq_answer_per_role"),)


@app.route("/")
def dashboard():
    staff_count = Staff.query.count()
    template_count = ReviewTemplate.query.count()
    review_count = Review.query.count()
    completed_count = Review.query.filter_by(status="Completed").count()

    latest_reviews = Review.query.order_by(Review.created_at.desc()).limit(8).all()
    return render_template(
        "dashboard.html",
        staff_count=staff_count,
        template_count=template_count,
        review_count=review_count,
        completed_count=completed_count,
        latest_reviews=latest_reviews,
    )


@app.route("/staff", methods=["GET", "POST"])
def staff():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        title = request.form.get("title", "").strip()
        email = request.form.get("email", "").strip().lower()
        manager_id = request.form.get("manager_id")

        if not name or not title or not email:
            flash("Name, title, and email are required.", "danger")
            return redirect(url_for("staff"))

        if Staff.query.filter_by(email=email).first():
            flash("A staff member with that email already exists.", "danger")
            return redirect(url_for("staff"))

        manager = Staff.query.get(int(manager_id)) if manager_id else None
        member = Staff(name=name, title=title, email=email, manager=manager)
        db.session.add(member)
        db.session.commit()
        flash("Staff member created.", "success")
        return redirect(url_for("staff"))

    members = Staff.query.order_by(Staff.name).all()
    return render_template("staff.html", members=members)


@app.route("/org-chart")
def org_chart():
    members = Staff.query.order_by(Staff.name).all()
    by_manager: dict[int | None, list[Staff]] = defaultdict(list)
    for member in members:
        by_manager[member.manager_id].append(member)

    roots = sorted(by_manager[None], key=lambda m: m.name.lower())
    return render_template("org_chart.html", roots=roots, by_manager=by_manager)


@app.route("/templates", methods=["GET", "POST"])
def templates():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        prompts = request.form.getlist("prompt")
        answer_by_values = request.form.getlist("answer_by")

        if not name:
            flash("Template name is required.", "danger")
            return redirect(url_for("templates"))

        if ReviewTemplate.query.filter_by(name=name).first():
            flash("Template name must be unique.", "danger")
            return redirect(url_for("templates"))

        template = ReviewTemplate(name=name, description=description)
        db.session.add(template)
        db.session.flush()

        valid_questions = 0
        for idx, prompt in enumerate(prompts):
            text = prompt.strip()
            answer_by = answer_by_values[idx] if idx < len(answer_by_values) else "both"
            if not text:
                continue
            valid_questions += 1
            question = TemplateQuestion(
                template_id=template.id,
                prompt=text,
                answer_by=answer_by,
                order_index=valid_questions,
            )
            db.session.add(question)

        if valid_questions == 0:
            db.session.rollback()
            flash("Add at least one question.", "danger")
            return redirect(url_for("templates"))

        db.session.commit()
        flash("Template created.", "success")
        return redirect(url_for("templates"))

    all_templates = ReviewTemplate.query.order_by(ReviewTemplate.created_at.desc()).all()
    return render_template("templates.html", templates=all_templates)


@app.route("/reviews", methods=["GET", "POST"])
def reviews():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        template_id = request.form.get("template_id")
        reviewer_id = request.form.get("reviewer_id")
        reviewee_id = request.form.get("reviewee_id")

        if not title or not template_id or not reviewer_id or not reviewee_id:
            flash("All fields are required to initiate a review.", "danger")
            return redirect(url_for("reviews"))

        if reviewer_id == reviewee_id:
            flash("Reviewer and reviewee must be different staff members.", "danger")
            return redirect(url_for("reviews"))

        review = Review(
            title=title,
            template_id=int(template_id),
            reviewer_id=int(reviewer_id),
            reviewee_id=int(reviewee_id),
        )
        db.session.add(review)
        db.session.commit()
        flash("Review initiated.", "success")
        return redirect(url_for("reviews"))

    reviews_list = Review.query.order_by(Review.created_at.desc()).all()
    templates_list = ReviewTemplate.query.order_by(ReviewTemplate.name).all()
    staff_members = Staff.query.order_by(Staff.name).all()
    return render_template(
        "reviews.html",
        reviews=reviews_list,
        templates=templates_list,
        staff_members=staff_members,
    )


@app.route("/reviews/<int:review_id>/<role>", methods=["GET", "POST"])
def complete_review(review_id: int, role: str):
    if role not in {"reviewer", "reviewee"}:
        flash("Invalid role.", "danger")
        return redirect(url_for("reviews"))

    review = Review.query.get_or_404(review_id)
    questions = (
        TemplateQuestion.query.filter_by(template_id=review.template_id)
        .order_by(TemplateQuestion.order_index)
        .all()
    )

    applicable = [q for q in questions if q.answer_by in {role, "both"}]

    if request.method == "POST":
        for question in applicable:
            text = request.form.get(f"q_{question.id}", "").strip()
            if not text:
                continue
            answer = ReviewAnswer.query.filter_by(
                review_id=review.id,
                question_id=question.id,
                role=role,
            ).first()
            if answer:
                answer.answer_text = text
            else:
                db.session.add(
                    ReviewAnswer(
                        review_id=review.id,
                        question_id=question.id,
                        role=role,
                        answer_text=text,
                    )
                )

        db.session.commit()
        evaluate_completion(review)
        flash(f"{role.title()} responses saved.", "success")
        return redirect(url_for("reviews"))

    existing_answers = {
        ans.question_id: ans.answer_text
        for ans in ReviewAnswer.query.filter_by(review_id=review.id, role=role).all()
    }
    return render_template(
        "complete_review.html",
        review=review,
        role=role,
        questions=applicable,
        existing_answers=existing_answers,
    )


@app.route("/reviews/<int:review_id>")
def view_review(review_id: int):
    review = Review.query.get_or_404(review_id)
    questions = (
        TemplateQuestion.query.filter_by(template_id=review.template_id)
        .order_by(TemplateQuestion.order_index)
        .all()
    )
    answers = ReviewAnswer.query.filter_by(review_id=review.id).all()

    indexed_answers: dict[tuple[int, str], str] = {}
    for answer in answers:
        indexed_answers[(answer.question_id, answer.role)] = answer.answer_text

    return render_template("review_detail.html", review=review, questions=questions, indexed_answers=indexed_answers)


def evaluate_completion(review: Review) -> None:
    questions = (
        TemplateQuestion.query.filter_by(template_id=review.template_id)
        .order_by(TemplateQuestion.order_index)
        .all()
    )
    expected_pairs: list[tuple[int, str]] = []
    for question in questions:
        if question.answer_by in {"reviewer", "both"}:
            expected_pairs.append((question.id, "reviewer"))
        if question.answer_by in {"reviewee", "both"}:
            expected_pairs.append((question.id, "reviewee"))

    actual_pairs = {
        (answer.question_id, answer.role)
        for answer in ReviewAnswer.query.filter_by(review_id=review.id).all()
        if answer.answer_text.strip()
    }

    review.status = "Completed" if all(pair in actual_pairs for pair in expected_pairs) else "In Progress"
    db.session.commit()


@app.cli.command("seed")
def seed_data():
    if Staff.query.first() or ReviewTemplate.query.first():
        print("Seed data already exists.")
        return

    ceo = Staff(name="Ava Johnson", title="CEO", email="ava@acme.com")
    hr = Staff(name="Noah Carter", title="HR Director", email="noah@acme.com", manager=ceo)
    eng_mgr = Staff(name="Mia Lopez", title="Engineering Manager", email="mia@acme.com", manager=ceo)
    engineer = Staff(name="Liam Patel", title="Software Engineer", email="liam@acme.com", manager=eng_mgr)
    db.session.add_all([ceo, hr, eng_mgr, engineer])

    template = ReviewTemplate(name="Quarterly Performance Review", description="Standard quarterly review template")
    db.session.add(template)
    db.session.flush()

    db.session.add_all(
        [
            TemplateQuestion(template_id=template.id, prompt="What were your key achievements this period?", answer_by="reviewee", order_index=1),
            TemplateQuestion(template_id=template.id, prompt="How effectively did this employee collaborate with peers?", answer_by="reviewer", order_index=2),
            TemplateQuestion(template_id=template.id, prompt="What growth goals should be prioritized next quarter?", answer_by="both", order_index=3),
        ]
    )

    db.session.commit()
    print("Seed data created.")


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
