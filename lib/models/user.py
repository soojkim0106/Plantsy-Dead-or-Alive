import re
import hashlib
from models.__init__ import CONN, CURSOR
from sqlite3 import IntegrityError
import secrets
class User:

    #! User will require update if scoreboard is True

    all = {}
    def __init__(self, name, password, id=None, password_is_hashed=False):
        self.name = name
        self.password_is_hashed = password_is_hashed
        self.password = password
        self.id = id

    def __repr__(self):
        return f"User {self.id}: {self.name}"

    #! Properties and Attributes
    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, new_password):
        if not self.password_is_hashed:
            if not re.match(r'[A-Za-z0-9@#$%^&+=]{8,}', new_password):
                print('Password must be 8 characters long and contain at least one digit, one uppercase letter, one lowercase letter and one special character')
                return None
            else:
                hashed_password, salt = self.hash_password(new_password)
                self._password = hashed_password
                self._salt = salt
        else:
            self._password = new_password


    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        if not isinstance(new_name, str):
            raise TypeError('Name must be a string')
        elif len(new_name) < 2:
            raise ValueError('Name must be 2 or more characters')
        else:
            self._name = new_name

    #!Association Methods
    def plants(self):
        from models.plant import Plant
        try:
            with CONN:
                CURSOR.execute(
                    """
                        SELECT DISTINCT plant_id FROM actions WHERE user_id =?
                    """,
                    (self.id,)
                )
                rows = CURSOR.fetchall()
                return [Plant.find_by("id", row[0]) for row in rows]
        except Exception as e:
            print("Error fetching user's plants:", e)

    def actions(self):
        from models.action import Action
        try:
            with CONN:
                CURSOR.execute(
                    """
                        SELECT * FROM actions WHERE user_id =?
                    """,
                    (self.id,)
                )
                rows = CURSOR.fetchall()
                return [Action(row[1], row[2], row[3], row[4], row[5], row[6], row[0]) for row in rows]
        except Exception as e:
            print("Error fetching user's action:", e)

    #! ORM class methods
    @classmethod
    def create_table(cls):
        try:
            with CONN:
                CURSOR.execute(
                    """
                        CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY,
                            name TEXT,
                            password TEXT,
                            salt TEXT
                        );
                    """
                )
        except Exception as e:
            return e

    @classmethod
    def drop_table(cls):
        try:
            with CONN:
                CURSOR.execute(
                """
                    DROP TABLE IF EXISTS users;
                """
                )
        except Exception as e:
            print("Error dropping users table:", e)

    @classmethod
    def create(cls, name, password):
        # hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if not re.match(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*]).{8,}$', password):
            return None
        
        try:
            with CONN:
                new_user = cls(name, password)
                new_user.save()
                return new_user
        except Exception as e:
            print("Error creating new user:", e)
            return None

    @classmethod
    def instance_from_db(cls, row):
        try:
            user = cls(row[1], row[2], row[0], password_is_hashed=True)
            user._salt = row[3]  # Assuming salt is the 4th column in your table
            cls.all[user.id] = user
            return user
        except Exception as e:
            print("Error fetching user from database:", e)

    @classmethod
    def find_by_name(cls, name):
        try:
            with CONN:
                CURSOR.execute(
                    """
                        SELECT * FROM users 
                        WHERE name =?;
                    """,
                    (name,),
                )
                row = CURSOR.fetchone()
                return cls.instance_from_db(row) if row else None
        except Exception as e:
            print("Error fetching user by name:", e)
    @classmethod
    def find_by_id(cls, id):
        try:
            with CONN:
                CURSOR.execute(
                    """
                        SELECT * FROM users WHERE id =?;
                    """,
                    (id,),
                )
                row = CURSOR.fetchone()
                return cls.instance_from_db(row) if row else None
        except Exception as e:
            print("Error fetching user by id:", e)

    @classmethod
    def find_by(cls, attr, val):
        try:
            with CONN:
                CURSOR.execute(
                    f"""
                    SELECT * FROM users
                    WHERE {attr} IS ?;
                    """,
                    (val,),
                )
                row = CURSOR.fetchone()
                return cls(row[1], row[0]) if row else None
        except Exception as e:
            print("Error finding users by attribute:", e)

    #! ORM instance method

    def save(self): 
        try:
            with CONN:
                CURSOR.execute(
                    """
                        INSERT INTO users (name, password, salt)
                        VALUES (?, ?, ?);
                    """,
                    (self.name, self._password, self._salt),
                )
                CONN.commit()
                self.id = CURSOR.lastrowid
                type(self).all[self.id] = self
                return self
        except IntegrityError as e:
            print("Name and password must be provided")
        except Exception as e:
            print("We could not save this user:", e)
            return None

    def delete(self):
        try:
            with CONN:
                CURSOR.execute(
                    """
                        DELETE FROM users WHERE id =?;
                    """,
                    (self.id,),
                )
                CONN.commit()
                del type(self).all[self.id]
                self.id = None
        except Exception as e:
            print("We could not delete this user:", e)

    def update_password(self, new_password):
        hashed_password, salt = self.hash_password(new_password)
        try:
            with CONN:
                CURSOR.execute(
                    """
                        UPDATE users
                        SET password = ?, salt = ?
                        WHERE id = ?;
                    """,
                    (hashed_password, salt, self.id),
                )
                CONN.commit()
                self._password = hashed_password
                self._salt = salt
                self.password_is_hashed = True

        except Exception as e:
            print("Error updating password:", e)

    def authenticate(self, password):
        if hasattr(self, "_password") and hasattr(self, "_salt"):
            hashed_password = self.hash_password(password, self._salt)[0]
            return self._password == hashed_password
        else:
            return False

    def hash_password(self, password, salt=None):
        if salt is None:
            salt = secrets.token_hex(16) 
        hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()
        return hashed_password, salt