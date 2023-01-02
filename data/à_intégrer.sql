CREATE OR REPLACE VIEW comptasso.v_synthese_payroll_by_budget AS (
SELECT DISTINCT
    b.id_budget,
    b.name,
    m.id_member,
    m.member_name,    
    cpb.fixed_cost,
    (SELECT min(date_min_period) FROM comptasso.get_payrolls(m.id_member, b.id_budget)) AS date_min_period,
    (SELECT max(date_max_period) FROM comptasso.get_payrolls(m.id_member, b.id_budget)) AS date_max_period,
    (SELECT sum(total_gross_remuneration)::numeric(8,2) FROM comptasso.get_payrolls(m.id_member, b.id_budget)) AS gross_remuneration_on_period,
    (SELECT sum(employer_charge_amount)::numeric(8,2) FROM comptasso.get_payrolls(m.id_member, b.id_budget)) AS employer_charge_amount_on_period,
    (SELECT sum(worked_days)::numeric(8,2) FROM comptasso.get_payrolls(m.id_member, b.id_budget)) AS total_worked_days_on_period,
    sum(cpb.nb_days_allocated)::numeric(8,2) AS allocated_days,
    CASE 
		WHEN cpb.fixed_cost IS NULL THEN (SELECT (sum(total_gross_remuneration)+sum(employer_charge_amount))/sum(worked_days) FROM comptasso.get_payrolls(m.id_member, b.id_budget)) * sum(cpb.nb_days_allocated)
		ELSE sum(cpb.nb_days_allocated*cpb.fixed_cost)::numeric(8,2)
    END AS work_valuation
  FROM comptasso.cor_payroll_budget cpb
  JOIN comptasso.t_payrolls p ON cpb.id_payroll=p.id_payroll
  LEFT JOIN comptasso.t_members m ON p.id_member=m.id_member
  LEFT JOIN comptasso.t_budgets b ON b.id_budget=cpb.id_budget
  GROUP BY 1,2,3,4,5
  );
 
 
 -- Tests
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
	  WHERE p.date_min_period<my_period.date_max_period
  	  AND p.date_max_period>my_period.date_min_period;
  END;
$$;