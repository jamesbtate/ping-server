CREATE TABLE `src_dst` (
  `id` smallint(5) unsigned NOT NULL AUTO_INCREMENT,
  `src` int(10) unsigned NOT NULL,
  `dst` int(10) unsigned NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB COLLATE='utf8_general_ci';
CREATE TABLE `output` (
  `time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `src_dst` smallint(5) unsigned NOT NULL,
  `latency` smallint(5) unsigned NOT NULL,
  KEY `src_dst` (`src_dst`),
  CONSTRAINT `output_ibfk_1` FOREIGN KEY (`src_dst`) REFERENCES `src_dst` (`id`)
) ENGINE=InnoDB COLLATE='utf8_general_ci';
