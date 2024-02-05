from datetime import datetime
import uuid


# User class
class Event:
    def __init__(self, title, location, start, end, desc, id=""):
        # Main initialiser
        self.title = title
        self.location = location
        self.start = start
        self.end = end
        self.desc = desc
        self.id = uuid.uuid4().hex if not id else id

    @classmethod
    def make_from_dict(cls, d):
        # Initialise User object from a dictionary
        return cls(
            d["title"],
            d["location"],
            d["start"],
            d["end"],
            d["desc"],
            d["id"],
        )

    def dict(self):
        # Return dictionary representation of the object
        return {
            "id": self.id,
            "title": self.title,
            "location": self.location,
            "start": self.start,
            "end": self.end,
            "desc": self.desc,
        }

    def get_eid(self):
        return self.id
