-- SQL script to create database tables and insert sample data (updated)

-- Drop tables if they exist
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS products;

-- Create users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL
);

-- Create products table
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    price REAL NOT NULL
);

-- Create orders table
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Insert sample data into users
INSERT INTO users (name, email) VALUES ('John', 'john@gmail.com');
INSERT INTO users (name, email) VALUES ('Alice', 'alice@gmail.com');
INSERT INTO users (name, email) VALUES ('Bob', 'bob@gmail.com');
INSERT INTO users (name, email) VALUES ('Charlie', 'charlie@gmail.com');

-- Insert sample data into products
INSERT INTO products (product_name, price) VALUES ('Laptop', 50000.0);
INSERT INTO products (product_name, price) VALUES ('Mouse', 500.0);
INSERT INTO products (product_name, price) VALUES ('Keyboard', 1200.0);
INSERT INTO products (product_name, price) VALUES ('Monitor', 15000.0);

-- Insert sample data into orders
INSERT INTO orders (user_id, amount) VALUES (1, 500.0);
INSERT INTO orders (user_id, amount) VALUES (2, 1200.0);
INSERT INTO orders (user_id, amount) VALUES (3, 800.0);
INSERT INTO orders (user_id, amount) VALUES (4, 15000.0);
