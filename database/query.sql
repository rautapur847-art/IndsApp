-- IndsApp Database Schema
-- Ye same schema hai jo tumne banayi thi, ek file me combine kiya hai
create DATABASE if not EXISTS IndsApp;
use IndsApp;
CREATE TABLE user (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    phone INT NOT NULL,
    status VARCHAR(20) DEFAULT 'offline',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE message (
    message_id INT PRIMARY KEY AUTO_INCREMENT,

    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,

    message TEXT NOT NULL,

    message_type VARCHAR(20) DEFAULT 'text',
    message_status VARCHAR(20) DEFAULT 'sent',

    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (sender_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES user(id) ON DELETE CASCADE
);


CREATE TABLE contacts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    owner_id INT NOT NULL,
    contact_id INT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_contact (owner_id, contact_id),
    FOREIGN KEY (owner_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES user(id) ON DELETE CASCADE
);
ALTER TABLE contacts add COLUMN  name VARCHAR(100) NOT NULL;
