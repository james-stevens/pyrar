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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `actions`
--

LOCK TABLES `actions` WRITE;
/*!40000 ALTER TABLE `actions` DISABLE KEYS */;
/*!40000 ALTER TABLE `actions` ENABLE KEYS */;
UNLOCK TABLES;

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
  `job_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'none',
  `failures` int(11) NOT NULL DEFAULT 0,
  `num_years` int(11) DEFAULT NULL,
  `authcode` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `execute_dt` datetime DEFAULT NULL,
  `created_dt` datetime DEFAULT NULL,
  `amended_dt` datetime DEFAULT NULL,
  PRIMARY KEY (`backend_id`),
  KEY `by_user` (`execute_dt`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `backend`
--

LOCK TABLES `backend` WRITE;
/*!40000 ALTER TABLE `backend` DISABLE KEYS */;
/*!40000 ALTER TABLE `backend` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `deleted_domains`
--

LOCK TABLES `deleted_domains` WRITE;
/*!40000 ALTER TABLE `deleted_domains` DISABLE KEYS */;
/*!40000 ALTER TABLE `deleted_domains` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `deleted_users`
--

DROP TABLE IF EXISTS `deleted_users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `deleted_users` (
  `deleted_user_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
  `email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payment_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`payment_data`)),
  `created_dt` datetime DEFAULT NULL,
  `amended_dt` datetime DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  PRIMARY KEY (`deleted_user_id`),
  UNIQUE KEY `by_login` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `deleted_users`
--

LOCK TABLES `deleted_users` WRITE;
/*!40000 ALTER TABLE `deleted_users` DISABLE KEYS */;
/*!40000 ALTER TABLE `deleted_users` ENABLE KEYS */;
UNLOCK TABLES;

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
  `status_id` int(11) NOT NULL DEFAULT 0,
  `auto_renew` tinyint(1) DEFAULT NULL,
  `ns` varchar(3500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ds` varchar(3500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `client_locks` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `for_sale_msg` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `for_sale_amount` decimal(10,0) DEFAULT NULL,
  `authcode` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reg_create_dt` datetime DEFAULT NULL,
  `created_dt` datetime DEFAULT NULL,
  `amended_dt` datetime DEFAULT NULL,
  `expiry_dt` datetime NOT NULL,
  PRIMARY KEY (`name`),
  UNIQUE KEY `by_id` (`domain_id`),
  KEY `by_expdt` (`expiry_dt`),
  KEY `by_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `domains`
--

LOCK TABLES `domains` WRITE;
/*!40000 ALTER TABLE `domains` DISABLE KEYS */;
/*!40000 ALTER TABLE `domains` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `events`
--

DROP TABLE IF EXISTS `events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `events` (
  `event_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `event_type` varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Unknown',
  `domain_id` int(10) unsigned NOT NULL DEFAULT 0,
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
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
-- Dumping data for table `events`
--

LOCK TABLES `events` WRITE;
/*!40000 ALTER TABLE `events` DISABLE KEYS */;
/*!40000 ALTER TABLE `events` ENABLE KEYS */;
UNLOCK TABLES;

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
  `authcode` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_dt` datetime DEFAULT NULL,
  `amended_dt` datetime DEFAULT NULL,
  PRIMARY KEY (`order_item_id`),
  KEY `by_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `orders`
--

LOCK TABLES `orders` WRITE;
/*!40000 ALTER TABLE `orders` DISABLE KEYS */;
/*!40000 ALTER TABLE `orders` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `payments`
--

DROP TABLE IF EXISTS `payments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `payments` (
  `payment_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
  `provider` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `providers_tag` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `single_use` tinyint(1) NOT NULL DEFAULT 0,
  `created_dt` datetime NOT NULL,
  `amended_dt` datetime NOT NULL,
  PRIMARY KEY (`payment_id`),
  UNIQUE KEY `by_type` (`user_id`,`provider`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `payments`
--

LOCK TABLES `payments` WRITE;
/*!40000 ALTER TABLE `payments` DISABLE KEYS */;
/*!40000 ALTER TABLE `payments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sales`
--

DROP TABLE IF EXISTS `sales`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sales` (
  `sales_item_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `transaction_id` int(10) unsigned NOT NULL DEFAULT 0,
  `price_charged` decimal(10,0) NOT NULL DEFAULT 0,
  `currency_charged` char(3) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `price_paid` decimal(10,0) NOT NULL DEFAULT 0,
  `currency_paid` char(3) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `domain_name` varchar(260) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `zone_name` varchar(260) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sales_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'none',
  `num_years` int(11) NOT NULL,
  `created_dt` datetime DEFAULT NULL,
  `amended_dt` datetime DEFAULT NULL,
  PRIMARY KEY (`sales_item_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sales`
--

LOCK TABLES `sales` WRITE;
/*!40000 ALTER TABLE `sales` DISABLE KEYS */;
/*!40000 ALTER TABLE `sales` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `session_keys`
--

LOCK TABLES `session_keys` WRITE;
/*!40000 ALTER TABLE `session_keys` DISABLE KEYS */;
/*!40000 ALTER TABLE `session_keys` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `sysadmins`
--

LOCK TABLES `sysadmins` WRITE;
/*!40000 ALTER TABLE `sysadmins` DISABLE KEYS */;
/*!40000 ALTER TABLE `sysadmins` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `transactions`
--

LOCK TABLES `transactions` WRITE;
/*!40000 ALTER TABLE `transactions` DISABLE KEYS */;
/*!40000 ALTER TABLE `transactions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `user_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email_verified` tinyint(1) NOT NULL DEFAULT 0,
  `default_auto_renew` tinyint(1) NOT NULL DEFAULT 1,
  `account_closed` tinyint(1) NOT NULL DEFAULT 0,
  `two_fa` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password_reset` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `discount_percent` int(11) DEFAULT NULL,
  `acct_sequence_id` int(10) unsigned NOT NULL DEFAULT 0,
  `acct_on_hold` tinyint(1) NOT NULL DEFAULT 0,
  `acct_current_balance` decimal(10,0) NOT NULL DEFAULT 0,
  `acct_previous_balance` decimal(10,0) NOT NULL DEFAULT 0,
  `acct_overdraw_limit` decimal(10,0) NOT NULL DEFAULT 0,
  `acct_warn_low_balance` decimal(10,0) NOT NULL DEFAULT 0,
  `acct_next_warning_dt` datetime DEFAULT NULL,
  `last_login_dt` datetime DEFAULT NULL,
  `created_dt` datetime DEFAULT NULL,
  `amended_dt` datetime DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `by_login` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

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
  `enabled` tinyint(3) unsigned NOT NULL DEFAULT 1,
  `allow_sales` tinyint(3) unsigned NOT NULL DEFAULT 1,
  `renew_limit` int(11) DEFAULT NULL,
  `owner_user_id` int(10) unsigned DEFAULT NULL,
  `owner_royalty_rate` int(11) DEFAULT NULL,
  `created_dt` datetime DEFAULT NULL,
  `amended_dt` datetime DEFAULT NULL,
  PRIMARY KEY (`zone`),
  KEY `by_last_change` (`amended_dt`,`enabled`,`allow_sales`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `zones`
--

LOCK TABLES `zones` WRITE;
/*!40000 ALTER TABLE `zones` DISABLE KEYS */;
/*!40000 ALTER TABLE `zones` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2023-01-02 15:26:17
GRANT USAGE ON *.* TO `webui`@`%` IDENTIFIED BY PASSWORD "YOUR-PASSWORD";
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`actions` TO `webui`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`domains` TO `webui`@`%`;
GRANT SELECT, INSERT, UPDATE ON `pyrar`.`users` TO `webui`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`session_keys` TO `webui`@`%`;
GRANT SELECT, INSERT, UPDATE ON `pyrar`.`zones` TO `webui`@`%`;
GRANT SELECT, INSERT ON `pyrar`.`events` TO `webui`@`%`;
GRANT SELECT, INSERT, UPDATE ON `pyrar`.`transactions` TO `webui`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`orders` TO `webui`@`%`;
GRANT SELECT, INSERT, UPDATE ON `pyrar`.`payments` TO `webui`@`%`;
GRANT SELECT, INSERT, UPDATE ON `pyrar`.`sales` TO `webui`@`%`;
GRANT SELECT, INSERT ON `pyrar`.`backend` TO `webui`@`%`;
GRANT USAGE ON *.* TO `raradm`@`%` IDENTIFIED BY PASSWORD "YOUR-PASSWORD";
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`zones` TO `raradm`@`%`;
GRANT SELECT, INSERT ON `pyrar`.`events` TO `raradm`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`orders` TO `raradm`@`%`;
GRANT SELECT, UPDATE, DELETE ON `pyrar`.`payments` TO `raradm`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`backend` TO `raradm`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`actions` TO `raradm`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`sysadmins` TO `raradm`@`%`;
GRANT SELECT, INSERT ON `pyrar`.`deleted_users` TO `raradm`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`sales` TO `raradm`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`deleted_domains` TO `raradm`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`domains` TO `raradm`@`%`;
GRANT SELECT, INSERT, UPDATE ON `pyrar`.`transactions` TO `raradm`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`session_keys` TO `raradm`@`%`;
GRANT SELECT, UPDATE, DELETE ON `pyrar`.`users` TO `raradm`@`%`;
GRANT USAGE ON *.* TO `epprun`@`%` IDENTIFIED BY PASSWORD "YOUR-PASSWORD";
GRANT SELECT ON `pyrar`.`zones` TO `epprun`@`%`;
GRANT SELECT, INSERT, UPDATE ON `pyrar`.`transactions` TO `epprun`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`sales` TO `epprun`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`actions` TO `epprun`@`%`;
GRANT SELECT, INSERT ON `pyrar`.`deleted_domains` TO `epprun`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`orders` TO `epprun`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`domains` TO `epprun`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`order_items` TO `epprun`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`epp_jobs` TO `epprun`@`%`;
GRANT SELECT, UPDATE ON `pyrar`.`payments` TO `epprun`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`domain_actions` TO `epprun`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`sales_items` TO `epprun`@`%`;
GRANT SELECT, UPDATE ON `pyrar`.`users` TO `epprun`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`backend` TO `epprun`@`%`;
GRANT SELECT, INSERT ON `pyrar`.`events` TO `epprun`@`%`;
