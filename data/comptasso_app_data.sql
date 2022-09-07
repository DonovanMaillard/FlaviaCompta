-- Insert budget types
INSERT INTO comptasso.dict_budget_types (label, description)
VALUES ('Subvention', 'Budget lié à un financement subventionné pour une action précise ou le fonctionnement de l''association'),
('Commandes / prestations', 'Budget lié aux activités de prestations de services et autres commandes'),
('Autre : adhésions, fonctionnement général etc', 'Budget de toute autre nature : dons, adhésions, fonctionnement général de l''association...');


-- Insert type d'actions sur les budgets
INSERT INTO comptasso.dict_budget_action_types (label, description)
VALUES ('Demande / Devis','Action relative à la demande/la plannification d''un budget'),
('Attribution / Bon de commande','Action validant l''attribution du budget'),
('Demande d''avance ou acompte','Action relative à une demande de versement d''avance ou d''acompte'),
('Demande de solde / Facturation','Action relative à une demande de paiement complet ou de versement du solde du budget'),
('Clôture','Action consistant à clôturer administrativement un budget (reçu, bilan de subvention etc)');


-- Insert operation types
INSERT INTO comptasso.dict_operation_types (label, description, operator)
VALUES ('Dépense', 'Mouvement lié à une sortie d''argent effectuée par l''association', '-'),
('Recette', 'Mouvement lié à une entrée d''argent au bénéfice de l''association', '+'),
('Engagement', 'Réserver une somme en vue d''une dépense planifiée : solde pour une commande avec acomptes ou paiement différé par exemple', ''),
('Transaction interne','Echange de fonds entre les comptes de l''association ne modifiant pas sa trésorerie globale', ''), 
('Remboursement de frais','Remboursement de frais avancés par les personnels dans le cadre de leurs activités salariées ou bénévoles au profit de l''association', ''),
('Valorisation du bénévolat','Contributions bénévoles, dons et mises à disposition en nature valorisés', ''), 
('Solde initial','Solde initial à la création du compte', '+');


-- Payment methods
INSERT INTO comptasso.dict_payment_methods (label, description)
VALUES ('Carte bancaire','Opération effectuée au moyen d''une carte bancaire de l''association'),
('Chèque bancaire','Opération effectuée au moyen d''un chèque bancaire'),
('Virement bancaire','Opération effectuée au moyen d''un virement bancaire'),
('Prélèvement automatique','Opération effectuée au moyen d''un prélèvement automatique sur ordre du débiteur'),
('Dépôt d''espèces','Mouvement correspondant à un dépôt d''espèces (adhésions etc)');

-- Fiscal categories
INSERT INTO comptasso.dict_categories (cd_category, label, detail, level, cd_broader, id_type_operation, seizable)
VALUES 
-- Dépenses
('60','Achats','Achats de biens et services (matériels, services, prestations...)',1,60,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE LABEL='Dépense'),false),
('601','Achats matières et fournitures stockées', 'Matériel stocké : filets à papillons, loupes, pièges, disques durs etc',2,60,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true),
('604','Achats études et prestations de services', 'Études, prestations, sous-traitance...',2,60,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true),
('606','Autres fournitures (fournitures non stockables, consommables...)','Fournitures de bureau, cartouches d''encre, dépenses d''hébergements...',2,60,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true),
('61','Services extérieurs','Dépenses liées aux services indirects utilisés pour le fonctionnement et les projets de l''association : assurances, locations, entretiens et réparations...',1,61,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),false),
('613','Locations immobilières et matérielles','Locations de salles, de véhicules, d''équipements matériels...',2,61,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true),
('615','Entretiens et réparations','Entretiens et réparations des véhicules et matériels de l''association',2,61,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true),
('616','Assurances','Assurances de l''association, de ses membres et équipements',2,61,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true),
('618','Documentations générales et techniques','Achats de documentations, guides, supports de formations...',2,61,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true),
('62','Autres services extérieurs','Dépenses des autres services extérieurs : publications, déplacements, frais bancaires et postaux, télécoms...',1,62,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),false),
('623','Publications, publicités (expositions, catalogues, publications...)','Frais d''infographie, de reprographie, de publication...',2,62,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true),
('625','Déplacements et missions (transport, repas, voyages...)','Frais kilométriques, paniers repas, frais de restauration, billets de transports en commun etc',2,62,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true),
('626','Frais postaux, bancaires & télécommunication','Frais postaux, frais de banque, frais téléphoniques et internet...',2,62,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true),
('63','Impôts, taxes et versements assimilés','Tous impôts et taxes',1,63,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true),
('64','Charges de personnel','Coûts directement associés à l''embauche et le rémunération des salariés',1,64,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),false),
('641','Rémunérations du personnel (salaires, primes, avantages...)','Salaires, primes, avantages',2,64,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),false),
('645','Charges de sécurité sociale et prévoyance','Cotisations sociales, frais de mutuelle etc',2,64,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),false),
('648','Autres charges de personnels (gratifications, indemnités de stage...)','Gratifications et indemnités de stages, services civiques etc',2,64,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true),
-- Recettes
('70','Ventes de prestations de services, produits finis et marchandises','Ventes de matériels, publications, études, animations et autres prestations.',1,70,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Recette'),false),
('706','Ventes de prestations de services','Ventes d''études, animations et autres prestations',2,70,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Recette'),true),
('74','Subventions d''exploitation','Recettes liées à des subventions',1,74,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Recette'),true),
('75','Autres produits de gestion courante','Autres produits : remboursements, avoirs ...',1,75,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Recette'),false),
('756','Cotisations/adhésions','Cotisations et adhésions',2,75,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Recette'),true),
('758','Divers : dons manuels, mécénats','Dons et mécénats',2,75,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Recette'),true),
-- Exploitation du bénévolat
('86','Emploi des contributions volontaires en nature','Emploi des contributions volontaires en nature : prêts de matériels, bénévolat...',1,86,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Valorisation du bénévolat'),false),
('864','Personnel bénévole','Emploi du bénévolat',2,86,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Valorisation du bénévolat'),false),
('861','Mise à disposition gratuite de biens et services','Emploi des biens et services mis à disposition bénévolement',2,86,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Valorisation du bénévolat'),false),
-- Valorisation du bénévolat
('87','Contributions volontaires en nature','Valorisation des contributions volontaires en nature : prêts de matériels, bénévolat...',1,87,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Valorisation du bénévolat'),false),
('870','Bénévolat','Valorisation du bénévolat',2,87,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Valorisation du bénévolat'),true),
('875','Dons en nature','Ensemble des dons en nature : matériels et consommables',2,87,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Valorisation du bénévolat'),true),
-- Transactions internes et catégories créées pour l'outil
('900','Transaction interne','Régules entre comptes : cotisations sociales, avances, trésorerie, transactions entre les comptes et activités',1,900,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Transaction interne'),true),
('910','Remboursement des avances de frais personnels','Remboursement des frais avancés par les personnels salariés ou bénévoles : frais kilométriques, matériels, abonnements...',1,910,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Remboursement de frais'),true),
('920','Masses salariales (rémunérations et charges)','Mouvements de comptes liés aux masses salariales, pouvant mélanger ou couvrir seulement en partie les catégories fiscales dédiées 641 et 645',1,920,(SELECT id_type_operation FROM comptasso.dict_operation_types WHERE label='Dépense'),true);

INSERT INTO comptasso.t_users (name, firstname, login, password, is_active)
VALUES('Test','Administrateur','admin','pbkdf2:sha256:260000$6I0pzswR3g8TQIrL$b0bf9bbec495852f284f13e82e83e9a729ab518d9af864cbc7634264f2465921',TRUE);
