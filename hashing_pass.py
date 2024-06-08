from werkzeug.security import generate_password_hash

# Create a new user with hashed password
hashed_password = generate_password_hash('test1', method='pbkdf2:sha256')
print(hashed_password)
