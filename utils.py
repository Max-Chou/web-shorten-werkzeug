# utils - helper funcitons
from urllib.parse import urlparse

BASE62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def is_valid_url(url):
    """Check if the scheme is HTTP or HTTPS"""
    parts = urlparse(url)
    return parts.scheme in {'http', 'https'}

def base62_encoder(number):
    if number == 0:
        return "0"
    base62 = ''
    while number:
        rem = number % 62
        number //= 62
        base62 = BASE62[rem] + base62

    return base62 
