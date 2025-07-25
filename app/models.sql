
-- DROP TABLE IF EXISTS flight_assignments;
-- DROP TABLE IF EXISTS crew_schedules;
-- DROP TABLE IF EXISTS crew_members;
-- DROP TABLE IF EXISTS flights;

-- Create flights table
-- CREATE TABLE flights (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     flight_number VARCHAR(20),
--     origin VARCHAR(255),
--     destination VARCHAR(255),
--     direction VARCHAR(10),
--     duration_minutes INT,
--     duration_text VARCHAR(20),
--     departure_time DATETIME NULL,
--     arrival_time DATETIME NULL,
--     origin_timezone VARCHAR(50),
--     destination_timezone VARCHAR(50),
--     origin_gmt_offset VARCHAR(10),
--     destination_gmt_offset VARCHAR(10)
-- );

-- CREATE TABLE crew_members (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     name VARCHAR(255),
--     role VARCHAR(255),
--     is_on_leave BOOLEAN NOT NULL DEFAULT FALSE
-- );

-- CREATE TABLE flight_assignments (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     flight_id INT,
--     flight_number VARCHAR(20),
--     departure VARCHAR(255),
--     arrival VARCHAR(255),
--     crew_id INT,
--     crew_name VARCHAR(255),
--     departure_time DATETIME NULL,
--     arrival_time DATETIME NULL,
--     duration_minutes INT,
--     FOREIGN KEY (flight_id) REFERENCES flights(id),
--     FOREIGN KEY (crew_id) REFERENCES crew_members(id)
-- );

-- CREATE TABLE crew_schedules (
--     id INT PRIMARY KEY AUTO_INCREMENT,
--     crew_id INT,
--     crew_name VARCHAR(255),
--     flight_id INT,
--     flight_number VARCHAR(20),
--     departure_time DATETIME NULL,
--     arrival_time DATETIME NULL,
--     FOREIGN KEY (crew_id) REFERENCES crew_members(id),
--     FOREIGN KEY (flight_id) REFERENCES flights(id)
-- );

-- CREATE INDEX idx_flights_flight_number ON flights(flight_number);
-- CREATE INDEX idx_crew_members_role ON crew_members(role);
-- CREATE INDEX idx_flight_assignments_flight_id ON flight_assignments(flight_id);
-- CREATE INDEX idx_flight_assignments_crew_id ON flight_assignments(crew_id);
-- CREATE INDEX idx_crew_schedules_crew_id ON crew_schedules(crew_id);
-- CREATE INDEX idx_crew_schedules_flight_id ON crew_schedules(flight_id);