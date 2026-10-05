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

# Import Blueprints 
from .routes import (
    auth_bp,
    profit_bonus_bp,
    budgets_bp,
    budgets_actions_bp,
    accounts_bp,
    funders_bp
    )

app = Flask(__name__, template_folder='../templates', static_folder='../static')

app.register_blueprint(auth_bp)
app.register_blueprint(profit_bonus_bp)
app.register_blueprint(budgets_bp)
app.register_blueprint(budgets_actions_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(funders_bp)


# Load configuration
app.config.from_pyfile('../../config/config.py')
# To get one variable, tape app.config['MY_VARIABLE']


#############
### UTILS ###
#############

#def allowed_file(filename):
#    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Todo : clean decimal inputs
def getDecimal(input, allow_none=False):
    if input is None or input=='' :
        decimal=0.00
    else :
        decimal=abs(float(str(input).replace(',','.')))
    return decimal


def getChoiceOrNone(input):
    if input =='' or input is None:
        choice=None
    else:
        choice=input
    return choice


def getFileUrl(input):
    f = request.files.get(input)
    if f :
        filename = uuid.uuid4().hex[:10]+'_'+secure_filename(f.filename)
        f.save(app.config['BASE_DIR']+'app/static/uploads/'+filename)
        file_url='uploads/'+filename
    else :
        file_url=None
    return file_url

@app.template_filter()
def format_datetime(value):
    format="dd-MM-y"
    return babel.dates.format_datetime(value, format)

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

##########
## APIS ##
##########

@app.route("/api/operations", methods=["GET"])
@login_required
def get_api_operations():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))

    libelle = request.args.get("libelle", "")
    montant = request.args.get("montant", type=float)
    categorie = request.args.get("categorie", "")
    date_apres = request.args.get("date_apres", type=str)
    date_avant = request.args.get("date_avant", type=str)

    query = vOperations.query

    
    if libelle:
        like_pattern = f"%{libelle}%"
        query = query.filter(or_(
            vOperations.name_operation.ilike(like_pattern),
            vOperations.detail_operation.ilike(like_pattern)
        ))

    if montant:
        try:
            montant = request.args.get("montant", "").replace(",", ".")
            montant_float = float(montant)
            query = query.filter(func.abs(vOperations.amount) == abs(montant_float))
        except ValueError:
            pass  # montant mal formé, on ignore le filtre

    if categorie:
        cat_pattern = f"%{categorie}%"
        query = query.filter(or_(
            vOperations.type_operation.ilike(cat_pattern),
            vOperations.category.ilike(cat_pattern),
            vOperations.parent_category.ilike(cat_pattern)
        ))

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


    total = query.count()

    results = query.filter(vOperations.type_operation != 'Engagement').order_by(vOperations.effective_date.desc()).order_by(vOperations.id_operation.desc()).offset((page - 1) * per_page).limit(per_page).all()

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
        "amount": float(op.amount),
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


#####################
# Toutes opérations #
#####################

# Liste
@app.route('/operations', methods=['GET', 'POST'])
@login_required
def operations():
    # All operations
    return render_template('operations/operations_list.html', type=None)

# Export CSV
@app.route('/operations/export_csv/<year>')
@app.route('/operations/export_csv', defaults={'year': None})
@login_required
def operationsCSV(year=None):
    @stream_with_context
    def generate():
        data = StringIO()
        w = csv.writer(data)

        # write header
        header=['Date_operation','Date_effet','Exercice','Libelle','Detail','Montant','Moyen_de_paiement','Compte','Budget','Groupe_operation','Type','Categorie_fiscale','Categorie_parente','Justificatif','Date_creation','Derniere_modification']
        w.writerow(header)
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # write each item
        if year :
            Operations = vOperations.query.filter(vOperations.type_operation != 'Engagement').filter(vOperations.year == year).order_by(vOperations.effective_date.desc()).all()
        else : 
            Operations = vOperations.query.filter(vOperations.type_operation != 'Engagement').order_by(vOperations.effective_date.desc()).all()
        for operation in Operations:
            if operation.uploaded_file is None or operation.uploaded_file == '':
                document_url=None
            else:
                document_url=app.config['BASE_URL']+'/static/'+str(operation.uploaded_file)
            w.writerow((
                operation.operation_date,  
                operation.effective_date, 
                operation.year,
                operation.name_operation,
                operation.detail_operation,
                operation.amount,
                operation.payment_method,
                operation.account_name,
                operation.budget_name,
                operation.id_grp_operation,
                operation.type_operation,
                operation.category,
                operation.parent_category,
                document_url,
                operation.meta_create_date,
                operation.meta_update_date
            ))
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)
        
    # stream the response as the data is generated
    response = Response(generate(), mimetype='text/csv')
    # add a filename
    response.headers.set("Content-Disposition", "attachment", filename=datetime.now().strftime("%Y%m%d_%H-%M-%S")+"_export_operations.csv")
    return response


# Suppression d'une opération ou de plusieurs opérations appariées
@app.route('/operations/<id_operation>/delete', methods=['GET', 'POST'])
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
@app.route('/operations/<type_operation>/add', methods=['GET', 'POST'])
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
@app.route('/operations/edit/<id_operation>', methods=['GET', 'POST'])
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


#######################
# Transferts internes #
#######################
# Add transfer
@app.route('/operations/transfer/<type_transfer>/add', methods=['GET', 'POST'])
@login_required
def addTransfer(type_transfer):
    #Get choices and form
    form = formTransfer(request.form)
    # Account
    FromAccounts = tAccounts.query.filter_by(is_personnal=False).filter_by(active=True)
    if type_transfer == 'Internal' :
        ToAccounts = tAccounts.query.filter_by(is_personnal=False).filter_by(active=True)
        id_type_operation = dictOperationTypes.query.filter_by(label = 'Transaction interne').one().id_type_operation
        id_category = dictCategories.query.filter_by(cd_category=900).one().id_category
    else :#refund
        ToAccounts = tAccounts.query.filter_by(is_personnal=True).filter_by(active=True)
        id_type_operation = dictOperationTypes.query.filter_by(label = 'Remboursement de frais').one().id_type_operation
        id_category = dictCategories.query.filter_by(cd_category=910).one().id_category
    form.from_id_account.choices = [('', '-- Sélectionnez un compte débiteur --')] + [(FromAccount.id_account, FromAccount.name) for FromAccount in FromAccounts]
    form.to_id_account.choices = [('', '-- Sélectionnez un compte créditeur --')] + [(ToAccount.id_account, ToAccount.name) for ToAccount in ToAccounts]
    # Payment method
    PaymentMethods = dictPaymentMethods.query.all()
    form.id_payment_method.choices = [('', '-- Sélectionnez un moyen de paiement --')] + [(PaymentMethod.id_payment_method, PaymentMethod.label) for PaymentMethod in PaymentMethods]
    if request.method == 'POST' and form.validate() :
        id_grp_operation = uuid.uuid4() #id_grp_operation
        debit = tOperations(
            id_grp_operation,
            request.form['name'],
            request.form['detail_transfer'],
            id_type_operation,
            None,
            request.form['effective_date'],
            -getDecimal(request.form.get('amount')),
            getChoiceOrNone(request.form['id_payment_method']),
            request.form['from_id_account'],
            None, # budget id
            id_category,
            None,
            bool('false'),
            current_user.id_user
        )
        credit = tOperations(
            id_grp_operation,
            request.form['name'],
            request.form['detail_transfer'],
            id_type_operation,
            None,
            request.form['effective_date'],
            getDecimal(request.form.get('amount')),
            getChoiceOrNone(request.form['id_payment_method']),
            request.form['to_id_account'],
            None, #budget_id
            id_category,
            None,
            bool('false'),
            current_user.id_user
        )
        db.session.add(debit)
        db.session.add(credit)
        db.session.commit()
        return redirect(url_for('operations'))
    # return form
    return render_template('operations/add_or_update_transfer.html', form=form, Transfert=None, Type=type_transfer)

# Update transfert
@app.route('/operations/transfer/edit/<id_grp_operation>', methods=['GET', 'POST'])
@login_required
def updateTransfer(id_grp_operation):
    #Get updated objects
    credit= tOperations.query.filter_by(id_grp_operation=id_grp_operation).filter(tOperations.amount>0).first()
    debit= tOperations.query.filter_by(id_grp_operation=id_grp_operation).filter(tOperations.amount<0).first()
    form = formTransfer(request.form)
    # Get choices and form
    if dictOperationTypes.query.get(credit.id_type_operation).label == 'Remboursement de frais' :
        type_operation = 'Refund'
        ToAccounts = tAccounts.query.filter_by(is_personnal=True).filter_by(active=True)
        id_type_operation = dictOperationTypes.query.filter_by(label = 'Remboursement de frais').one().id_type_operation
        id_category = dictCategories.query.filter_by(cd_category=910).one().id_category
    elif dictOperationTypes.query.get(credit.id_type_operation).label == 'Transaction interne' :
        type_operation = 'Internal'
        ToAccounts = tAccounts.query.filter_by(is_personnal=False).filter_by(active=True)
        id_type_operation = dictOperationTypes.query.filter_by(label = 'Transaction interne').one().id_type_operation
        id_category = dictCategories.query.filter_by(cd_category=900).one().id_category
    # Filter debitable accounts
    FromAccounts = tAccounts.query.filter_by(is_personnal=False)
    form.from_id_account.choices = [('', '-- Sélectionnez un compte débiteur --')] + [(FromAccount.id_account, FromAccount.name) for FromAccount in FromAccounts]
    # Filter creditable accounts
    form.to_id_account.choices = [('', '-- Sélectionnez un compte créditeur --')] + [(ToAccount.id_account, ToAccount.name) for ToAccount in ToAccounts]
    # Payment method
    PaymentMethods = dictPaymentMethods.query.all()
    form.id_payment_method.choices = [('', '-- Sélectionnez un moyen de paiement --')] + [(PaymentMethod.id_payment_method, PaymentMethod.label) for PaymentMethod in PaymentMethods]
    # Pre-load data
    form.process(
        obj=credit, 
        detail_transfer=credit.detail_operation, 
        from_id_account=debit.id_account,
        to_id_account=credit.id_account)
    # Update data
    if request.method == 'POST' and form.validate() :
        # id_grp_operation unchanged
        #Libelle
        credit.name = request.form['name']
        debit.name= request.form['name']
        # Details
        credit.detail_operation = request.form['detail_transfer']
        debit.detail_operation = request.form['detail_transfer']
        # id_type_operation unchanged
        # Effective_date
        credit.effective_date = request.form['effective_date']
        debit.effective_date =request.form['effective_date']
        # Amount
        credit.amount = getDecimal(request.form.get('amount'))
        debit.amount = -getDecimal(request.form.get('amount'))
        # Payment method
        credit.id_payment_method = getChoiceOrNone(request.form['id_payment_method'])
        debit.id_payment_method =getChoiceOrNone(request.form['id_payment_method'])
        # id_account
        credit.id_account = request.form['to_id_account']
        debit.id_account = request.form['from_id_account']
        # let None as id_budget
        # let id_category unchanged
        # let None as file
        # let false as pointed
        # id_digitiser
        credit.meta_id_digitiser = current_user.id_user
        debit.meta_id_digitiser =current_user.id_user
        db.session.commit()
        return redirect(url_for('operations'))
    # return form
    return render_template('operations/add_or_update_transfer.html', form=form, Transfert=id_grp_operation, Type=type_operation)



# Suppression
@app.route('/operations/transfer/<id_grp_operation>/delete', methods=['GET', 'POST'])
@login_required
def deleteTransfer(id_grp_operation): 
    operations=tOperations.query.filter_by(id_grp_operation=id_grp_operation)
    for operation in operations :
        db.session.delete(operation)
        db.session.commit()
    return redirect(url_for('operations'))


###############
# Engagements #
###############
# Liste
@app.route('/commitments')
@login_required
def commitments():
    Commitments = vOperations.query.filter(vOperations.type_operation == 'Engagement').order_by(vOperations.operation_date.desc()).all()
    return render_template('operations/commitments_list.html', Commitments=Commitments)

# Ajout
@app.route('/commitment/add', methods=['GET', 'POST'])
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
@app.route('/commitment/edit/<id_operation>', methods=['GET','POST'])
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
@app.route('/commitment/convert/<id_operation>', methods=['GET','POST'])
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
@app.route('/commitment/<id_operation>/delete', methods=['GET', 'POST'])
@login_required
def deleteCommitment(id_operation): 
    operation= db.session.get(tOperations, id_operation) #tOperations.query.get(id_operation)
    db.session.delete(operation)
    db.session.commit()
    return redirect(url_for('commitments'))


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


### Documents ###
# List documents
@app.route('/documents', methods=['GET'])
@login_required
def documents():
    documents = vDocuments.query.order_by(vDocuments.meta_create_date.desc()).all()
    return render_template('admin/documents/documents_list.html', documents = documents )

# Add document
@app.route('/documents/add', methods=['GET', 'POST'])
@login_required
def addDocument():
    form = formDocument(request.form)
    #Types de documents
    DocumentTypes = dictDocumentType.query.all()
    form.id_type.choices = [('', '-- Sélectionnez un type de document --')] + [(DocumentType.id_type, DocumentType.label) for DocumentType in DocumentTypes]
    # Formulaire
    if request.method == 'POST' and form.validate():
        document = tDocuments(
            request.form['title'], 
            request.form['description'], 
            request.form['id_type'],
            getFileUrl('uploaded_file'),
            current_user.id_user,
        )
        db.session.add(document)
        db.session.commit()
        return redirect('/documents')
    return render_template('admin/documents/add_or_update_document.html', form=form, document=None)


# Edit account
@app.route('/documents/edit/<id_document>', methods=['GET', 'POST'])
@login_required
def updateDocument(id_document):
  # pre-loaded form
    Document = db.session.get(tDocuments, id_document) #tDocuments.query.get(id_document)
    form = formDocument(request.form, obj=Document)
    # types
    DocumentTypes = dictDocumentType.query.all()
    form.id_type.choices = [('', '-- Sélectionnez un type de document --')] + [(DocumentType.id_type, DocumentType.label) for DocumentType in DocumentTypes]
    form.id_type.default=Document.id_type
    #Formulaire
    if request.method == 'POST' and form.validate():
        Document.title = request.form['title'], 
        Document.description = request.form['description'],
        if not request.form.get('keep_file'):
            Document.uploaded_file = getFileUrl('uploaded_file')
        db.session.commit()
        return redirect(url_for('documents'))
    return render_template('admin/documents/add_or_update_document.html', form=form, document=Document)

# Delete funder
@app.route('/documents/delete/<id_document>', methods=['GET', 'POST'])
@login_required
def deleteDocument(id_document):
    current_document= db.session.get(tDocuments, id_document) #tDocuments.query.get(id_document)
    db.session.delete(current_document)
    db.session.commit()
    return redirect('/documents')

##################
### WORK VALUE ###
##################

## Payrolls
@app.route('/payrolls')
@login_required
def payrolls():
    members=tMembers.query.filter_by(is_employed=True)
    id_member = request.args.get('id_member', None, type=int)
    if id_member:
        payrolls = vPayrolls.query.filter_by(id_member=id_member).order_by(vPayrolls.date_min_period.desc()).all()
    else :
        payrolls = vPayrolls.query.order_by(vPayrolls.date_min_period.desc()).all()
    return render_template('payrolls/payrolls_list.html', payrolls=payrolls, members=members)


@app.route('/payrolls/add', methods=['GET', 'POST'])
@login_required
def addPayroll():
    form = formPayroll(request.form)
    # Get employees
    Members = tMembers.query.filter_by(is_employed=True)
    form.id_member.choices = [('', '-- Sélectionnez un salarié --')]+[(Member.id_member, Member.member_name) for Member in Members]
    # Get months
    form.period_month.choices = [('1','Janvier'),('2', 'Février'),('3','Mars'),('4','Avril'),('5','Mai'),('6','Juin'),('7','Juillet'),('8','Août'),('9','Septembre'),('10','Octobre'),('11','Novembre'),('12','Décembre')]
    # Pre-fill period data
    # Pre-load data
    form.period_month.data = str(date.today().month)
    form.period_year.data = date.today().year
    # Get data from form
    if request.method == 'POST' and form.validate():
        payroll = tPayrolls(
            request.form['id_member'],
            datetime(int(request.form['period_year']), int(request.form['period_month']), 1), #min date
            datetime(int(request.form['period_year']), int(request.form['period_month']), monthrange(int(request.form['period_year']), int(request.form['period_month']))[1]), #max date
            getDecimal(request.form['gross_remuneration']), 
            getDecimal(request.form['gross_premium']), 
            getDecimal(request.form['employer_charge_amount']),
            getDecimal(request.form['worked_days']),
            getFileUrl('uploaded_file'),
            )
        db.session.add(payroll)
        db.session.commit()
        return redirect(url_for('payrolls'))
    return render_template('payrolls/add_or_update_member_payroll.html', form=form, payroll=None, Members=Members)

# Update payroll
@app.route('/payrolls/edit/<id_payroll>', methods=['GET', 'POST'])
@login_required
def updatePayroll(id_payroll):
    payroll = db.session.get(tPayrolls, id_payroll) #tPayrolls.query.get(id_payroll)
    form = formPayroll(request.form, obj=payroll)
    # Get employees
    Members = tMembers.query.filter_by(is_employed=True)
    form.id_member.choices = [(Member.id_member, Member.member_name) for Member in Members]
    form.id_member.default = payroll.id_member
    # Get months
    form.period_month.choices = [('1','Janvier'),('2', 'Février'),('3','Mars'),('4','Avril'),('5','Mai'),('6','Juin'),('7','Juillet'),('8','Août'),('9','Septembre'),('10','Octobre'),('11','Novembre'),('12','Décembre')]
    form.period_month.data = str(payroll.date_min_period.month)
    form.period_year.data = payroll.date_min_period.year
    if request.method == 'POST' and form.validate():
        payroll.id_member = request.form['id_member'], 
        payroll.date_min_period = datetime(int(request.form['period_year']), int(request.form['period_month']), 1), 
        payroll.date_max_period = datetime(int(request.form['period_year']), int(request.form['period_month']), monthrange(int(request.form['period_year']), int(request.form['period_month']))[1]), 
        payroll.gross_remuneration = getDecimal(request.form['gross_remuneration']), 
        payroll.gross_premium = getDecimal(request.form['gross_premium']), 
        payroll.employer_charge_amount = getDecimal(request.form['employer_charge_amount']), 
        payroll.worked_days = getDecimal(request.form['worked_days'])
        if not request.form.get('keep_file'):
            payroll.uploaded_file = getFileUrl('uploaded_file')
        db.session.commit()
        return redirect(url_for('payrolls'))
    return render_template('payrolls/add_or_update_member_payroll.html', form=form, payroll=payroll, Members=Members)

# Details payroll
@app.route('/payrolls/detail/<id_payroll>', methods=['GET', 'POST'])
@login_required
def detailPayroll(id_payroll):
    payroll = db.session.get(vPayrolls, id_payroll) #vPayrolls.query.get(id_payroll)
    corsPayrollBudget = vDecodeCorPayrollBudget.query.filter_by(id_payroll=id_payroll).order_by(vDecodeCorPayrollBudget.budget_name.desc()).all()
    form = formPayrollBudget(request.form)
    # Get budgets
    Budgets = tBudgets.query.filter_by(date_closing=None)
    form.id_budget.choices = [('','Gestion associative & Autres activités')]+[(Budget.id_budget, Budget.name) for Budget in Budgets]
    if request.method == 'POST' and form.validate():
        # Insert data
        payrollBudget = corPayrollBudget(
            id_payroll,
            getChoiceOrNone(request.form['id_budget']),  
            getDecimal(request.form['nb_days_allocated'])
            )
        db.session.add(payrollBudget)
        db.session.commit()
        return redirect(url_for('detailPayroll', id_payroll=id_payroll))
    return render_template('payrolls/detail_payroll.html', payroll=payroll, corsPayrollBudget=corsPayrollBudget, form=form, payrollBudget=None, Budgets=Budgets)

# Delete payroll
@app.route('/payrolls/delete/<id_payroll>', methods=['GET', 'POST'])
@login_required
def deletePayroll(id_payroll):
    current_payroll=db.session.get(tPayrolls, id_payroll) #tPayrolls.query.get(id_payroll)
    db.session.delete(current_payroll)
    db.session.commit()
    return redirect(url_for('payrolls'))


######################
# Cor payroll budget #
######################
@app.route('/payrolls/<id_payroll>/cor_budget/add', methods=['GET', 'POST'])
@login_required
def addCorPayrollBudget(id_payroll):
    form = formPayrollBudget(request.form)
    # Get budgets
    Budgets = tBudgets.query.filter_by(date_closing=None)
    form.id_budget.choices = [('','Gestion associative & Autres activités')]+[(Budget.id_budget, Budget.name) for Budget in Budgets]
    if request.method == 'POST' and form.validate():
        # Insert data
        payrollBudget = corPayrollBudget(
            id_payroll,
            getChoiceOrNone(request.form['id_budget']),  
            getDecimal(request.form['nb_days_allocated'])
            )
        db.session.add(payrollBudget)
        db.session.commit()
        return redirect(url_for('detailPayroll', id_payroll=id_payroll))
    return render_template('payrolls/add_or_update_allocation_payroll_budget.html', form=form, payrollBudget=None, Budgets=Budgets)


@app.route('/payrolls/<id_payroll>/cor_budget/<id_payroll_budget>/edit', methods=['GET', 'POST'])
@login_required
def updateCorPayrollBudget(id_payroll, id_payroll_budget):
    cor = db.session.get(corPayrollBudget, id_payroll_budget) #corPayrollBudget.query.get(id_payroll_budget)
    form = formPayrollBudget(request.form, obj=cor)
    # Get budgets
    Budgets = tBudgets.query.filter_by(date_closing=None)
    form.id_budget.choices = [('','Gestion associative & Autres activités')]+[(Budget.id_budget, Budget.name) for Budget in Budgets]
    if request.method == 'POST' and form.validate():
        cor.id_budget = getChoiceOrNone(request.form['id_budget'])
        cor.nb_days_allocated = getDecimal(request.form['nb_days_allocated'])
        db.session.commit()
        return redirect(url_for('detailPayroll', id_payroll=id_payroll))
    return render_template('payrolls/add_or_update_allocation_payroll_budget.html', form=form, corPayrollBudget=cor, Budgets=Budgets)


# Delete doc payroll budget
@app.route('/payrolls/<id_payroll>/cor_budget/<id_payroll_budget>/delete', methods=['GET', 'POST'])
@login_required
def deleteCorPayrollBudget(id_payroll, id_payroll_budget):
    cor = db.session.get(corPayrollBudget, id_payroll_budget) #corPayrollBudget.query.get(id_payroll_budget)
    db.session.delete(cor)
    db.session.commit()
    return redirect(url_for('detailPayroll', id_payroll=id_payroll))


"""
######
# Volunteering

@app.route('/members/volunteering')
@login_required
def volunteering():
    members=tMembers.query.all()
    id_member = request.args.get('id_member', None, type=int)
    if id_member:
        volunteerings = vPayrolls.query.filter_by(id_member=id_member).filter(vPayrolls.volunteering_valuation != 0).all()
    else :
        volunteerings = vPayrolls.query.filter(vPayrolls.volunteering_valuation != 0).all()
    return render_template('volunteering/volunteering_list.html', volunteerings=volunteerings)


@app.route('/members/volunteering/add', methods=['GET', 'POST'])
@login_required
def addVolunteering():
    form = formVolunteering(request.form)
    # Get members
    Members = tMembers.query.all()
    form.id_member.choices = [('', '-- Sélectionnez un membre --')]+[(Member.id_member, Member.member_name) for Member in Members]
    # Get months
    form.period_month.choices = [('1','Janvier'),('2', 'Février'),('3','Mars'),('4','Avril'),('5','Mai'),('6','Juin'),('7','Juillet'),('8','Août'),('9','Septembre'),('10','Octobre'),('11','Novembre'),('12','Décembre')]
    # Pre-fill period data
    # Pre-load data
    form.period_month.data = str(date.today().month)
    form.period_year.data = date.today().year
    # Pre-load daily valuation
    form.daily_valuation.data = app.config['DAILY_VALUATION']
    # Get data from form
    if request.method == 'POST' and form.validate():
        volunteering = tPayrolls(
            request.form['id_member'],
            datetime(int(request.form['period_year']), int(request.form['period_month']), 1), #min date
            datetime(int(request.form['period_year']), int(request.form['period_month']), monthrange(int(request.form['period_year']), int(request.form['period_month']))[1]), #max date
            0, #as gross_remuneration, 
            0, #as gross_premium, 
            0, #as employer_charge_amount,
            getDecimal(request.form['real_worked_days'])*getDecimal(request.form['daily_valuation']), # as volunteering valuation 
            getDecimal(request.form['real_worked_days'])
            )
        db.session.add(volunteering)
        db.session.commit()
        return redirect(url_for('volunteering'))
    return render_template('volunteering/add_or_update_member_volunteering.html', form=form, volunteering=None, Members=Members)

# Update volunteering
@app.route('/employees/volunteering/edit/<id_work_value>', methods=['GET', 'POST'])
@login_required
def updateVolunteering(id_work_value):
    volunteering = db.session.get(tPayrolls, id_work_value) #tPayrolls.query.get(id_work_value)
    form = formVolunteering(request.form, obj=volunteering)
    # Get employees
    Members = tMembers.query.all()
    form.id_member.choices = [(Member.id_member, Member.member_name) for Member in Members]
    form.id_member.default = volunteering.id_member
    # Get months
    form.period_month.choices = [('1','Janvier'),('2', 'Février'),('3','Mars'),('4','Avril'),('5','Mai'),('6','Juin'),('7','Juillet'),('8','Août'),('9','Septembre'),('10','Octobre'),('11','Novembre'),('12','Décembre')]
    form.period_month.data = str(volunteering.date_min_period.month)
    form.period_year.data = volunteering.date_min_period.year
    form.daily_valuation.data = volunteering.volunteering_valuation/volunteering.real_worked_days
    if request.method == 'POST' and form.validate():
        volunteering.id_member = request.form['id_member'], 
        volunteering.date_min_period = datetime(int(request.form['period_year']), int(request.form['period_month']), 1), 
        volunteering.date_max_period = datetime(int(request.form['period_year']), int(request.form['period_month']), monthrange(int(request.form['period_year']), int(request.form['period_month']))[1]), 
        volunteering.real_worked_days = getDecimal(request.form['real_worked_days'])
        volunteering.volunteering_valuation = getDecimal(request.form['daily_valuation'])*getDecimal(request.form['real_worked_days'])
        db.session.commit()
        return redirect(url_for('volunteering'))
    return render_template('volunteering/add_or_update_member_volunteering.html', form=form, Members=Members)

# Details volunteering
@app.route('/employees/volunteering/detail/<id_work_value>', methods=['GET', 'POST'])
@login_required
def detailVolunteering(id_work_value):
    current_volunteering=db.session.get(vPayrolls, id_work_value) #vPayrolls.query.get(id_work_value)
    return render_template('volunteering/detail_volunteering.html', volunteering=current_volunteering)

# Delete volunteering
@app.route('/employees/volunteering/delete/<id_work_value>', methods=['GET', 'POST'])
@login_required
def deleteVolunteering(id_work_value):
    current_volunteering=db.session.get(tPayrolls, id_work_value) #tPayrolls.query.get(id_work_value)
    db.session.delete(current_volunteering)
    db.session.commit()
    return redirect(url_for('volunteering'))
"""



#################
### Resultats ###
#################

# Export as pdf
@app.route('/results')
@login_required
def results():
    years=db.session.query(vResultByYear.year).distinct()
    return render_template('results/results.html', years=years)


#####################
### RESULTATS PDF ###
#####################

# Export as pdf
@app.route('/results/pdf/year/<year>')
@login_required
def resultsPDF(year):
    recettes=vResultByYear.query.filter_by(year=year).filter_by(type_category='Recette').all()
    depenses=vResultByYear.query.filter_by(year=year).filter_by(type_category='Dépense').all()
    current_date=date.today()
    result=sum([r.amount for r in recettes])+sum([d.amount for d in depenses])
    filename='export_bilan_'+year
    header_url=app.config['BASE_URL']+'/static/img/bandeau_pdf.png'
    html = render_template('results_pdf.html',depenses=depenses, recettes=recettes, year=year, current_date=current_date, result=result, header_url=header_url)
    options = {"enable-local-file-access": None}
    pdf = pdfkit.from_string(html, False, options=options)
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename={}.pdf".format(filename)
    return response


###########################
### Frais kilométriques ###
###########################
# Pour le moment,traité comme de simples dépenses
