ALTER TABLE comments
    ADD COLUMN page_id varchar(170) DEFAULT NULL AFTER path;

CREATE INDEX explicit_thread_index
    ON comments (`site`, `page_id`, `creation_date`);
