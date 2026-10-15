from flask import Flask, Blueprint, render_template, request, flash, get_flashed_messages, redirect, url_for, make_response, stream_with_context, jsonify, current_app
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
from .utils import *

operations_bp = Blueprint("operations",__name__,url_prefix="/operations")

#####################
## Search function ##
#####################

# Filtering function for API & Downloads
def search_operations():
    query = vOperations.query.filter(vOperations.type_operation != 'Engagement')

    id_type_operation = request.args.get("id_type_operation", "")
    libelle = request.args.get("libelle", "")
    id_budget = request.args.get("id_budget", "")
    id_account = request.args.get("id_account", "")
    montant = request.args.get("montant", type=str)
    category = request.args.get("category", "")
    id_spending_allocation = request.args.get("id_spending_allocation", "")
    with_depreciation = request.args.get("with_depreciation") is not None
    invoice_reference = request.args.get("invoice_reference", "")
    date_apres = request.args.get("date_apres", type=str)
    date_avant = request.args.get("date_avant", type=str)
    missing_file = request.args.get("missing_file") is not None
    for_vat_summary = request.args.get("for_vat_summary") is not None

    if id_type_operation:
        query = query.filter(
            vOperations.id_type_operation == id_type_operation
        )

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

    if id_spending_allocation :
        query = query.filter(
            vOperations.id_spending_allocation == id_spending_allocation
        )

    if invoice_reference:
        like_pattern = f"%{invoice_reference}%"
        query = query.filter(
            vOperations.invoice_reference.ilike(like_pattern)
        )

    if with_depreciation :
        query = query.filter(vOperations.with_depreciation.is_not(None))

    if montant:
        try:
            montant = request.args.get("montant", "")
            montant_decimal = abs_decimal(montant)
            query = query.filter(func.abs(vOperations.amount) == montant_decimal)
        except ValueError:
            pass  # montant mal formé, on ignore le filtre

    if date_apres:
        try:
            date_apres_parsed = datetime.strptime(date_apres, "%Y-%m-%d").date()

            query = query.filter(vOperations.effective_date >= date_apres_parsed)
        except ValueError:
            pass

    if date_avant:
        try:
            date_avant_parsed = datetime.strptime(date_avant, "%Y-%m-%d").date()

            query = query.filter(vOperations.effective_date <= date_avant_parsed)
        except ValueError:
            pass

    if missing_file :
        query = query.filter(and_(
            vOperations.type_operation == 'Dépense',
            vOperations.uploaded_file.is_(None)))

    # Si "for_vat_summary" mais pas de période définie, ne retourner aucune donnée
    if for_vat_summary and not (date_apres and date_avant):
        query = query.filter(vOperations.id_operation < 0)

    if for_vat_summary and date_apres and date_avant :
        query = query.filter(or_(
        # Recettes comportant de la TVA
        and_(
            vOperations.type_operation == 'Recette',
            vOperations.vat_amount.isnot(None),
            vOperations.vat_amount != 0,
        ),
        # Dépenses avec une TVA récupérable
        and_(
            vOperations.type_operation == 'Dépense',
            vOperations.recoverable_vat_amount.isnot(None),
            vOperations.recoverable_vat_amount != 0,
        ),
    ))

    return query

def compute_vat_summary(query):
    """Résumé de TVA sur les opérations filtrées par `query`.
    Renvoie des Decimal : collected (recettes), recoverable (dépenses), balance (à reverser si > 0)."""
    collected = (query.filter(vOperations.type_operation == 'Recette').with_entities(func.coalesce(func.sum(vOperations.vat_amount), 0)).scalar())
    recoverable = (query.filter(vOperations.type_operation == 'Dépense').with_entities(func.coalesce(func.sum(vOperations.recoverable_vat_amount), 0)).scalar())
    collected = Decimal(collected)
    recoverable = Decimal(recoverable)
    # Retourner une table des TVA collectées, récupérables, et du différentiel
    return {
        "collected": collected,
        "recoverable": recoverable,
        "balance": collected - recoverable,
    }

@operations_bp.route("/api", methods=["GET"])
@login_required
def get_api_operations():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))

    query = search_operations()

    total = query.count()

    # Calculs des montants de TVA collectés, Récupérables, et bilan. Utilisé par le bilan de TVA
    vat_summary = None
    if (request.args.get("for_vat_summary") is not None and request.args.get("date_apres") and request.args.get("date_avant")):
        vat_summary = compute_vat_summary(query)

    results = query.order_by(vOperations.effective_date.desc()).order_by(vOperations.id_operation.desc()).offset((page - 1) * per_page).limit(per_page).all()

    data = [{
        "id_operation": op.id_operation,
        "effective_date": op.effective_date.strftime('%Y-%m-%d') if op.effective_date else "",
        "operation_date": op.operation_date.strftime('%Y-%m-%d') if op.operation_date else "",
        "name_operation": op.name_operation,
        "invoice_reference": op.invoice_reference,
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
        "vat_amount": op.vat_amount,
        "affectation": op.affectation,
        "vat_ratio": op.vat_ratio,
        "recoverable_vat_amount": op.recoverable_vat_amount,
        "with_depreciation": op.with_depreciation,
        "uploaded_file": url_for('static', filename=op.uploaded_file) if op.uploaded_file else "",
        "locked" : op.locked,
        "meta_create_date": op.meta_create_date,
        "meta_update_date": op.meta_update_date
    } for op in results]

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "vat_summary": vat_summary,
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
        "reference_facture",
        "detail",
        "type_operation",
        "categorie",
        "categorie_parent",
        "budget",
        "compte",
        "methode_paiement",
        "montant_ttc",
        "montant_tva",
        "affectation",
        "taux_recuparation_tva",
        "tva_recuperable",
        "amortissement",
        "justificatif",
        "verouillee",
        "saisi_le",
        "modifie_le"
    ])

    for op in results:
        writer.writerow([
            op.id_operation,
            op.effective_date.strftime('%Y-%m-%d') if op.effective_date else "",
            op.operation_date.strftime('%Y-%m-%d') if op.operation_date else "",
            op.name_operation,
            op.invoice_reference,
            op.detail_operation,
            op.type_operation,
            op.category,
            op.parent_category,
            op.budget_name,
            op.account_name,
            op.payment_method,
            Decimal(op.amount),
            op.vat_amount,
            op.affectation,
            op.vat_ratio,
            op.recoverable_vat_amount,
            url_for('static', filename=op.uploaded_file) if op.uploaded_file else "",
            op.locked,
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
    allocations = db.session.query(dictVatRatio.id_spending_allocation, dictVatRatio.label)
    types = db.session.query(dictOperationTypes.id_type_operation, dictOperationTypes.label).filter(dictOperationTypes.label !='Engagement').filter(dictOperationTypes.label !='Solde initial').filter(dictOperationTypes.label != 'Valorisation du bénévolat')
    return render_template('operations/operations_list.html', budgets=budgets, accounts=accounts, categories=categories, allocations=allocations, types=types)

# Suppression d'une opération ou de plusieurs opérations appariées
@operations_bp.route('/<id_operation>/delete', methods=['GET', 'POST'])
@login_required
def deleteMovement(id_operation): 
    operation=db.session.get(tOperations, id_operation) 
    db.session.delete(operation)
    db.session.commit()
    return redirect(url_for('operations.operations'))



#######################
# Dépenses & Recettes #
#######################
# Ajout
@operations_bp.route('/<type_operation>/add', methods=['GET', 'POST'])
@login_required
def addMovement(type_operation): #movement = Dépense + Recette
    #Get choices and form
    id_type_operation = dictOperationTypes.query.filter_by(label = type_operation).one().id_type_operation
    if type_operation=='Recette': 
        # Charger le formulaire de base
        form = formMovementBase(request.form)
        Accounts = tAccounts.query.filter_by(is_personnal=False).filter_by(active=True)
    else :
        # Charger le formulaire étendu pour les dépenses
        form = formMovementExtended(request.form)
        Accounts = tAccounts.query.filter_by(active=True)
        # Affectation choices
        VatRatios = dictVatRatio.query.order_by(dictVatRatio.ratio.desc()).all()
        form.id_spending_allocation.choices = [('', '-- Sélectionnez une affectation --')] + [(r.id_spending_allocation, r.label, {'data-ratio': str(r.ratio) if r.ratio is not None else ''}) for r in VatRatios]
    # Form Choices
    # accounts
    form.id_account.choices = [('', '-- Sélectionnez un compte --')] + [(Account.id_account, Account.name) for Account in Accounts]
    if request.method == 'GET':
        form.id_account.data = str(current_user.id_default_account)
    # Budget
    activeBudgets = tBudgets.query.filter_by(date_closing=None).order_by(tBudgets.name)
    form.id_budget.choices = [('', '-- Sélectionnez un budget --')] + [(activeBudget.id_budget, activeBudget.name, {'data-vat': str(activeBudget.vat_amount) if activeBudget.vat_amount is not None else 0}) for activeBudget in activeBudgets]
    # Category
    Categories = dictCategories.query.filter(dictCategories.id_type_operation == id_type_operation, dictCategories.seizable == True).order_by(dictCategories.cd_category).all()
    form.id_category.choices = [('', '-- Sélectionnez une catégorie --')] + [(category.id_category, str(category.cd_category)+" - "+category.label, {'data-keywords': category.keywords or ''}) for category in Categories]
    # Payment method
    PaymentMethods = dictPaymentMethods.query.all() # TODO filtrer avec la cor.
    form.id_payment_method.choices = [('', '-- Sélectionnez un moyen de paiement --')] + [(PaymentMethod.id_payment_method, PaymentMethod.label) for PaymentMethod in PaymentMethods]
    # VAT Rates for autocompletion
    rates = current_app.config['VAT_RATES_AUTOCOMPLETE']          # [('20 %', '0.20'), ...]
    form.vat_rate_autocompletion.choices = [(rate, label) for rate, label in rates]
    if request.method == 'GET':
        form.vat_rate_autocompletion.data = current_app.config['VAT_DEFAULT_RATE']
    # allow null operation_date
    if request.form.get('operation_date') == '' and request.method == 'POST' and form.validate()  :
        operation_date = None
    else :
        operation_date = request.form.get('operation_date')
    # Get cleaned amound
    if type_operation == 'Dépense' and request.method == 'POST' and form.validate()  :
        amount = -abs_decimal(request.form.get('amount'))
    else :
        amount = abs_decimal(request.form.get('amount'))
    # Commit form
    if request.method == 'POST' and form.validate() :
        if type_operation=='Dépense':
            # Calcul de la TVA récupérable à partir du montant de TVA, et de l'affectation
            id_spending_allocation = request.form['id_spending_allocation']
            allocation = db.session.get(dictVatRatio, form.id_spending_allocation.data)
            vat_ratio = allocation.ratio if allocation and allocation.ratio is not None else None
            vat_amount = abs_decimal(form.vat_amount.data)
            recoverable_vat_amount = (vat_amount * vat_ratio).quantize(Decimal('0.01')) if (vat_amount is not None and vat_ratio is not None) else None
            with_depreciation = bool(request.form.get('with_depreciation'))
        else : 
            # Set None/0 for additional inputs
            id_spending_allocation = None
            vat_ratio = None
            recoverable_vat_amount = Decimal('0.00')
            with_depreciation = None
        Operation = tOperations(
            None, #id_grp_operation
            request.form['name'],
            request.form['detail_operation'],
            id_type_operation,
            operation_date,
            request.form['effective_date'],
            amount,
            abs_decimal(request.form['vat_amount']),
            id_spending_allocation,
            vat_ratio,
            recoverable_vat_amount,
            with_depreciation,
            getChoiceOrNone(request.form['id_payment_method']),
            getChoiceOrNone(request.form['id_account']),
            getChoiceOrNone(request.form['id_budget']),
            getChoiceOrNone(request.form['id_category']),
            request.form['invoice_reference'],
            getFileUrl('uploaded_file'),
            current_user.id_user
        )
        db.session.add(Operation)
        db.session.commit()
        return redirect(url_for('operations.operations'))
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
    if type_operation=='Recette': 
        # Charger le formulaire de base
        form = formMovementBase(request.form)
        Accounts = tAccounts.query.filter_by(is_personnal=False).filter_by(active=True)
    else :
        # Charger le formulaire étendu pour les dépenses
        form = formMovementExtended(request.form)
        Accounts = tAccounts.query.filter_by(active=True)
        # Affectation choices
        VatRatios = dictVatRatio.query.order_by(dictVatRatio.ratio.desc()).all()
        form.id_spending_allocation.choices = [('', '-- Sélectionnez une affectation --')] + [(r.id_spending_allocation, r.label, {'data-ratio': str(r.ratio) if r.ratio is not None else ''}) for r in VatRatios]
    # Form Choices
    # accounts
    form.id_account.choices = [('', '-- Sélectionnez un compte --')] + [(Account.id_account, Account.name) for Account in Accounts]
    # Budget
    activeBudgets = tBudgets.query.filter_by(date_closing=None).order_by(tBudgets.name)
    form.id_budget.choices = [('', '-- Sélectionnez un budget --')] + [(activeBudget.id_budget, activeBudget.name, {'data-vat': str(activeBudget.vat_amount) if activeBudget.vat_amount is not None else 0}) for activeBudget in activeBudgets]
    # Category
    Categories = dictCategories.query.filter(dictCategories.id_type_operation == Operation.id_type_operation, dictCategories.seizable == True).order_by(dictCategories.cd_category).all()
    form.id_category.choices = [('', '-- Sélectionnez une catégorie --')] + [(category.id_category, str(category.cd_category)+" - "+category.label) for category in Categories]
    # Payment method
    PaymentMethods = dictPaymentMethods.query.all() # TODO filtrer avec la cor.
    form.id_payment_method.choices = [('', '-- Sélectionnez un moyen de paiement --')] + [(PaymentMethod.id_payment_method, PaymentMethod.label) for PaymentMethod in PaymentMethods]
    # VAT Rates for autocompletion
    # Ne pas recharger les seuils pour faciliter la saisie en édition, afin de ne pas introduire d'erreurs ou ne pas recalculer la TVA de manière involontaire/transparente.
    # Pré-remplir avec les valeurs existantes
    if request.method == 'GET':
        form.process(obj=Operation)
        form.amount.data = abs(Operation.amount) if Operation.amount is not None else None
    # allow null operation_date
    if request.form.get('operation_date') == '' and request.method == 'POST' and form.validate()  :
        operation_date = None
    else :
        operation_date = request.form.get('operation_date')
    # Get cleaned amount
    if type_operation == 'Dépense' and request.method == 'POST' and form.validate()  :
        # Affectation choices
        VatRatios = dictVatRatio.query.order_by(dictVatRatio.ratio.desc()).all()
        form.id_spending_allocation.choices = [('', '-- Sélectionnez une affectation --')] + [(r.id_spending_allocation, r.label, {'data-ratio': str(r.ratio) if r.ratio is not None else ''}) for r in VatRatios]
        amount = -abs_decimal(request.form.get('amount'))
    else :
        amount = abs_decimal(request.form.get('amount'))
    # Update
    if request.method == 'POST' and form.validate():
        vat_amount = abs_decimal(form.vat_amount.data)
        # let None as id_grp_operations
        Operation.name = request.form['name']
        Operation.detail_operation = request.form['detail_operation']
        # - let id_type_operation unchanged
        Operation.operation_date = operation_date
        Operation.effective_date = request.form['effective_date']
        Operation.amount = amount
        Operation.vat_amount = vat_amount
        if type_operation == 'Dépense' :
            # Calcul de la TVA récupérable à partir du montant de TVA, et de l'affectation
            allocation = db.session.get(dictVatRatio, form.id_spending_allocation.data)
            vat_ratio = allocation.ratio if allocation and allocation.ratio is not None else None
            recoverable_vat_amount = (vat_amount * vat_ratio).quantize(Decimal('0.01')) if (vat_amount is not None and vat_ratio is not None) else None
            Operation.id_spending_allocation = request.form['id_spending_allocation']
            Operation.vat_ratio = vat_ratio
            Operation.recoverable_vat_amount = recoverable_vat_amount
            Operation.with_depreciation = bool(request.form.get('with_depreciation'))
        Operation.id_payment_method = getChoiceOrNone(request.form['id_payment_method'])
        Operation.id_account = getChoiceOrNone(request.form['id_account'])
        Operation.id_budget = getChoiceOrNone(request.form['id_budget'])
        Operation.id_category = getChoiceOrNone(request.form['id_category'])
        Operation.invoice_reference = request.form['invoice_reference']
        if not request.form.get('keep_file'):
            Operation.uploaded_file = getFileUrl('uploaded_file')
        Operation.meta_id_digitiser = current_user.id_user
        db.session.commit()
        return redirect(url_for('operations.operations'))
    # Return form
    return render_template('operations/add_or_update_movement.html', form=form, Operation=Operation, type_operation=type_operation)

