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
from .utils import login_manager

auth_bp = Blueprint("auth",__name__)

##################
# Authentication #
##################

@login_manager.user_loader
def load_user(id_user):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return db.session.get(tUsers, id_user)

# Login
@auth_bp.route('/login', methods=['GET','POST'])
def login():
    form=formLogin(request.form)
    if request.method == 'POST' and form.validate():
        login = request.form.get('login')
        password = request.form.get('password')
        user = tUsers.query.filter_by(login=login).first()
        # check if the user actually exists
        # take the user-supplied password, hash it, and compare it to the hashed password in the database
        if not user or not check_password_hash(user.password, password) or not user.is_active:
            flash('Mot de passe incorrect ou compte inactif. Si le problème persiste, veuillez contacter l\'administrateur')
            return redirect(url_for('login')) # if the user doesn't exist or password is wrong, reload the page
        # if the above check passes, then we know the user has the right credentials
        login_user(user, remember=True, duration=timedelta(minutes=1))
        track_login=loginHistory(
            user.id_user,
            datetime.now()
            )
        db.session.add(track_login)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('login.html', form=form)

#SignUp
@auth_bp.route('/signup', methods=['GET','POST'])
def signup():
    form=formSignUp(request.form)
    if request.method == 'POST' and form.validate():
        if request.form.get('password') != request.form.get('password_confirm'):
            flash('Vous avez renseigné deux mots de passe différents, votre demande est invalide.', category="danger")
        if tUsers.query.filter_by(login=request.form['login']).first() is not None :
            flash('Un compte existe déjà avec cet identifiant.', category="danger")
        if request.form.get('password')==request.form.get('password_confirm') and not tUsers.query.filter_by(login=request.form['login']).first() :
            User = tUsers(
            request.form['name'],
            request.form['firstname'],
            request.form['email'],
            request.form['login'],
            generate_password_hash(request.form['password']),
            bool(False)
            )
            db.session.add(User)
            db.session.commit()
            flash('Votre demande d\'accès a bien été enregistrée. Un administrateur doit désormais activer votre compte.', category="success")
            return redirect(url_for('signup'))
    return render_template('signup.html', form=form)

# LogOut
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))