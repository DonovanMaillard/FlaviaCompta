from flask import Blueprint, request, current_app
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
    return babel.dates.format_datetime(value, format)