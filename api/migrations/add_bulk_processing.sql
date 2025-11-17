-- Migration: Add bulk processing tables
-- Run this after updating the database models

-- Add batch table
CREATE TABLE IF NOT EXISTS batches (
    id VARCHAR PRIMARY KEY DEFAULT 'batch_' || substr(hex(randomblob(6)), 1, 12),
    tenant_id VARCHAR NOT NULL,
    client_id VARCHAR,
    batch_name VARCHAR,
    total_files INTEGER DEFAULT 0,
    processed_files INTEGER DEFAULT 0,
    failed_files INTEGER DEFAULT 0,
    status VARCHAR DEFAULT 'processing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Add clients table
CREATE TABLE IF NOT EXISTS clients (
    id VARCHAR PRIMARY KEY DEFAULT 'client_' || substr(hex(randomblob(6)), 1, 12),
    tenant_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    gstin VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add foreign key columns to existing jobs table
ALTER TABLE jobs ADD COLUMN batch_id VARCHAR REFERENCES batches(id);
ALTER TABLE jobs ADD COLUMN client_id VARCHAR REFERENCES clients(id);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_batches_tenant_id ON batches(tenant_id);
CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status);
CREATE INDEX IF NOT EXISTS idx_jobs_batch_id ON jobs(batch_id);
CREATE INDEX IF NOT EXISTS idx_jobs_client_id ON jobs(client_id);
CREATE INDEX IF NOT EXISTS idx_clients_tenant_id ON clients(tenant_id);

-- Insert sample client for testing
INSERT INTO clients (id, tenant_id, name, gstin, email) VALUES 
('client_test123', 'tenant_test', 'Test Client Pvt Ltd', '29ABCDE1234F1Z5', 'test@example.com');

