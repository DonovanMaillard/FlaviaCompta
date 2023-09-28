DROP SCHEMA IF EXISTS comptasso;
CREATE SCHEMA comptasso;

-- TABLES DE DICTIONNAIRES 

CREATE TABLE comptasso.dict_budget_types (
	id_type_budget serial PRIMARY KEY,
	label varchar(50),
	description varchar(255)
); --OK, alimenté

CREATE TABLE comptasso.dict_budget_action_types (
	id_budget_action_types serial PRIMARY KEY,
	label varchar(50),
	description varchar(255)
); --OK, alimenté

-- PAYMENT_METHODS
CREATE TABLE comptasso.dict_payment_methods (
	id_payment_method serial PRIMARY KEY,
	label varchar(50) NOT NULL,
	description varchar(255)
); -- OK alimenté

-- OPERATION_TYPES
CREATE TABLE comptasso.dict_operation_types (
	id_type_operation serial PRIMARY KEY,
	label varchar(50),
	description varchar(255),
	operator varchar(1)
); --OK alimenté

CREATE TABLE comptasso.dict_categories (
	id_category serial PRIMARY KEY,
	cd_category integer,
	label varchar(255) NOT NULL,
	detail varchar(255),
	level integer,
	cd_broader integer,
	id_type_operation integer,
	seizable boolean
);

-- 
-- TABLES DE DONNEES DYNAMIQUES

CREATE TABLE comptasso.t_funders (
	id_funder serial PRIMARY KEY,
	name varchar(50) NOT NULL,
	code varchar(10),
	logo_url varchar(255),
	address varchar(255),
	city varchar(255),
	zip_code integer,
	comment TEXT,
	active boolean,
	meta_create_date timestamp WITHOUT time ZONE,
	meta_update_date timestamp WITHOUT time ZONE 
); --OK

CREATE TABLE comptasso.t_members (
	id_member serial PRIMARY KEY,
	member_name varchar(50),
	member_role varchar(50),
	is_employed boolean,
	active boolean DEFAULT true,
	meta_create_date timestamp WITHOUT time ZONE,
	meta_update_date timestamp WITHOUT time ZONE 
);

CREATE TABLE comptasso.t_budgets (
	id_budget serial PRIMARY KEY,
	name varchar(50) NOT NULL,
	reference varchar(50),
	id_funder integer,
	id_type_budget integer,
	date_max_expenditure date, -- Date maximale d'éligibilité des dépenses
	date_return date, -- Date de rendu (bilans comptables, rapports et autres documents administratifs liés au budget)
	budget_amount numeric(8,2),
	payroll_limit numeric(8,2), -- Masse salariale maximale
	indirect_charges numeric(8,2), -- Charges indirectes(%)
	comment text,
	allowed_fixed_cost boolean,
	active boolean,
	meta_create_date timestamp WITHOUT time ZONE,
	meta_update_date timestamp WITHOUT time ZONE
); --OK

CREATE TABLE comptasso.t_accounts (
	id_account serial PRIMARY KEY,
	name varchar(50) NOT NULL,
	account_number bigint,
	bank varchar(50),
	bank_url varchar(255),
	iban varchar(50), 
	uploaded_file varchar(255),
	is_personnal boolean DEFAULT False,
	active boolean DEFAULT True,
	meta_create_date timestamp WITHOUT time ZONE,
	meta_update_date timestamp WITHOUT time ZONE
);--OK 

CREATE TABLE comptasso.t_operations (
	id_operation serial PRIMARY KEY,
	id_grp_operation uuid,
	name varchar(50) NOT NULL,
	detail_operation varchar(255),
	id_type_operation integer,
	operation_date date,
	effective_date date,
	amount numeric(8,2) NOT NULL, -- Les débits sont stockés avec un nombre négatif, les crédits avec un nombre positif
	id_payment_method integer,
	id_account integer NOT NULL,
	id_budget integer,
	id_category integer NOT NULL,
	uploaded_file varchar(255),
	pointed boolean DEFAULT false,
	meta_id_digitiser integer,
	meta_create_date timestamp WITHOUT time ZONE,
	meta_update_date timestamp WITHOUT time ZONE
);

CREATE TABLE comptasso.t_payrolls (
	id_payroll serial PRIMARY KEY,
	id_member integer NOT NULL,
	date_min_period date NOT NULL,
	date_max_period date NOT NULL,
	gross_remuneration numeric(8,2) NOT NULL,
	gross_premium numeric(8,2) NOT NULL,
	employer_charge_amount numeric(8,2) NOT NULL,
	worked_days numeric(8,2) NOT NULL,
	uploaded_file varchar(255),
	meta_create_date timestamp WITHOUT time ZONE,
	meta_update_date timestamp WITHOUT time ZONE
);


CREATE TABLE comptasso.t_volunteerings(
	id_volunteering serial PRIMARY KEY,
	date_min_period date NOT NULL,
	date_max_period date NOT NULL,
	id_budget integer,
	id_member integer NOT NULL,
	worked_days numeric(8,2) NOT NULL,
	valuation_cost numeric(8,2) NOT NULL,
	meta_create_date timestamp WITHOUT time ZONE,
	meta_update_date timestamp WITHOUT time ZONE
);

CREATE TABLE comptasso.t_users (
	id_user serial PRIMARY KEY,
	name varchar(100), 
	firstname varchar(100),
	email varchar(100),
	login varchar(50) NOT NULL,
	password varchar(255) NOT NULL,
	is_active boolean DEFAULT FALSE,
	meta_create_date timestamp WITHOUT time ZONE,
	meta_update_date timestamp WITHOUT time ZONE
);

CREATE TABLE comptasso.login_history (
	id_session serial PRIMARY KEY,
	id_user integer NOT NULL,
	login_time timestamp without time zone NOT NULL DEFAULT now()
);

CREATE TABLE comptasso.t_activities (
	id_activity serial primary key,
	label varchar(255) NOT NULL,
	description text,
	active boolean
);

--
-- CORRESPONDANCES
CREATE TABLE comptasso.cor_action_budget (
	id_action_budget serial PRIMARY KEY,
	id_budget_action_types integer NOT NULL,
	id_budget integer NOT NULL,
	date_action date NOT NULL,
	description_action varchar(255),
	uploaded_file varchar(255),
	meta_create_date timestamp WITHOUT time ZONE,
	meta_update_date timestamp WITHOUT time ZONE
);

CREATE TABLE comptasso.cor_payroll_budget (
	id_payroll_budget serial PRIMARY KEY,
	id_payroll integer NOT NULL,
	id_budget integer,
	nb_days_allocated numeric(8,2) NOT NULL,
	fixed_cost numeric(8,2),
	meta_create_date timestamp WITHOUT time ZONE,
	meta_update_date timestamp WITHOUT time ZONE
);



--
-- FONCTIONS & FONCTIONS TRIGGERS
CREATE OR REPLACE FUNCTION comptasso.get_sum_movement(cur_id_budget integer, cur_operation_type text)
RETURNS numeric(8,2)
LANGUAGE plpgsql IMMUTABLE
    AS $$
-- Fonction permettant de connaitre la somme des mouvements d'un type donné pour un budget donné
  DECLARE 
   result numeric(8,2);
  BEGIN
   SELECT INTO result COALESCE(ABS(sum(amount)), 0) 
   FROM comptasso.t_operations op
   JOIN comptasso.dict_operation_types dot ON op.id_type_operation=dot.id_type_operation
   WHERE id_budget=cur_id_budget 
   AND dot.label=cur_operation_type;
   RETURN result;
  END;
$$;


CREATE OR REPLACE FUNCTION comptasso.get_account_balance(cur_id_account integer)
RETURNS numeric(8,2)
LANGUAGE plpgsql IMMUTABLE
    AS $$
-- Fonction permettant de connaitre le solde d'un compte donné
  DECLARE 
   balance numeric(8,2);
  BEGIN
   SELECT INTO balance sum(amount) 
   FROM comptasso.t_operations op
   JOIN comptasso.dict_operation_types dot ON op.id_type_operation=dot.id_type_operation
   WHERE id_account=cur_id_account 
   AND dot.label!='Engagement';
   RETURN balance;
  END;
$$;


CREATE OR REPLACE FUNCTION comptasso.get_account_commitment(cur_id_account integer)
RETURNS numeric(8,2)
LANGUAGE plpgsql IMMUTABLE
    AS $$
-- Fonction permettant de connaitre les engagements pour un compte donné
  DECLARE 
   balance numeric(8,2);
  BEGIN
   SELECT INTO balance sum(amount) 
   FROM comptasso.t_operations op
   JOIN comptasso.dict_operation_types dot ON op.id_type_operation=dot.id_type_operation
   WHERE id_account=cur_id_account 
   AND dot.label='Engagement';
   RETURN balance;
  END;
$$;



-- Fonction trigger calculant les meta_create_date et meta_update_date
CREATE OR REPLACE FUNCTION public.fct_trg_meta_dates_change()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
begin
        if(TG_OP = 'INSERT') THEN
                NEW.meta_create_date = NOW();
        ELSIF(TG_OP = 'UPDATE') THEN
                NEW.meta_update_date = NOW();
                if(NEW.meta_create_date IS NULL) THEN
                        NEW.meta_create_date = NOW();
                END IF;
        end IF;
        return NEW;
end;
$function$
;


CREATE OR REPLACE FUNCTION comptasso.get_payrolls(cur_id_member integer, cur_id_budget integer)
RETURNS TABLE (
  id_payroll integer,
  date_min_period date,
  date_max_period date,
  gross_remuneration numeric(8,2),
  gross_premium numeric(8,2),
  total_gross_remuneration numeric(8,2),
  employer_charge_amount numeric(8,2),
  worked_days numeric(8,2)
  )
LANGUAGE plpgsql IMMUTABLE
    AS $$
-- Fonction permettant de connaitre les engagements pour un compte donné
  BEGIN
    RETURN QUERY 
    WITH my_period AS (
      SELECT 
          min(p.date_min_period) AS date_min_period,
          max(p.date_max_period) AS date_max_period
        FROM comptasso.t_payrolls p
        JOIN comptasso.cor_payroll_budget cpb ON p.id_payroll=cpb.id_payroll
        WHERE p.id_member = cur_id_member 
        AND cpb.id_budget=cur_id_budget)
      SELECT 
        p.id_payroll,
        p.date_min_period,
        p.date_max_period,
        p.gross_remuneration,
        p.gross_premium,
        p.gross_remuneration+p.gross_premium AS total_gross_remuneration,
        p.employer_charge_amount,
      p.worked_days
    FROM comptasso.t_payrolls p
    CROSS JOIN my_period
    WHERE p.date_min_period<=my_period.date_max_period
      AND p.date_max_period>=my_period.date_min_period
      AND p.id_member = cur_id_member 
    ;
  END;
$$;

-- Create triggers on tables with meta_date fields
CREATE TRIGGER tri_meta_dates_change_t_funders
BEFORE INSERT OR UPDATE ON comptasso.t_funders 
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();

CREATE TRIGGER tri_meta_dates_change_t_members 
BEFORE INSERT OR UPDATE ON comptasso.t_members
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();

CREATE TRIGGER tri_meta_dates_change_t_budgets 
BEFORE INSERT OR UPDATE ON comptasso.t_budgets
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();

CREATE TRIGGER tri_meta_dates_change_t_accounts 
BEFORE INSERT OR UPDATE ON comptasso.t_accounts 
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();

CREATE TRIGGER tri_meta_dates_change_t_operations 
BEFORE INSERT OR UPDATE ON comptasso.t_operations 
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();

CREATE TRIGGER tri_meta_dates_change_t_users 
BEFORE INSERT OR UPDATE ON comptasso.t_users 
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();

CREATE TRIGGER tri_meta_dates_change_cor_action_budget 
BEFORE INSERT OR UPDATE ON comptasso.cor_action_budget 
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();

CREATE TRIGGER tri_meta_dates_change_t_payrolls
BEFORE INSERT OR UPDATE ON comptasso.t_payrolls
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();

CREATE TRIGGER tri_meta_dates_change_cor_payroll_budget 
BEFORE INSERT OR UPDATE ON comptasso.cor_payroll_budget 
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();

CREATE TRIGGER tri_meta_dates_change_t_volunteerings
BEFORE INSERT OR UPDATE ON comptasso.t_volunteerings
FOR EACH ROW EXECUTE PROCEDURE fct_trg_meta_dates_change();


--
-- VUES CALCULEES
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
    ac.active AS active
  FROM comptasso.t_accounts ac
  LEFT JOIN comptasso.t_operations op ON op.id_account=ac.id_account
  GROUP BY ac.id_account, ac.name, ac.account_number, ac.bank, ac.iban, ac.uploaded_file, ac.meta_create_date, ac.meta_update_date, ac.active
  ORDER BY active DESC, name ASC
); 


CREATE OR REPLACE VIEW comptasso.v_actions AS (
	SELECT
		cab.id_action_budget,
		cab.id_budget, 
		cab.date_action AS date_action, 
		dbat.label AS type_action, 
		cab.description_action AS description_action,
		cab.uploaded_file AS uploaded_file
	FROM comptasso.cor_action_budget cab
	LEFT JOIN comptasso.dict_budget_action_types dbat ON dbat.id_budget_action_types=cab.id_budget_action_types
	ORDER BY cab.date_action
);


CREATE OR REPLACE VIEW comptasso.v_operations AS (
	SELECT
		op.id_operation AS id_operation,
		op.id_grp_operation AS id_grp_operation,
		op.name AS name_operation,
		op.detail_operation AS detail_operation,
		dot.id_type_operation AS id_type_operation,
		dot.label AS type_operation,
		op.operation_date AS operation_date,
		op.effective_date AS effective_date,
		extract('year' FROM op.effective_date)::integer AS year,
		op.amount AS amount, -- Les débits sont stockés avec un nombre négatif, les crédits avec un nombre positif
		dpm.label AS payment_method,
		op.id_account AS id_account,
		ac.name AS account_name,
		ac.is_personnal AS personnal_account,
		op.id_budget AS id_budget,
		b.name AS budget_name,
		cat.cd_category||'. '||cat.label AS category,
		cat2.cd_category||'. ' ||cat2.label AS parent_category,
		op.uploaded_file AS uploaded_file,
		op.pointed AS pointed,
		op.meta_create_date AS meta_crate_date,
		op.meta_update_date AS meta_update_date
	FROM comptasso.t_operations op
	LEFT JOIN comptasso.dict_operation_types dot ON dot.id_type_operation=op.id_type_operation
	LEFT JOIN comptasso.dict_payment_methods dpm ON dpm.id_payment_method=op.id_payment_method
	LEFT JOIN comptasso.t_accounts ac ON ac.id_account=op.id_account
	LEFT JOIN comptasso.t_budgets b ON b.id_budget=op.id_budget
	LEFT JOIN comptasso.dict_categories cat ON cat.id_category=op.id_category
	LEFT JOIN comptasso.dict_categories cat2 ON cat.cd_broader=cat2.cd_category
	ORDER BY effective_date
);

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

CREATE OR REPLACE VIEW comptasso.v_decode_payroll_budgets AS (
  SELECT 
    cpb.id_payroll_budget AS id_payroll_budget,
    p.id_payroll AS id_payroll,
    cpb.id_budget AS id_budget,
    b.name AS budget_name,
    cpb.nb_days_allocated AS nb_days_allocated,
    cpb.fixed_cost AS fixed_cost
  FROM comptasso.cor_payroll_budget cpb
  LEFT JOIN comptasso.t_payrolls p ON cpb.id_payroll=p.id_payroll
  LEFT JOIN comptasso.t_budgets b ON cpb.id_budget = b.id_budget
);

-- Vue synthèse payroll budget
CREATE OR REPLACE VIEW comptasso.v_synthese_payroll_budget AS(
SELECT
  p.id_member,
  m.member_name,
  cpb.id_budget,
  b.name,
  cpb.fixed_cost,
  (SELECT min(date_min_period) FROM comptasso.get_payrolls(p.id_member,cpb.id_budget)) AS date_min_period,
  (SELECT max(date_max_period) FROM comptasso.get_payrolls(p.id_member,cpb.id_budget)) AS date_max_period,
  (SELECT sum(total_gross_remuneration) FROM comptasso.get_payrolls(p.id_member,cpb.id_budget)) AS total_gross_remuneration,
  (SELECT sum(employer_charge_amount) FROM comptasso.get_payrolls(p.id_member,cpb.id_budget)) AS total_employer_charges,
  (SELECT sum(worked_days) FROM comptasso.get_payrolls(p.id_member,cpb.id_budget)) AS total_work_days,
  sum(cpb.nb_days_allocated) AS allocated_days,
  -- Rémunération brute au réel si pas de cout fixe
  CASE 
    WHEN cpb.fixed_cost IS NULL THEN (SELECT round(sum(total_gross_remuneration)/sum(worked_days),2) FROM comptasso.get_payrolls(p.id_member,cpb.id_budget))*sum(cpb.nb_days_allocated)
    ELSE NULL
  END AS justified_remuneration,
  -- Charges employeurs au réel si pas de cout fixe
  CASE 
    WHEN cpb.fixed_cost IS NULL THEN (SELECT round(sum(employer_charge_amount)/sum(worked_days),2) FROM comptasso.get_payrolls(p.id_member,cpb.id_budget))*sum(cpb.nb_days_allocated)
    ELSE NULL
  END AS justified_charges,
  -- Cout fixe appliqué
  CASE 
    WHEN cpb.fixed_cost IS NOT NULL THEN (cpb.fixed_cost*sum(cpb.nb_days_allocated))
    ELSE NULL
  END AS justified_fixed_cost,
  -- Masse salariale globale décomptée
  CASE 
    -- Si au réel, somme des charges et de la rémunération brute
    WHEN cpb.fixed_cost IS NULL THEN (SELECT round(sum(employer_charge_amount)/sum(worked_days),2) FROM comptasso.get_payrolls(p.id_member,cpb.id_budget))*sum(cpb.nb_days_allocated)+(SELECT round(sum(total_gross_remuneration)/sum(worked_days),2) FROM comptasso.get_payrolls(p.id_member,cpb.id_budget))*sum(cpb.nb_days_allocated)
    -- Cout forfaitaire si appliqué
    ELSE (cpb.fixed_cost*sum(cpb.nb_days_allocated))
  END AS justified_payroll
FROM comptasso.cor_payroll_budget cpb
JOIN comptasso.t_payrolls p ON cpb.id_payroll=p.id_payroll 
JOIN comptasso.t_budgets b ON b.id_budget=cpb.id_budget
JOIN comptasso.t_members m ON m.id_member=p.id_member
GROUP BY 1,2,3,4,5)
;


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
    COALESCE(max(cab.date_action)::text, '-'::text) AS last_action_date
   FROM comptasso.t_budgets b
   	 LEFT JOIN comptasso.t_activities a ON b.id_activity = a.id_activity
     LEFT JOIN comptasso.dict_budget_types bt ON b.id_type_budget = bt.id_type_budget
     LEFT JOIN comptasso.t_funders f ON f.id_funder = b.id_funder
     LEFT JOIN comptasso.t_operations op ON op.id_budget = b.id_budget
     LEFT JOIN comptasso.cor_action_budget cab ON cab.id_budget = b.id_budget
  GROUP BY b.id_budget, b.name, b.reference, f.id_funder, f.name, bt.label, a.label, b.date_max_expenditure, b.date_return, b.budget_amount, b.payroll_limit, b.indirect_charges, b.comment, b.active, (comptasso.get_sum_movement(b.id_budget, 'Recette'::text)), ((comptasso.get_sum_movement(b.id_budget, 'Recette'::text) / b.budget_amount * 100::numeric)::numeric(8,2)), (comptasso.get_sum_movement(b.id_budget, 'Dépense'::text)), ((comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) / b.budget_amount * 100::numeric)::numeric(8,2)), (comptasso.get_sum_movement(b.id_budget, 'Engagement'::text)), ((comptasso.get_sum_movement(b.id_budget, 'Engagement'::text) / b.budget_amount * 100::numeric)::numeric(8,2)), (b.budget_amount - (comptasso.get_sum_movement(b.id_budget, 'Dépense'::text) + comptasso.get_sum_movement(b.id_budget, 'Engagement'::text)))
  ORDER BY b.active DESC, b.name;


CREATE VIEW comptasso.v_synthese_activities AS (
SELECT 
	a.id_activity,
	a.label,
	a.description,
	a.active,
	sum(COALESCE(b.budget_amount, 0::numeric)::numeric(8,2) - comptasso.get_sum_movement(b.id_budget, 'Recette'::text)) AS to_receive, -- to receive amount
	sum(COALESCE(b.budget_amount, 0::numeric)::numeric(8,2)) AS global_amount, -- total amounts
	b1.count AS active_budgets,
	b2.count AS inactive_budgets,
FROM comptasso.t_activities a
LEFT JOIN comptasso.t_budgets b ON b.id_activity=a.id_activity
LEFT JOIN LATERAL ( SELECT count(*)
            FROM comptasso.t_budgets
            WHERE active
            GROUP BY id_activity) b1 ON b1.id_activity=a.id_activity
LEFT JOIN LATERAL ( SELECT count(*)
            FROM comptasso.t_budgets
            WHERE NOT active
            GROUP BY id_activity) b2 ON b1.id_activity=a.id_activity
GROUP BY a.id_activity, a.label, a.description, a.active
);


CREATE VIEW comptasso.v_result_by_year AS (
WITH years AS (
	SELECT generate_series(min(EXTRACT('year' FROM op.effective_date))::integer,max(EXTRACT('year' FROM op.effective_date))::integer) AS year
	FROM comptasso.t_operations op
),
details AS (
	SELECT DISTINCT 
	y.YEAR,
	typ.LABEL AS type_category,
	cat.LEVEL AS level,
	cat.cd_category::TEXT AS cd_category,
	cat.cd_category||'. '||cat.LABEL AS label,
	cat.cd_broader,
	sum(op.amount) AS sum,
	jsonb_build_object('category',cat.cd_category||'. '||cat.LABEL,'result',sum(op.amount)) AS json
FROM comptasso.dict_categories cat
JOIN comptasso.dict_operation_types typ ON cat.id_type_operation = typ.id_type_operation
CROSS JOIN years y
LEFT JOIN LATERAL (
	SELECT * 
	FROM comptasso.t_operations op
	JOIN comptasso.dict_operation_types typ ON op.id_type_operation = typ.id_type_operation 
	WHERE EXTRACT('year' FROM op.effective_date)::integer=y.YEAR::integer
	AND op.id_category = cat.id_category 
	) op ON TRUE
WHERE typ.LABEL IN ('Recette','Dépense')
GROUP BY 1,2,3,4,5,6
ORDER BY 1,2,4,5
)
SELECT DISTINCT 
	d.YEAR AS year,
	d.type_category AS type_category,
	d.cd_category AS cd_category,
	d.LABEL AS label,
	jsonb_agg(child.json) AS json,
	COALESCE(sum(child.sum),0) AS amount
FROM details d
JOIN details child ON d.cd_category::text=child.cd_broader::text
WHERE d.LEVEL=1 AND child.YEAR=d.year
GROUP BY 1,2,3,4
);


-----------------------------------
--- CONTRAINTES ET FOREIGN KEYS ---
-----------------------------------

ALTER TABLE comptasso.dict_categories 
ADD CONSTRAINT fk_dict_categories_id_type_operation FOREIGN KEY (id_type_operation) 
REFERENCES comptasso.dict_operation_types(id_type_operation) ON UPDATE CASCADE;

ALTER TABLE comptasso.dict_categories
ADD CONSTRAINT dict_categories_unique_cd_category UNIQUE (cd_category);

-- t_budgets
ALTER TABLE comptasso.t_budgets
ADD CONSTRAINT fk_t_budgets_id_funder FOREIGN KEY (id_funder) 
REFERENCES comptasso.t_funders(id_funder) ON UPDATE CASCADE;

ALTER TABLE comptasso.t_budgets
ADD CONSTRAINT fk_t_budgets_id_type_budget FOREIGN KEY (id_type_budget) 
REFERENCES comptasso.dict_budget_types(id_type_budget) ON UPDATE CASCADE;

-- t_operations
ALTER TABLE comptasso.t_operations
ADD CONSTRAINT fk_t_operations_id_account FOREIGN KEY (id_account) 
REFERENCES comptasso.t_accounts(id_account) ON UPDATE CASCADE;

ALTER TABLE comptasso.t_operations
ADD CONSTRAINT fk_t_operations_id_type_operation FOREIGN KEY (id_type_operation) 
REFERENCES comptasso.dict_operation_types(id_type_operation) ON UPDATE CASCADE;

ALTER TABLE comptasso.t_operations
ADD CONSTRAINT fk_t_operations_id_payment_method FOREIGN KEY (id_payment_method) 
REFERENCES comptasso.dict_payment_methods(id_payment_method) ON UPDATE CASCADE;

ALTER TABLE comptasso.t_operations
ADD CONSTRAINT fk_t_operations_id_budget FOREIGN KEY (id_budget) 
REFERENCES comptasso.t_budgets(id_budget) ON UPDATE CASCADE;

ALTER TABLE comptasso.t_operations
ADD CONSTRAINT fk_t_operations_id_category FOREIGN KEY (id_category) 
REFERENCES comptasso.dict_categories(id_category) ON UPDATE CASCADE;

ALTER TABLE comptasso.t_budgets
ADD CONSTRAINT fk_t_budgets_id_activity FOREIGN KEY (id_activity) 
REFERENCES comptasso.t_activities(id_activity) ON UPDATE CASCADE;

-- cor_action_budget
ALTER TABLE comptasso.cor_action_budget
ADD CONSTRAINT fk_cor_action_budget_id_action_type FOREIGN KEY (id_budget_action_types) 
REFERENCES comptasso.dict_budget_action_types(id_budget_action_types) ON UPDATE CASCADE;

ALTER TABLE comptasso.cor_action_budget
ADD CONSTRAINT fk_cor_action_budget_id_budget FOREIGN KEY (id_budget) 
REFERENCES comptasso.t_budgets(id_budget) ON UPDATE CASCADE ON DELETE CASCADE;

-- t_work_value
ALTER TABLE comptasso.t_work_value
ADD CONSTRAINT fk_t_work_value_id_member FOREIGN KEY (id_member) 
REFERENCES comptasso.t_members(id_member) ON UPDATE CASCADE;

-- cor_work_budget
ALTER TABLE comptasso.cor_work_budget
ADD CONSTRAINT fk_cor_work_budget_id_budget FOREIGN KEY (id_budget) 
REFERENCES comptasso.t_budgets(id_budget) ON UPDATE CASCADE;

ALTER TABLE comptasso.cor_work_budget
ADD CONSTRAINT fk_cor_work_budget_id_member FOREIGN KEY (id_member) 
REFERENCES comptasso.t_members(id_member) ON UPDATE CASCADE;

-- Avoid operations with amount of 0
ALTER TABLE comptasso.t_operations 
ADD CONSTRAINT t_operations_amount_is_not_zero CHECK (amount != 0);

-- Add unique constraint on login
ALTER TABLE comptasso.t_users
ADD CONSTRAINT unique_t_users_login UNIQUE (login);

-- Add foreign key on id_user
ALTER TABLE comptasso.login_history
ADD CONSTRAINT fk_login_history_id_user FOREIGN KEY (id_user) 
REFERENCES comptasso.t_users(id_user) ON UPDATE CASCADE;


