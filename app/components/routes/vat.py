from flask import Flask, Blueprint, render_template, request, flash, get_flashed_messages, redirect, url_for, make_response, stream_with_context, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.wrappers import Response
from io import StringIO, BytesIO
from datetime import datetime, timedelta, date
from flask_login import login_required, current_user, login_user, logout_user, LoginManager
from calendar import monthrange
from sqlalchemy import func, or_, and_
from zipfile import ZipFile, ZipInfo
from decimal import Decimal, InvalidOperation

import os
import pdfkit
import csv
import uuid
import babel

from ..init_db import db
from ..models import *
from ..forms import *

vat_bp = Blueprint("vat",__name__,url_prefix="/vat")


###################
### Calculateur ###
###################

# Results per year
@vat_bp.route('/')
@login_required
def vatReport():
    return render_template('vat/vat_report.html')

## Export PDF ##
#@vat_bp.route("/vat/pdf", methods=["GET"])
#@login_required
#def vat_report_pdf():
#    query = search_operations() 
# Ne pas permettre d'exporter en PDF toutes les opérations sans filtres
# if request.args.get("for_vat_summary") is None:
#       abort(400)


@vat_bp.route("/vat/pdf", methods=["GET"])
@login_required
def vatReportPdf():
    # Le bilan ne doit être produit qu'avec une période définie et si demandée "pour le bilan tva"
    if not (request.args.get("for_vat_summary") is not None
            and request.args.get("date_apres") and request.args.get("date_avant")):
        flash("Choisissez une période complète (date de début et de fin) pour exporter le bilan.")
        return redirect(request.referrer or url_for('operations.operations'))

    try:
        date_min = date.fromisoformat(request.args["date_apres"])
        date_max = date.fromisoformat(request.args["date_avant"])
    except ValueError:
        abort(400) # paramètres passés manuellement

    query = search_operations()
    order = (vOperations.effective_date, vOperations.id_operation)
    recettes = query.filter(vOperations.type_operation == 'Recette').order_by(*order).all()
    depenses = query.filter(vOperations.type_operation == 'Dépense').order_by(*order).all()
    summary = compute_vat_summary(query)

    html = render_template(
        'operations/vat_pdf.html',
        recettes=recettes, depenses=depenses, summary=summary,
        date_min=date_min, date_max=date_max, current_date=date.today(),
        header_url=current_app.config['BASE_URL'] + '/static/img/bandeau_pdf.png',
    )
    pdf = pdfkit.from_string(html, False, options={
        "enable-local-file-access": None, "encoding": "UTF-8", "page-size": "A4",
        "footer-center": "Page [page] / [topage]", "footer-font-size": "8",
    })

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'inline; filename="bilan_tva_{date_min}_{date_max}.pdf"'
    return response