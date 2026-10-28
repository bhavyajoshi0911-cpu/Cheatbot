from werkzeug.security import generate_password_hash, check_password_hash


class User:
    def __init__(self, id=None, username='', email='', password_hash=''):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password)

    @staticmethod
    def verify_password(stored_hash, password):
        return check_password_hash(stored_hash, password)
