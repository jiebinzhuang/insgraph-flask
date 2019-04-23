-- Initialize the database.
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS tree;
DROP TABLE IF EXISTS project;
DROP TABLE IF EXISTS point;
DROP TABLE IF EXISTS step;

CREATE TABLE tree (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_code TEXT  NULL,
  name TEXT  NOT NULL,
  level INTEGER  NULL,
  parent_id INTEGER  NULL
);
CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE project (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  projecct_code TEXT UNIQUE NOT NULL,
  projecct_name TEXT NOT NULL
);

CREATE TABLE point (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  point_name TEXT  NOT NULL,
  tree_id TEXT  NOT NULL,
  isauto TEXT   NULL,
  canauto TEXT   NULL,
  condition TEXT   NULL,
  memo TEXT   NULL
);
CREATE TABLE step (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  step_name TEXT  NULL,
  step_result TEXT   NULL,
  iorder INTEGER NOT NULL,
  point_id TEXT  NOT NULL
);

INSERT INTO user (username, password) VALUES ('admin', 'pbkdf2:sha256:50000$6bWF7SCz$4c908d77978d26544b8c3855e9a47253dd51bb0a829e6880732e4ed5e8cd17d8');
INSERT INTO project (projecct_code, projecct_name) VALUES ('SI-api', '数据迁移组件CDT-XDR');
INSERT INTO project (projecct_code, projecct_name) VALUES ('THINKPAD', 'docker部署组件');
INSERT INTO project (projecct_code, projecct_name) VALUES ('DUBBO', 'rpcK框架');