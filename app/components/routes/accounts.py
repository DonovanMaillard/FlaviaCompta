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

accounts_bp = Blueprint("accounts",__name__,url_prefix="/accounts")


################
### ACCOUNTS ###
################
# List accounts
@accounts_bp.route('/<type>')
@accounts_bp.route('/', defaults={'type': 'organism'})
@login_required
def accounts(type):
    if type == 'personnal' :
        Accounts = vAccounts.query.filter_by(is_personnal=True)
    else : 
        Accounts = vAccounts.query.filter_by(is_personnal=False)
    return render_template('accounts/accounts_list.html', Accounts = Accounts, Type = type)


# Detail account
@accounts_bp.route('/detail/<id_account>', methods=['GET', 'POST'])
@login_required
def detailAccount(id_account):
    Account = db.session.get(vAccounts, id_account) #vAccounts.query.get(id_account)
    Operations = vOperations.query.filter(vOperations.id_account==id_account, vOperations.type_operation != 'Engagement').order_by(vOperations.effective_date.desc()).all()
    Commitments = vOperations.query.filter(vOperations.id_account==id_account, vOperations.type_operation == 'Engagement').order_by(vOperations.effective_date.desc()).all()
    return render_template('accounts/details_account.html', Account = Account, Operations = Operations, Commitments = Commitments )

# Add account
@accounts_bp.route('/add/<type>', methods=['GET', 'POST'])
@accounts_bp.route('/add', defaults={'type': 'not_personnal'}, methods=['GET', 'POST'])
@login_required
def addAccount(type):
    form = formAccount(request.form)
    if type == 'personnal':
        is_personnal = True
    else : 
        is_personnal = False
    # Commit form
    if request.method == 'POST' and form.validate() :
        Account = tAccounts(
            request.form['name'],
            request.form['account_number'],
            request.form['bank'],
            request.form.get('bank_url'),
            request.form['iban'],
            getFileUrl('uploaded_file'),
            is_personnal,
            bool(request.form.get('active'))
        )
        db.session.add(Account)
        db.session.commit()
        return redirect(url_for('accounts', type=type))
    return render_template('accounts/add_or_update_account.html', form=form, Account=None, active=None, Type=type)

# Edit account
@accounts_bp.route('/edit/<id_account>', methods=['GET', 'POST'])
@login_required
def updateAccount(id_account):
  # pre-loaded form
    Account = db.session.get(tAccounts, id_account)
    if Account.is_personnal:
        type = 'personnal'
    else :
        type = 'not_personnal'
    form = formAccount(request.form, obj=Account)
    if request.method == 'POST' and form.validate():
        Account.name = request.form['name'], 
        Account.account_number = request.form['account_number'],
        Account.bank = request.form['bank'],
        Account.bank_url = request.form.get('bank_url'),
        Account.iban = request.form['iban'],
        if not request.form.get('keep_file'):
            Account.uploaded_file = getFileUrl('uploaded_file'),
        Account.active = bool(request.form.get('active'))
        db.session.commit()
        return redirect(url_for('accounts', type=type))
    return render_template('accounts/add_or_update_account.html', form=form, Account=Account)

# Delete account
@accounts_bp.route('/delete/<id_account>', methods=['GET','POST'])
@login_required
def deleteAccount(id_account):
    current_account=db.session.get(tAccounts, id_account)
    db.session.delete(current_account)
    db.session.commit()
    return redirect(url_for('accounts'))

