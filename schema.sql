USE `ping`;
CREATE TABLE `src_dst` (
  `id` smallint(5) unsigned NOT NULL AUTO_INCREMENT,
  `src` int(10) unsigned NOT NULL,
  `dst` int(10) unsigned NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB COLLATE='utf8_general_ci';
CREATE TABLE `output` (
  `time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `src_dst` smallint(5) unsigned NOT NULL,
  `latency` smallint(5) unsigned NOT NULL,
  KEY `src_dst` (`src_dst`),
  CONSTRAINT `output_ibfk_1` FOREIGN KEY (`src_dst`) REFERENCES `src_dst` (`id`)
) ENGINE=InnoDB COLLATE='utf8_general_ci';

CREATE TABLE `binary_src_dst` (
  `id` smallint(5) unsigned NOT NULL AUTO_INCREMENT,
  `src` int(10) unsigned NOT NULL,
  `dst` int(10) unsigned NOT NULL,
  `binary_file` varchar(256) NULL,
  `max_records` bigint(20) unsigned NOT NULL DEFAULT '604800',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB COLLATE='utf8_general_ci';
