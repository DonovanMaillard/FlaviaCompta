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

utils_bp = Blueprint("utils",__name__)

#############
### UTILS ###
#############

# Init login manager
login_manager = LoginManager()

#def allowed_file(filename):
#    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def abs_decimal(value):
    #Renvoie None si la valeur est vide, lève ValueError si elle est invalide.""", 
    # mais traite les virgules et l'abs() pour gérer les négatifs selon les besoins du logiciel
    if value is None or str(value).strip() == '':
        return None
    try:
        amount = abs(Decimal(str(value).strip().replace(' ', '').replace(',', '.')))
    except InvalidOperation:
        raise ValueError(f"Montant invalide : {value!r}")
    return abs(amount).quantize(Decimal('0.01'))


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



def format_datetime(value):
    format="dd-MM-y"
    return babel.dates.format_datetime(value, format)