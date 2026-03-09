import pymysql
import sys

# Database credentials
DB_HOST = "ballast.proxy.rlwy.net"
DB_PORT = 58607
DB_USER = "root"
DB_PASSWORD = "CtBeFkVkJSUcybwQFvevXGaOMspvxDHZ"

# SQL for creating release_notes table
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `release_notes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `project_id` BIGINT NOT NULL COMMENT 'Associated project',
    `version` VARCHAR(50) NOT NULL COMMENT 'Semantic version (e.g., 1.0.0, 2.1.3)',
    `title` VARCHAR(255) NOT NULL COMMENT 'Release title',
    `release_date` DATE NULL COMMENT 'Scheduled or actual release date',
    `release_type` ENUM('MAJOR', 'MINOR', 'PATCH', 'HOTFIX') DEFAULT 'MINOR' COMMENT 'Release classification',
    `start_sprint` INT NULL COMMENT 'Starting sprint ID for this release range',
    `end_sprint` INT NULL COMMENT 'Ending sprint ID for this release range',
    
    -- Content (JSON structure)
    `content` JSON NULL COMMENT 'Structured content: {features: [], bug_fixes: [], improvements: [], breaking_changes: [], known_issues: []}',
    `summary` TEXT NULL COMMENT 'Executive summary or overview',
    
    -- Status management
    `status` ENUM('DRAFT', 'PUBLISHED', 'ARCHIVED') DEFAULT 'DRAFT' COMMENT 'Publication status',
    
    -- Metadata
    `created_by` INT NOT NULL COMMENT 'User ID of creator (must be PROJECT_MANAGER)',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `published_at` DATETIME NULL COMMENT 'When the release note was published',
    `published_by` INT NULL COMMENT 'User ID who published the release note',
    
    -- Indexes for performance
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_created_by` (`created_by`),
    INDEX `idx_version` (`version`),
    INDEX `idx_release_date` (`release_date`),
    INDEX `idx_published_at` (`published_at`),
    
    -- Foreign key constraints
    CONSTRAINT `fk_release_notes_project`
        FOREIGN KEY (`project_id`)
        REFERENCES `projects` (`project_id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Project release notes with versioning and structured content';
"""

try:
    print(f"Connecting to {DB_HOST}:{DB_PORT}...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=False
    )
    
    cursor = conn.cursor()
    
    # Get list of tenant databases
    cursor.execute("SHOW DATABASES")
    databases = [row[0] for row in cursor.fetchall()]
    
    # Filter out system databases
    tenant_dbs = [db for db in databases if db not in 
                  ['information_schema', 'mysql', 'performance_schema', 'sys', 'railway', 'agilemind_db']]
    
    print(f"\nFound {len(tenant_dbs)} tenant databases: {tenant_dbs}\n")
    
    for db_name in tenant_dbs:
        try:
            print(f"Processing database: {db_name}")
            cursor.execute(f"USE `{db_name}`")
            
            # Check if table already exists
            cursor.execute("SHOW TABLES LIKE 'release_notes'")
            if cursor.fetchone():
                print(f"  ⚠️  Table `release_notes` already exists in {db_name}, skipping...")
                continue
            
            # Create the table
            cursor.execute(CREATE_TABLE_SQL)
            conn.commit()
            print(f"  ✅ Successfully created `release_notes` table in {db_name}")
            
        except Exception as e:
            print(f"  ❌ Error processing {db_name}: {e}")
            conn.rollback()
            continue
    
    cursor.close()
    conn.close()
    
    print("\n✅ Migration completed successfully!")
    
except Exception as e:
    print(f"❌ Migration failed: {e}")
    sys.exit(1)
