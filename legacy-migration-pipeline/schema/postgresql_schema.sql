-- ============================================================================
-- ERP Target Database Schema - PostgreSQL DDL
-- Generated from legacy ERP data migration analysis
-- Company: 聯泰興實業有限公司 (Hardware/Industrial Belt Distributor)
-- ============================================================================

-- Drop tables if exist (in reverse dependency order)
DROP TABLE IF EXISTS sales_order_lines CASCADE;
DROP TABLE IF EXISTS sales_orders CASCADE;
DROP TABLE IF EXISTS purchase_order_lines CASCADE;
DROP TABLE IF EXISTS purchase_orders CASCADE;
DROP TABLE IF EXISTS inventory CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS warehouses CASCADE;
DROP TABLE IF EXISTS parties CASCADE;
DROP TABLE IF EXISTS chart_of_accounts CASCADE;
DROP TABLE IF EXISTS banks CASCADE;

-- ============================================================================
-- PARTIES (Combined Customers and Suppliers)
-- ============================================================================
CREATE TABLE parties (
    party_id VARCHAR(20) PRIMARY KEY,
    party_type VARCHAR(10) NOT NULL CHECK (party_type IN ('customer', 'supplier')),
    name VARCHAR(200) NOT NULL,
    short_name VARCHAR(100),
    tax_id VARCHAR(20),
    contact_person VARCHAR(100),
    phone VARCHAR(30),
    fax VARCHAR(30),
    email VARCHAR(100),
    address_full TEXT,
    address_zip VARCHAR(10),
    address_city VARCHAR(50),
    address_district VARCHAR(50),
    address_line VARCHAR(200),
    status VARCHAR(1) DEFAULT 'A' CHECK (status IN ('A', 'I', 'D')),
    credit_limit DECIMAL(15, 2) DEFAULT 0,
    balance DECIMAL(15, 2) DEFAULT 0,
    created_at DATE DEFAULT CURRENT_DATE,
    updated_at DATE DEFAULT CURRENT_DATE,
    memo TEXT
);

CREATE INDEX idx_parties_party_type ON parties(party_type);
CREATE INDEX idx_parties_name ON parties(name);
CREATE INDEX idx_parties_status ON parties(status);
CREATE INDEX idx_parties_tax_id ON parties(tax_id);

-- ============================================================================
-- PRODUCTS
-- ============================================================================
CREATE TABLE products (
    product_id VARCHAR(30) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description VARCHAR(500),
    category VARCHAR(50),
    unit VARCHAR(20) DEFAULT '條',
    origin VARCHAR(50),
    cost DECIMAL(15, 4) DEFAULT 0,
    price DECIMAL(15, 4) DEFAULT 0,
    min_stock DECIMAL(15, 4) DEFAULT 0,
    max_stock DECIMAL(15, 4) DEFAULT 0,
    safety_stock DECIMAL(15, 4) DEFAULT 0,
    reorder_point DECIMAL(15, 4) DEFAULT 0,
    weight DECIMAL(10, 4) DEFAULT 0,
    status VARCHAR(1) DEFAULT 'A' CHECK (status IN ('A', 'I', 'D')),
    created_at DATE DEFAULT CURRENT_DATE,
    updated_at DATE DEFAULT CURRENT_DATE,
    memo TEXT
);

CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_products_origin ON products(origin);

-- ============================================================================
-- WAREHOUSES
-- ============================================================================
CREATE TABLE warehouses (
    warehouse_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200),
    address TEXT,
    contact_phone VARCHAR(30),
    manager VARCHAR(50),
    status VARCHAR(1) DEFAULT 'A' CHECK (status IN ('A', 'I', 'D')),
    created_at DATE DEFAULT CURRENT_DATE,
    updated_at DATE DEFAULT CURRENT_DATE,
    memo TEXT
);

CREATE INDEX idx_warehouses_name ON warehouses(name);
CREATE INDEX idx_warehouses_status ON warehouses(status);

-- ============================================================================
-- INVENTORY (Stock by Warehouse)
-- ============================================================================
CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(30) NOT NULL REFERENCES products(product_id),
    warehouse_id VARCHAR(10) NOT NULL REFERENCES warehouses(warehouse_id),
    quantity_on_hand DECIMAL(15, 4) DEFAULT 0,
    quantity_reserved DECIMAL(15, 4) DEFAULT 0,
    quantity_available DECIMAL(15, 4) GENERATED ALWAYS AS (quantity_on_hand - quantity_reserved) STORED,
    unit_cost DECIMAL(15, 4) DEFAULT 0,
    total_value DECIMAL(15, 2) GENERATED ALWAYS AS (quantity_on_hand * unit_cost) STORED,
    last_count_date DATE,
    last_receipt_date DATE,
    status VARCHAR(1) DEFAULT 'A' CHECK (status IN ('A', 'I')),
    created_at DATE DEFAULT CURRENT_DATE,
    updated_at DATE DEFAULT CURRENT_DATE,
    UNIQUE(product_id, warehouse_id)
);

CREATE INDEX idx_inventory_product_id ON inventory(product_id);
CREATE INDEX idx_inventory_warehouse_id ON inventory(warehouse_id);
CREATE INDEX idx_inventory_status ON inventory(status);

-- ============================================================================
-- SALES ORDERS (Headers from tbsslipx)
-- ============================================================================
CREATE TABLE sales_orders (
    order_id VARCHAR(20) PRIMARY KEY,
    order_number VARCHAR(20) NOT NULL UNIQUE,
    order_date DATE NOT NULL,
    invoice_number VARCHAR(20),
    party_id VARCHAR(20) NOT NULL REFERENCES parties(party_id),
    party_name VARCHAR(100),
    party_address TEXT,
    contact_phone VARCHAR(30),
    contact_person VARCHAR(50),
    warehouse_id VARCHAR(10) DEFAULT 'A' REFERENCES warehouses(warehouse_id),
    currency_code VARCHAR(5) DEFAULT 'NTD',
    exchange_rate DECIMAL(10, 6) DEFAULT 1.000000,
    subtotal DECIMAL(15, 2) DEFAULT 0,
    tax_amount DECIMAL(15, 2) DEFAULT 0,
    discount_amount DECIMAL(15, 2) DEFAULT 0,
    total_amount DECIMAL(15, 2) DEFAULT 0,
    payment_status VARCHAR(1) DEFAULT '0',
    shipping_status VARCHAR(1) DEFAULT '0',
    order_status VARCHAR(1) DEFAULT '1',
    slip_type VARCHAR(2) DEFAULT '1',
    memo TEXT,
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sales_orders_order_number ON sales_orders(order_number);
CREATE INDEX idx_sales_orders_order_date ON sales_orders(order_date);
CREATE INDEX idx_sales_orders_party_id ON sales_orders(party_id);
CREATE INDEX idx_sales_orders_status ON sales_orders(order_status);
CREATE INDEX idx_sales_orders_created_at ON sales_orders(created_at);

-- ============================================================================
-- SALES ORDER LINES (from tbsslipdtx)
-- ============================================================================
CREATE TABLE sales_order_lines (
    line_id SERIAL PRIMARY KEY,
    order_id VARCHAR(20) NOT NULL REFERENCES sales_orders(order_id),
    line_number INTEGER NOT NULL,
    product_id VARCHAR(30) NOT NULL REFERENCES products(product_id),
    product_name VARCHAR(200),
    description VARCHAR(500),
    unit VARCHAR(20),
    quantity DECIMAL(15, 4) DEFAULT 0,
    unit_price DECIMAL(15, 4) DEFAULT 0,
    discount_percent DECIMAL(5, 2) DEFAULT 0,
    discount_amount DECIMAL(15, 2) DEFAULT 0,
    tax_percent DECIMAL(5, 2) DEFAULT 0,
    tax_amount DECIMAL(15, 2) DEFAULT 0,
    line_total DECIMAL(15, 2) GENERATED ALWAYS AS (
        quantity * unit_price * (1 - discount_percent / 100) + tax_amount
    ) STORED,
    warehouse_id VARCHAR(10) DEFAULT 'A' REFERENCES warehouses(warehouse_id),
    delivery_date DATE,
    status VARCHAR(1) DEFAULT 'A' CHECK (status IN ('A', 'I', 'C')),
    memo TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sales_order_lines_order_id ON sales_order_lines(order_id);
CREATE INDEX idx_sales_order_lines_product_id ON sales_order_lines(product_id);
CREATE INDEX idx_sales_order_lines_warehouse_id ON sales_order_lines(warehouse_id);

-- ============================================================================
-- PURCHASE ORDERS (Headers from tbsslipj)
-- ============================================================================
CREATE TABLE purchase_orders (
    order_id VARCHAR(20) PRIMARY KEY,
    order_number VARCHAR(20) NOT NULL UNIQUE,
    order_date DATE NOT NULL,
    invoice_number VARCHAR(20),
    party_id VARCHAR(20) NOT NULL REFERENCES parties(party_id),
    party_name VARCHAR(100),
    party_address TEXT,
    contact_phone VARCHAR(30),
    contact_person VARCHAR(50),
    warehouse_id VARCHAR(10) DEFAULT 'A' REFERENCES warehouses(warehouse_id),
    currency_code VARCHAR(5) DEFAULT 'NTD',
    exchange_rate DECIMAL(10, 6) DEFAULT 1.000000,
    subtotal DECIMAL(15, 2) DEFAULT 0,
    tax_amount DECIMAL(15, 2) DEFAULT 0,
    discount_amount DECIMAL(15, 2) DEFAULT 0,
    total_amount DECIMAL(15, 2) DEFAULT 0,
    payment_status VARCHAR(1) DEFAULT '0',
    receiving_status VARCHAR(1) DEFAULT '0',
    order_status VARCHAR(1) DEFAULT '1',
    slip_type VARCHAR(2) DEFAULT '4',
    memo TEXT,
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_purchase_orders_order_number ON purchase_orders(order_number);
CREATE INDEX idx_purchase_orders_order_date ON purchase_orders(order_date);
CREATE INDEX idx_purchase_orders_party_id ON purchase_orders(party_id);
CREATE INDEX idx_purchase_orders_status ON purchase_orders(order_status);
CREATE INDEX idx_purchase_orders_created_at ON purchase_orders(created_at);

-- ============================================================================
-- PURCHASE ORDER LINES (from tbsslipdtj)
-- ============================================================================
CREATE TABLE purchase_order_lines (
    line_id SERIAL PRIMARY KEY,
    order_id VARCHAR(20) NOT NULL REFERENCES purchase_orders(order_id),
    line_number INTEGER NOT NULL,
    product_id VARCHAR(30) NOT NULL REFERENCES products(product_id),
    product_name VARCHAR(200),
    description VARCHAR(500),
    unit VARCHAR(20),
    quantity DECIMAL(15, 4) DEFAULT 0,
    unit_price DECIMAL(15, 4) DEFAULT 0,
    discount_percent DECIMAL(5, 2) DEFAULT 0,
    discount_amount DECIMAL(15, 2) DEFAULT 0,
    tax_percent DECIMAL(5, 2) DEFAULT 0,
    tax_amount DECIMAL(15, 2) DEFAULT 0,
    line_total DECIMAL(15, 2) GENERATED ALWAYS AS (
        quantity * unit_price * (1 - discount_percent / 100) + tax_amount
    ) STORED,
    warehouse_id VARCHAR(10) DEFAULT 'A' REFERENCES warehouses(warehouse_id),
    delivery_date DATE,
    status VARCHAR(1) DEFAULT 'A' CHECK (status IN ('A', 'I', 'C')),
    memo TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_purchase_order_lines_order_id ON purchase_order_lines(order_id);
CREATE INDEX idx_purchase_order_lines_product_id ON purchase_order_lines(product_id);
CREATE INDEX idx_purchase_order_lines_warehouse_id ON purchase_order_lines(warehouse_id);

-- ============================================================================
-- CHART OF ACCOUNTS (from tbasubject)
-- ============================================================================
CREATE TABLE chart_of_accounts (
    account_id VARCHAR(20) PRIMARY KEY,
    account_code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    name_en VARCHAR(200),
    account_type VARCHAR(10) DEFAULT 'asset' CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')),
    balance_type VARCHAR(1) DEFAULT 'D' CHECK (balance_type IN ('D', 'C')),
    subclass_id VARCHAR(10),
    subclass_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_control_account BOOLEAN DEFAULT FALSE,
    allow_direct_entry BOOLEAN DEFAULT TRUE,
    tax_type VARCHAR(10),
    reconciliation_account VARCHAR(20),
    created_at DATE DEFAULT CURRENT_DATE,
    updated_at DATE DEFAULT CURRENT_DATE,
    memo TEXT
);

CREATE INDEX idx_chart_of_accounts_account_code ON chart_of_accounts(account_code);
CREATE INDEX idx_chart_of_accounts_account_type ON chart_of_accounts(account_type);
CREATE INDEX idx_chart_of_accounts_balance_type ON chart_of_accounts(balance_type);
CREATE INDEX idx_chart_of_accounts_is_active ON chart_of_accounts(is_active);

-- ============================================================================
-- BANKS (from tbabank)
-- ============================================================================
CREATE TABLE banks (
    bank_id VARCHAR(20) PRIMARY KEY,
    bank_code VARCHAR(10) NOT NULL,
    branch_code VARCHAR(10),
    bank_name VARCHAR(200) NOT NULL,
    branch_name VARCHAR(200),
    swift_code VARCHAR(11),
    address TEXT,
    contact_phone VARCHAR(30),
    contact_person VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATE DEFAULT CURRENT_DATE,
    updated_at DATE DEFAULT CURRENT_DATE,
    memo TEXT
);

CREATE INDEX idx_banks_bank_code ON banks(bank_code);
CREATE INDEX idx_banks_bank_name ON banks(bank_name);
CREATE INDEX idx_banks_is_active ON banks(is_active);

-- ============================================================================
-- SAMPLE DATA - INSERT STATEMENTS
-- ============================================================================

-- Parties (Customers and Suppliers)
INSERT INTO parties (party_id, party_type, name, short_name, tax_id, contact_person, phone, address_full, address_zip, status, created_at) VALUES
('1143', 'customer', '恆峰', '恆峰', '', '陳先生', '02-25918322', '台北市大同區迪化街二段191巷9號1樓', '103', 'A', '2024-08-26'),
('2308', 'customer', '吉科', '吉科', '', '', '0933553963', '台中市大里區爽文路859巷8號', '412', 'A', '2024-01-08'),
('2514', 'customer', '順順', '順順', '', '', '047513388', '彰化市崙平南路201號', '500', 'A', '2024-08-27'),
('2716', 'customer', '晉昌', '晉昌', '', '', '047551050', '彰化縣和美鎮湖內里彰新路6段657號', '508', 'A', '2024-08-27'),
('2801', 'customer', '明欣', '明欣', '', '', '048323014', '彰化縣員林市莒光路59號', '510', 'A', '2024-08-27'),
('T002', 'supplier', '燦達企業', '燦達', '', '', '0225581621', '台北市大同區太原路73號3F-5', '103', 'A', '2024-08-30'),
('T033', 'supplier', '建億橡膠股份有限公司', '建億', '', '陳先生', '048365466', '彰化縣員林市鎮興里麒麟巷212弄66號', '510', 'A', '2019-08-14'),
('T067', 'supplier', '勝梨', '勝梨', '', '', '03-4614001~3', '桃園市中壢區福星三街11號', '320', 'A', '2024-08-27'),
('T068', 'supplier', '達基', '達基', '', '', '02-27918100', '台北市內湖區民權東路六段21巷25號', '114', 'A', '2024-08-26');

-- Products
INSERT INTO products (product_id, name, description, unit, origin, cost, price, status, created_at) VALUES
('VB048', '三角皮帶 VB-48', 'VB皮帶 48', '條', '台灣', 8.0000, 41.0000, 'A', '2022-06-28'),
('C-240', '三角皮帶 C-240', 'C-240 三角皮帶', '條', '泰國', 288.0000, 1267.2000, 'A', '2022-06-28'),
('M-59', '三角皮帶 M-59', 'M-59 三角皮帶', '條', '泰國', 19.5000, 103.8000, 'A', '2021-08-23'),
('XPB-2410-P', 'XPB-2410 進口', 'XPB-2410 進口皮帶', '條', '泰國', 395.0000, 700.0000, 'A', '2024-08-27'),
('SPA-1432 OH', 'SPA-1432 OH', 'SPA-1432 OH 皮帶', '條', '泰國', 68.0000, 74.0000, 'A', '2023-08-09'),
('5M-1125*15M/M', '5M-1125*15M/M', '皮帶 5M系列', '條', '台灣', 0.0000, 0.0000, 'A', '2024-08-26'),
('P5V-1250 OH', 'P5V-1250 OH', 'P5V-1250 OH 工業皮帶', '條', '台灣', 175.0000, 3150.0000, 'A', '1999-03-26');

-- Warehouses
INSERT INTO warehouses (warehouse_id, name, location, status) VALUES
('A', '總倉', '總倉庫', 'A'),
('0000', '虛擬倉庫', '虛擬庫存', 'A');

-- Chart of Accounts
INSERT INTO chart_of_accounts (account_id, account_code, name, name_en, account_type, balance_type, subclass_id, is_active) VALUES
('1', '0001', '應收帳款', 'Accounts Receivable', 'asset', 'D', '11', TRUE),
('2', '0002', '應收票據', 'Notes Receivable', 'asset', 'D', '11', TRUE),
('3', '1110', '零用金', 'Petty Cash', 'asset', 'D', '11', TRUE),
('4', '1111', '現金', 'Cash', 'asset', 'D', '11', TRUE),
('5', '1112', '銀行存款', 'Cash in Banks', 'asset', 'D', '11', TRUE),
('6', '1113', '銀行存款-台灣銀行', 'Bank of Taiwan', 'asset', 'D', '11', TRUE);

-- Banks
INSERT INTO banks (bank_id, bank_code, bank_name, branch_name, is_active) VALUES
('0040037', '004', '臺灣銀行', '營業部', TRUE),
('0040048', '004', '臺灣銀行', '發行部', TRUE),
('0040059', '004', '臺灣銀行', '公庫部', TRUE),
('0040071', '004', '臺灣銀行', '館前分行', TRUE),
('0040082', '004', '臺灣銀行', '信託部', TRUE);

-- Sales Order Sample
INSERT INTO sales_orders (order_id, order_number, order_date, party_id, party_name, party_address, contact_phone, subtotal, tax_amount, total_amount, order_status, created_at) VALUES
('1', '1130826001', '2024-08-26', '1143', '恆峰', '台北市大同區迪化街二段191巷9號1樓', '02-25918322', 10171.43, 508.57, 10680.00, '1', '2024-08-23'),
('2', '1130108017', '2024-01-08', '2308', '吉科', '台中市大里區爽文路859巷8號', '0933553963', 400.00, 20.00, 420.00, '1', '2024-01-08'),
('3', '1130827003', '2024-08-27', '2514', '順順', '彰化市崙平南路201號', '047513388', 668.57, 33.43, 702.00, '1', '2024-08-27');

-- Sales Order Line Sample
INSERT INTO sales_order_lines (order_id, line_number, product_id, product_name, unit, quantity, unit_price, tax_percent, tax_amount) VALUES
('1', 1, 'P5V-1250 OH', 'P5V-1250 OH', '條', 3.0000, 175.0000, 5.00, 26.25),
('1', 2, 'PA050', '三角皮帶 A-50', '條', 1.0000, 72.5000, 5.00, 3.63),
('2', 1, 'VB048', '三角皮帶 VB-48', '條', 10.0000, 40.0000, 5.00, 20.00),
('3', 1, 'XPB-2410-P', 'XPB-2410 進口', '條', 2.0000, 334.2850, 5.00, 16.71);

-- Purchase Order Sample
INSERT INTO purchase_orders (order_id, order_number, order_date, party_id, party_name, party_address, contact_phone, subtotal, tax_amount, total_amount, order_status, created_at) VALUES
('P1', '1130827001', '2024-08-27', 'T067', '勝梨', '桃園市中壢區福星三街11號', '03-4614001~3', 1204.76, 60.24, 1265.00, '1', '2024-08-27'),
('P2', '1130826001', '2024-08-26', 'T068', '達基', '台北市內湖區民權東路六段21巷25號', '02-27918100', 328.57, 16.43, 345.00, '1', '2024-08-26');

-- Purchase Order Line Sample
INSERT INTO purchase_order_lines (order_id, line_number, product_id, product_name, unit, quantity, unit_price, tax_percent, tax_amount) VALUES
('P1', 1, 'XPB-2410-P', 'XPB-2410 進口', '條', 3.0000, 395.0000, 5.00, 59.29),
('P1', 2, '0013', '郵寄運費', '回', 1.0000, 80.0000, 0.00, 0.00),
('P2', 1, 'RL581*25M/M', '581L*25M/M', '條', 1.0000, 300.0000, 5.00, 15.00);

-- Inventory Sample
INSERT INTO inventory (product_id, warehouse_id, quantity_on_hand, quantity_reserved, unit_cost) VALUES
('VB048', 'A', 8.0000, 0.0000, 8.0000),
('C-240', 'A', 288.0000, 0.0000, 288.0000),
('M-59', 'A', 19.5000, 0.0000, 19.5000),
('XPB-2410-P', 'A', 0.0000, 0.0000, 395.0000),
('P5V-1250 OH', 'A', 175.0000, 0.0000, 175.0000);
