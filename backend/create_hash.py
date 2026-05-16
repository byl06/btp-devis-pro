import bcrypt

password = "000000"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(f"Mot de passe: {password}")
print(f"Hash: {hashed.decode()}")