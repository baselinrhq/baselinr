-- Migration script to change baselinr_runs primary key from run_id to (run_id, dataset_name)
-- This allows multiple tables to be profiled in the same run

-- Step 1: Drop the existing primary key constraint
ALTER TABLE baselinr_runs DROP CONSTRAINT IF EXISTS baselinr_runs_pkey;

-- Step 2: Add the new composite primary key
ALTER TABLE baselinr_runs ADD PRIMARY KEY (run_id, dataset_name);

-- Note: If you have existing data with duplicate run_ids but different dataset_names,
-- you may need to clean up duplicates first. This script assumes each run_id has unique dataset_names.

