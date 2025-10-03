from mongoengine import Document, StringField, ListField, DateTimeField, IntField

class Ebook(Document):
    title = StringField(required=True)
    author = StringField(required=True)
    description = StringField()
    tags = ListField(StringField())
    published_date = DateTimeField()
    popularity = IntField(default=0)
    tier = StringField(choices=["regular", "premium"])
