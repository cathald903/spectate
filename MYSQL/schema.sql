CREATE DATABASE /*!32312 IF NOT EXISTS*/ mysqldb /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci */;

CREATE TABLE sport
(
    name VARCHAR
    (75),
    slug VARCHAR
    (200)NOT NULL,
    active boolean NOT NULL,
    PRIMARY KEY
    (name)
) 