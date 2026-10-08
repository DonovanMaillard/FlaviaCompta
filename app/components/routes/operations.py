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
from .utils import getDecimal

operations_bp = Blueprint("operations",__name__,url_prefix="/operations")

#####################
## Search function ##
#####################

# Filtering function for API & Downloads
def search_operations():
    query = vOperations.query.filter(vOperations.type_operation != 'Engagement')

    libelle = request.args.get("libelle", "")
    id_budget = request.args.get("id_budget", "")
    id_account = request.args.get("id_account", "")
    montant = request.args.get("montant", type=float)
    category = request.args.get("category", "")
    date_apres = request.args.get("date_apres", type=str)
    date_avant = request.args.get("date_avant", type=str)


    if libelle:
        like_pattern = f"%{libelle}%"
        query = query.filter(or_(
            vOperations.name_operation.ilike(like_pattern),
            vOperations.detail_operation.ilike(like_pattern)
        ))

    if id_budget == "none":
        query = query.filter(vOperations.id_budget.is_(None))
    elif id_budget:
        query = query.filter(vOperations.id_budget == id_budget)

    if id_account:
        query = query.filter(
            vOperations.id_account == id_account
        )

    if category:
        query = query.filter(
            vOperations.category == category
        )

    if montant:
        try:
            montant = request.args.get("montant", "").replace(",", ".")
            montant_float = float(montant)
            query = query.filter(func.abs(vOperations.amount) == abs(montant_float))
        except ValueError:
            pass  # montant mal formé, on ignore le filtre

    if date_apres:
        try:
            date_apres_parsed = datetime.strptime(
                date_apres, "%Y-%m-%d"
            ).date()

            query = query.filter(
                vOperations.meta_create_date >= date_apres_parsed
            )
        except ValueError:
            pass

    if date_avant:
        try:
            date_avant_parsed = datetime.strptime(date_avant, "%Y-%m-%d").date()

            query = query.filter(vOperations.meta_create_date < date_avant_parsed + timedelta(days=1))
        except ValueError:
            pass

    return query


@operations_bp.route("/api", methods=["GET"])
@login_required
def get_api_operations():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))

    query = search_operations()

    total = query.count()

    results = query.order_by(vOperations.effective_date.desc()).order_by(vOperations.id_operation.desc()).offset((page - 1) * per_page).limit(per_page).all()

    data = [{
        "id_operation": op.id_operation,
        "effective_date": op.effective_date.strftime('%Y-%m-%d') if op.effective_date else "",
        "operation_date": op.operation_date.strftime('%Y-%m-%d') if op.operation_date else "",
        "name_operation": op.name_operation,
        "detail_operation": op.detail_operation,
        "type_operation": op.type_operation,
        "category": op.category,
        "parent_category": op.parent_category,
        "id_budget": op.id_budget,
        "budget_name": op.budget_name,
        "id_account": op.id_account,
        "account_name": op.account_name,
        "payment_method": op.payment_method,
        "amount": Decimal(op.amount),
        "uploaded_file": url_for('static', filename=op.uploaded_file) if op.uploaded_file else "",
        "meta_create_date": op.meta_create_date,
        "meta_update_date": op.meta_update_date
    } for op in results]

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "data": data
    })


# Download
@operations_bp.route("/download", methods=["GET"])
@login_required
def download_operations():

    query = search_operations()

    results = (
        query
        .order_by(vOperations.effective_date.desc())
        .all()
    )

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "id_operation",
        "date_effet",
        "date_operation",
        "libelle",
        "detail",
        "type_operation",
        "categorie",
        "categorie_parent",
        "budget",
        "compte",
        "methode_paiement",
        "montant",
        "justificatif",
        "saisi_le",
        "modifie_le"
    ])

    for op in results:
        writer.writerow([
            op.id_operation,
            op.effective_date.strftime('%Y-%m-%d') if op.effective_date else "",
            op.operation_date.strftime('%Y-%m-%d') if op.operation_date else "",
            op.name_operation,
            op.detail_operation,
            op.type_operation,
            op.category,
            op.parent_category,
            op.budget_name,
            op.account_name,
            op.payment_method,
            Decimal(op.amount),
            url_for('static', filename=op.uploaded_file) if op.uploaded_file else "",
            op.meta_create_date,
            op.meta_update_date
        ])

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=operations.csv"
        }
    )


#####################
# Toutes opérations #
#####################

# Liste
@operations_bp.route('/', methods=['GET', 'POST'])
@login_required
def operations():
    budgets = db.session.query(vOperations.id_budget, vOperations.budget_name).filter(vOperations.id_budget.isnot(None)).distinct().order_by(vOperations.budget_name).all()
    accounts = db.session.query(vOperations.id_account, vOperations.account_name).distinct().order_by(vOperations.account_name).all()
    categories = db.session.query(vOperations.category).distinct().order_by(vOperations.category)
    return render_template('operations/operations_list.html', budgets=budgets, accounts=accounts, categories=categories, type=None)

# Suppression d'une opération ou de plusieurs opérations appariées
@operations_bp.route('/<id_operation>/delete', methods=['GET', 'POST'])
@login_required
def deleteMovement(id_operation): 
    operation=db.session.get(tOperations, id_operation) #tOperations.query.get(id_operation)
    db.session.delete(operation)
    db.session.commit()
    return redirect(url_for('operations'))



#######################
# Dépenses & Recettes #
#######################
# Ajout
@operations_bp.route('/<type_operation>/add', methods=['GET', 'POST'])
@login_required
def addMovement(type_operation): #movement = Dépense + Recette
    #Get choices and form
    id_type_operation = dictOperationTypes.query.filter_by(label = type_operation).one().id_type_operation
    form = formMovement(request.form)
    # Get accounts
    if type_operation=='Recette': 
        Accounts = tAccounts.query.filter_by(is_personnal=False).filter_by(active=True)
    else :
        Accounts = tAccounts.query.filter_by(active=True)
    # Form Choices
    # accounts
    form.id_account.choices = [('', '-- Sélectionnez un compte --')] + [(Account.id_account, Account.name) for Account in Accounts]
    # Budget
    activeBudgets = tBudgets.query.filter_by(date_closing=None)
    form.id_budget.choices = [('', '-- Sélectionnez un budget --')] + [(activeBudget.id_budget, activeBudget.name) for activeBudget in activeBudgets]
    # Category
    Categories = dictCategories.query.filter(dictCategories.id_type_operation == id_type_operation, dictCategories.seizable == True).order_by(dictCategories.cd_category).all()
    form.id_category.choices = [('', '-- Sélectionnez une catégorie --')] + [(category.id_category, str(category.cd_category)+" - "+category.label) for category in Categories]
    # Payment method
    PaymentMethods = dictPaymentMethods.query.all() # TODO filtrer avec la cor.
    form.id_payment_method.choices = [('', '-- Sélectionnez un moyen de paiement --')] + [(PaymentMethod.id_payment_method, PaymentMethod.label) for PaymentMethod in PaymentMethods]
    # allow null operation_date
    if request.form.get('operation_date') == '' and request.method == 'POST' and form.validate()  :
        operation_date = None
    else :
        operation_date = request.form.get('operation_date')
    # Get cleaned amound
    if type_operation == 'Dépense' and request.method == 'POST' and form.validate()  :
        amount = -getDecimal(request.form.get('amount'))
    else :
        amount = getDecimal(request.form.get('amount'))
    # Commit form
    if request.method == 'POST' and form.validate() :
        Operation = tOperations(
            None, #id_grp_operation
            request.form['name'],
            request.form['detail_operation'],
            id_type_operation,
            # allow None operation date
            operation_date,
            request.form['effective_date'],
            amount,
            getChoiceOrNone(request.form['id_payment_method']),
            getChoiceOrNone(request.form['id_account']),
            getChoiceOrNone(request.form['id_budget']),
            getChoiceOrNone(request.form['id_category']),
            getFileUrl('uploaded_file'),
            bool('false'),
            current_user.id_user
        )
        db.session.add(Operation)
        db.session.commit()
        return redirect(url_for('operations'))
    # Return form
    return render_template('operations/add_or_update_movement.html', form=form, Operation=None, type_operation=type_operation)


# Modification
@operations_bp.route('/edit/<id_operation>', methods=['GET', 'POST'])
@login_required
def updateMovement(id_operation): #movement = Dépense + Recette
    # Pre-load form data
    # pre-loaded form
    Operation = db.session.get(tOperations, id_operation) #tOperations.query.get(id_operation)
    type_operation = dictOperationTypes.query.filter_by(id_type_operation = Operation.id_type_operation).one().label
    #Get choices and form
    form = formMovement(request.form, obj=Operation)
    # Get accounts
    if type_operation=='Recette':
        Accounts = tAccounts.query.filter_by(is_personnal=False).filter_by(active=True)
    else :
        Accounts = tAccounts.query.filter_by(active=True)
    # Form Choices
    # accounts
    form.id_account.choices = [('', '-- Sélectionnez un compte --')] + [(Account.id_account, Account.name) for Account in Accounts]
    form.id_account.default=Operation.id_account
    # Budget
    activeBudgets = tBudgets.query.filter_by(date_closing=None)
    form.id_budget.choices = [('', '-- Sélectionnez un budget --')] + [(activeBudget.id_budget, activeBudget.name) for activeBudget in activeBudgets]
    form.id_budget.default=Operation.id_budget
    # Category
    Categories = dictCategories.query.filter(dictCategories.id_type_operation == Operation.id_type_operation, dictCategories.seizable == True).order_by(dictCategories.cd_category).all()
    form.id_category.choices = [('', '-- Sélectionnez une catégorie --')] + [(category.id_category, str(category.cd_category)+" - "+category.label) for category in Categories]
    form.id_category.default=Operation.id_category
    # Payment method
    PaymentMethods = dictPaymentMethods.query.all() # TODO filtrer avec la cor.
    form.id_payment_method.choices = [('', '-- Sélectionnez un moyen de paiement --')] + [(PaymentMethod.id_payment_method, PaymentMethod.label) for PaymentMethod in PaymentMethods]
    form.id_payment_method.default=Operation.id_payment_method
    # allow null operation_date
    if request.form.get('operation_date') == '' and request.method == 'POST' and form.validate()  :
        operation_date = None
    else :
        operation_date = request.form.get('operation_date')
    # Get cleaned amound
    if type_operation == 'Dépense' and request.method == 'POST' and form.validate()  :
        amount = -getDecimal(request.form.get('amount'))
    else :
        amount = getDecimal(request.form.get('amount'))
    # Update
    if request.method == 'POST' and form.validate():
        # let None as id_grp_operations
        Operation.name = request.form['name'],
        Operation.detail_operation = request.form['detail_operation'],
        # - let id_type_operation unchanged
        Operation.operation_date = operation_date
        Operation.effective_date = request.form['effective_date']
        Operation.amount = amount
        Operation.id_payment_method = getChoiceOrNone(request.form['id_payment_method'])
        Operation.id_account = getChoiceOrNone(request.form['id_account'])
        Operation.id_budget = getChoiceOrNone(request.form['id_budget'])
        Operation.id_category = getChoiceOrNone(request.form['id_category'])
        if not request.form.get('keep_file'):
            Operation.uploaded_file = getFileUrl('uploaded_file')
        Operation.meta_id_digitiser = current_user.id_user
        db.session.commit()
        return redirect(url_for('operations'))
    # Return form
    return render_template('operations/add_or_update_movement.html', form=form, Operation=Operation, type_operation=type_operation)


