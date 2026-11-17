from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import ProjectDocument, Risk
from app.projects.routes import project_manager, visible_project_or_404
from app.risks import risks_bp
from app.risks.forms import ProjectDocumentForm, RiskForm


@risks_bp.route("/<int:project_id>/risks-documents")
@login_required
def index(project_id):
    project = visible_project_or_404(project_id)
    risks = db.session.scalars(
        db.select(Risk).where(Risk.project_id == project.id).order_by(Risk.created_at.desc())
    ).all()
    documents = db.session.scalars(
        db.select(ProjectDocument)
        .where(ProjectDocument.project_id == project.id)
        .order_by(ProjectDocument.created_at.desc())
    ).all()
    return render_template(
        "risks/index.html",
        project=project,
        risks=risks,
        documents=documents,
        risk_form=RiskForm(),
        document_form=ProjectDocumentForm(),
        can_manage=project_manager(project),
    )


@risks_bp.route("/<int:project_id>/risks", methods=["POST"])
@login_required
def create_risk(project_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    form = RiskForm()
    if not form.validate_on_submit():
        flash("No se pudo registrar el riesgo; revisa los datos.", "danger")
        return redirect(url_for("risks.index", project_id=project.id))
    risk = Risk(
        project_id=project.id,
        title=form.title.data.strip(),
        description=(form.description.data or "").strip(),
        category=form.category.data,
        probability=form.probability.data,
        impact=form.impact.data,
        mitigation=form.mitigation.data.strip(),
    )
    db.session.add(risk)
    db.session.commit()
    flash("Riesgo registrado; severidad calculada automáticamente.", "success")
    return redirect(url_for("risks.index", project_id=project.id))


@risks_bp.route("/<int:project_id>/risks/<int:risk_id>/edit", methods=["GET", "POST"])
@login_required
def edit_risk(project_id, risk_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    risk = db.session.get(Risk, risk_id)
    if risk is None or risk.project_id != project.id:
        abort(404)
    form = RiskForm(obj=risk)
    if form.validate_on_submit():
        form.populate_obj(risk)
        risk.title = risk.title.strip()
        risk.description = (risk.description or "").strip()
        risk.mitigation = risk.mitigation.strip()
        db.session.commit()
        flash("Riesgo actualizado.", "success")
        return redirect(url_for("risks.index", project_id=project.id))
    return render_template(
        "risks/risk_form.html", form=form, project=project, heading="Editar riesgo"
    )


@risks_bp.route("/<int:project_id>/risks/<int:risk_id>/delete", methods=["POST"])
@login_required
def delete_risk(project_id, risk_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    risk = db.session.get(Risk, risk_id)
    if risk is None or risk.project_id != project.id:
        abort(404)
    db.session.delete(risk)
    db.session.commit()
    flash("Riesgo eliminado.", "success")
    return redirect(url_for("risks.index", project_id=project.id))


@risks_bp.route("/<int:project_id>/documents", methods=["POST"])
@login_required
def add_document(project_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    form = ProjectDocumentForm()
    if not form.validate_on_submit():
        flash("No se pudo adjuntar el enlace; revisa los datos.", "danger")
        return redirect(url_for("risks.index", project_id=project.id))
    document = ProjectDocument(
        project_id=project.id,
        added_by_user_id=current_user.id,
        title=form.title.data.strip(),
        document_type=form.document_type.data,
        url=form.url.data.strip(),
        description=(form.description.data or "").strip(),
    )
    db.session.add(document)
    db.session.commit()
    flash("Enlace documental agregado.", "success")
    return redirect(url_for("risks.index", project_id=project.id))


@risks_bp.route("/<int:project_id>/documents/<int:document_id>/delete", methods=["POST"])
@login_required
def delete_document(project_id, document_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    document = db.session.get(ProjectDocument, document_id)
    if document is None or document.project_id != project.id:
        abort(404)
    db.session.delete(document)
    db.session.commit()
    flash("Enlace documental eliminado.", "success")
    return redirect(url_for("risks.index", project_id=project.id))
