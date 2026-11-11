from flask import Blueprint, render_template, make_response, current_app
from datetime import date
from flask_login import login_required
import pdfkit
from ..init_db import db
from ..models import vResultByYear

results_bp = Blueprint("results",__name__,url_prefix="/results")



#################
### Resultats ###
#################

# Results per year
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
    # Une catégorie sans opération sur l'année a un montant NULL dans la vue : compté comme 0
    total_recettes=sum(r.amount or 0 for r in recettes)
    total_depenses=sum(d.amount or 0 for d in depenses)
    result=total_recettes+total_depenses
    filename='export_bilan_'+year
    header_url=current_app.config['BASE_URL']+'/static/img/bandeau_pdf.png'
    html = render_template('results/results_pdf.html',depenses=depenses, recettes=recettes, year=year, current_date=current_date, result=result, total_recettes=total_recettes, total_depenses=total_depenses, header_url=header_url)
    options = {"enable-local-file-access": None}
    pdf = pdfkit.from_string(html, False, options=options)
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename={}.pdf".format(filename)
    return response
