from flask import Flask, render_template, redirect, url_for
from flask_login import login_required
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
    admin_bp,
    vat_bp
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
app.register_blueprint(vat_bp)

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

