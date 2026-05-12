import unittest
import json
from app import create_app
from extensions import db
from models.user import User
from models.university import University
from werkzeug.security import generate_password_hash
import os

class TestAuth(unittest.TestCase):
    
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

    def test_login_failed(self):
        response = self.client.post('/auth/login', json={
            'email': 'wrong@example.com',
            'password': 'wrongpassword'
        })
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 401)
        self.assertIn('error', data)

    def test_login_success(self):
        uni = University(name="Test Univ", name_ar="جامعة", code="TST", is_active=True)
        db.session.add(uni)
        db.session.commit()

        user = User(
            username='teststudent',
            email='student@univ.edu.dz',
            password_hash=generate_password_hash('password123'),
            role='student',
            university_id=uni.id,
            is_verified=True
        )
        db.session.add(user)
        db.session.commit()

        response = self.client.post('/auth/login', json={
            'email': 'student@univ.edu.dz',
            'password': 'password123'
        })
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', data)

if __name__ == '__main__':
    unittest.main()
