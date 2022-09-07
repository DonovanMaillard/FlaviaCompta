INSERT INTO comptasso.t_accounts()-- Accounts


INSERT INTO -- Personnal accounts


INSERT INTO comptasso.t_funders (name, code, logo_url,address, city, zip_code, comment, active, meta_create_date)
VALUES
('DREAL Auvergne-Rhône-Alpes','DREAL AURA','http://www.auvergne-rhone-alpes.developpement-durable.gouv.fr/plugins/internet_multicolor/_images/mariannes/ara.svg','7 rue Léo Lagrange','Clermont-Ferrand Cedex 1','63033','',true,now()),
('Région Auvergne-Rhône-Alpes','Région AURA','https://www.auvergnerhonealpes.fr/cms_viewFile.php?idtf=7479&path=Logo-Region-Gris-pastille-Bleue-PNG-RVB.png','1 esplanade François Mitterrand
CS 20033','Lyon Cedex 2','69269','',true,now());


INSERT INTO comptasso.t_members (member_name, member_role, is_employed, meta_create_date)
VALUES
('Grégory Guicherd','Président',false,now()),
('Philippe Bordet','Trésorier',false,now()),
('Philippe Francoz','Administrateur',false,now()),
('Pascal Dupont','Secrétaire',false,now()),
('Yann Baillet','Chargé de mission',true,now()),
('Donovan Maillard','Chargé de mission',true,now());


INSERT INTO -- Lignes budgétaires


