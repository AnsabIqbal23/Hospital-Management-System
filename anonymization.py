import random
from cryptography.fernet import Fernet
import os

# Persistent encryption key for reversible anonymization
KEY_FILE = "encryption.key"

if os.path.exists(KEY_FILE):
    with open(KEY_FILE, "rb") as key_file:
        encryption_key = key_file.read()
else:
    encryption_key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(encryption_key)

cipher = Fernet(encryption_key)

def mask_name(name):
    return "ANON_" + str(random.randint(1000, 9999))

def mask_contact(contact):
    return "XXX-XXX-" + contact[-4:]

# Mask diagnosis by showing only first 3 characters followed by asterisks
def mask_diagnosis(diagnosis):
    if len(diagnosis) <= 3:
        return "***"
    return diagnosis[:3] + "*" * (len(diagnosis) - 3)

def encrypt_value(value):
    return cipher.encrypt(value.encode()).decode()

def decrypt_value(value):
    return cipher.decrypt(value.encode()).decode()