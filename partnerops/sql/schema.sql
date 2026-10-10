-- PartnerOps schema. Duplicates allowed at the table level (deduped in KPIs).
CREATE TABLE partners(id TEXT PRIMARY KEY, name TEXT, tier TEXT, region TEXT);
CREATE TABLE deals(id SERIAL PRIMARY KEY, ext_id TEXT, partner_id TEXT REFERENCES partners(id),
                   stage TEXT, amount_eur INT, created DATE);
CREATE TABLE enablement(partner_id TEXT REFERENCES partners(id), module TEXT, done BOOL,
                        PRIMARY KEY (partner_id, module));
