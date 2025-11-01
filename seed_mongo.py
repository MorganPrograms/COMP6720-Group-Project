from mongo.models import Ebook
from mongoengine import connect
from datetime import datetime
import os
connect(host=os.getenv('MONGO_URI','mongodb://localhost:27017/ebook_catalog'))
Ebook.drop_collection()
Ebook(title='Flask Fundamentals', author='John Doe', description='Learn Flask', genres=['programming'], published_date=datetime(2023,1,1), access_tier='free', file_ref='file://books/flask.epub').save()
Ebook(title='Advanced Graph Theory', author='Jane Smith', description='Graphs', genres=['math'], published_date=datetime(2024,5,10), access_tier='premium', file_ref='file://books/graphs.epub').save()
print('Mongo seeded')
