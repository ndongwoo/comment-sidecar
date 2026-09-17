TRUNCATE TABLE ip_addresses;

ALTER TABLE ip_addresses
    CHANGE COLUMN ip ip_hash char(64) NOT NULL,
    ADD PRIMARY KEY (ip_hash);
