import os
import json
from app import logger
from authlib.jose import JsonWebKey, jwt

JWT_KEY_PATH = "/data/signing_key.json"

def load_key():
    try:
        with open(JWT_KEY_PATH, "r", encoding="utf-8") as key_file:
            key_data = json.load(key_file)
        return JsonWebKey.import_key(key_data)
    except FileNotFoundError:
        signing_key = JsonWebKey.generate_key("RSA", 2048, is_private=True)
        key_data = signing_key.as_dict(is_private=True)
        os.makedirs(os.path.dirname(JWT_KEY_PATH), exist_ok=True)
        temp_path = f"{JWT_KEY_PATH}.tmp"
        with open(temp_path, "w", encoding="utf-8") as key_file:
            json.dump(key_data, key_file)
        os.replace(temp_path, JWT_KEY_PATH)
        logger.info("[jwt] generated new general signing key")
        return signing_key

jwt_key = load_key()

def encode_jwt(payload):
    return jwt.encode({"alg": "RS256"}, payload, jwt_key).decode("utf-8")

def decode_jwt(payload):
    return jwt.decode(payload, jwt_key)