from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user

bp = Blueprint('auth', __name__)

