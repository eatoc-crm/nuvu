-- NUVU — one-shot cleanup of all is_test sandbox data.
-- Deletes chase logs, portal sessions tied to test pipeline rows, progression, then pipeline.
-- Run in Supabase SQL editor after testing.

DELETE FROM chase_messages
WHERE property_id IN (
    SELECT sp.id
    FROM sales_progression sp
    INNER JOIN sales_pipeline p ON p.property_address = sp.property_address
    WHERE p.is_test = true
  );

DELETE FROM chase_confirmations
WHERE property_id IN (
    SELECT sp.id
    FROM sales_progression sp
    INNER JOIN sales_pipeline p ON p.property_address = sp.property_address
    WHERE p.is_test = true
  );

DELETE FROM portal_sessions
WHERE property_id IN (
    SELECT id FROM sales_pipeline WHERE is_test = true
  );

DELETE FROM sales_progression
WHERE property_address IN (
    SELECT property_address FROM sales_pipeline WHERE is_test = true
  );

DELETE FROM sales_pipeline
WHERE is_test = true;
