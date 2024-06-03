# Face class
class Face:
    def __init__(self, name, event_id, images, id):
        # Main initialiser
        self.name = name
        self.event_id = event_id
        self.images = images
        self.id = id

    @classmethod
    def make_from_dict(cls, d):
        # Initialise User object from a dictionary
        return cls(
            d["name"],
            d["event_id"],
            d["images"],
            d["id"],
        )

    def dict(self):
        # Return dictionary representation of the object
        return {
            "id": self.id,
            "name": self.name,
            "images": self.images,
            "event_id": self.event_id,
        }

    def get_eid(self):
        return self.id
