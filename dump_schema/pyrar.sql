-- MariaDB dump 10.19  Distrib 10.6.8-MariaDB, for Linux (x86_64)
--
-- Host: 192.168.1.240    Database: pyrar
-- ------------------------------------------------------
-- Server version	10.6.8-MariaDB-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `actions`
--

DROP TABLE IF EXISTS `actions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `actions` (
  `action_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `domain_id` int(10) unsigned NOT NULL DEFAULT 0,
  `execute_dt` datetime NOT NULL,
  `action` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`action_id`),
  KEY `by_dom` (`domain_id`),
  KEY `by_date` (`execute_dt`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `backend`
--

DROP TABLE IF EXISTS `backend`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `backend` (
  `backend_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `domain_id` int(10) unsigned NOT NULL DEFAULT 0,
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
  `job_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `failures` int(11) NOT NULL DEFAULT 0,
  `num_years` int(11) DEFAULT NULL,
  `authcode` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `execute_dt` datetime NOT NULL,
  `created_dt` datetime NOT NULL,
  `amended_dt` datetime NOT NULL,
  PRIMARY KEY (`backend_id`),
  KEY `by_user` (`execute_dt`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `class_by_name`
--

DROP TABLE IF EXISTS `class_by_name`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `class_by_name` (
  `class_by_name_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(260) COLLATE utf8mb4_unicode_ci NOT NULL,
  `class` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `amended_dt` datetime NOT NULL,
  PRIMARY KEY (`class_by_name_id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `class_by_regexp`
--

DROP TABLE IF EXISTS `class_by_regexp`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `class_by_regexp` (
  `name_regexp_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name_regexp` varchar(260) COLLATE utf8mb4_unicode_ci NOT NULL,
  `zone` varchar(260) COLLATE utf8mb4_unicode_ci NOT NULL,
  `class` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `amended_dt` datetime NOT NULL,
  PRIMARY KEY (`name_regexp_id`),
  UNIQUE KEY `zone` (`zone`,`name_regexp`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `contacts`
--

DROP TABLE IF EXISTS `contacts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `contacts` (
  `contact_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
  `name` varchar(250) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `org_name` varchar(250) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `street` varchar(350) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `state` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `postcode` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `country` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fax` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_dt` datetime NOT NULL,
  `amended_dt` datetime NOT NULL,
  PRIMARY KEY (`contact_id`),
  KEY `by_owner` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `deleted_domains`
--

DROP TABLE IF EXISTS `deleted_domains`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `deleted_domains` (
  `domain_id` int(10) unsigned NOT NULL DEFAULT 0,
  `name` varchar(260) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
  `status_id` int(10) unsigned NOT NULL DEFAULT 0,
  `auto_renew` tinyint(1) DEFAULT NULL,
  `ns` varchar(3500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(3500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `client_locks` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_dt` datetime DEFAULT NULL,
  `amended_dt` datetime DEFAULT NULL,
  `expiry_dt` datetime NOT NULL,
  `deleted_dt` datetime NOT NULL,
  UNIQUE KEY `domain_id` (`domain_id`),
  KEY `by_name` (`name`),
  KEY `by_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `domains`
--

DROP TABLE IF EXISTS `domains`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `domains` (
  `domain_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(260) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
  `contact_id` int(10) unsigned DEFAULT NULL,
  `status_id` int(11) NOT NULL DEFAULT 0,
  `auto_renew` tinyint(1) DEFAULT NULL,
  `ns` varchar(3500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(3500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `client_locks` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `for_sale_msg` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `for_sale_amount` decimal(10,0) DEFAULT NULL,
  `authcode` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reg_create_dt` datetime DEFAULT NULL,
  `created_dt` datetime NOT NULL,
  `amended_dt` datetime NOT NULL,
  `expiry_dt` datetime NOT NULL,
  PRIMARY KEY (`name`),
  UNIQUE KEY `by_id` (`domain_id`),
  KEY `by_expdt` (`expiry_dt`),
  KEY `by_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `events`
--

DROP TABLE IF EXISTS `events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `events` (
  `event_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `event_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `domain_id` int(10) unsigned DEFAULT NULL,
  `user_id` int(10) unsigned DEFAULT NULL,
  `when_dt` datetime DEFAULT NULL,
  `who_did_it` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `from_where` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `program` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `function` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `line_num` int(11) DEFAULT NULL,
  `notes` varchar(1024) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `filename` varchar(1024) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`event_id`),
  KEY `by_domain` (`domain_id`),
  KEY `by_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `messages`
--

DROP TABLE IF EXISTS `messages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `messages` (
  `message_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
  `message` varchar(3000) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_read` tinyint(1) NOT NULL,
  `created_dt` datetime NOT NULL,
  PRIMARY KEY (`user_id`,`message_id`),
  UNIQUE KEY `by_id` (`message_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `orders`
--

DROP TABLE IF EXISTS `orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `orders` (
  `order_item_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
  `price_charged` decimal(10,0) NOT NULL DEFAULT 0,
  `currency_charged` char(3) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `price_paid` decimal(10,0) NOT NULL DEFAULT 0,
  `currency_paid` char(3) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `domain_id` int(10) unsigned NOT NULL DEFAULT 0,
  `order_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'none',
  `num_years` int(11) NOT NULL,
  `authcode` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_dt` datetime NOT NULL,
  `amended_dt` datetime NOT NULL,
  PRIMARY KEY (`order_item_id`),
  KEY `by_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `payments`
--

DROP TABLE IF EXISTS `payments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `payments` (
  `payment_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
  `provider` varchar(1000) COLLATE utf8mb4_unicode_ci NOT NULL,
  `token` varchar(3000) COLLATE utf8mb4_unicode_ci NOT NULL,
  `token_type` tinyint(4) NOT NULL,
  `created_dt` datetime NOT NULL,
  `amended_dt` datetime NOT NULL,
  `user_can_delete` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`payment_id`),
  UNIQUE KEY `by_token` (`token`,`provider`) USING HASH
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sales`
--

DROP TABLE IF EXISTS `sales`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sales` (
  `sales_item_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `transaction_id` int(10) unsigned NOT NULL,
  `user_id` int(10) unsigned DEFAULT NULL,
  `price_charged` decimal(10,0) NOT NULL DEFAULT 0,
  `currency_charged` char(3) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `price_paid` decimal(10,0) NOT NULL DEFAULT 0,
  `currency_paid` char(3) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `domain_name` varchar(260) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `domain_id` int(10) unsigned NOT NULL,
  `zone_name` varchar(260) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `registry` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sales_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `num_years` int(11) NOT NULL,
  `is_refund_of` int(10) unsigned DEFAULT NULL,
  `been_refunded` tinyint(1) DEFAULT NULL,
  `created_dt` datetime DEFAULT NULL,
  `amended_dt` datetime DEFAULT NULL,
  PRIMARY KEY (`sales_item_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `session_keys`
--

DROP TABLE IF EXISTS `session_keys`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `session_keys` (
  `session_key` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
  `amended_dt` datetime DEFAULT NULL,
  `created_dt` datetime DEFAULT NULL,
  PRIMARY KEY (`session_key`),
  UNIQUE KEY `by_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sysadmins`
--

DROP TABLE IF EXISTS `sysadmins`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sysadmins` (
  `login` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `htpasswd` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_dt` datetime DEFAULT NULL,
  `amended_dt` datetime DEFAULT NULL,
  PRIMARY KEY (`login`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `transactions`
--

DROP TABLE IF EXISTS `transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `transactions` (
  `transaction_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
  `acct_sequence_id` int(10) unsigned NOT NULL DEFAULT 0,
  `amount` decimal(10,0) NOT NULL DEFAULT 0,
  `pre_balance` decimal(10,0) NOT NULL DEFAULT 0,
  `post_balance` decimal(10,0) NOT NULL DEFAULT 0,
  `sales_item_id` int(10) unsigned DEFAULT NULL,
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_dt` datetime DEFAULT NULL,
  PRIMARY KEY (`user_id`,`acct_sequence_id`),
  UNIQUE KEY `by_id` (`transaction_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `user_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `email` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_id` int(10) unsigned DEFAULT NULL,
  `email_verified` tinyint(1) NOT NULL DEFAULT 0,
  `default_auto_renew` tinyint(1) NOT NULL DEFAULT 1,
  `account_closed` tinyint(1) NOT NULL DEFAULT 0,
  `email_opt_out` varchar(2000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `two_fa` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password_reset` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `discount_percent` int(11) DEFAULT NULL,
  `acct_sequence_id` int(10) unsigned NOT NULL DEFAULT 1,
  `acct_on_hold` tinyint(1) NOT NULL DEFAULT 0,
  `acct_current_balance` decimal(10,0) NOT NULL DEFAULT 0,
  `acct_previous_balance` decimal(10,0) NOT NULL DEFAULT 0,
  `acct_overdraw_limit` decimal(10,0) NOT NULL DEFAULT 0,
  `acct_warn_low_balance` decimal(10,0) NOT NULL DEFAULT 0,
  `acct_next_warning_dt` datetime DEFAULT NULL,
  `last_login_dt` datetime DEFAULT NULL,
  `created_dt` datetime NOT NULL,
  `amended_dt` datetime NOT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `by_login` (`email`),
  UNIQUE KEY `by_pass_rst` (`password_reset`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `zones`
--

DROP TABLE IF EXISTS `zones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `zones` (
  `zone` varchar(260) COLLATE utf8mb4_unicode_ci NOT NULL,
  `registry` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `price_info` varchar(3500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `enabled` tinyint(1) NOT NULL DEFAULT 1,
  `allow_sales` tinyint(1) NOT NULL DEFAULT 1,
  `renew_limit` int(11) DEFAULT NULL,
  `owner_user_id` int(10) unsigned DEFAULT NULL,
  `owner_royalty_rate` int(11) DEFAULT NULL,
  `created_dt` datetime DEFAULT NULL,
  `amended_dt` datetime DEFAULT NULL,
  PRIMARY KEY (`zone`),
  KEY `by_last_change` (`amended_dt`,`enabled`,`allow_sales`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

