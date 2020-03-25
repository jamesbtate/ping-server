"""
Stores upgrade instructions for MySQL collector database
"""

import database_mysql
import logging
import re


def get_code_version():
    """ Return the integer of the highest DB version function in this module. """
    my_things = globals()
    versions = []
    for thing in my_things:
        match = re.match("version_([0-9]+)$", thing)
        if match:
            versions.append(int(match.groups()[0]))
    versions.sort()
    return versions[-1]


def upgrade_database(db: database_mysql.DatabaseMysql):
    """ Upgrade the database using the version_# functions in this module. """
    code_version = get_code_version()
    db_version = db.get_db_version()
    for i in range(db_version + 1, code_version + 1):
        logging.info("Upgrading database to schema version %i", i)
        func = globals()['version_' + str(i)]
        queries = func()
        for query in queries:
            db.execute(query)
        db.commit()


def version_1():
    queries = [
        'alter table output charset=utf8mb4 collate=utf8mb4_unicode_ci;',
        'alter table src_dst charset=utf8mb4 collate=utf8mb4_unicode_ci;',
        'alter table binary_src_dst charset=utf8mb4 collate=utf8mb4_unicode_ci;',
        'CREATE TABLE `version` '
        '( `ping_schema` bigint(20) NOT NULL, PRIMARY KEY (`ping_schema`)) '
        'ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;',
        'INSERT INTO version VALUES (1);'
    ]
    return queries


def version_2():
    queries = [
        'DROP TABLE binary_src_dst;',
        'DROP TABLE output;',
        'UPDATE version SET ping_schema=2;'
    ]
    return queries


def version_3():
    """ Add tables for managing probers """
    queries = [
        '''
        CREATE TABLE `prober` (
         `id` bigint(20) NOT NULL, PRIMARY KEY (`id`),
         `name` varchar(255) NOT NULL,
         `description` TEXT NULL,
         `key` varchar(255) NOT NULL,
         `added` datetime NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''',
        '''
        CREATE TABLE `prober_target` (
         `id` bigint(20) NOT NULL, PRIMARY KEY (`id`),
         `prober_id` BIGINT(20) NOT NULL,
         `name` varchar(255) NOT NULL,
         `description` TEXT NULL,
         `ip` INT UNSIGNED NOT NULL,
         `type` ENUM('icmp', 'udp', 'tcp') NOT NULL,
         `port` INT UNSIGNED NULL,
         `added` datetime NOT NULL,
         INDEX (prober_id),
         FOREIGN KEY (prober_id) REFERENCES prober(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        ''',
        'UPDATE version SET ping_schema=3;'
    ]
    return queries


def version_4():
    """ Replace src_dst.src with prober_id reference """
    queries = [
        'ALTER TABLE src_dst DROP COLUMN src;',
        'ALTER TABLE src_dst ADD COLUMN prober_id BIGINT NOT NULL AFTER id;',
        'ALTER TABLE src_dst ADD FOREIGN KEY (prober_id) REFERENCES prober (id);',
        'UPDATE version SET ping_schema=4;'
    ]
    return queries


def version_5():
    """ Make primary keys of prober and prober_target AUTO_INCREMENT """
    queries = [
        'ALTER TABLE prober_target MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT;',
        'SET FOREIGN_KEY_CHECKS=0;',
        'ALTER TABLE prober MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT;',
        'SET FOREIGN_KEY_CHECKS=1;',
        'UPDATE version SET ping_schema=5;'
    ]
    return queries
