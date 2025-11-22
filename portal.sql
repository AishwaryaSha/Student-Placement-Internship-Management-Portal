/* 
==========================================================
Placement Portal (MySQL 8) — Admin + Student only
Database: placement_portal
Date: CURRENT_DATE
==========================================================

ER / Relational Schema (overview)

Entities:
- student(student_id PK, roll_no UNIQUE, first_name, last_name, email UNIQUE, phone, department, batch YEAR, cgpa, created_at)
- placement_office(office_id PK, name, contact_person, email, phone, location, created_at)
- opportunity(opportunity_id PK, office_id FK->placement_office, title, company, description, vacancy, min_cgpa, posted_on, application_deadline, applications_count)
- application(application_id PK, student_id FK->student, opportunity_id FK->opportunity, applied_on, status ENUM, remarks, UNIQUE(student_id, opportunity_id))
- announcement(announcement_id PK, office_id FK->placement_office NULLABLE, title, content, post_date, valid_until)
- assessment(assessment_id PK, opportunity_id FK->opportunity, title, max_marks, date_scheduled, mode ENUM('ONLINE','OFFLINE'), duration_minutes INT NULL, description)
- interview(interview_id PK, application_id FK->application, schedule_time, mode ENUM('ONLINE','OFFLINE'), venue, panel, created_at, result ENUM)
- application_audit(audit_id PK, application_id, action, action_time, details)
- users(user_id PK, username UNIQUE, password_hash, role ENUM('ADMIN','STUDENT'), student_id FK->student NULL, created_at)

3NF: Each table’s non-key attributes depend only on its key; no transitive dependencies; single-attribute PKs; no repeating groups.

Rubric (DB): PK/FK + ON DELETE rules, helpful indexes; 3 deterministic functions; 2 procedures; 2 triggers; 3 views; MySQL users & GRANTs.
==========================================================
*/

DROP DATABASE IF EXISTS placement_portal;
CREATE DATABASE placement_portal;
USE placement_portal;

-- =========================
-- Tables
-- =========================
CREATE TABLE student (
  student_id INT AUTO_INCREMENT PRIMARY KEY,
  roll_no VARCHAR(32) NOT NULL UNIQUE,
  first_name VARCHAR(100) NOT NULL,
  last_name  VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  phone VARCHAR(20),
  department VARCHAR(100) NOT NULL,
  batch YEAR NOT NULL,
  cgpa DECIMAL(3,2) NOT NULL CHECK (cgpa >= 0.00 AND cgpa <= 10.00),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE placement_office (
  office_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  contact_person VARCHAR(150) NOT NULL,
  email VARCHAR(255),
  phone VARCHAR(20),
  location VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE opportunity (
  opportunity_id INT AUTO_INCREMENT PRIMARY KEY,
  office_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  company VARCHAR(200) NOT NULL,
  description TEXT,
  vacancy INT NOT NULL DEFAULT 1 CHECK (vacancy >= 0),
  min_cgpa DECIMAL(3,2) NOT NULL DEFAULT 0.00,
  posted_on DATE NOT NULL,
  application_deadline DATE,
  applications_count INT NOT NULL DEFAULT 0,
  CONSTRAINT fk_opp_office FOREIGN KEY (office_id) REFERENCES placement_office(office_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE application (
  application_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  opportunity_id INT NOT NULL,
  applied_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status ENUM('APPLIED','SHORTLISTED','INTERVIEW_SCHEDULED','OFFERED','REJECTED','WITHDRAWN') NOT NULL DEFAULT 'APPLIED',
  remarks VARCHAR(500),
  CONSTRAINT uc_app UNIQUE (student_id, opportunity_id),
  CONSTRAINT fk_app_student FOREIGN KEY (student_id) REFERENCES student(student_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_app_opportunity FOREIGN KEY (opportunity_id) REFERENCES opportunity(opportunity_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE announcement (
  announcement_id INT AUTO_INCREMENT PRIMARY KEY,
  office_id INT NULL,
  title VARCHAR(200) NOT NULL,
  content TEXT NOT NULL,
  post_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  valid_until DATE,
  CONSTRAINT fk_ann_office FOREIGN KEY (office_id) REFERENCES placement_office(office_id)
    ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE assessment (
  assessment_id INT AUTO_INCREMENT PRIMARY KEY,
  opportunity_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  max_marks INT NOT NULL CHECK (max_marks > 0),
  date_scheduled DATETIME,
  mode ENUM('ONLINE','OFFLINE') NOT NULL DEFAULT 'ONLINE',
  duration_minutes INT NULL,
  description TEXT,
  CONSTRAINT fk_asmt_opp FOREIGN KEY (opportunity_id) REFERENCES opportunity(opportunity_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE interview (
  interview_id INT AUTO_INCREMENT PRIMARY KEY,
  application_id INT NOT NULL,
  schedule_time DATETIME NOT NULL,
  mode ENUM('ONLINE','OFFLINE') NOT NULL,
  venue VARCHAR(255),
  panel TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  result ENUM('PENDING','PASS','FAIL','RESCHEDULED') NOT NULL DEFAULT 'PENDING',
  CONSTRAINT fk_int_app FOREIGN KEY (application_id) REFERENCES application(application_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE application_audit (
  audit_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  application_id INT NOT NULL,
  action VARCHAR(100) NOT NULL,
  action_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  details TEXT
) ENGINE=InnoDB;

CREATE TABLE users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(100) NOT NULL UNIQUE,
  password_hash CHAR(64) NOT NULL,
  role ENUM('ADMIN','STUDENT') NOT NULL,
  student_id INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_users_student FOREIGN KEY (student_id) REFERENCES student(student_id)
    ON DELETE SET NULL
) ENGINE=InnoDB;

-- Indexes
CREATE INDEX idx_app_student ON application(student_id);
CREATE INDEX idx_app_opp ON application(opportunity_id);
CREATE INDEX idx_opp_office ON opportunity(office_id);
CREATE INDEX idx_opp_deadline ON opportunity(application_deadline);
CREATE INDEX idx_announce_valid ON announcement(valid_until);

-- =========================
-- Seed data
-- =========================
INSERT INTO placement_office (name, contact_person, email, phone, location) VALUES
 ('Central Placement Cell', 'Dr. Kavita Rao', 'cpc@example.edu', '080-1111-2222', 'Main Block, Floor 2'),
 ('School of CS Placement', 'Mr. Arjun Menon', 'csplace@example.edu', '080-3333-4444', 'CS Block'),
 ('Industry Relations', 'Ms. Neha Gupta', 'ir@example.edu', '080-5555-6666', 'Admin Tower');

INSERT INTO student (roll_no, first_name, last_name, email, phone, department, batch, cgpa) VALUES
 ('PESU/CS/2023001', 'Aarav', 'Sharma', 'aarav.sharma@example.com', '9876543210', 'CSE', 2027, 9.10),
 ('PESU/CS/2023002', 'Diya', 'Nair', 'diya.nair@example.com', '9876543211', 'CSE', 2026, 8.20),
 ('PESU/EC/2023003', 'Rahul', 'Mehta', 'rahul.mehta@example.com', '9876543212', 'ECE', 2027, 7.35),
 ('PESU/ME/2023004', 'Ishita', 'Patel', 'ishita.patel@example.com', '9876543213', 'ME', 2025, 8.80);

INSERT INTO opportunity (office_id, title, company, description, vacancy, min_cgpa, posted_on, application_deadline)
VALUES
 (1, 'Software Engineer Intern', 'AlphaTech', 'Backend + Data APIs', 10, 8.00, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 20 DAY)),
 (2, 'Data Analyst Intern', 'DataWiz', 'SQL + Python + BI', 6, 7.50, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 7 DAY)),
 (3, 'Embedded Systems Trainee', 'CircuLabs', 'MCU & C programming', 5, 7.00, DATE_SUB(CURDATE(), INTERVAL 30 DAY), DATE_SUB(CURDATE(), INTERVAL 10 DAY)); -- expired

INSERT INTO application (student_id, opportunity_id, status, remarks) VALUES
 (1, 1, 'APPLIED', 'Excited to contribute'),
 (2, 2, 'SHORTLISTED', 'Good SQL profile'),
 (3, 3, 'APPLIED', 'Embedded interest');

INSERT INTO announcement (office_id, title, content, valid_until) VALUES
 (1, 'Pre-Placement Talk - AlphaTech', 'Join PPT at 4 PM in Main Auditorium.', DATE_ADD(CURDATE(), INTERVAL 5 DAY)),
 (NULL, 'Resume Workshop', 'Open to all batches. Bring your laptop.', DATE_ADD(CURDATE(), INTERVAL 3 DAY));

INSERT INTO assessment (opportunity_id, title, max_marks, date_scheduled, mode, duration_minutes, description) VALUES
 (1, 'AlphaTech Online Test', 100, DATE_ADD(NOW(), INTERVAL 3 DAY), 'ONLINE', 90, 'DSA + APIs (online)'),
 (2, 'DataWiz Aptitude', 60, DATE_ADD(NOW(), INTERVAL 2 DAY), 'OFFLINE', NULL, 'SQL, Stats, Logic (offline hall)');

INSERT INTO interview (application_id, schedule_time, mode, venue, panel, result)
VALUES
 (2, DATE_ADD(NOW(), INTERVAL 4 DAY), 'ONLINE', 'Google Meet', 'A. Menon; P. Rao', 'PENDING');

-- App users: admin + one mapped student (Aarav/student_id=1)
-- admin / admin123
-- aarav / student123
INSERT INTO users (username, password_hash, role, student_id) VALUES
 ('admin', SHA2('admin123',256), 'ADMIN', NULL),
 ('aarav', SHA2('student123',256), 'STUDENT', 1);

-- Ensure applications_count

SET SQL_SAFE_UPDATES=0;

UPDATE opportunity o
LEFT JOIN (
  SELECT opportunity_id, COUNT(*) AS c FROM application GROUP BY opportunity_id
) a ON a.opportunity_id = o.opportunity_id
SET o.applications_count = IFNULL(a.c,0);

SET SQL_SAFE_UPDATES=1;
-- =========================
-- Functions
-- =========================
DELIMITER $$

DROP FUNCTION IF EXISTS fn_get_student_fullname $$
CREATE FUNCTION fn_get_student_fullname (sid INT)
RETURNS VARCHAR(255)
DETERMINISTIC
READS SQL DATA
BEGIN
  DECLARE fullname VARCHAR(255);
  SELECT CONCAT(first_name, ' ', last_name) INTO fullname
  FROM student WHERE student_id = sid;
  RETURN fullname;
END $$

DROP FUNCTION IF EXISTS fn_days_left_for_opportunity $$
CREATE FUNCTION fn_days_left_for_opportunity (opp_id INT)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
  DECLARE dl DATE;
  DECLARE days_left INT;
  SELECT application_deadline INTO dl FROM opportunity WHERE opportunity_id = opp_id;
  IF dl IS NULL THEN
    RETURN NULL;
  END IF;
  SET days_left = DATEDIFF(dl, CURDATE());
  RETURN days_left;
END $$

DROP FUNCTION IF EXISTS fn_cgpa_grade $$
CREATE FUNCTION fn_cgpa_grade (cg DECIMAL(3,2))
RETURNS VARCHAR(4)
DETERMINISTIC
NO SQL
BEGIN
  RETURN CASE
    WHEN cg >= 9.0 THEN 'A+'
    WHEN cg >= 8.0 THEN 'A'
    WHEN cg >= 7.0 THEN 'B'
    WHEN cg >= 6.0 THEN 'C'
    ELSE 'D'
  END;
END $$

-- =========================
-- Procedures
-- =========================
DROP PROCEDURE IF EXISTS sp_create_application $$
CREATE PROCEDURE sp_create_application(
  IN p_student INT,
  IN p_opportunity INT,
  OUT p_appid INT
)
BEGIN
  DECLARE v_exists INT DEFAULT 0;
  DECLARE v_min DECIMAL(3,2);
  DECLARE v_cg DECIMAL(3,2);

  IF (SELECT COUNT(*) FROM student WHERE student_id = p_student) = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Student does not exist';
  END IF;

  IF (SELECT COUNT(*) FROM opportunity WHERE opportunity_id = p_opportunity) = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Opportunity does not exist';
  END IF;

  SELECT COUNT(*) INTO v_exists FROM application 
  WHERE student_id = p_student AND opportunity_id = p_opportunity;
  IF v_exists > 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Duplicate application not allowed';
  END IF;

  SELECT min_cgpa INTO v_min FROM opportunity WHERE opportunity_id = p_opportunity;
  SELECT cgpa INTO v_cg FROM student WHERE student_id = p_student;

  IF v_cg < v_min THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CGPA below eligibility threshold';
  END IF;

  IF (SELECT application_deadline FROM opportunity WHERE opportunity_id = p_opportunity) IS NOT NULL
     AND (SELECT DATEDIFF(application_deadline, CURDATE()) FROM opportunity WHERE opportunity_id = p_opportunity) < 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Opportunity deadline has passed';
  END IF;

  INSERT INTO application (student_id, opportunity_id, status, remarks)
  VALUES (p_student, p_opportunity, 'APPLIED', 'Applied via portal');

  SET p_appid = LAST_INSERT_ID();
END $$

DROP PROCEDURE IF EXISTS sp_schedule_interview $$
CREATE PROCEDURE sp_schedule_interview(
  IN p_application_id INT,
  IN p_time DATETIME,
  IN p_mode ENUM('ONLINE','OFFLINE'),
  IN p_venue VARCHAR(255),
  IN p_panel TEXT
)
BEGIN
  IF (SELECT COUNT(*) FROM application WHERE application_id = p_application_id) = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Application not found';
  END IF;

  INSERT INTO interview (application_id, schedule_time, mode, venue, panel, result)
  VALUES (p_application_id, p_time, p_mode, p_venue, p_panel, 'PENDING');

  UPDATE application SET status = 'INTERVIEW_SCHEDULED'
  WHERE application_id = p_application_id;
END $$

DELIMITER ;

-- =========================
-- Triggers
-- =========================
DELIMITER $$

DROP TRIGGER IF EXISTS trg_application_after_insert $$
CREATE TRIGGER trg_application_after_insert
AFTER INSERT ON application
FOR EACH ROW
BEGIN
  UPDATE opportunity
    SET applications_count = applications_count + 1
  WHERE opportunity_id = NEW.opportunity_id;

  INSERT INTO application_audit (application_id, action, details)
  VALUES (NEW.application_id, 'CREATE', CONCAT('Applied by student_id=', NEW.student_id));
END $$

DROP TRIGGER IF EXISTS trg_application_after_delete $$
CREATE TRIGGER trg_application_after_delete
AFTER DELETE ON application
FOR EACH ROW
BEGIN
  UPDATE opportunity
    SET applications_count = GREATEST(applications_count - 1, 0)
  WHERE opportunity_id = OLD.opportunity_id;

  INSERT INTO application_audit (application_id, action, details)
  VALUES (OLD.application_id, 'DELETE', CONCAT('Deleted application for student_id=', OLD.student_id));
END $$

DELIMITER ;

-- =========================
-- Views (join/aggregate/nested)
-- =========================
CREATE OR REPLACE VIEW vw_opportunity_stats AS
SELECT 
  o.opportunity_id,
  o.title,
  o.company,
  o.min_cgpa,
  o.vacancy,
  o.posted_on,
  o.application_deadline,
  COUNT(a.application_id) AS total_applications,
  ROUND(AVG(s.cgpa),2) AS avg_applicant_cgpa
FROM opportunity o
LEFT JOIN application a ON a.opportunity_id = o.opportunity_id
LEFT JOIN student s ON s.student_id = a.student_id
GROUP BY o.opportunity_id, o.title, o.company, o.min_cgpa, o.vacancy, o.posted_on, o.application_deadline;

CREATE OR REPLACE VIEW vw_student_app_counts AS
SELECT 
  s.student_id,
  CONCAT(s.first_name,' ',s.last_name) AS student_name,
  s.department,
  s.batch,
  COUNT(a.application_id) AS app_count
FROM student s
LEFT JOIN application a ON a.student_id = s.student_id
GROUP BY s.student_id, student_name, s.department, s.batch;

CREATE OR REPLACE VIEW vw_above_average_applicants AS
SELECT sac.*
FROM vw_student_app_counts sac
WHERE sac.app_count > (SELECT AVG(app_count) FROM vw_student_app_counts);

-- =========================
-- MySQL users & privileges (Admin + View only; Office removed)
-- =========================
DROP USER IF EXISTS 'portal_admin'@'localhost';
DROP USER IF EXISTS 'portal_view'@'localhost';

CREATE USER 'portal_admin'@'localhost' IDENTIFIED BY 'adminpass';
CREATE USER 'portal_view'@'localhost' IDENTIFIED BY 'viewpass';

GRANT ALL PRIVILEGES ON placement_portal.* TO 'portal_admin'@'localhost';

GRANT SELECT ON placement_portal.vw_opportunity_stats TO 'portal_view'@'localhost';
GRANT SELECT ON placement_portal.vw_student_app_counts TO 'portal_view'@'localhost';
GRANT SELECT ON placement_portal.vw_above_average_applicants TO 'portal_view'@'localhost';
GRANT SELECT ON placement_portal.placement_office TO 'portal_view'@'localhost';
GRANT SELECT ON placement_portal.opportunity TO 'portal_view'@'localhost';

FLUSH PRIVILEGES;
