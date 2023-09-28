DROP VIEW IF EXISTS comptasso.v_result_by_year;

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


DROP TABLE IF EXISTS comptasso.dict_kilometric_scale;