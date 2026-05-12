from flask import Blueprint, render_template, jsonify
from extensions import db
from models.university import University
from models.faculty import Faculty
from models.department import Department

webapp_bp = Blueprint('webapp', __name__)

@webapp_bp.route('/')
def index():
    return render_template('webapp.html')

@webapp_bp.route('/api/universities')
def get_universities():
    unis = University.query.filter_by(is_active=True).order_by(University.name).all()
    return jsonify([{'id': u.id, 'name': u.name, 'city': u.city} for u in unis])

@webapp_bp.route('/api/faculties/<int:uni_id>')
def get_faculties(uni_id):
    facs = Faculty.query.filter_by(university_id=uni_id, is_active=True).order_by(Faculty.name).all()
    return jsonify([{'id': f.id, 'name': f.name} for f in facs])

@webapp_bp.route('/api/departments/<int:fac_id>')
def get_departments(fac_id):
    depts = Department.query.filter_by(faculty_id=fac_id, is_active=True).order_by(Department.name).all()
    return jsonify([{'id': d.id, 'name': d.name} for d in depts])
