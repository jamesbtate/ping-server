"""
Stores upgrade instructions for MySQL collector database
"""


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
