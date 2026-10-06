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

commitments_bp = Blueprint("commitments",__name__,url_prefix="/commitments")


###############
# Engagements #
###############
# Liste
@commitments_bp.route('/')
@login_required
def commitments():
    Commitments = vOperations.query.filter(vOperations.type_operation == 'Engagement').order_by(vOperations.operation_date.desc()).all()
    return render_template('operations/commitments_list.html', Commitments=Commitments)

# Ajout
@commitments_bp.route('/add', methods=['GET', 'POST'])
@login_required
def addCommitment():
    #Get choices and form
    id_type_operation = dictOperationTypes.query.filter_by(label = 'Engagement').one().id_type_operation
    form = formCommitment(request.form)
    # Form Choices
    # accounts
    Accounts = tAccounts.query.filter_by(is_personnal=False).filter_by(active=True)
    form.id_account.choices = [('', '-- Sélectionnez un compte --')] + [(Account.id_account, Account.name) for Account in Accounts]
    # Budget
    activeBudgets = tBudgets.query.filter_by(date_closing=None)
    form.id_budget.choices = [('', '-- Sélectionnez un budget --')] + [(activeBudget.id_budget, activeBudget.name) for activeBudget in activeBudgets]
    # Category
    id_type_depenses = dictOperationTypes.query.filter_by(label = 'Dépense').one().id_type_operation
    Categories = dictCategories.query.filter(dictCategories.id_type_operation == id_type_depenses, dictCategories.seizable == True).order_by(dictCategories.cd_category).all()
    form.id_category.choices = [('', '-- Sélectionnez une catégorie --')] + [(category.id_category, str(category.cd_category)+" - "+category.label) for category in Categories]
    # Commit form
    if request.method == 'POST' and form.validate() :
        Commitment = tOperations(
            None, #None as id_grp_operation
            request.form['name'],
            request.form['detail_operation'],
            id_type_operation,
            request.form['operation_date'],
            None,
            -getDecimal(request.form.get('amount')),
            None,
            getChoiceOrNone(request.form['id_account']),
            getChoiceOrNone(request.form['id_budget']),
            getChoiceOrNone(request.form['id_category']),
            getFileUrl('uploaded_file'),
            bool('false'),
            current_user.id_user
        )
        db.session.add(Commitment)
        db.session.commit()
        return redirect(url_for('commitments'))
    # Return form
    return render_template('operations/add_or_update_commitment.html', form=form, Operation=None)

# Modification
@commitments_bp.route('/edit/<id_operation>', methods=['GET','POST'])
@login_required
def updateCommitment(id_operation):
    # pre-loaded form
    Operation = db.session.get(tOperations, id_operation) #tOperations.query.get(id_operation)
    #Get choices and form
    id_type_operation = dictOperationTypes.query.filter_by(label = 'Engagement').one().id_type_operation
    form = formCommitment(request.form, obj=Operation)
    # Form Choices
    # accounts
    Accounts = tAccounts.query.filter_by(is_personnal=False).filter_by(active=True)
    form.id_account.choices = [('', '-- Sélectionnez un compte --')] + [(Account.id_account, Account.name) for Account in Accounts]
    form.id_account.default=Operation.id_account
    # Budget
    activeBudgets = tBudgets.query.filter_by(date_closing=None)
    form.id_budget.choices = [('', '-- Sélectionnez un budget --')] + [(activeBudget.id_budget, activeBudget.name) for activeBudget in activeBudgets]
    form.id_budget.default=Operation.id_budget
    # Category
    id_type_depenses = dictOperationTypes.query.filter_by(label = 'Dépense').one().id_type_operation
    Categories = dictCategories.query.filter(dictCategories.id_type_operation == id_type_depenses, dictCategories.seizable == True).order_by(dictCategories.cd_category).all()
    form.id_category.choices = [('', '-- Sélectionnez une catégorie --')] + [(category.id_category, str(category.cd_category)+" - "+category.label) for category in Categories]
    form.id_category.default=Operation.id_category
    # update
    if request.method == 'POST' and form.validate():
        # Let None as id_grp_operation
        Operation.name = request.form['name']
        Operation.detail_operation = request.form['detail_operation']
        Operation.operation_date = request.form['operation_date']
        #let none as effective date
        Operation.amount = -getDecimal(request.form.get('amount'))
        Operation.id_account = getChoiceOrNone(request.form['id_account'])
        Operation.id_budget = getChoiceOrNone(request.form['id_budget'])
        Operation.id_category = getChoiceOrNone(request.form['id_category'])
        if not request.form.get('keep_file'):
            Operation.uploaded_file = getFileUrl('uploaded_file')
        Operation.meta_id_digitiser = current_user.id_user
        db.session.commit()
        return redirect(url_for('commitments'))
    return render_template('operations/add_or_update_commitment.html', form=form, Operation=Operation)

# Conversions
@commitments_bp.route('/convert/<id_operation>', methods=['GET','POST'])
@login_required
def convertCommitment(id_operation):
    # pre-loaded form
    Operation = db.session.get(tOperations, id_operation) #tOperations.query.get(id_operation)
    #Get choices and form
    id_type_operation = dictOperationTypes.query.filter_by(label = 'Dépense').one().id_type_operation
    form = formMovement(request.form, obj=Operation)
    # Form Choices
    # accounts
    Accounts = tAccounts.query.filter_by(is_personnal=False).filter_by(active=True)
    form.id_account.choices = [('', '-- Sélectionnez un compte --')] + [(Account.id_account, Account.name) for Account in Accounts]
    form.id_account.default=Operation.id_account
    # Budget
    activeBudgets = tBudgets.query.filter_by(date_closing=None)
    form.id_budget.choices = [('', '-- Sélectionnez un budget --')] + [(activeBudget.id_budget, activeBudget.name) for activeBudget in activeBudgets]
    form.id_budget.default=Operation.id_budget
    # Category
    id_type_depenses = dictOperationTypes.query.filter_by(label = 'Dépense').one().id_type_operation
    Categories = dictCategories.query.filter(dictCategories.id_type_operation == id_type_depenses, dictCategories.seizable == True).all()
    form.id_category.choices = [('', '-- Sélectionnez une catégorie --')] + [(category.id_category, str(category.cd_category)+" - "+category.label) for category in Categories]
    form.id_category.default=Operation.id_category
    # Payment method
    PaymentMethods = dictPaymentMethods.query.all() # TODO filtrer avec la cor.
    form.id_payment_method.choices = [('', '-- Sélectionnez un moyen de paiement --')] + [(PaymentMethod.id_payment_method, PaymentMethod.label) for PaymentMethod in PaymentMethods]
    # update
    if request.method == 'POST' and form.validate():
        # Let None as id_grp_operation
        Operation.name = request.form['name']
        Operation.detail_operation = request.form['detail_operation']
        Operation.id_type_operation = id_type_operation
        Operation.operation_date = request.form['operation_date']
        Operation.effective_date = request.form['effective_date']
        Operation.amount = -getDecimal(request.form.get('amount'))
        Operation.id_payment_method = getChoiceOrNone(request.form['id_payment_method'])
        Operation.id_account = getChoiceOrNone(request.form['id_account'])
        Operation.id_budget = getChoiceOrNone(request.form['id_budget'])
        Operation.id_category = getChoiceOrNone(request.form['id_category'])
        Operation.uploaded_file = getFileUrl('uploaded_file')
        Operation.meta_id_digitiser = current_user.id_user
        db.session.commit()
        return redirect(url_for('operations'))
    return render_template('operations/add_or_update_movement.html', form=form, Operation=Operation, type_operation="Dépense", Convert=True)


# Suppression
@commitments_bp.route('/<id_operation>/delete', methods=['GET', 'POST'])
@login_required
def deleteCommitment(id_operation): 
    operation= db.session.get(tOperations, id_operation) #tOperations.query.get(id_operation)
    db.session.delete(operation)
    db.session.commit()
    return redirect(url_for('commitments'))
