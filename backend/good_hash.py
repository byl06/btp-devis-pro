import bcrypt

password = "000000"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(f"NOUVEAU HASH pour '000000': {hashed.decode()}")