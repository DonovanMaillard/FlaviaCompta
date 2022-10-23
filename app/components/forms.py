from flask_sqlalchemy import SQLAlchemy
from wtforms import Form, validators, BooleanField, StringField, TextAreaField, IntegerField, SelectField, DecimalField, PasswordField
from flask_wtf.file import FileField, FileAllowed
from wtforms.fields import DateField
from werkzeug.utils import secure_filename

from .init_db import db


class formSignUp(Form):
    name = StringField('name', [validators.Length(max=100, message='Ne doit pas dépasser 100 caractères'), validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Votre nom"})
    firstname = StringField('firstname', [validators.Length(max=100, message="Ne doit pas dépasser 100 caractères"), validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Votre prénom"})
    email = StringField('email', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Votre email"})
    login = StringField('login',[validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Créez un identifiant"})
    password = PasswordField('password',[validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Votre mot de passe"})
    password_confirm = PasswordField('password_confirm',[validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Confirmez votre mot de passe"})

class formLogin(Form):
    login = StringField('login',[validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')])
    password = PasswordField('password',[validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')])

class formFunder(Form):
    name = StringField('Nom du financeur', [validators.Length(min=1, max=50, message='Ne doit pas dépasser 50 caractères'), validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Nom de l'organisme financeur"})
    code = StringField('Code du financeur', [validators.Length( max=10, message="Ne doit pas dépasser 10 caractères")], render_kw={"placeholder": "Description"})
    logo_url = StringField('URL du logo du financeur', [validators.url(message='N\'est pas une URL valide'), validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')])
    address = StringField('Adresse postale', [validators.Length(min=1, max=255), validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Adresse postale"})
    city = StringField('Ville', [validators.Length(min=1, max=255), validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Ville"})
    zip_code = IntegerField('Code postal', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')])
    comment = TextAreaField('Remarque', [validators.Length(min=0, max=255)], render_kw={"placeholder": "Remarque"})
    active = BooleanField('Actif')

class formBudget(Form):
    name = StringField('Référence du budget', [validators.Length(min=1, max=50, message='Doit faire entre 1 et 50 caractères'), validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Référence du budget"})
    reference = StringField('Description', [validators.Length(max=50, message='Ne doit pas dépasser 50 caractères')], render_kw={"placeholder": "Référence du budget"})
    id_funder = SelectField('Funder', [validators.NoneOf([''], message='Vous devez sélectionner une valeur')])
    id_type_budget = SelectField('TypeBudget', [validators.NoneOf([''], message='Vous devez sélectionner une valeur')])
    id_activity = SelectField('Activity')
    date_max_expenditure = DateField('Date de fin des dépenses')
    date_return = DateField('Date bilan et rendus')
    budget_amount = DecimalField('Montant du budget', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')],places=2)
    payroll_limit = DecimalField('Masse salariale éligible', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')],places=2)
    indirect_charges = DecimalField('Taux de charges indirectes', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')],places=2)
    comment = TextAreaField('Remarque', [validators.Length(min=0, max=255)], render_kw={"placeholder": "Remarque"})
    allowed_fixed_cost = BooleanField('allowed_fixed_cost')
    active = BooleanField('Actif') 

class formAccount(Form):
    name = StringField('Nom du compte', [validators.Length(min=1, max=50, message='Doit faire entre 1 et 50 caractères'), validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Nom du compte"})
    account_number = IntegerField('Numéro de compte', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "N° de compte"})
    bank = StringField('Nom de la banque', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner'), validators.Length(max=50, message='Ne doit pas dépasser 50 caractères')], render_kw={"placeholder": "Banque"})
    bank_url = StringField('Lien vers le portail de connexion de la banque', [validators.Optional(), validators.url(message='N\'est pas une URL valide'), validators.Length(max=255, message='Doit faire moins de 255 caractères')], render_kw={"placeholder": "Lien vers le portail de connexion de la banque"})
    iban = StringField('IBAN', [validators.Length(max=50, message='Ne doit pas dépasser 50 caractères')], render_kw={"placeholder": "Iban"})
    uploaded_file = FileField('uploaded_file')
    keep_file = BooleanField('keep_file', default=True)

# For actions on a budget
class formAction(Form):
    id_budget_action_types = SelectField('TypeAction', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')])
    date_action = DateField('Date d\'action', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')])
    description_action = TextAreaField()
    uploaded_file = FileField('uploaded_file')
    keep_file = BooleanField('keep_file', default=True)


# For activities 
class formActivity(Form):
    label =StringField('Description', [validators.Length(max=255, message='Ne doit pas dépasser 255 caractères')], render_kw={"placeholder": "Nom de l'activité"})
    description = StringField('Description', render_kw={"placeholder": "Description de l'activité"})
    active = BooleanField('Actif')

class formMovement(Form):
    name = StringField('Libellé de l\'opération', [validators.Length(min=1, max=50, message='Doit faire entre 1 et 50 caractères'), validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Libellé de l'opération"})
    detail_operation = TextAreaField('Détail de l\'opération', render_kw={"placeholder": "Précisions sur l'opération"})
    operation_date = DateField('operation_date', [validators.Optional()])
    effective_date = DateField('effective_date', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')])
    amount = DecimalField('amount', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner'), validators.NoneOf([0, 0.00], message='Le montant ne peut pas être de 0€')], places=2)
    id_payment_method = SelectField('id_payment_method', [validators.Optional()], default=None)
    id_account = SelectField('id_account', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner'),validators.NoneOf([''], message='Vous devez sélectionner une valeur')])
    id_budget = SelectField('id_budget')
    id_category = SelectField('id_category', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner'),validators.NoneOf([''], message='Vous devez sélectionner une valeur')])
    uploaded_file = FileField('uploaded_file')
    keep_file = BooleanField('keep_file', default=True)
    pointed = BooleanField('pointed')

class formCommitment(Form):
    name = StringField('Libellé de l\'opération', [validators.Length(min=1, max=50, message='Doit faire entre 1 et 50 caractères'), validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Libellé de l'opération"})
    detail_operation = TextAreaField('Détail de l\'opération', render_kw={"placeholder": "Précisions sur l'opération"})
    operation_date = DateField('operation_date', [validators.Optional()])
    amount = DecimalField('amount', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner'), validators.NoneOf([0, 0.00], message='Le montant ne peut pas être de 0€')], places=2)
    id_account = SelectField('id_account', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner'),validators.NoneOf([''], message='Vous devez sélectionner une valeur')])
    id_budget = SelectField('id_budget')
    id_category = SelectField('id_category', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner'),validators.NoneOf([''], message='Vous devez sélectionner une valeur')])
    uploaded_file = FileField('uploaded_file')
    keep_file = BooleanField('keep_file', default=True)

class formTransfer(Form):
    name = StringField('Libellé du transfert', [validators.Length(min=1, max=50, message='Doit faire entre 1 et 50 caractères'), validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Libellé du transfert"})
    detail_transfer = TextAreaField('Précisions sur le transfert', render_kw={"placeholder": "Précisions sur le transfert"})
    effective_date = DateField('effective_date', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')])
    amount = DecimalField('amount', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner'), validators.NoneOf([0, 0.00], message='Le montant ne peut pas être de 0€')], places=2)
    id_payment_method = SelectField('id_payment_method')
    from_id_account = SelectField('from_id_account', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner'),validators.NoneOf([''], message='Vous devez sélectionner une valeur')])
    to_id_account = SelectField('to_id_account', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner'),validators.NoneOf([''], message='Vous devez sélectionner une valeur')])

class formPayroll(Form):
    id_member = SelectField('id_member', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner'),validators.NoneOf([''], message='Vous devez sélectionner une valeur')])
    period_month = SelectField('period_month', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')])
    period_year = IntegerField('period_year', [validators.NumberRange(min=1900, max=2100), validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')])
    gross_remuneration = DecimalField('gross_remuneration', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], default=0, places=2)
    gross_premium = DecimalField('gross_premium', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], default=0, places=2)
    employer_charge_amount = DecimalField('employer_charge_amount', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], default=0, places=2)
    real_worked_days = DecimalField('real_worked_days', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], places=2)

# Todo error messages
class formPayrollBudget(Form):
    id_budget = SelectField('id_budget', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner'),validators.NoneOf([''], message='Vous devez sélectionner une valeur')])
    id_member = SelectField('id_member', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner'),validators.NoneOf([''], message='Vous devez sélectionner une valeur')])
    date_min_period = DateField('date_min_period', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')])
    date_max_period = DateField('date_max_period', [validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')])
    nb_days_allocated = DecimalField('nb_days_allocated', places=2)
    fixed_cost = DecimalField('fixed_cost', validators=[validators.Optional()], places=2)

class formMember(Form):
    member_name = StringField('Nom du membre', [validators.Length(min=1, max=50, message='Doit faire entre 1 et 50 caractères'), validators.InputRequired(message='Cette information est obligatoire, veuillez la renseigner')], render_kw={"placeholder": "Nom du membre"})
    member_role = StringField('Rôle au sein de l\'association', [validators.Length(min=0, max=50, message='Ne doit pas dépasser 50 caractères')], render_kw={"placeholder": "Rôle au sein de l\'association"})
    is_employed = BooleanField('is_employed')
    active = BooleanField('active')
    generate_personnal_account = BooleanField('generate_personnal_account')
