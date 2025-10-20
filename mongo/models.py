from mongoengine import Document, StringField, ListField, DateTimeField, FloatField
class Ebook(Document):
    meta = {'collection':'ebooks'}
    title = StringField(required=True)
    author = StringField(required=True)
    description = StringField()
    genres = ListField(StringField())
    published_date = DateTimeField()
    access_tier = StringField(choices=['free','premium'], default='free')
    file_ref = StringField()
    average_rating = FloatField(default=0.0)
