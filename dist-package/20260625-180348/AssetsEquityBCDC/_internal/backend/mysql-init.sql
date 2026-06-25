CREATE DATABASE IF NOT EXISTS asset_equity CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'asset_equity_user'@'%' IDENTIFIED BY 'ChangeMe123!';
GRANT ALL PRIVILEGES ON asset_equity.* TO 'asset_equity_user'@'%';
FLUSH PRIVILEGES;

USE asset_equity;

CREATE TABLE IF NOT EXISTS equipment_types (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE,
  requires_serial_model TINYINT NOT NULL DEFAULT 0
);

INSERT INTO equipment_types (name, requires_serial_model)
VALUES
  ('Desktop', 1),
  ('Adaptateur', 0),
  ('Cable d''alimentation', 0),
  ('Cable HDMI (15m)', 0),
  ('Cable HDMI (30m)', 0),
  ('Cable HDMI (3m)', 0),
  ('Cable HDMI (5m)', 0),
  ('Cable locker', 0),
  ('Cable locker (noir)', 0),
  ('Casque', 0),
  ('Chargeur Laptop Tige', 0),
  ('Chargeur Laptop Type C', 0),
  ('Desktop complet (Region Ouest)', 1),
  ('Desktop complet EDRMS', 1),
  ('DVD/CD-R', 0),
  ('Extratime', 0),
  ('Finger', 1),
  ('Flash Disk 16GB', 0),
  ('Imprimante Bixolon', 1),
  ('Imprimante Evolis', 1),
  ('Imprimante Evolis (Libanga)', 1),
  ('Kit Starlink', 0),
  ('Laptop OmniBook', 1),
  ('Laptop OmniBook (Region Ouest)', 1),
  ('Laptop Pavillon', 1),
  ('Laptop ProBook', 1),
  ('Laptop ProBook (Libanga)', 1),
  ('Laptop ProBook (EDRMS)', 1),
  ('Laptop ProBook (Region Ouest)', 1),
  ('Lecteur DVD/CD externe Tecsa', 0),
  ('Moniteur', 1),
  ('Moniteur Diagonal 24 pouces', 1),
  ('Pen BK', 0),
  ('Rouleau Extratime', 0),
  ('Ruban Bixolon', 0),
  ('Ruban monochrome (black 1)', 0),
  ('Ruban monochrome (black 2)', 0),
  ('Ruban monochrome (couleur)', 0),
  ('Ruban monochrome (white)', 0),
  ('Sac Laptop', 0),
  ('Scanner biometrique (Kojak)', 1),
  ('Scanner Ricoh', 1),
  ('Souris avec fil', 0),
  ('Souris sans fil (avec pile)', 0),
  ('Souris sans fil (sans pile)', 0),
  ('Support Laptop', 0),
  ('Switch 24 ports', 1),
  ('Switch 48 ports', 1),
  ('Unité Centrale', 1),
  ('Webcam', 1),
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
  equipment_type VARCHAR(80) NOT NULL,
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

CREATE TABLE IF NOT EXISTS stock_policies (
  id INT AUTO_INCREMENT PRIMARY KEY,
  equipment_type VARCHAR(80) NOT NULL UNIQUE,
  lead_time_days INT NOT NULL,
  emergency_days INT NOT NULL,
  minimum_stock INT NOT NULL,
  target_days INT NOT NULL,
  service_factor VARCHAR(20) NOT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_stock_policies_equipment_type
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
  entry_serial_number_id INT,
  timestamp DATETIME NOT NULL,
  movement_type VARCHAR(20) NOT NULL,
  equipment_type VARCHAR(80) NOT NULL,
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

CREATE TABLE IF NOT EXISTS entry_serial_numbers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  material_id INT,
  entry_movement_id INT,
  exit_movement_id INT,
  equipment_type VARCHAR(80) NOT NULL,
  serial_number VARCHAR(255) NOT NULL,
  normalized_serial_number VARCHAR(255) NOT NULL UNIQUE,
  status VARCHAR(20) NOT NULL DEFAULT 'in_stock',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_entry_serials_material
    FOREIGN KEY (material_id) REFERENCES materials(id)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  CONSTRAINT fk_entry_serials_entry_movement
    FOREIGN KEY (entry_movement_id) REFERENCES movements(id)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  CONSTRAINT fk_entry_serials_exit_movement
    FOREIGN KEY (exit_movement_id) REFERENCES movements(id)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  CONSTRAINT fk_entry_serials_equipment_type
    FOREIGN KEY (equipment_type) REFERENCES equipment_types(name)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
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
