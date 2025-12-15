import hashlib

def Hash(menssagem):
    hash_obj = hashlib.sha256(menssagem.encode('utf-8'))
    return hash_obj.hexdigest()

