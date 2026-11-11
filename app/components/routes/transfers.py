from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
import uuid
from sqlalchemy import or_
from ..init_db import db
from ..models import dictCategories, dictOperationTypes, dictPaymentMethods, tAccounts, tOperations
from ..forms import formTransfer
from .utils import abs_decimal, getChoiceOrNone

transfers_bp = Blueprint("transfers",__name__,url_prefix="/operations/transfer")

#######################
# Transferts internes #
#######################
# Add transfer
@transfers_bp.route('/<type_transfer>/add', methods=['GET', 'POST'])
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
    if request.method == 'GET':
        form.from_id_account.data = str(current_user.id_default_account)
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
            -abs_decimal(request.form.get('amount')),
            None, #vat_amount
            None, #spending_allocation
            None, #vat_ratio
            None, #recoverable_vat_amount
            None, #with_deprecation
            getChoiceOrNone(request.form['id_payment_method']),
            request.form['from_id_account'],
            None, # budget id
            id_category,
            None, #invoice_reference
            None, #uploaded_file
            current_user.id_user
        )
        credit = tOperations(
            id_grp_operation,
            request.form['name'],
            request.form['detail_transfer'],
            id_type_operation,
            None,
            request.form['effective_date'],
            abs_decimal(request.form.get('amount')),
            None, #vat_amount
            None, #spending_allocation
            None, #vat_ratio
            None, #recoverable_vat_amount
            None, #with_deprecation
            getChoiceOrNone(request.form['id_payment_method']),
            request.form['to_id_account'],
            None, # budget id
            id_category,
            None, #invoice_reference
            None, #uploaded_file
            current_user.id_user
        )
        db.session.add(debit)
        db.session.add(credit)
        db.session.commit()
        return redirect(url_for('operations.operations'))
    # return form
    return render_template('operations/add_or_update_transfer.html', form=form, Transfert=None, Type=type_transfer)

# Update transfert
@transfers_bp.route('/edit/<id_grp_operation>', methods=['GET', 'POST'])
@login_required
def updateTransfer(id_grp_operation):
    #Get updated objects
    credit= tOperations.query.filter_by(id_grp_operation=id_grp_operation).filter(tOperations.amount>0).first_or_404()
    debit= tOperations.query.filter_by(id_grp_operation=id_grp_operation).filter(tOperations.amount<0).first_or_404()
    form = formTransfer(request.form,
        obj=credit,
        detail_transfer=credit.detail_operation,
        from_id_account=debit.id_account,
        to_id_account=credit.id_account,)
    # Get choices and form
    if dictOperationTypes.query.get(credit.id_type_operation).label == 'Remboursement de frais' :
        type_operation = 'Refund'
        ToAccounts = tAccounts.query.filter_by(is_personnal=True).filter(or_(tAccounts.active == True, tAccounts.id_account == credit.id_account))
        id_type_operation = dictOperationTypes.query.filter_by(label = 'Remboursement de frais').one().id_type_operation
        id_category = dictCategories.query.filter_by(cd_category=910).one().id_category
    elif dictOperationTypes.query.get(credit.id_type_operation).label == 'Transaction interne' :
        type_operation = 'Internal'
        ToAccounts = tAccounts.query.filter_by(is_personnal=False).filter(or_(tAccounts.active == True, tAccounts.id_account == credit.id_account))
        id_type_operation = dictOperationTypes.query.filter_by(label = 'Transaction interne').one().id_type_operation
        id_category = dictCategories.query.filter_by(cd_category=900).one().id_category
    # Filter debitable accounts
    FromAccounts = tAccounts.query.filter_by(is_personnal=False).filter(or_(tAccounts.active == True, tAccounts.id_account == debit.id_account))
    form.from_id_account.choices = [('', '-- Sélectionnez un compte débiteur --')] + [(FromAccount.id_account, FromAccount.name) for FromAccount in FromAccounts]
    # Filter creditable accounts
    form.to_id_account.choices = [('', '-- Sélectionnez un compte créditeur --')] + [(ToAccount.id_account, ToAccount.name) for ToAccount in ToAccounts]
    # Payment method
    PaymentMethods = dictPaymentMethods.query.all()
    form.id_payment_method.choices = [('', '-- Sélectionnez un moyen de paiement --')] + [(PaymentMethod.id_payment_method, PaymentMethod.label) for PaymentMethod in PaymentMethods]
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
        credit.amount = abs_decimal(request.form.get('amount'))
        debit.amount = -abs_decimal(request.form.get('amount'))
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
        return redirect(url_for('operations.operations'))
    # return form
    return render_template('operations/add_or_update_transfer.html', form=form, Transfert=id_grp_operation, Type=type_operation)

# Suppression
@transfers_bp.route('/<id_grp_operation>/delete', methods=['POST'])
@login_required
def deleteTransfer(id_grp_operation): 
    operations=tOperations.query.filter_by(id_grp_operation=id_grp_operation)
    for operation in operations :
        db.session.delete(operation)
    db.session.commit()
    return redirect(url_for('operations.operations'))