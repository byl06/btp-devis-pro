import bcrypt

# Le mot de passe que tu veux tester
password = "123456"

# Générer un nouveau hash
salt = bcrypt.gensalt()
new_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
print(f"Nouveau hash pour '{password}': {new_hash.decode()}")

# Tester le hash existant (celui dans la base)
existing_hash = "$2b$12$jJnY5ChS63D7D1K3Z5nUOuI9wEQyIC.B2zH.skSgI6KfFfq9exaYS"
print(f"\nTest du hash existant:")
result = bcrypt.checkpw(password.encode('utf-8'), existing_hash.encode('utf-8'))
print(f"Résultat: {result}")

if not result:
    print("\nLe hash existant ne correspond pas. Utilise ce nouveau hash:")
    print(new_hash.decode())