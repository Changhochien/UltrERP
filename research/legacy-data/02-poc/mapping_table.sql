
-- ============================================================================
-- PRODUCT CODE MAPPING TABLE
-- Proposed schema to resolve the 660 orphan numeric → alphanumeric codes
-- ============================================================================
CREATE TABLE IF NOT EXISTS raw_legacy.product_code_mapping (
    id               SERIAL PRIMARY KEY,
    legacy_code      VARCHAR(30)  NOT NULL,   -- Original code from tbsslipdtx.col_7
    target_code      VARCHAR(30)  NOT NULL,   -- Resolved tbsstock.col_1 (or 'UNKNOWN')
    resolution_type  VARCHAR(20)  NOT NULL,  -- 'exact_match' | 'manual_map' | 'unknown'
    confidence       DECIMAL(5,2) DEFAULT 0, -- 0.00–100.00
    notes            TEXT,
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    created_by       VARCHAR(50)  DEFAULT 'poc_script',
    UNIQUE(legacy_code)
);

-- Index for fast lookups during import
CREATE INDEX IF NOT EXISTS idx_pcm_legacy_code  ON raw_legacy.product_code_mapping(legacy_code);
CREATE INDEX IF NOT EXISTS idx_pcm_target_code  ON raw_legacy.product_code_mapping(target_code);
CREATE INDEX IF NOT EXISTS idx_pcm_resolution  ON raw_legacy.product_code_mapping(resolution_type);

-- Populate with KNOWN matches (confidence=100)
-- These are the codes that appear in BOTH tbsslipdtx and tbsstock
-- Match rate: 96.9% (5,921 of 6,111 codes)
INSERT INTO raw_legacy.product_code_mapping
    (legacy_code, target_code, resolution_type, confidence, notes)
SELECT DISTINCT d.col_7, s.col_1, 'exact_match', 100.00,
       'Code found in both tbsslipdtx and tbsstock'
  FROM raw_legacy.tbsslipdtx d
  JOIN raw_legacy.tbsstock   s ON d.col_7 = s.col_1
ON CONFLICT (legacy_code) DO NOTHING;

-- Populate all orphan codes as 'unknown' (confidence=0) for manual review
INSERT INTO raw_legacy.product_code_mapping
    (legacy_code, target_code, resolution_type, confidence, notes)
SELECT DISTINCT orphan_code, 'UNKNOWN', 'unknown', 0.00,
       'Orphan code — requires manual mapping'
  FROM unnest(ARRAY{'RB052-6', 'LA017-3', '3V0710-2', '3V0750-2', 'LM018.4-5', 'LM014-5', 'LK027.5-4', 'LA016-3', '925VB 30-22', 'LF073-5', 'N33V-820', '3V0800-1', 'LK013', 'LM021.5-5', 'LM032-1', 'PSPB-3350', '23100-0040', 'PP0103-I', 'N3 OA043', 'P5V-1600', '23100-9010-M1', 'LE140-5', 'N3PE-140', 'N3 PB050', 'LA118-5', '3V-0710-M', 'PSPB-3150', 'LA015-3', 'SPZ-1462', 'PSPB-3550', 'RB038-3', 'RB023', '000', '23100GAKA9010', 'BMT-GE8達可達', 'LA017-1', 'LA033-4', 'LA036-5', 'LA042-1', 'LA061-1', 'LA067-5', 'LB059-4', 'LK024', 'N1 PB050', 'N3 OC090', 'N3 PA050', 'N3SPC-3250', 'N4A220', 'N5A067', 'NOM021.5-5', 'NVT-193', 'P5V-0900', 'PSPB-2400', 'PSPC-3350', 'SPA-1457', 'SPZ-1900', 'VMB030', 'VS16*573', 'LM031-5', 'LM028-1', 'PSPA-0950 OH', 'LM019.5', 'LK011.8', 'LF033-1', 'LE140-3', 'LC190-5', 'LC130-5', 'LC110-4', 'LC089-5', 'LC081-4', 'LC069-A8', 'LC048-4', 'LC047-4', 'LC040-4', 'LC038-1', 'LB380-3', 'LB375', 'LB169-5', 'LB168-5', 'LB144-5', 'LB143-5', 'LB113-4', 'LB096-5', 'LB076-5', 'LB064-5', 'LB063-5', 'LB062-5', 'LB052-4', 'LB039-5', 'LA188-4', 'LA120-5', 'LA115-5', 'LA074-5', 'LA061-4', 'LA059-1', 'LA057-1', 'LA056-1', 'LA052-5', 'LA052-1', 'LA047-1', 'LA046-1', 'LA045-5', 'LA039-5', 'LA038-1', 'LA036-1', 'LA033-5', 'LA029-5', 'LA027-1', 'LA019-3', 'LA016-1', 'LA015-4', 'J6-550', 'PSPB-3650', 'PSPB-3750', 'PSPB-4000', 'PSPB-4500', 'PSPC-4250', 'BS022', 'BMT-GWO-23100', 'BMT-GWD-23100', 'BMT-GMO', 'BMT', 'RB045-3', '8M-800*21M/M', 'RB101-6', '8M-560*25M/M3', 'RC083-3', 'RC095', 'RH280*26M/M', 'RL150*21M/M', 'RL263*28m/m', '850VB', '670VA 22-22', '225L*22M/M', 'S-2 9*2230', 'S4.5M-504', 'S8M-1120*19M/M', 'SPA-1700-5', 'SPC-6000', 'SPZ-1000', 'SPZ-1487-2', 'VA915', 'VD740 41', '運費', '3V-0630-M', 'PB025.5-1', 'P8V-4750 OH', 'P5V-1500', 'P5V-1400', 'P5V-1320', 'P5V-1120', 'P5V-0890', 'P5V-0850', 'P5V-0600', 'P3VX-0475OH', 'XL120*5M/M PU', 'OC130', 'OC119', 'NVT-100*1610', 'NOM020.5-5', 'NM019.5-5', 'NM018.4-5', 'NAO081-3', 'N5M058', 'N5K035', 'N5C137', 'N5C119', 'N5C118', 'N5BO050', 'N5B098', 'N5B091', 'N5B087', 'N5A120', 'N5A118', 'N5A046', 'N4B103', 'N3SPA-1232', 'N3OHC113', 'N3OHB120', 'N3OHB108', 'N3C242', 'N3 PC-168', 'N3 PA225', 'N3 OM027', 'N3 OM026', 'N1B046-1', 'N1A038-1', 'N1 PA050', 'N1 OH M-31', 'N1 OA041'}::VARCHAR[]) AS orphan_code
  LEFT JOIN raw_legacy.product_code_mapping pcm
         ON pcm.legacy_code = orphan_code
 WHERE pcm.legacy_code IS NULL
ON CONFLICT (legacy_code) DO NOTHING;
