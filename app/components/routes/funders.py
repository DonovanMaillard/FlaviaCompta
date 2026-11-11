from flask import Blueprint, render_template, request, redirect
from flask_login import login_required
from ..init_db import db
from ..models import tFunders, vBudgets
from ..forms import formFunder

funders_bp = Blueprint("funders",__name__,url_prefix="/funders")



### Funders ###
# List funders
@funders_bp.route('/', methods=['GET'])
@login_required
def funders():
    return render_template('funders/funders_list.html', Funders = tFunders.query.all() )

# Detail funder
@funders_bp.route('/detail/<id_funder>', methods=['GET'])
@login_required
def detailFunder(id_funder):
    return render_template('funders/details_funder.html', Funder = db.get_or_404(tFunders, id_funder), Budgets=vBudgets.query.filter_by(id_funder=id_funder).all() )

# Add funder
@funders_bp.route('/add', methods=['GET', 'POST'])
@login_required
def addFunder():
    form = formFunder(request.form)
    if request.method == 'POST' and form.validate():
        funder = tFunders(
            request.form['name'], 
            request.form['code'], 
            request.form['logo_url'], 
            request.form['address'], 
            request.form['city'], 
            request.form['zip_code'], 
            request.form['comment'], 
            bool(request.form.get('active'))
        )
        db.session.add(funder)
        db.session.commit()
        return redirect('/funders')
    return render_template('funders/add_or_update_funder.html', form=form, funder=None, active=None)

# Edit funder
@funders_bp.route('/edit/<id_funder>', methods=['GET', 'POST'])
@login_required
def updateFunder(id_funder):
    funder = db.get_or_404(tFunders, id_funder)
    form = formFunder(request.form, obj=funder)
    if request.method == 'POST' and form.validate():
        funder.name=request.form['name']
        funder.code=request.form['code']
        funder.logo_url=request.form['logo_url']
        funder.address=request.form['address']
        funder.city=request.form['city']
        funder.zip_code=request.form['zip_code']
        funder.comment=request.form['comment']
        funder.active=bool(request.form.get('active'))
        db.session.commit()
        return redirect('/funders')
    return render_template('funders/add_or_update_funder.html', form=form, funder=funder, active=funder.active)

# Delete funder
@funders_bp.route('/delete/<id_funder>', methods=['POST'])
@login_required
def deleteFunder(id_funder):
    current_funder=db.get_or_404(tFunders, id_funder)
    db.session.delete(current_funder)
    db.session.commit()
    return redirect('/funders')
