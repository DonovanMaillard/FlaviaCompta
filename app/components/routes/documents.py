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

documents_bp = Blueprint("documents",__name__,url_prefix="/documents")


### Documents ###
# List documents
@documents_bp.route('/', methods=['GET'])
@login_required
def documents():
    documents = vDocuments.query.order_by(vDocuments.meta_create_date.desc()).all()
    return render_template('admin/documents/documents_list.html', documents = documents )

# Add document
@documents_bp.route('/add', methods=['GET', 'POST'])
@login_required
def addDocument():
    form = formDocument(request.form)
    #Types de documents
    DocumentTypes = dictDocumentType.query.all()
    form.id_type.choices = [('', '-- Sélectionnez un type de document --')] + [(DocumentType.id_type, DocumentType.label) for DocumentType in DocumentTypes]
    # Formulaire
    if request.method == 'POST' and form.validate():
        document = tDocuments(
            request.form['title'], 
            request.form['description'], 
            request.form['id_type'],
            getFileUrl('uploaded_file'),
            current_user.id_user,
        )
        db.session.add(document)
        db.session.commit()
        return redirect('/documents')
    return render_template('admin/documents/add_or_update_document.html', form=form, document=None)


# Edit document
@documents_bp.route('/edit/<id_document>', methods=['GET', 'POST'])
@login_required
def updateDocument(id_document):
  # pre-loaded form
    Document = db.session.get(tDocuments, id_document) #tDocuments.query.get(id_document)
    form = formDocument(request.form, obj=Document)
    # types
    DocumentTypes = dictDocumentType.query.all()
    form.id_type.choices = [('', '-- Sélectionnez un type de document --')] + [(DocumentType.id_type, DocumentType.label) for DocumentType in DocumentTypes]
    form.id_type.default=Document.id_type
    #Formulaire
    if request.method == 'POST' and form.validate():
        Document.title = request.form['title'], 
        Document.description = request.form['description'],
        if not request.form.get('keep_file'):
            Document.uploaded_file = getFileUrl('uploaded_file')
        db.session.commit()
        return redirect(url_for('documents'))
    return render_template('admin/documents/add_or_update_document.html', form=form, document=Document)

# Delete document
@documents_bp.route('/delete/<id_document>', methods=['GET', 'POST'])
@login_required
def deleteDocument(id_document):
    current_document= db.session.get(tDocuments, id_document) #tDocuments.query.get(id_document)
    db.session.delete(current_document)
    db.session.commit()
    return redirect('/documents')