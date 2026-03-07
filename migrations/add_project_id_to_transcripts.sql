-- Add project_id to transcripts table

-- Since we need to run this on each tenant schema, we need to be careful.
-- This SQL is intended to be run by the migration script which iterates over schemas.
-- However, if run against a single DB, we can just use the table name.

-- We'll use a procedure to add the column safely if it doesn't exist.

DROP PROCEDURE IF EXISTS AddProjectIdToTranscripts;

DELIMITER //

CREATE PROCEDURE AddProjectIdToTranscripts()
BEGIN
    -- unique index or column check
    IF NOT EXISTS (
        SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'transcripts' AND COLUMN_NAME = 'project_id'
    ) THEN
        ALTER TABLE transcripts ADD COLUMN project_id BIGINT DEFAULT NULL AFTER file_name;
        ALTER TABLE transcripts ADD INDEX idx_project_id (project_id);
    END IF;
END //

DELIMITER ;

CALL AddProjectIdToTranscripts();

DROP PROCEDURE IF EXISTS AddProjectIdToTranscripts;
