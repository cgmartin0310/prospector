-- Insert counties for Delaware
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'New Castle', id FROM state WHERE abbreviation = 'DE';
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'Kent', id FROM state WHERE abbreviation = 'DE';
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'Sussex', id FROM state WHERE abbreviation = 'DE';

-- Insert counties for Texas (major ones)
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'Harris', id FROM state WHERE abbreviation = 'TX';
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'Dallas', id FROM state WHERE abbreviation = 'TX';
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'Tarrant', id FROM state WHERE abbreviation = 'TX';
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'Bexar', id FROM state WHERE abbreviation = 'TX';
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'Travis', id FROM state WHERE abbreviation = 'TX';
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'Collin', id FROM state WHERE abbreviation = 'TX';

-- Insert counties for California (major ones)
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'Los Angeles', id FROM state WHERE abbreviation = 'CA';
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'San Francisco', id FROM state WHERE abbreviation = 'CA';
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'San Diego', id FROM state WHERE abbreviation = 'CA';
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'Orange', id FROM state WHERE abbreviation = 'CA';
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'Riverside', id FROM state WHERE abbreviation = 'CA';
INSERT OR IGNORE INTO county (name, state_id) 
SELECT 'Sacramento', id FROM state WHERE abbreviation = 'CA';
