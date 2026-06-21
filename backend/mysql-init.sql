CREATE DATABASE IF NOT EXISTS asset_equity CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'asset_equity_user'@'%' IDENTIFIED BY 'ChangeMe123!';
GRANT ALL PRIVILEGES ON asset_equity.* TO 'asset_equity_user'@'%';
FLUSH PRIVILEGES;

USE asset_equity;

CREATE TABLE IF NOT EXISTS equipment_types (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(40) NOT NULL UNIQUE,
  requires_serial_model TINYINT NOT NULL DEFAULT 0
);

INSERT INTO equipment_types (name, requires_serial_model)
VALUES
  ('Desktop', 1),
  ('Laptop', 1),
  ('Ecran', 1),
  ('Souris', 0),
  ('Switch', 1),
  ('Routeur', 1),
  ('Clavier', 0),
  ('Other', 0)
ON DUPLICATE KEY UPDATE
  requires_serial_model = VALUES(requires_serial_model);

CREATE TABLE IF NOT EXISTS materials (
  id INT AUTO_INCREMENT PRIMARY KEY,
  equipment_type VARCHAR(40) NOT NULL,
  serial_number VARCHAR(255),
  model VARCHAR(255),
  description TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_materials_equipment_type
    FOREIGN KEY (equipment_type) REFERENCES equipment_types(name)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  display_name VARCHAR(120) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(30) NOT NULL DEFAULT 'user',
  photo_url VARCHAR(500),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_credentials_changed_at DATETIME,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS movements (
  id INT AUTO_INCREMENT PRIMARY KEY,
  material_id INT,
  timestamp DATETIME NOT NULL,
  movement_type VARCHAR(20) NOT NULL,
  equipment_type VARCHAR(40) NOT NULL,
  quantity INT NOT NULL,
  serial_number VARCHAR(255),
  model VARCHAR(255),
  destination VARCHAR(255),
  taken_by VARCHAR(255),
  initiated_by VARCHAR(80),
  notes TEXT,
  CONSTRAINT fk_movements_material
    FOREIGN KEY (material_id) REFERENCES materials(id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT fk_movements_equipment_type
    FOREIGN KEY (equipment_type) REFERENCES equipment_types(name)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT fk_movements_initiated_by
    FOREIGN KEY (initiated_by) REFERENCES users(username)
    ON UPDATE CASCADE
    ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  actor_username VARCHAR(80),
  action VARCHAR(80) NOT NULL,
  entity_type VARCHAR(80) NOT NULL,
  entity_id VARCHAR(120),
  old_value TEXT,
  new_value TEXT,
  ip_address VARCHAR(80),
  user_agent VARCHAR(500),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_audit_logs_actor
    FOREIGN KEY (actor_username) REFERENCES users(username)
    ON UPDATE CASCADE
    ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  token VARCHAR(255) NOT NULL UNIQUE,
  username VARCHAR(80) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME NOT NULL,
  revoked_at DATETIME,
  CONSTRAINT fk_sessions_user
    FOREIGN KEY (username) REFERENCES users(username)
    ON UPDATE CASCADE
    ON DELETE CASCADE
);

INSERT INTO users (username, display_name, password_hash, role, photo_url)
VALUES
  ('admin', 'Admin Equity', SHA2('StrongPassword123!', 256), 'admin', 'https://ui-avatars.com/api/?name=Admin&background=b60f1e&color=ffffff'),
  ('user', 'Utilisateur BCDC', SHA2('Password2026!', 256), 'user', 'https://ui-avatars.com/api/?name=User&background=b60f1e&color=ffffff')
ON DUPLICATE KEY UPDATE
  display_name = VALUES(display_name),
  role = VALUES(role),
  photo_url = VALUES(photo_url);
