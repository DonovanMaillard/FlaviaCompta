from flask import Flask, render_template, request, flash, get_flashed_messages, redirect, url_for, make_response, stream_with_context, jsonify
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


#import logging
import os
import pdfkit
import csv
import uuid
import babel

from .init_db import db
from .models import *
from .forms import *
from .routes.utils import *

# Import Blueprints 
from .routes import (
    auth_bp,
    profit_bonus_bp,
    budgets_bp,
    budgets_actions_bp,
    accounts_bp,
    funders_bp,
    documents_bp,
    commitments_bp,
    transfers_bp,
    results_bp,
    payrolls_bp,
    operations_bp,
    utils_bp
    )

app = Flask(__name__, template_folder='../templates', static_folder='../static')

app.register_blueprint(auth_bp)
app.register_blueprint(profit_bonus_bp)
app.register_blueprint(budgets_bp)
app.register_blueprint(budgets_actions_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(funders_bp)
app.register_blueprint(documents_bp)
app.register_blueprint(commitments_bp)
app.register_blueprint(transfers_bp)
app.register_blueprint(results_bp)
app.register_blueprint(payrolls_bp)
app.register_blueprint(operations_bp)
app.register_blueprint(utils_bp)

# Load configuration
app.config.from_pyfile('../../config/config.py')
# To get one variable, tape app.config['MY_VARIABLE']

############
### MAIN ###
############

@app.route('/')
@login_required
def index():
    return render_template('home.html')

# Features
@app.route('/features')
@login_required
def features():
    return render_template('about/features.html')

# Tutorial
@app.route('/tutorial')
@login_required
def tutorial():
    return render_template('about/tutorial.html')


#############
### Admin ###
#############
### Members ###
@app.route('/admin/members', methods=['GET'])
@login_required
def members():
    Members=tMembers.query.all()
    return render_template('admin/members/members_list.html', Members=Members)

@app.route('/admin/member/add', methods=['GET','POST'])
@login_required
def addMember():
    form = formMember(request.form)
    if request.method == 'POST' and form.validate():
        member = tMembers(
            request.form['member_name'],
            request.form['member_role'],
            bool(request.form.get('is_employed')),
            bool(request.form.get('active'))
            )
        db.session.add(member)
        db.session.commit()
        return redirect(url_for('members'))
    return render_template('admin/members/add_or_update_member.html', form=form, Member=None, active=True, is_employed=False)

@app.route('/admin/member/edit/<id_member>', methods=['GET','POST'])
@login_required
def updateMember(id_member):
    member = db.session.get(tMembers, id_member) #tMembers.query.get(id_member)
    form = formMember(request.form, obj=member)
    if request.method == 'POST' and form.validate():
        member.member_name = request.form['member_name']
        member.member_role = request.form['member_role']
        member.is_employed = bool(request.form.get('is_employed'))
        member.active = bool(request.form.get('active'))
        db.session.commit()
        return redirect(url_for('members'))
    return render_template('admin/members/add_or_update_member.html', form=form, Member=member, active=member.active, is_employed=member.is_employed)

### Categories ###
# List categories
@app.route('/admin/categories')
@login_required
def categories():
    Depenses=dictCategories.query.filter_by(id_type_operation = dictOperationTypes.query.filter_by(label='Dépense').one().id_type_operation).all()
    Recettes=dictCategories.query.filter_by(id_type_operation = dictOperationTypes.query.filter_by(label='Recette').one().id_type_operation).all()
    Benevolats=dictCategories.query.filter_by(id_type_operation = dictOperationTypes.query.filter_by(label='Valorisation du bénévolat').one().id_type_operation).all()
    Transferts=dictCategories.query.filter_by(id_type_operation = dictOperationTypes.query.filter_by(label='Transaction interne').one().id_type_operation).all()
    return render_template('admin/categories/categories_list.html', Depenses = Depenses, Recettes=Recettes, Benevolats=Benevolats,Transferts=Transferts)

### Activities
@app.route('/activities', methods=['GET'])
@login_required
def activities():
    return render_template('admin/activities/activities_list.html', Activities = tActivities.query.all() )

