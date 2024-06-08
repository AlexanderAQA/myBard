#!/bin/bash

# Update package lists
sudo apt-get update

# Install ntp
sudo apt-get install -y ntp

# Clean up Docker
sudo docker-compose down -v
sudo docker system prune -a -f

# Install PostgreSQL if it is not already installed
sudo apt-get install -y postgresql postgresql-contrib libpq-dev

# Ensure PostgreSQL is stopped to free up port 5432
sudo systemctl stop postgresql

# Install Docker and Docker Compose
sudo apt-get install -y docker.io
sudo apt-get install -y docker-compose

# Create Docker network
sudo docker network create mybard_network

# Create Docker Compose file
cat <<EOF > docker-compose.yml
version: '3.1'

services:
  web:
    build: .
    container_name: mybard_web
    restart: always
    ports:
      - "5000:5000"
    networks:
      - mybard_network
    depends_on:
      - db

  db:
    image: postgres
    container_name: mybard_postgres
    restart: always
    environment:
      POSTGRES_DB: myappdb
      POSTGRES_USER: myappuser
      POSTGRES_PASSWORD: mypassword
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - mybard_network

volumes:
  postgres_data:

networks:
  mybard_network:
EOF

# Start Docker Compose
sudo docker-compose build
sudo docker-compose up -d

# Wait for PostgreSQL to initialize
sleep 10

# Modify PostgreSQL configuration to allow remote connections inside the container
sudo docker exec -it mybard_postgres bash -c "echo \"listen_addresses = '*'\" >> /var/lib/postgresql/data/postgresql.conf"
sudo docker exec -it mybard_postgres bash -c "echo \"host    all             all             0.0.0.0/0               md5\" >> /var/lib/postgresql/data/pg_hba.conf"

# Restart PostgreSQL to apply changes
sudo docker exec -it mybard_postgres bash -c "pg_ctl -D /var/lib/postgresql/data restart"

# Wait for PostgreSQL to restart
sleep 10

# Create tables in the PostgreSQL database with logging
sudo docker exec -i mybard_postgres psql -U myappuser -d myappdb <<EOF | tee create_tables.log
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS songs (
  id SERIAL PRIMARY KEY,
  filename VARCHAR(255) NOT NULL,
  tags TEXT,
  longitude_minutes INT,
  artist VARCHAR(100)
);

-- Insert a basic user with hashed password                 # \2b\$12\$J2615NCQwz9DzBX3jE68F.WaWlFBFmZJYeyH7I6efrX8.fVgQNd62
INSERT INTO users (username, password_hash) VALUES ('admin', '\2b\$12\$J2615NCQwz9DzBX3jE68F.WaWlFBFmZJYeyH7I6efrX8.fVgQNd62');
EOF

# Confirm table creation
sudo docker exec -i mybard_postgres psql -U myappuser -d myappdb -c "\dt"

echo "Setup complete. You can now start your Flask application with Docker."
