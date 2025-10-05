import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    MYSQL_URI = f"mysql+pymysql://{os.getenv('MYSQL_USER','root')}:{os.getenv('MYSQL_PASS','')}@{os.getenv('MYSQL_HOST','localhost')}:{os.getenv('MYSQL_PORT',3306)}/{os.getenv('MYSQL_DB','ebook_service')}"
    MONGO_URI = os.getenv('MONGO_URI','mongodb://localhost:27017/ebooks')
    NEO4J_URI = os.getenv('NEO4J_URI','bolt://localhost:7687')
    NEO4J_USER = os.getenv('NEO4J_USER','neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD','admin')
    REDIS_HOST = os.getenv('REDIS_HOST','localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT',6379))
    JWT_SECRET = os.getenv('JWT_SECRET','supersecret-demo')
    PORT = int(os.getenv('PORT',5000))
