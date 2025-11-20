-- phpMyAdmin SQL Dump
-- version 5.2.0
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Nov 14, 2025 at 04:08 PM
-- Server version: 10.4.27-MariaDB
-- PHP Version: 8.2.0

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `ebook_service`
--

-- --------------------------------------------------------

--
-- Table structure for table `books`
--

CREATE TABLE `books` (
  `id` int(11) NOT NULL,
  `mongo_id` varchar(50) DEFAULT NULL,
  `title` varchar(200) DEFAULT NULL,
  `access_tier` enum('Free','Premium') DEFAULT 'Free',
  `genre` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `books`
--

INSERT INTO `books` (`id`, `mongo_id`, `title`, `access_tier`, `genre`) VALUES
(1, 'mongo_001', 'Free Book 1', 'Free', 'Fiction'),
(2, 'mongo_002', 'Premium Book 1', 'Premium', 'Science Fiction'),
(3, 'mongo_003', 'The Ocean’s Secret', 'Free', 'Adventure'),
(4, 'mongo_004', 'Quantum Hearts', 'Premium', 'Romance'),
(5, 'mongo_005', 'The Hidden Algorithm', 'Premium', 'Science Fiction'),
(6, 'mongo_006', 'Whispers of the Wind', 'Free', 'Drama'),
(7, 'mongo_007', 'Digital Dreams', 'Premium', 'Technology'),
(8, 'mongo_008', 'Shadows of Tomorrow', 'Premium', 'Thriller'),
(9, 'mongo_009', 'Mystic Tides', 'Free', 'Fantasy'),
(10, 'mongo_010', 'Parallel Minds', 'Premium', 'Psychological Fiction'),
(11, 'mongo_011', 'A Taste of Starlight', 'Premium', 'Science Fiction'),
(12, 'mongo_012', 'Beneath the Willow', 'Free', 'Romance'),
(13, 'mongo_013', 'Code of the Ancients', 'Premium', 'Historical Fiction'),
(14, 'mongo_014', 'The Last Signal', 'Premium', 'Mystery'),
(15, 'mongo_015', 'Harvest Moon Rising', 'Free', 'Fantasy'),
(16, 'mongo_016', 'Through Rusted Gates', 'Free', 'Post-Apocalyptic'),
(17, 'mongo_017', 'Neon City Chronicles', 'Premium', 'Cyberpunk'),
(18, 'mongo_018', 'Fragments of Eden', 'Free', 'Drama'),
(19, 'mongo_019', 'The Infinite Library', 'Premium', 'Fantasy'),
(20, 'mongo_020', 'Echoes in the Void', 'Premium', 'Science Fiction'),
(21, 'mongo_021', 'Canvas of the Soul', 'Free', 'Art'),
(22, 'mongo_022', 'The Copper Revolution', 'Premium', 'Historical Fiction'),
(23, 'mongo_023', 'Silent Coordinates', 'Premium', 'Mystery'),
(24, 'mongo_024', 'Fires of the Forgotten', 'Free', 'Fantasy'),
(25, 'mongo_025', 'The Logic of Emotion', 'Premium', 'Philosophy'),
(26, 'mongo_026', 'Under Crimson Skies', 'Free', 'Adventure'),
(27, 'mongo_027', 'Viridian Code', 'Premium', 'Technology'),
(28, 'mongo_028', 'Chronicles of Ashvale', 'Free', 'Fantasy'),
(29, 'mongo_029', 'The Last Horizon', 'Premium', 'Science Fiction'),
(30, 'mongo_030', 'Dreams of the Mechanist', 'Premium', 'Steampunk');

-- --------------------------------------------------------

--
-- Table structure for table `payments`
--

CREATE TABLE `payments` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `transaction_date` datetime DEFAULT current_timestamp(),
  `status` enum('Success','Failed') DEFAULT 'Success'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `payments`
--

INSERT INTO `payments` (`id`, `user_id`, `amount`, `transaction_date`, `status`) VALUES
(1, 2, '9.99', '2025-10-20 05:05:28', 'Success'),
(2, 4, NULL, '2025-11-09 15:28:12', 'Success');

-- --------------------------------------------------------

--
-- Table structure for table `ratings`
--

CREATE TABLE `ratings` (
  `user_id` int(11) NOT NULL,
  `book_id` varchar(100) NOT NULL,
  `rating` float NOT NULL,
  `date` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `ratings`
--

INSERT INTO `ratings` (`user_id`, `book_id`, `rating`, `date`) VALUES
(4, 'mongo_011', 5, '2025-11-09 15:53:58');

-- --------------------------------------------------------

--
-- Table structure for table `reading_progress`
--

CREATE TABLE `reading_progress` (
  `user_id` int(11) NOT NULL,
  `book_id` varchar(100) NOT NULL,
  `last_page` int(11) DEFAULT 1,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `reading_progress`
--

INSERT INTO `reading_progress` (`user_id`, `book_id`, `last_page`, `updated_at`) VALUES
(4, 'mongo_011', 2, '2025-11-09 15:53:51');

-- --------------------------------------------------------

--
-- Table structure for table `subscriptions`
--

CREATE TABLE `subscriptions` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `tier` enum('Free','Premium') NOT NULL,
  `start_date` date NOT NULL,
  `expiry_date` date DEFAULT NULL,
  `status` enum('Active','Expired','Cancelled') DEFAULT 'Active'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `subscriptions`
--

INSERT INTO `subscriptions` (`id`, `user_id`, `tier`, `start_date`, `expiry_date`, `status`) VALUES
(1, 1, 'Free', '2025-10-20', NULL, 'Active'),
(2, 2, 'Premium', '2025-10-20', '2025-11-19', 'Active');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `subscription_tier` enum('Free','Premium') DEFAULT 'Free'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `username`, `email`, `password_hash`, `subscription_tier`) VALUES
(1, 'alice', 'alice@example.com', 'hashed_pw_123', 'Free'),
(2, 'bob', 'bob@example.com', 'hashed_pw_456', 'Premium'),
(3, 'testman', 'Chucktesta@gmail.com', 'scrypt:32768:8:1$sfZBKEur5VGnhjpQ$87022bccab795ec06682badefc03ea570466e1af0c9d1c1deca6ea0a9f35b0daedbac2c6576940f99b070b96b713c1a39ddd06d8d5afc9b5fb5b83b29187ddce', 'Free'),
(4, 'Testingman', 'testingman@test.com', 'scrypt:32768:8:1$UVKRpBBdEVusDSy1$6cc343c1cf3e22edc7ff879aa8e3c2f53c1c76c5ecbb43930a05eb53b3817591cde8e8819f13348449e8d1726ff2f569f534dea1024fc77612429bc88630d4a3', 'Premium'),
(5, 'testman@test.com', 'testmanemail@testing.com', 'scrypt:32768:8:1$RkUcGpWGVVK5EggX$c640435577c2ba8c2613c5cabe132d313734272295d77ed67565a2fa6eaf861f27118209413d71f8965e0414892bab050ea17cf33ead8c70336659893c88aa4c', 'Premium'),
(6, 'Beta', 'Beta@beta.com', 'scrypt:32768:8:1$Oh4Crs92AALlFq7y$de2c434fa19e3774d345c439412eddbada7ab122ec2c355ac2f46335f037aebee64b34e9c638bbce9bb75a6af63a42c3dbc4eafa0e8510120ab2159ef5d63743', 'Premium');

-- --------------------------------------------------------

--
-- Table structure for table `user_books`
--

CREATE TABLE `user_books` (
  `user_id` int(11) NOT NULL,
  `book_id` varchar(100) NOT NULL,
  `date_subscribed` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `user_books`
--

INSERT INTO `user_books` (`user_id`, `book_id`, `date_subscribed`) VALUES
(4, 'mongo_011', '2025-11-09 15:53:43'),
(4, 'mongo_012', '2025-11-09 15:59:03'),
(4, 'mongo_013', '2025-11-09 16:18:50'),
(4, 'mongo_021', '2025-11-09 16:09:18');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `books`
--
ALTER TABLE `books`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `payments`
--
ALTER TABLE `payments`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `ratings`
--
ALTER TABLE `ratings`
  ADD PRIMARY KEY (`user_id`,`book_id`);

--
-- Indexes for table `reading_progress`
--
ALTER TABLE `reading_progress`
  ADD PRIMARY KEY (`user_id`,`book_id`);

--
-- Indexes for table `subscriptions`
--
ALTER TABLE `subscriptions`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indexes for table `user_books`
--
ALTER TABLE `user_books`
  ADD PRIMARY KEY (`user_id`,`book_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `books`
--
ALTER TABLE `books`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=31;

--
-- AUTO_INCREMENT for table `payments`
--
ALTER TABLE `payments`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `subscriptions`
--
ALTER TABLE `subscriptions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `payments`
--
ALTER TABLE `payments`
  ADD CONSTRAINT `payments_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`);

--
-- Constraints for table `subscriptions`
--
ALTER TABLE `subscriptions`
  ADD CONSTRAINT `subscriptions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
