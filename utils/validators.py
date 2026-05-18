import re

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password):
    if len(password) < 8:
        return False, 'Password must be at least 8 characters long'
    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter (A-Z)'
    if not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter (a-z)'
    if not re.search(r'[0-9]', password):
        return False, 'Password must contain at least one number (0-9)'
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~]', password):
        return False, 'Password must contain at least one special character (!@#$%^&*...)'
    return True, ''
