-- Pre-v19 migration cleanup for custom droga modules.
-- Odoo 19 drops the legacy table `uom_category` during uom migration.
-- Any custom FK to `uom_category` must be removed before upgrading.

ALTER TABLE IF EXISTS droga_inventory_cons_issue_detail
    DROP CONSTRAINT IF EXISTS droga_inventory_cons_issue_detail_product_uom_category_id_fkey;

ALTER TABLE IF EXISTS droga_inventory_cons_receive_detail
    DROP CONSTRAINT IF EXISTS droga_inventory_cons_receive_detai_product_uom_category_id_fkey;

ALTER TABLE IF EXISTS droga_inventory_cons_receive_detail_pharma
    DROP CONSTRAINT IF EXISTS droga_inventory_cons_receive_deta_product_uom_category_id_fkey1;

ALTER TABLE IF EXISTS droga_inventory_office_supplies_request_detail
    DROP CONSTRAINT IF EXISTS droga_inventory_office_supplies_re_product_uom_category_id_fkey;

ALTER TABLE IF EXISTS droga_inventory_transfer_custom_detail
    DROP CONSTRAINT IF EXISTS droga_inventory_transfer_custom_de_product_uom_category_id_fkey;

ALTER TABLE IF EXISTS droga_pharma_compounding_detail
    DROP CONSTRAINT IF EXISTS droga_pharma_compounding_detail_product_uom_category_id_fkey;

ALTER TABLE IF EXISTS droga_stock_adjustment_request_detail
    DROP CONSTRAINT IF EXISTS droga_stock_adjustment_request_det_product_uom_category_id_fkey;

-- Optional data cleanup for stored related fields that will be recomputed in upgraded modules:
-- UPDATE droga_inventory_cons_issue_detail SET product_uom_category_id = NULL;
-- UPDATE droga_inventory_cons_receive_detail SET product_uom_category_id = NULL;
-- UPDATE droga_inventory_cons_receive_detail_pharma SET product_uom_category_id = NULL;
-- UPDATE droga_inventory_office_supplies_request_detail SET product_uom_category_id = NULL;
-- UPDATE droga_inventory_transfer_custom_detail SET product_uom_category_id = NULL;
-- UPDATE droga_pharma_compounding_detail SET product_uom_category_id = NULL;
-- UPDATE droga_stock_adjustment_request_detail SET product_uom_category_id = NULL;
