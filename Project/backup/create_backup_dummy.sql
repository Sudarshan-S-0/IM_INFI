-- SQL script to create a dummy dataset with 5 entries per table

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

-- Insert dummy data into users (5 rows)
INSERT INTO users (name, email) VALUES ('User One', 'one@dummy.com');
INSERT INTO users (name, email) VALUES ('User Two', 'two@dummy.com');
INSERT INTO users (name, email) VALUES ('User Three', 'three@dummy.com');
INSERT INTO users (name, email) VALUES ('User Four', 'four@dummy.com');
INSERT INTO users (name, email) VALUES ('User Five', 'five@dummy.com');

-- Insert dummy data into products (5 rows)
INSERT INTO products (product_name, price) VALUES ('Product A', 10.99);
INSERT INTO products (product_name, price) VALUES ('Product B', 20.49);
INSERT INTO products (product_name, price) VALUES ('Product C', 5.99);
INSERT INTO products (product_name, price) VALUES ('Product D', 99.00);
INSERT INTO products (product_name, price) VALUES ('Product E', 150.50);

-- Insert dummy data into orders (5 rows)
INSERT INTO orders (user_id, amount) VALUES (1, 10.99);
INSERT INTO orders (user_id, amount) VALUES (2, 40.98);
INSERT INTO orders (user_id, amount) VALUES (3, 5.99);
INSERT INTO orders (user_id, amount) VALUES (4, 99.00);
INSERT INTO orders (user_id, amount) VALUES (5, 301.00);
