DROP DATABASE IF EXISTS ebook_service;
CREATE DATABASE ebook_service;
USE ebook_service;


DROP TABLE IF EXISTS user_book;
DROP TABLE IF EXISTS rating;
DROP TABLE IF EXISTS payment;
DROP TABLE IF EXISTS subscription;
DROP TABLE IF EXISTS tier;
DROP TABLE IF EXISTS users;


CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email)
) AUTO_INCREMENT = 1001;


CREATE TABLE IF NOT EXISTS tier (
    tier_id INT PRIMARY KEY AUTO_INCREMENT,
    tier_name ENUM('Free', 'Premium') UNIQUE NOT NULL,
    base_price DECIMAL(10,2) NOT NULL
) AUTO_INCREMENT = 1;


CREATE TABLE IF NOT EXISTS subscription (
    subscription_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    tier_id INT NOT NULL,
    start_date DATE NOT NULL,
    expiry_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (tier_id) REFERENCES tier(tier_id),
    INDEX idx_user_id (user_id),
    INDEX idx_tier_id (tier_id),
    INDEX idx_is_active (is_active),
    INDEX idx_user_active (user_id, is_active)
) AUTO_INCREMENT = 5001;


CREATE TABLE IF NOT EXISTS payment (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    subscription_id INT NOT NULL,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    card_last4 VARCHAR(4),
    FOREIGN KEY (subscription_id) REFERENCES subscription(subscription_id),
    INDEX idx_subscription_id (subscription_id),
    INDEX idx_payment_date (payment_date)
) AUTO_INCREMENT = 10001;


CREATE TABLE IF NOT EXISTS rating (
    rating_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    book_mongo_id VARCHAR(50) NOT NULL,
    star INT NOT NULL CHECK (star >= 1 AND star <= 5),
    rating_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_book_mongo_id (book_mongo_id),
    INDEX idx_book_star (book_mongo_id, star)
) AUTO_INCREMENT = 2001;


CREATE TABLE IF NOT EXISTS user_book (
    user_id INT NOT NULL,
    book_mongo_id VARCHAR(50) NOT NULL,
    last_accessed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    reading_status ENUM('Reading', 'Completed') DEFAULT 'Reading',
    PRIMARY KEY (user_id, book_mongo_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_reading_status (reading_status),
    INDEX idx_last_accessed (last_accessed_date),
    INDEX idx_book_status (book_mongo_id, reading_status)
);