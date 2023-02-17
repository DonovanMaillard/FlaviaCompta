-- Ajout des justificatifs pour les masses salariales
ALTER TABLE comptasso.t_payrolls ADD COLUMN uploaded_file varchar(255);

DROP VIEW comptasso.v_payrolls;

CREATE OR REPLACE VIEW comptasso.v_payrolls AS (
  SELECT
    p.id_payroll,
    p.id_member,
    m.member_name,
    p.date_min_period,
    p.date_max_period,
    p.gross_remuneration,
    p.gross_premium,
    p.employer_charge_amount,
    p.gross_remuneration+p.gross_premium+p.employer_charge_amount as total_amount, 
    p.worked_days, 
    p.uploaded_file
  FROM comptasso.t_payrolls p
  JOIN comptasso.t_members m ON p.id_member=m.id_member
  ORDER BY p.date_min_period
);

-- Ajout d'une rubrique pour les documents
CREATE TABLE comptasso.dict_document_type (
	id_type serial PRIMARY KEY,
	label varchar(50),
	description text
);

INSERT INTO comptasso.dict_document_type (label, description)
VALUES 
('Modèles et fichiers types','Modèles, fichiers de saisie des congés, justificatifs type de frais kilométriques etc'), 
('Extraits de comptes','Extraits de comptes mensuels édités par la banque'),
('Autres documents bancaires','Contrats bancaires, RIB, procurations etc'),
('Bilans annuels validés','Bilans comptables et Rapports d''activités validés en AG'),
('Divers','Contrats de travail, attestations, status, et autres documents divers à archiver')
;

CREATE TABLE comptasso.t_documents (
	id_document serial PRIMARY KEY,
	title varchar(255) NOT NULL,
	description text,
	id_type integer NOT NULL,
	uploaded_file varchar(255) NOT NULL,
	meta_id_digitiser integer,
	meta_create_date timestamp WITHOUT time ZONE,
	meta_update_date timestamp WITHOUT time ZONE
);

-- Clé étrangère et triggers pour le type de document
CREATE TRIGGER tri_meta_dates_change_t_documents 
BEFORE INSERT OR UPDATE ON comptasso.t_documents 
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();

ALTER TABLE comptasso.t_documents
ADD CONSTRAINT fk_t_documents_id_type FOREIGN KEY (id_type) 
REFERENCES comptasso.dict_document_type(id_type) ON UPDATE CASCADE;

ALTER TABLE comptasso.t_documents
ADD CONSTRAINT fk_t_documents_id_digitiser FOREIGN KEY (meta_id_digitiser) 
REFERENCES comptasso.t_users(id_user) ON UPDATE CASCADE;

-- Vue des documents
CREATE OR REPLACE VIEW comptasso.v_documents AS (
	SELECT 
		d.id_document,
		d.title,
		d.description,
		dt.label AS type,
		d.uploaded_file,
		u.firstname||' '||u.name AS digitiser,
		d.meta_create_date,
		d.meta_update_date
	FROM comptasso.t_documents d
	LEFT JOIN comptasso.dict_document_type dt ON d.id_type=dt.id_type
	LEFT JOIN comptasso.t_users u ON u.id_user = d.meta_id_digitiser
);


-- Fix foreing keys on cor_payroll_budget
ALTER TABLE comptasso.cor_payroll_budget
ADD CONSTRAINT fk_t_budgets_id_budget FOREIGN KEY (id_budget) 
REFERENCES comptasso.t_budgets(id_budget) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE comptasso.cor_payroll_budget
ADD CONSTRAINT fk_t_payrolls_id_payroll FOREIGN KEY (id_payroll) 
REFERENCES comptasso.t_payrolls(id_payroll) ON UPDATE CASCADE ON DELETE CASCADE;

-- Count operations for each account or budget to disable delete buttons
DROP VIEW comptasso.v_budgets; 

CREATE OR REPLACE VIEW comptasso.v_budgets
AS SELECT b.id_budget,
    b.name,
    b.reference,
    f.id_funder,
    f.name AS funder,
    bt.label AS type_budget,
    a.label AS activity,
    COALESCE(b.date_max_expenditure::text, '-'::text) AS date_max_expenditure,
    COALESCE(b.date_return::text, '-'::text) AS date_return,
    COALESCE(b.budget_amount, 0::numeric)::numeric(8,2) AS budget_amount,
    COALESCE(b.payroll_limit, 0::numeric)::numeric(8,2) AS payroll_limit,
    COALESCE(b.indirect_charges, 0::numeric)::numeric(8,2) AS indirect_charges,
    COALESCE(b.indirect_charges / 100::numeric * b.payroll_limit, 0::numeric)::numeric(8,2) AS indirect_charges_amount,
    b.comment,
    b.active,
    comptasso.get_sum_movement(b.id_budget, 'Recette'::text) AS received_amount,
    (comptasso.get_sum_movement(b.id_budget, 'Recette'::text) / b.budget_amount * 100::numeric)::numeric(8,2) AS percent_received,
    comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) AS spent_amount,
    (comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) / b.budget_amount * 100::numeric)::numeric(8,2) AS percent_spent,
    comptasso.get_sum_movement(b.id_budget, 'Engagement'::text) AS committed_amount,
    (comptasso.get_sum_movement(b.id_budget, 'Engagement'::text) / b.budget_amount * 100::numeric)::numeric(8,2) AS percent_committed,
    b.budget_amount - (comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) + comptasso.get_sum_movement(b.id_budget, 'Engagement'::text)) AS available_amount,
    COALESCE(max(op.effective_date)::text, '-'::text) AS last_operation,
    COALESCE(max(cab.date_action)::text, '-'::text) AS last_action_date,
    count(op.*) AS nb_operations
   FROM comptasso.t_budgets b
   	 LEFT JOIN comptasso.t_activities a ON b.id_activity = a.id_activity
     LEFT JOIN comptasso.dict_budget_types bt ON b.id_type_budget = bt.id_type_budget
     LEFT JOIN comptasso.t_funders f ON f.id_funder = b.id_funder
     LEFT JOIN comptasso.t_operations op ON op.id_budget = b.id_budget
     LEFT JOIN comptasso.cor_action_budget cab ON cab.id_budget = b.id_budget
  GROUP BY b.id_budget, b.name, b.reference, f.id_funder, f.name, bt.label, a.label, b.date_max_expenditure, b.date_return, b.budget_amount, b.payroll_limit, b.indirect_charges, b.comment, b.active, (comptasso.get_sum_movement(b.id_budget, 'Recette'::text)), ((comptasso.get_sum_movement(b.id_budget, 'Recette'::text) / b.budget_amount * 100::numeric)::numeric(8,2)), (comptasso.get_sum_movement(b.id_budget, 'Dépense'::text)), ((comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) / b.budget_amount * 100::numeric)::numeric(8,2)), (comptasso.get_sum_movement(b.id_budget, 'Engagement'::text)), ((comptasso.get_sum_movement(b.id_budget, 'Engagement'::text) / b.budget_amount * 100::numeric)::numeric(8,2)), (b.budget_amount - (comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) + comptasso.get_sum_movement(b.id_budget, 'Engagement'::text)))
  ORDER BY b.active DESC, b.name;

DROP VIEW comptasso.v_accounts;

CREATE OR REPLACE VIEW comptasso.v_accounts AS (
  SELECT 
    ac.id_account, 
    ac.name AS name, 
    ac.account_number AS account_number,
    ac.bank AS bank,
    ac.bank_url AS bank_url,
    ac.iban AS iban, 
    ac.uploaded_file AS uploaded_file,
    ac.is_personnal AS is_personnal,
    ac.meta_create_date AS meta_create_date,
    ac.meta_update_date AS meta_update_date,
    comptasso.get_account_balance(ac.id_account) AS account_balance,
    comptasso.get_account_commitment(ac.id_account) AS account_commitments,
    max(op.effective_date) AS last_operation,
    count(op.*) AS nb_operations,
    ac.active AS active
  FROM comptasso.t_accounts ac
  LEFT JOIN comptasso.t_operations op ON op.id_account=ac.id_account
  GROUP BY ac.id_account, ac.name, ac.account_number, ac.bank, ac.iban, ac.uploaded_file, ac.meta_create_date, ac.meta_update_date, ac.active
  ORDER BY active DESC, name ASC
); 
