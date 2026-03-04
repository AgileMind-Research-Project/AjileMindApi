-- Migration: Create new_tasks and recurring_bugs tables
-- Run this migration for each tenant schema

-- New Tasks table (from brainstorming reports)
CREATE TABLE IF NOT EXISTS new_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_id INT NOT NULL,
    transcript_id INT NOT NULL,
    task_title VARCHAR(500) NOT NULL,
    assignee VARCHAR(255),
    due_date VARCHAR(50),
    priority VARCHAR(50),
    status ENUM('pending', 'approved', 'removed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_new_tasks_status (status),
    INDEX idx_new_tasks_report_id (report_id),
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
    FOREIGN KEY (transcript_id) REFERENCES transcripts(id) ON DELETE CASCADE
);

-- Recurring Bugs table (from retrospective reports)
CREATE TABLE IF NOT EXISTS recurring_bugs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_id INT NOT NULL,
    transcript_id INT NOT NULL,
    bug_description VARCHAR(1000) NOT NULL,
    severity VARCHAR(50),
    mentioned_count INT DEFAULT 1,
    status ENUM('open', 'resolved', 'dismissed') DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_recurring_bugs_status (status),
    INDEX idx_recurring_bugs_report_id (report_id),
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
    FOREIGN KEY (transcript_id) REFERENCES transcripts(id) ON DELETE CASCADE
);
