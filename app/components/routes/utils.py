from flask import Blueprint, request, current_app, flash, redirect
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_login import LoginManager
from decimal import Decimal, InvalidOperation
import uuid
import babel.dates

utils_bp = Blueprint("utils",__name__)

#############
### UTILS ###
#############

# Init login manager
login_manager = LoginManager()

# Extensions utilisées si ALLOWED_EXTENSIONS n'est pas défini dans config.py
DEFAULT_ALLOWED_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg', 'webp', 'zip', 'rar']

def allowed_extensions():
    return [ext.lower().lstrip('.') for ext in current_app.config.get('ALLOWED_EXTENSIONS', DEFAULT_ALLOWED_EXTENSIONS)]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions()

# Refuse toute requête contenant un fichier non autorisé, avant que la route ne l'enregistre
@utils_bp.before_app_request
def check_uploaded_files():
    for _, f in request.files.items(multi=True):
        if f.filename and not allowed_file(f.filename):
            flash(f"Le fichier « {f.filename} » n'est pas autorisé. Extensions acceptées : {', '.join(allowed_extensions())}.", category="danger")
            return redirect(request.url)

# Liste des extensions pour l'attribut accept des champs fichier : {{ form.uploaded_file(accept=upload_accept) }}
@utils_bp.app_context_processor
def inject_upload_accept():
    return {'upload_accept': ','.join('.' + ext for ext in allowed_extensions())}

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
    if f and allowed_file(f.filename):
        filename = uuid.uuid4().hex[:10]+'_'+secure_filename(f.filename)
        f.save(current_app.config['BASE_DIR']+'app/static/uploads/'+filename)
        file_url='uploads/'+filename
    else :
        file_url=None
    return file_url


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def format_datetime(value):
    format="dd-MM-y"
    return babel.dates.format_datetime(value, format, locale=current_app.config.get('LOCALE', 'fr_FR'))
