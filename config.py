import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    MYSQL_HOST = os.getenv('MYSQL_HOST','localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT',3306))
    MYSQL_USER = os.getenv('MYSQL_USER','root')
    MYSQL_PASS = os.getenv('MYSQL_PASS','')
    MYSQL_DB = os.getenv('MYSQL_DB','ebook_service')
    MYSQL_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    MONGO_URI = os.getenv('MONGO_URI','mongodb://localhost:27017/ebooks')
    NEO4J_URI = os.getenv('NEO4J_URI','bolt://localhost:7687')
    NEO4J_USER = os.getenv('NEO4J_USER','neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD','test')
    REDIS_HOST = os.getenv('REDIS_HOST','127.0.0.1')
    REDIS_PORT = int(os.getenv('REDIS_PORT',6379))
    JWT_SECRET = os.getenv('JWT_SECRET','change_this_secret')
    FLASK_PORT = int(os.getenv('FLASK_PORT',5000))
