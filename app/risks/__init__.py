from flask import Blueprint

risks_bp = Blueprint("risks", __name__, url_prefix="/projects")

from app.risks import routes
