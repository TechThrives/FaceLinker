from datetime import datetime
import uuid


# User class
class User:
    def __init__(self, first_name, last_name, email, id="", events=[]):
        # Main initialiser
        self.id = uuid.uuid4().hex if not id else id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.events = events

    @classmethod
    def make_from_dict(cls, d):
        # Initialise User object from a dictionary
        return cls(
            d["first_name"],
            d["last_name"],
            d["email"],
            d["id"],
        )

    def dict(self):
        # Return dictionary representation of the object
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "events": self.events,
        }

    def display_name(self):
        # Return concatenation of name components
        return self.first_name + " " + self.last_name

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id


# Anonymous user class
class Anonymous:
    @property
    def is_authenticated(self):
        return False

    @property
    def is_active(self):
        return False

    @property
    def is_anonymous(self):
        return True

    def get_id(self):
        return None
