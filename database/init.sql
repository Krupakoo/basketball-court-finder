-- 1. Rozszerzenie przestrzenne PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS lobby_participants CASCADE;
DROP TABLE IF EXISTS lobbies_3x3 CASCADE;
DROP TABLE IF EXISTS check_ins CASCADE;
DROP TABLE IF EXISTS court_reviews CASCADE;
DROP TABLE IF EXISTS courts CASCADE;
DROP TABLE IF EXISTS users CASCADE;

DROP TYPE IF EXISTS surface_type_enum CASCADE;
DROP TYPE IF EXISTS rim_type_enum CASCADE;
DROP TYPE IF EXISTS net_type_enum CASCADE;
DROP TYPE IF EXISTS backboard_type_enum CASCADE;
DROP TYPE IF EXISTS lobby_status_enum CASCADE;

-- 2. Typy wyliczeniowe dla infrastruktury boiska
CREATE TYPE surface_type_enum AS ENUM ('tartan', 'asphalt', 'concrete', 'indoor_parquet');
CREATE TYPE rim_type_enum AS ENUM ('standard_rigid', 'flex_spring', 'double_rim');
CREATE TYPE net_type_enum AS ENUM ('chain', 'nylon', 'none');
CREATE TYPE backboard_type_enum AS ENUM ('acrylic_glass', 'steel_grid', 'wood_plywood', 'fiberglass');
CREATE TYPE lobby_status_enum AS ENUM ('open', 'in_progress', 'finished', 'cancelled');

-- 3. Tabela użytkowników i grywalizacji
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    xp_points INT DEFAULT 0,
    player_level INT DEFAULT 1,
    reputation_score INT DEFAULT 10,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Tabela boisk z kolumną przestrzenną
CREATE TABLE courts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    surface surface_type_enum NOT NULL DEFAULT 'asphalt',
    rim_type rim_type_enum DEFAULT 'standard_rigid',
    net_type net_type_enum DEFAULT 'chain',
    backboard backboard_type_enum DEFAULT 'acrylic_glass',
    hoops_count INT CHECK (hoops_count >= 1) DEFAULT 2,
    has_lighting BOOLEAN DEFAULT FALSE,
    is_fenced BOOLEAN DEFAULT TRUE,
    created_by_user_id INT REFERENCES users(id) ON DELETE SET NULL,
    location GEOGRAPHY(Point, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_courts_location ON courts USING GIST (location);

-- 5. Monitorowanie obłożenia w czasie rzeczywistym (Check-In)
CREATE TABLE check_ins (
    id SERIAL PRIMARY KEY,
    court_id INT NOT NULL REFERENCES courts(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    checked_in_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '90 minutes'),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_check_ins_active ON check_ins (court_id, is_active, expires_at);

-- 6. Matchmaking 3x3 (Lobby na mapie)
CREATE TABLE lobbies_3x3 (
    id SERIAL PRIMARY KEY,
    court_id INT NOT NULL REFERENCES courts(id) ON DELETE CASCADE,
    host_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(100) DEFAULT 'Pickup Game 3x3',
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    max_players INT DEFAULT 6,
    status lobby_status_enum DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lobby_participants (
    lobby_id INT REFERENCES lobbies_3x3(id) ON DELETE CASCADE,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    team_number INT CHECK (team_number IN (1, 2)),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (lobby_id, user_id)
);

-- 7. Oceny i crowd-sourcing stanu boiska
CREATE TABLE court_reviews (
    id SERIAL PRIMARY KEY,
    court_id INT NOT NULL REFERENCES courts(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


INSERT INTO users (username, email, password_hash, xp_points, player_level) VALUES
('jordan23', 'jordan@example.com', 'hash_test_1', 450, 3),
('kobe24', 'kobe@example.com', 'hash_test_2', 120, 1),
('lebron6', 'lebron@example.com', 'hash_test_3', 950, 5);


INSERT INTO courts (name, description, surface, rim_type, net_type, backboard, hoops_count, has_lighting, is_fenced, created_by_user_id, location) VALUES
(
    'Boisko Orlik - Park Jordana', 
    'Nawierzchnia poliuretanowa, regularnie grany streetball.', 
    'tartan', 
    'flex_spring', 
    'chain', 
    'acrylic_glass', 
    2, 
    TRUE, 
    TRUE, 
    1, 
    ST_SetSRID(ST_MakePoint(19.9168, 50.0631), 4326)::geography
),
(
    'Streetball Court Błonia', 
    'Klasyczny asfalt, twarde obręcze bez siatek.', 
    'asphalt', 
    'standard_rigid', 
    'none', 
    'steel_grid', 
    4, 
    FALSE, 
    FALSE, 
    2, 
    ST_SetSRID(ST_MakePoint(19.9074, 50.0598), 4326)::geography
),
(
    'Orlik MOSiR', 
    'Dobre oświetlenie wieczorem, 2 pełnowymiarowe kosze.', 
    'tartan', 
    'standard_rigid', 
    'nylon', 
    'acrylic_glass', 
    2, 
    TRUE, 
    TRUE, 
    1, 
    ST_SetSRID(ST_MakePoint(20.6033, 49.9691), 4326)::geography
);

INSERT INTO check_ins (court_id, user_id, checked_in_at, expires_at, is_active) VALUES
(1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '60 minutes', TRUE),
(1, 2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '45 minutes', TRUE);
