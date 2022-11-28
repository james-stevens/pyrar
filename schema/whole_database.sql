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
-- Table structure for table `deleted_domains`
--

DROP TABLE IF EXISTS `deleted_domains`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `deleted_domains` (
  `deleted_domain_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `domain_id` int(10) unsigned NOT NULL DEFAULT 0,
  `name` varchar(260) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `zone` varchar(260) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
  `status_id` int(10) unsigned NOT NULL DEFAULT 0,
  `renew_id` int(10) unsigned NOT NULL DEFAULT 0,
  `name_servers` text COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_dt` datetime DEFAULT NULL,
  `amended_dt` datetime DEFAULT NULL,
  `expiry_dt` datetime NOT NULL,
  `deleted_dt` datetime NOT NULL,
  PRIMARY KEY (`zone`,`name`),
  UNIQUE KEY `by_id` (`deleted_domain_id`),
  KEY `by_expdt` (`expiry_dt`),
  KEY `by_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10450 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
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
-- Table structure for table `domain_actions`
--

DROP TABLE IF EXISTS `domain_actions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `domain_actions` (
  `domain_id` int(10) unsigned NOT NULL DEFAULT 0,
  `when_dt` datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
  `new_status_id` int(11) DEFAULT NULL,
  `action` varchar(25) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`domain_id`,`when_dt`),
  KEY `by_date` (`when_dt`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `domain_actions`
--

LOCK TABLES `domain_actions` WRITE;
/*!40000 ALTER TABLE `domain_actions` DISABLE KEYS */;
/*!40000 ALTER TABLE `domain_actions` ENABLE KEYS */;
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
  `zone` varchar(260) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `user_id` int(10) unsigned NOT NULL DEFAULT 0,
  `status_id` int(10) unsigned NOT NULL DEFAULT 0,
  `created_dt` datetime DEFAULT NULL,
  `amended_dt` datetime DEFAULT NULL,
  `expiry_dt` datetime NOT NULL,
  PRIMARY KEY (`zone`,`name`),
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
  `email_varified` tinyint(1) NOT NULL DEFAULT 0,
  `payment_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`payment_data`)),
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
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2022-11-28 11:38:43
GRANT USAGE ON *.* TO `webui`@`%` IDENTIFIED BY PASSWORD "YOUR-PASSWORD";
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`domain_actions` TO `webui`@`%`;
GRANT SELECT, INSERT, UPDATE ON `pyrar`.`domains` TO `webui`@`%`;
GRANT SELECT, INSERT, UPDATE ON `pyrar`.`users` TO `webui`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`session_keys` TO `webui`@`%`;
GRANT SELECT, INSERT ON `pyrar`.`events` TO `webui`@`%`;
GRANT USAGE ON *.* TO `raradm`@`%` IDENTIFIED BY PASSWORD "YOUR-PASSWORD";
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`session_keys` TO `raradm`@`%`;
GRANT SELECT ON `pyrar`.`users` TO `raradm`@`%`;
GRANT SELECT, INSERT, UPDATE ON `pyrar`.`events` TO `raradm`@`%`;
GRANT SELECT ON `pyrar`.`deleted_users` TO `raradm`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`domain_actions` TO `raradm`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`deleted_domains` TO `raradm`@`%`;
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`domains` TO `raradm`@`%`;
GRANT USAGE ON *.* TO `epprun`@`%` IDENTIFIED BY PASSWORD "YOUR-PASSWORD";
GRANT SELECT, INSERT, UPDATE, DELETE ON `pyrar`.`domain_actions` TO `epprun`@`%`;
GRANT SELECT ON `pyrar`.`users` TO `epprun`@`%`;
