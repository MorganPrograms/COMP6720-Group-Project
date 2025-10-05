import os
from redis import Redis
def get_redis():
    return Redis(host=os.getenv('REDIS_HOST','localhost'), port=int(os.getenv('REDIS_PORT',6379)), decode_responses=True)
