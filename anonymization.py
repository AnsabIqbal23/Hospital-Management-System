import random
from cryptography.fernet import Fernet

# Optional encryption key
encryption_key = Fernet.generate_key()
cipher = Fernet(encryption_key)

def mask_name(name):
    return "ANON_" + str(random.randint(1000, 9999))

def mask_contact(contact):
    return "XXX-XXX-" + contact[-4:]

def encrypt_value(value):
    return cipher.encrypt(value.encode()).decode()

def decrypt_value(value):
    return cipher.decrypt(value.encode()).decode()