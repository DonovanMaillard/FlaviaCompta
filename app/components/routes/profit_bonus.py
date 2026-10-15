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

profit_bonus_bp = Blueprint("profit_bonus",__name__,url_prefix="/profit_bonus")


# Filtering function for API & Downloads
def search_profit_bonus():
    query = vProfitBonus.query

    id_member = request.args.get("id_member", "")
    id_budget = request.args.get("id_budget", "")
    date_apres = request.args.get("date_apres", type=str)
    date_avant = request.args.get("date_avant", type=str)

    if id_member:
        query = query.filter(
            vProfitBonus.id_member == id_member
        )

    if id_budget:
        query = query.filter(
            vProfitBonus.id_budget == id_budget
        )

    if date_apres:
        try:
            date_apres_parsed = datetime.strptime(
                date_apres, "%Y-%m-%d"
            ).date()

            query = query.filter(
                vProfitBonus.meta_create_date >= date_apres_parsed
            )
        except ValueError:
            pass

    if date_avant:
        try:
            date_avant_parsed = datetime.strptime(date_avant, "%Y-%m-%d").date()

            query = query.filter(vProfitBonus.meta_create_date < date_avant_parsed + timedelta(days=1))
        except ValueError:
            pass

    return query

# API
@profit_bonus_bp.route("/api", methods=["GET"])
@login_required
def get_api_profit_bonus():

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))

    query = search_profit_bonus()

    total = query.count()

    total_bonus = query.with_entities(
        func.coalesce(
            func.sum(vProfitBonus.profit_bonus_amount),
            0
        )
    ).scalar()

    results = (
        query
        .order_by(vProfitBonus.meta_create_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    data = [{
        "id_pb": pb.id_pb,
        "id_budget": pb.id_budget,
        "budget_name": pb.name,
        "budget_amount": pb.budget_amount,
        "budget_received_amount": pb.received_amount,
        "budget_date_closing": pb.date_closing,
        "id_member": pb.id_member,
        "member_name": pb.member_name,
        "allocated_amount": pb.allocated_amount,
        "profit_percent": pb.profit_percent,
        "profit_bonus_amount": pb.profit_bonus_amount,
        "meta_create_date": pb.meta_create_date,
        "meta_update_date": pb.meta_update_date
    } for pb in results]

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "data": data,
        "total_profit_bonus": str(total_bonus)
    })

# Download
@profit_bonus_bp.route("/download", methods=["GET"])
@login_required
def download_profit_bonus():

    query = search_profit_bonus()

    results = (
        query
        .order_by(vProfitBonus.meta_create_date.desc())
        .all()
    )

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Budget",
        "Montant previsionnel budget",
        "Recettes reelles",
        "Date de clôture",
        "Salarié",
        "Montant attribué",
        "Pourcentage",
        "Prime acquise",
        "Date calcul intéressement",
        "Date modification"
    ])

    for pb in results:
        writer.writerow([
            pb.id_pb,
            pb.name,
            pb.budget_amount,
            pb.received_amount,
            pb.date_closing,
            pb.member_name,
            pb.allocated_amount,
            pb.profit_percent,
            pb.profit_bonus_amount,
            pb.meta_create_date,
            pb.meta_update_date
        ])

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=profit_bonus.csv"
        }
    )

# Page
## Intéressement
@profit_bonus_bp.route('/', methods=['GET'])
@login_required
def profitBonus():
    budgets = db.session.query(vProfitBonus.id_budget, vProfitBonus.name).distinct().order_by(vProfitBonus.name).all()
    members = db.session.query(tMembers.id_member, tMembers.member_name).filter_by(is_employed=True).distinct().order_by(tMembers.member_name).all()
    #All profit bonus
    return render_template('profit_bonus/list.html', budgets=budgets, members=members)
