-- Create the Media_management database
CREATE DATABASE IF NOT EXISTS Media_management;
USE Media_management;

-- Create the users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,  -- Use BCRYPT or Argon2 for hashing
    email VARCHAR(120) UNIQUE NOT NULL,
    profile_text TEXT,
    profile_picture VARCHAR(255),
    role ENUM('Admin', 'User', 'Guest') DEFAULT 'User',
    status ENUM('Active', 'Suspended') DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    last_activity TIMESTAMP NULL,
    CHECK (CHAR_LENGTH(password) >= 60)  -- Ensures hashed password length
);

-- Create the requests table
CREATE TABLE requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    media_type ENUM('Movie', 'TV Show', 'Music') NOT NULL,
    title VARCHAR(255) NOT NULL,
    status ENUM('Pending', 'In Progress', 'Completed', 'Failed') DEFAULT 'Pending',
    priority ENUM('Low', 'Medium', 'High') DEFAULT 'Medium',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_status_update TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE KEY unique_request (user_id, title)  -- Prevents duplicate requests by the same user
);

-- Create the recommendations table
CREATE TABLE recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    media_title VARCHAR(255) NOT NULL,
    related_media_title VARCHAR(255) NOT NULL,
    user_id INT,
    recommendation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_status BOOLEAN DEFAULT FALSE,
    viewed_status BOOLEAN DEFAULT FALSE,
    sent_to_email VARCHAR(120),
    confidence_score DECIMAL(5, 2) DEFAULT 0.00,  -- Range from 0.00 to 100.00
    rating ENUM('Excellent', 'Good', 'Average', 'Poor') DEFAULT 'Average',
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (sent_to_email) REFERENCES users(email)
);

-- Create the past_recommendations table
CREATE TABLE past_recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    media_title VARCHAR(255) NOT NULL,
    related_media_title VARCHAR(255) NOT NULL,
    sent_to_email VARCHAR(120),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sent_to_email) REFERENCES users(email)
);

-- Create the downloads table
CREATE TABLE downloads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT,
    torrent_name VARCHAR(255),
    download_status ENUM('Queued', 'Downloading', 'Paused', 'Completed', 'Failed') DEFAULT 'Queued',
    progress INT DEFAULT 0,  -- Percentage
    estimated_completion_time TIMESTAMP NULL,
    retry_count INT DEFAULT 0,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (request_id) REFERENCES requests(id),
    CHECK (progress BETWEEN 0 AND 100)  -- Ensures valid progress range
);

-- Create the media_library table
CREATE TABLE media_library (
    id INT AUTO_INCREMENT PRIMARY KEY,
    media_type ENUM('Movie', 'TV Show', 'Music') NOT NULL,
    title VARCHAR(255) UNIQUE NOT NULL,
    tmdb_id INT,  -- Reference to TMDb entries
    genre VARCHAR(100),
    language VARCHAR(50),
    duration INT,  -- Duration in minutes
    file_path VARCHAR(255),
    file_size BIGINT,  -- File size in bytes
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the notifications table
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    notification_type ENUM('Recommendation', 'Update', 'Request Status') NOT NULL,
    severity ENUM('Info', 'Warning', 'Critical') DEFAULT 'Info',
    content TEXT,
    read_status BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Create the audit_logs table
CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action_type ENUM('Login', 'Request Creation', 'Download Update', 'Recommendation Sent', 'Notification Sent') NOT NULL,
    action_details TEXT,
    table_affected VARCHAR(50),
    ip_address VARCHAR(45),  -- Supports IPv4 and IPv6
    user_agent VARCHAR(255),
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Stored Procedure for Archiving Old Recommendations
DELIMITER //
CREATE PROCEDURE ArchiveOldRecommendations()
BEGIN
    INSERT INTO past_recommendations (media_title, related_media_title, sent_to_email, sent_at)
    SELECT media_title, related_media_title, sent_to_email, NOW()
    FROM recommendations
    WHERE sent_status = TRUE;

    DELETE FROM recommendations
    WHERE sent_status = TRUE;
END //
DELIMITER ;

-- Stored Procedure for Deleting Old Audit Logs
DELIMITER //
CREATE PROCEDURE CleanOldAuditLogs()
BEGIN
    DELETE FROM audit_logs
    WHERE action_timestamp < (NOW() - INTERVAL 30 DAY);
END //
DELIMITER ;

-- Stored Procedure for Creating User Requests
DELIMITER //
CREATE PROCEDURE CreateUserRequest(IN p_user_id INT, IN p_media_type ENUM('Movie', 'TV Show', 'Music'), IN p_title VARCHAR(255))
BEGIN
    INSERT INTO requests (user_id, media_type, title, status, priority)
    VALUES (p_user_id, p_media_type, p_title, 'Pending', 'Medium');
END //
DELIMITER ;

-- Stored Procedure for Marking Notifications as Read
DELIMITER //
CREATE PROCEDURE MarkNotificationAsRead(IN p_notification_id INT)
BEGIN
    UPDATE notifications
    SET read_status = TRUE
    WHERE id = p_notification_id;
END //
DELIMITER ;

-- View for User Activity Summary
CREATE VIEW user_activity_summary AS
SELECT 
    u.username,
    COUNT(DISTINCT r.id) AS total_requests,
    COUNT(DISTINCT d.id) AS total_downloads,
    COUNT(DISTINCT n.id) AS total_notifications,
    MAX(u.last_activity) AS last_activity
FROM users u
LEFT JOIN requests r ON u.id = r.user_id
LEFT JOIN downloads d ON r.id = d.request_id
LEFT JOIN notifications n ON u.id = n.user_id
GROUP BY u.username;

-- View for Download Progress
CREATE VIEW download_progress AS
SELECT 
    d.id AS download_id,
    r.title AS media_title,
    d.torrent_name,
    d.download_status,
    d.progress,
    d.estimated_completion_time
FROM downloads d
JOIN requests r ON d.request_id = r.id;

-- View for Recent Recommendations
CREATE VIEW recent_recommendations AS
SELECT 
    r.media_title,
    r.related_media_title,
    r.sent_to_email,
    r.recommendation_date,
    r.confidence_score,
    r.rating
FROM recommendations r
WHERE r.sent_status = TRUE;

-- Trigger for Inserting Audit Logs on User Actions
CREATE TRIGGER after_request_insert
AFTER INSERT ON requests
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (user_id, action_type, action_details, table_affected, action_timestamp)
    VALUES (NEW.user_id, 'Request Creation', CONCAT('Request for media: ', NEW.title), 'requests', NOW());
END;

-- Trigger for Updating Last Activity Timestamp
CREATE TRIGGER update_last_activity
AFTER INSERT OR UPDATE ON requests
FOR EACH ROW
BEGIN
    UPDATE users
    SET last_activity = NOW()
    WHERE id = NEW.user_id;
END;

-- Trigger for Notification Sent Logging
CREATE TRIGGER after_notification_sent
AFTER INSERT ON notifications
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (user_id, action_type, action_details, table_affected, action_timestamp)
    VALUES (NEW.user_id, 'Notification Sent', CONCAT('Notification sent: ', NEW.content), 'notifications', NOW());
END;

-- Trigger for Marking Recommendations as Sent
CREATE TRIGGER mark_recommendation_sent
AFTER INSERT ON notifications
FOR EACH ROW
BEGIN
    IF NEW.notification_type = 'Recommendation' THEN
        UPDATE recommendations
        SET sent_status = TRUE
        WHERE sent_to_email = NEW.user_id;
    END IF;
END;
