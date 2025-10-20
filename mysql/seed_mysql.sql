-- ================================================
--  MySQL Schema + Seed Data for Polyglot Demo
-- ================================================

-- Drop and recreate database
DROP DATABASE IF EXISTS ebook_service;
CREATE DATABASE ebook_service;
USE ebook_service;

-- ================================================
-- USERS TABLE
-- ================================================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    subscription_tier ENUM('Free', 'Premium') DEFAULT 'Free'
);

-- ================================================
-- SUBSCRIPTIONS TABLE
-- ================================================
CREATE TABLE subscriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    tier ENUM('Free', 'Premium') NOT NULL,
    start_date DATE NOT NULL,
    expiry_date DATE,
    status ENUM('Active', 'Expired', 'Cancelled') DEFAULT 'Active',
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ================================================
-- PAYMENTS TABLE
-- ================================================
CREATE TABLE payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    amount DECIMAL(10,2),
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('Success', 'Failed') DEFAULT 'Success',
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ================================================
-- BOOKS TABLE (Reference only — main data in MongoDB)
-- ================================================
CREATE TABLE books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mongo_id VARCHAR(50),
    title VARCHAR(200),
    access_tier ENUM('Free', 'Premium') DEFAULT 'Free'
);

-- ================================================
-- RATINGS TABLE
-- ================================================
CREATE TABLE ratings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    book_id INT NOT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    UNIQUE (user_id, book_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (book_id) REFERENCES books(id)
);

-- ================================================
-- USER_BOOK (Reading History)
-- ================================================
CREATE TABLE user_book (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    book_id INT NOT NULL,
    access_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, book_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (book_id) REFERENCES books(id)
);

-- ================================================
-- SEED DATA
-- ================================================

INSERT INTO users (username, email, password_hash, subscription_tier)
VALUES 
('alice', 'alice@example.com', 'hashed_pw_123', 'Free'),
('bob', 'bob@example.com', 'hashed_pw_456', 'Premium');

INSERT INTO subscriptions (user_id, tier, start_date, expiry_date, status)
VALUES
(1, 'Free', CURDATE(), NULL, 'Active'),
(2, 'Premium', CURDATE(), DATE_ADD(CURDATE(), INTERVAL 30 DAY), 'Active');

INSERT INTO books (mongo_id, title, access_tier)
VALUES
('mongo_001', 'Free Book 1', 'Free'),
('mongo_002', 'Premium Book 1', 'Premium');

INSERT INTO ratings (user_id, book_id, rating)
VALUES
(2, 2, 5),
(1, 1, 4);

INSERT INTO user_book (user_id, book_id)
VALUES
(1, 1),
(2, 2);

INSERT INTO payments (user_id, amount, status)
VALUES
(2, 9.99, 'Success');
