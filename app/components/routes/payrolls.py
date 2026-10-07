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

payrolls_bp = Blueprint("payrolls",__name__,url_prefix="/payrolls")


##################
### WORK VALUE ###
##################

## Payrolls
@payrolls_bp.route('/')
@login_required
def payrolls():
    members=tMembers.query.filter_by(is_employed=True)
    id_member = request.args.get('id_member', None, type=int)
    if id_member:
        payrolls = vPayrolls.query.filter_by(id_member=id_member).order_by(vPayrolls.date_min_period.desc()).all()
    else :
        payrolls = vPayrolls.query.order_by(vPayrolls.date_min_period.desc()).all()
    return render_template('payrolls/payrolls_list.html', payrolls=payrolls, members=members)


@payrolls_bp.route('/add', methods=['GET', 'POST'])
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
@payrolls_bp.route('/edit/<id_payroll>', methods=['GET', 'POST'])
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
@payrolls_bp.route('/detail/<id_payroll>', methods=['GET', 'POST'])
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
@payrolls_bp.route('/delete/<id_payroll>', methods=['GET', 'POST'])
@login_required
def deletePayroll(id_payroll):
    current_payroll=db.session.get(tPayrolls, id_payroll) #tPayrolls.query.get(id_payroll)
    db.session.delete(current_payroll)
    db.session.commit()
    return redirect(url_for('payrolls'))


######################
# Cor payroll budget #
######################
@payrolls_bp.route('/<id_payroll>/cor_budget/add', methods=['GET', 'POST'])
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


@payrolls_bp.route('/<id_payroll>/cor_budget/<id_payroll_budget>/edit', methods=['GET', 'POST'])
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
@payrolls_bp.route('/<id_payroll>/cor_budget/<id_payroll_budget>/delete', methods=['GET', 'POST'])
@login_required
def deleteCorPayrollBudget(id_payroll, id_payroll_budget):
    cor = db.session.get(corPayrollBudget, id_payroll_budget) #corPayrollBudget.query.get(id_payroll_budget)
    db.session.delete(cor)
    db.session.commit()
    return redirect(url_for('detailPayroll', id_payroll=id_payroll))

