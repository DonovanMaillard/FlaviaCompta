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
from decimal import Decimal

import os
import pdfkit
import csv
import uuid
import babel

from ..init_db import db
from ..models import *
from ..forms import *

results_bp = Blueprint("results",__name__,url_prefix="/results")



#################
### Resultats ###
#################

# Export as pdf
@results_bp.route('/')
@login_required
def results():
    years=db.session.query(vResultByYear.year).distinct()
    return render_template('results/results.html', years=years)


#####################
### RESULTATS PDF ###
#####################

# Export as pdf
@results_bp.route('/pdf/year/<year>')
@login_required
def resultsPDF(year):
    recettes=vResultByYear.query.filter_by(year=year).filter_by(type_category='Recette').all()
    depenses=vResultByYear.query.filter_by(year=year).filter_by(type_category='Dépense').all()
    current_date=date.today()
    result=sum([r.amount for r in recettes])+sum([d.amount for d in depenses])
    filename='export_bilan_'+year
    header_url=app.config['BASE_URL']+'/static/img/bandeau_pdf.png'
    html = render_template('results/results_pdf.html',depenses=depenses, recettes=recettes, year=year, current_date=current_date, result=result, header_url=header_url)
    options = {"enable-local-file-access": None}
    pdf = pdfkit.from_string(html, False, options=options)
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename={}.pdf".format(filename)
    return response
