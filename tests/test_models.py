import unittest
from app import create_app
from extensions import db
from models.university import University
from models.faculty import Faculty
from models.department import Department
import os

class TestModels(unittest.TestCase):
    
    def setUp(self):
        os.environ['TESTING'] = 'True'
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_create_university(self):
        uni = University(name="Test Univ", name_ar="جامعة تجريبية", code="TST", is_active=True)
        db.session.add(uni)
        db.session.commit()
        
        saved_uni = University.query.filter_by(name="Test Univ").first()
        self.assertIsNotNone(saved_uni)
        self.assertEqual(saved_uni.name_ar, "جامعة تجريبية")
        self.assertTrue(saved_uni.is_active)

    def test_create_faculty_and_department(self):
        uni = University(name="Tech Univ", name_ar="جامعة التقنية", code="TECH")
        db.session.add(uni)
        db.session.commit()

        fac = Faculty(name="CS", name_ar="علوم الحاسوب", code="CS", university_id=uni.id)
        db.session.add(fac)
        db.session.commit()

        dept = Department(name="AI", name_ar="الذكاء الاصطناعي", code="AI", faculty_id=fac.id, university_id=uni.id)
        db.session.add(dept)
        db.session.commit()

        saved_dept = Department.query.filter_by(name="AI").first()
        self.assertIsNotNone(saved_dept)
        self.assertEqual(saved_dept.faculty.name, "CS")
        self.assertEqual(saved_dept.university.name, "Tech Univ")

if __name__ == '__main__':
    unittest.main()
