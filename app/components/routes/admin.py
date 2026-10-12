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

admin_bp = Blueprint("admin",__name__,url_prefix="/admin")


#############
### Admin ###
#############
### Members ###
@admin_bp.route('/members', methods=['GET'])
@login_required
def members():
    Members=tMembers.query.all()
    return render_template('admin/members/members_list.html', Members=Members)

@admin_bp.route('/member/add', methods=['GET','POST'])
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
        return redirect(url_for('admin.members'))
    return render_template('admin/members/add_or_update_member.html', form=form, Member=None, active=True, is_employed=False)

@admin_bp.route('/member/edit/<id_member>', methods=['GET','POST'])
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
        return redirect(url_for('admin.members'))
    return render_template('admin/members/add_or_update_member.html', form=form, Member=member, active=member.active, is_employed=member.is_employed)

### Categories ###
# List categories
@admin_bp.route('/categories')
@login_required
def categories():
    Depenses=dictCategories.query.filter_by(id_type_operation = dictOperationTypes.query.filter_by(label='Dépense').one().id_type_operation).all()
    Recettes=dictCategories.query.filter_by(id_type_operation = dictOperationTypes.query.filter_by(label='Recette').one().id_type_operation).all()
    Benevolats=dictCategories.query.filter_by(id_type_operation = dictOperationTypes.query.filter_by(label='Valorisation du bénévolat').one().id_type_operation).all()
    Transferts=dictCategories.query.filter_by(id_type_operation = dictOperationTypes.query.filter_by(label='Transaction interne').one().id_type_operation).all()
    return render_template('admin/categories/categories_list.html', Depenses = Depenses, Recettes=Recettes, Benevolats=Benevolats,Transferts=Transferts)

### Activities
@admin_bp.route('/activities', methods=['GET'])
@login_required
def activities():
    return render_template('admin/activities/activities_list.html', Activities = tActivities.query.all() )


# Features
@admin_bp.route('/features')
@login_required
def features():
    return render_template('admin/features.html')

# Tutorial
@admin_bp.route('/tutorial')
@login_required
def tutorial():
    return render_template('admin/tutorial.html')


