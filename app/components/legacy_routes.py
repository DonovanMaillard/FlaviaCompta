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
from .routes.utils import *

# Import Blueprints 
from .routes import (
    auth_bp,
    profit_bonus_bp,
    budgets_bp,
    budgets_actions_bp,
    accounts_bp,
    funders_bp,
    documents_bp,
    commitments_bp,
    transfers_bp,
    results_bp,
    payrolls_bp,
    operations_bp,
    utils_bp,
    admin_bp
    )

app = Flask(__name__, template_folder='../templates', static_folder='../static')

app.register_blueprint(auth_bp)
app.register_blueprint(profit_bonus_bp)
app.register_blueprint(budgets_bp)
app.register_blueprint(budgets_actions_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(funders_bp)
app.register_blueprint(documents_bp)
app.register_blueprint(commitments_bp)
app.register_blueprint(transfers_bp)
app.register_blueprint(results_bp)
app.register_blueprint(payrolls_bp)
app.register_blueprint(operations_bp)
app.register_blueprint(utils_bp)
app.register_blueprint(admin_bp)

# Load configuration
app.config.from_pyfile('../../config/config.py')
# To get one variable, tape app.config['MY_VARIABLE']

############
### MAIN ###
############

@app.route('/')
@login_required
def index():
    return render_template('home.html')

@app.errorhandler(401)
def unauthorized(error):
    return redirect(url_for('auth.login'))

