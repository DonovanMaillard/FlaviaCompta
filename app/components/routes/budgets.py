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

budgets_bp = Blueprint("budgets",__name__,url_prefix="/budgets")

############################################
## MISE EN PLACE D'UNE API ET DES EXPORTS ##
##            EN DEVELOPPEMENT            ##
############################################


#####################
## Search function ##
#####################

# Filtering function for API & Downloads
def search_budgets():
    query = vBudgets.query

    budget_name = request.args.get("budget_name", type=str)
    reference = request.args.get("reference", type=str)
    montant = request.args.get("montant", type=str)
    id_funder = request.args.get("id_funder", "")
    closed = request.args.get("closed") is not None
    id_type_budget = request.args.get("id_type_budget", "")
    id_activity = request.args.get("id_activity", "")
    demarre_apres = request.args.get("demarre_apres", type=str)
    demarre_avant = request.args.get("demarre_avant", type=str)
    cloture_apres = request.args.get("cloture_apres", type=str)
    cloture_avant = request.args.get("cloture_avant", type=str)

    if budget_name:
        like_pattern = f"%{budget_name}%"
        query = query.filter(vBudgets.name.ilike(like_pattern))

    if reference:
        like_pattern = f"%{reference}%"
        query = query.filter(vBudgets.reference.ilike(like_pattern))

    if montant:
        try:
            montant = request.args.get("montant", "")
            montant_decimal = abs_decimal(montant)
            query = query.filter(func.abs(vBudgets.budget_amount) == montant_decimal)
        except ValueError:
            pass  # montant mal formé, on ignore le filtre

    if id_funder :
        query = query.filter(vBudgets.id_funder == id_funder)       

    if closed :
        query = query.filter(vBudgets.date_closing.is_not(None))

    if id_type_budget:
        query = query.filter(vBudgets.id_type_budget == id_type_budget)

    if id_activity:
        query = query.filter(vBudgets.id_activity == id_activity)
    
    if demarre_apres:
        try:
            demarre_apres_parsed = datetime.strptime(demarre_apres, "%Y-%m-%d").date()
            query = query.filter(vBudgets.date_start >= demarre_apres_parsed)
        except ValueError:
            pass

    if demarre_avant:
        try:
            demarre_avant_parsed = datetime.strptime(demarre_avant, "%Y-%m-%d").date()
            query = query.filter(vBudgets.date_start <= demarre_avant_parsed)
        except ValueError:
            pass

    if cloture_apres:
        try:
            cloture_apres_parsed = datetime.strptime(cloture_apres, "%Y-%m-%d").date()
            query = query.filter(vBudgets.date_closing >= cloture_apres_parsed)
        except ValueError:
            pass

    if cloture_avant:
        try:
            cloture_avant_parsed = datetime.strptime(cloture_avant, "%Y-%m-%d").date()
            query = query.filter(vBudgets.date_closing >= cloture_avant_parsed)
        except ValueError:
            pass

    return query


@budgets_bp.route("/api", methods=["GET"])
@login_required
def get_api_budgets():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))

    query = search_budgets()

    total = query.count()

    results = query.order_by(vBudgets.date_closing.isnot(None),vBudgets.name).offset((page - 1) * per_page).limit(per_page).all()

    data = [{
        "id_budget" : b.id_budget,
        "budget_name" : b.name,
        "reference" : b.reference,
        "id_funder" : b.id_funder,
        "funder" : b.funder,
        "type_budget" : b.type_budget,
        "id_activity" : b.id_activity,
        "activity" : b.activity,
        "date_start" : b.date_start,
        "date_max_expenditure" : b.date_max_expenditure,
        "date_return" : b.date_return,
        "budget_amount" : b.budget_amount,
        "payroll_limit" : b.payroll_limit,
        "indirect_charges" : b.indirect_charges,
        "indirect_charges_amount" : b.indirect_charges_amount,
        "comment" : b.comment,
        "received_amount" : b.received_amount,
        "percent_received" : b.percent_received,
        "spent_amount" : b.spent_amount,
        "percent_spent" : b.percent_spent,
        "committed_amount" : b.committed_amount,
        "percent_committed" : b.percent_committed,
        "last_operation" : b.last_operation,
        "last_action_date" : b.last_action_date,
        "nb_operations" : b.nb_operations,
        "draft_allocations" : b.draft_allocations,
        "profit_bonus" : b.profit_bonus,
        "date_closing" : b.date_closing,
        "meta_create_date" : b.meta_create_date,
        "meta_update_date" : b.meta_update_date
    } for b in results]

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "data": data
    })

# Download
@budgets_bp.route("/download", methods=["GET"])
@login_required
def download_budgets():

    query = search_budgets()

    results = (
        query
        .order_by(vBudgets.meta_create_date.desc())
        .all()
    )

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "id_budget",
        "nom_budget",
        "reference",
        "financeur",
        "type_budget",
        "activite",
        "date_demarrage",
        "date_max_depenses",
        "date_rendus",
        "montant_budget",
        "masse_salariale_max",
        "pourcent_charges_indirectes",
        "montant_max_charges_indirectes",
        "commentaire",
        "montant_percu",
        "pourcentage_percu",
        "montant_depense",
        "pourcentage_depense",
        "montant_engage",
        "pourcentage_engage",
        "derniere_operation",
        "nb_operations",
        "repartition_salaries",
        "eligible_interessement",
        "cloture_le",
        "saisi_le",
        "modifie_le"
    ])

    for b in results:
        writer.writerow([
            b.id_budget,
            b.name,
            b.reference,
            b.funder,
            b.type_budget,
            b.activity,
            b.date_start,
            b.date_max_expenditure,
            b.date_return,
            b.budget_amount,
            b.payroll_limit,
            b.indirect_charges,
            b.indirect_charges_amount,
            b.comment,
            b.received_amount,
            str(b.percent_received)+"%",
            b.spent_amount,
            str(b.percent_spent)+"%",
            b.committed_amount,
            str(b.percent_committed)+"%",
            b.last_operation,
            b.nb_operations,
            b.draft_allocations,
            b.profit_bonus,
            b.date_closing,
            b.meta_create_date,
            b.meta_update_date
        ])

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=budgets.csv"
        }
    )


###############
### BUDGETS ###
###############
#List budgets
@budgets_bp.route('/')
@login_required
def budgets():
    Budgets = vBudgets.query.all()
    Activities=vSyntheseActivities.query.all()
    funders=db.session.query(tFunders.id_funder, tFunders.name).order_by(tFunders.name).all()
    types=db.session.query(dictBudgetTypes.id_type_budget, dictBudgetTypes.label).order_by(dictBudgetTypes.label).all()
    activities=db.session.query(tActivities.id_activity, tActivities.label).order_by(tActivities.label).all()
    return render_template('budgets/budgets_list.html', Budgets=Budgets, Activities=Activities, funders=funders, types=types, activities=activities)

# Details budget & list actions
@budgets_bp.route('/detail/<id_budget>', methods=['GET', 'POST'])
@login_required
def detailBudget(id_budget):
    Budget = db.session.get(vBudgets, id_budget) 
    Actions = vActions.query.filter_by(id_budget=id_budget)
    Operations = vOperations.query.filter(vOperations.id_budget==id_budget, vOperations.type_operation != 'Engagement').order_by(vOperations.effective_date.desc()).all()
    Commitments = vOperations.query.filter(vOperations.id_budget==id_budget, vOperations.type_operation == 'Engagement').order_by(vOperations.effective_date.desc()).all()
    Payrolls = vSynthesePayrollBudget.query.filter_by(id_budget=id_budget).all()
    #Allocation d'un budget à chaque salarié
    members = tMembers.query.filter_by(is_employed=True).order_by(tMembers.member_name).all()   # liste d'objets
    names = {m.id_member: m.member_name for m in members}
    form = formAllocatedBudget(request.form if request.method == 'POST' else None)
    # GET : une ligne par membre, pré-remplie depuis le jsonb
    if request.method == 'GET':
        existants = Budget.draft_allocations or {}
        for m in members:
            value = existants.get(str(m.id_member))
            form.rows.append_entry({
                "id_member": m.id_member,
                "allocated_amount": Decimal(value) if value is not None else None,
            })
    # POST : annule et remplace le contenu du jsonb
    if request.method == 'POST' and form.validate():
        tBudget = db.session.get(tBudgets, id_budget)
        tBudget.draft_allocations = {
            str(l["id_member"]): str(l["allocated_amount"])
            for l in form.rows.data
            if l["allocated_amount"] is not None and l["id_member"] in names
        }
        db.session.commit()
        flash("Attributions enregistrées.")
        return redirect(url_for('budgets.detailBudget', id_budget=id_budget))
    return render_template('budgets/details_budget.html', Budget = Budget, Actions = Actions, Operations = Operations, Commitments = Commitments, Payrolls = Payrolls, form=form, names=names)

# Add budget
@budgets_bp.route('/add', methods=['GET', 'POST'])
@login_required
def addBudget():
    form = formBudget(request.form)
    # Funders
    activeFunders = tFunders.query.filter_by(active=True)
    form.id_funder.choices = [('', '-- Sélectionnez un financeur --')] + [(activeFunder.id_funder, activeFunder.name) for activeFunder in activeFunders]
    # Type budget
    TypesBudget = dictBudgetTypes.query.all()
    form.id_type_budget.choices = [('', '-- Sélectionnez un type --')] + [(TypeBudget.id_type_budget, TypeBudget.label) for TypeBudget in TypesBudget]
    # Activité
    Activities = tActivities.query.filter_by(active=True).all()
    form.id_activity.choices = [('', '-- Sélectionnez une activité --')] + [(Activity.id_activity, Activity.label) for Activity in Activities]
    # Date de démarrage par défaut :
    form.date_start.data = date.today()
    if request.method == 'POST' and form.validate() :
        Budget = tBudgets(
            request.form['name'], 
            request.form['reference'], 
            getChoiceOrNone(request.form['id_funder']), 
            getChoiceOrNone(request.form['id_type_budget']), 
            getChoiceOrNone(request.form['id_activity']),
            request.form['date_max_expenditure'], 
            request.form['date_return'], 
            abs_decimal(request.form.get('budget_amount')), 
            abs_decimal(request.form['payroll_limit']), 
            abs_decimal(request.form['indirect_charges']), 
            request.form['comment'], 
            bool(request.form.get('profit_bonus')),
            request.form['date_start'],
        )
        db.session.add(Budget)
        db.session.commit()
        return redirect('/budgets')
    return render_template('budgets/add_or_update_budget.html', form=form, activeFunders=activeFunders, TypesBudget=TypesBudget, Budget=None, active=None, profit_bonus=False)

# Edit budget
@budgets_bp.route('/edit/<int:id_budget>', methods=['GET', 'POST'])
@login_required
def updateBudget(id_budget):
    Budget = db.get_or_404(tBudgets, id_budget)
    form = formBudget(request.form if request.method == 'POST' else None, obj=Budget)
    # Funders
    activeFunders = tFunders.query.filter_by(active=True)
    form.id_funder.choices = [('', '-- Sélectionnez un financeur --')] + [(f.id_funder, f.name) for f in activeFunders]
    # Type budget
    TypesBudget = dictBudgetTypes.query.all()
    form.id_type_budget.choices = [('', '-- Sélectionnez un type --')] + [(t.id_type_budget, t.label) for t in TypesBudget]
    # Activité
    Activities = tActivities.query.filter_by(active=True).all()
    form.id_activity.choices = [('', '-- Sélectionnez une activité --')] + [(a.id_activity, a.label) for a in Activities]
    if request.method == 'POST' and form.validate():
        form.populate_obj(Budget)
        # Forcer le None dans les selects ignorés
        Budget.id_funder = getChoiceOrNone(form.id_funder.data)
        Budget.id_type_budget = getChoiceOrNone(form.id_type_budget.data)
        Budget.id_activity = getChoiceOrNone(form.id_activity.data)
        db.session.commit()
        return redirect('/budgets')

    return render_template('budgets/add_or_update_budget.html', form=form, Budget=Budget)


# Close budget
@budgets_bp.route('/close/<id_budget>', methods=['GET', 'POST'])
@login_required
def closeBudget(id_budget):
    # Add closing date to budget
    Budget=db.session.get(tBudgets, id_budget)
    Budget.date_closing = func.current_date()
    if Budget.profit_bonus :
        # Add profit_bonus to tProfitBonus
        profit_bonus_ratio=Decimal(str(app.config['PROFIT_BONUS_RATIO']))
        print(profit_bonus_ratio)
        for id_member, allocated_amount in (Budget.draft_allocations or {}).items():
                allocated_amount = Decimal(allocated_amount)
                if allocated_amount == 0:
                    continue
                db.session.add(tProfitBonus(
                    id_budget=id_budget,
                    id_member=int(id_member),
                    allocated_amount=allocated_amount,
                    profit_percent=profit_bonus_ratio,
                    profit_bonus_amount =allocated_amount*profit_bonus_ratio
                ))
        db.session.commit()
    return redirect('/budgets')


# Delete budget
@budgets_bp.route('/delete/<id_budget>', methods=['GET', 'POST'])
@login_required
def deleteBudget(id_budget):
    current_budget=db.session.get(tBudgets, id_budget) #tBudgets.query.get(id_budget)
    db.session.delete(current_budget)
    db.session.commit()
    return redirect('/budgets')
