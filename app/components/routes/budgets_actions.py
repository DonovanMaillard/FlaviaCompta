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

budgets_actions_bp = Blueprint("budgets_actions",__name__,url_prefix="/budgets")


######################
### Budget actions ###
######################
# Add action
@budgets_actions_bp.route('/detail/<id_budget>/addAction', methods=['GET', 'POST'])
@login_required
def addAction(id_budget):
    form = formAction(request.form)
    Budget = tBudgets.query.get(id_budget)
    # Type Action
    TypesAction = dictBudgetActionTypes.query.all()
    form.id_budget_action_types.choices = [(TypeAction.id_budget_action_types, TypeAction.label) for TypeAction in TypesAction]
    # Charger le formulaire
    if request.method == 'POST' and form.validate() :
        Action = corActionBudget(
            getChoiceOrNone(request.form['id_budget_action_types']),
            Budget.id_budget, 
            request.form['date_action'],
            request.form['description_action'],
            getFileUrl('uploaded_file')
            )
        db.session.add(Action)
        db.session.commit()
        return redirect(url_for('detailBudget', id_budget=id_budget))
    return render_template('budgets/add_or_update_action.html', form=form, Budget=Budget, Action=None)


# Edit action
@budgets_actions_bp.route('/budgets/detail/<id_budget>/editAction/<id_action_budget>', methods=['GET', 'POST'])
@login_required
def updateAction(id_budget, id_action_budget):
    # pre-loaded form
    Action = db.session.get(corActionBudget, id_action_budget) #corActionBudget.query.get(id_action_budget)
    form = formAction(request.form, obj=Action)
    # Type Action
    TypesAction = dictBudgetActionTypes.query.all()
    form.id_budget_action_types.choices = [(TypeAction.id_budget_action_types, TypeAction.label) for TypeAction in TypesAction]
    form.id_budget_action_types.default = Action.id_budget_action_types
    # Budget
    Budget = db.session.get(tBudgets, id_budget) #tBudgets.query.get(id_budget)
    # Charger le formulaire
    if request.method == 'POST' and form.validate():
        Action.id_budget_action_types = getChoiceOrNone(request.form['id_budget_action_types'])
        Action.id_budget = Budget.id_budget
        Action.date_action = request.form['date_action']
        Action.description_action = request.form['description_action']
        if not request.form.get('keep_file'):
            Action.uploaded_file = getFileUrl('uploaded_file')
        db.session.commit()
        return redirect(url_for('detailBudget', id_budget=id_budget))
    return render_template('budgets/add_or_update_action.html', form=form, Budget=Budget, Action=Action)


# Delete action
@budgets_actions_bp.route('/budgets/detail/<id_budget>/deleteAction/<id_action_budget>', methods=['GET', 'POST'])
@login_required
def deleteAction(id_budget, id_action_budget):
    current_action=db.session.get(corActionBudget, id_action_budget) #corActionBudget.query.get(id_action_budget)
    db.session.delete(current_action)
    db.session.commit()
    return redirect(url_for('detailBudget', id_budget=id_budget))
