-- Hand-calculated fixture seed (see SPEC.md for expectations).
INSERT INTO partners VALUES
 ('P1','Acme','gold','EU'), ('P2','Beta','silver','EU'), ('P3','Gamma','bronze','US');
INSERT INTO deals(ext_id, partner_id, stage, amount_eur, created) VALUES
 ('D01','P1','won',10000,'2026-07-01'),
 ('D02','P1','won',20000,'2026-07-05'),
 ('D03','P1','lost',15000,'2026-07-06'),
 ('D04','P2','won',5000,'2026-07-10'),
 ('D05','P2','open',8000,'2026-08-01'),
 ('D06','P3','lost',4000,'2026-07-12'),
 ('D07','P3','won',NULL,'2026-08-02'),
 ('D01','P1','won',10000,'2026-08-03'),
 ('D09','P2','won',500000,'2026-08-04'),
 ('D10','P3',NULL,3000,'2026-08-05'),
 ('D11','P1','open',NULL,'2026-08-06');
INSERT INTO enablement VALUES
 ('P1','M1',true), ('P1','M2',true),
 ('P2','M1',true), ('P2','M2',false),
 ('P3','M1',false);
