import os
from redis import Redis

def get_redis():
    return Redis(host=os.getenv('REDIS_HOST','127.0.0.1'), port=int(os.getenv('REDIS_PORT',6379)), decode_responses=True)
