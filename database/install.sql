-- =====================================================
-- BTP Devis Pro - Installation complète
-- =====================================================

USE btp_devis;

-- TABLE UTILISATEUR
CREATE TABLE UTILISATEUR (
    id_user INT PRIMARY KEY AUTO_INCREMENT,
    nom VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    mot_de_passe VARCHAR(255),
    mot_de_passe_hash VARCHAR(255),
    entreprise VARCHAR(150),
    telephone VARCHAR(20)
);

-- TABLE CLIENT
CREATE TABLE CLIENT (
    id_client INT PRIMARY KEY AUTO_INCREMENT,
    nom VARCHAR(100),
    telephone VARCHAR(20),
    email VARCHAR(100),
    adresse TEXT
);

-- TABLE PROJET
CREATE TABLE PROJET (
    id_projet INT PRIMARY KEY AUTO_INCREMENT,
    nom_projet VARCHAR(150),
    description TEXT,
    localisation VARCHAR(150)
);

-- TABLE DEVIS
CREATE TABLE DEVIS (
    id_devis INT PRIMARY KEY AUTO_INCREMENT,
    date_creation DATETIME,
    total DECIMAL(10,2),
    statut VARCHAR(50) DEFAULT 'brouillon',
    id_client INT,
    id_user INT,
    id_projet INT,
    FOREIGN KEY (id_client) REFERENCES CLIENT(id_client),
    FOREIGN KEY (id_user) REFERENCES UTILISATEUR(id_user),
    FOREIGN KEY (id_projet) REFERENCES PROJET(id_projet)
);

-- TABLE LIGNE_DEVIS
CREATE TABLE LIGNE_DEVIS (
    id_ligne INT PRIMARY KEY AUTO_INCREMENT,
    designation VARCHAR(150),
    quantite INT,
    prix_unitaire DECIMAL(10,2),
    total_ligne DECIMAL(10,2),
    id_devis INT,
    FOREIGN KEY (id_devis) REFERENCES DEVIS(id_devis)
);

-- TABLE FACTURE
CREATE TABLE FACTURE (
    id_facture INT PRIMARY KEY AUTO_INCREMENT,
    date_facture DATETIME,
    montant DECIMAL(10,2),
    statut VARCHAR(50) DEFAULT 'non payée',
    id_devis INT UNIQUE,
    FOREIGN KEY (id_devis) REFERENCES DEVIS(id_devis)
);

-- TABLE ABONNEMENTS
CREATE TABLE ABONNEMENTS (
    id_abonnement INT PRIMARY KEY AUTO_INCREMENT,
    id_user INT NOT NULL,
    statut VARCHAR(20) DEFAULT 'actif',
    date_debut DATETIME,
    date_fin DATETIME,
    type_abonnement VARCHAR(50) DEFAULT 'mensuel',
    FOREIGN KEY (id_user) REFERENCES UTILISATEUR(id_user)
);

-- TABLE SETTINGS
CREATE TABLE SETTINGS (
    id_setting INT PRIMARY KEY AUTO_INCREMENT,
    id_user INT NOT NULL,
    company_name VARCHAR(200),
    company_logo VARCHAR(500),
    company_email VARCHAR(100),
    company_phone VARCHAR(50),
    company_address TEXT,
    primary_color VARCHAR(20) DEFAULT '#1E3A8A',
    secondary_color VARCHAR(20) DEFAULT '#7C3AED',
    accent_color VARCHAR(20) DEFAULT '#06B6D4',
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY (id_user) REFERENCES UTILISATEUR(id_user)
);

-- UTILISATEUR ADMIN (mot de passe: admin123)
INSERT INTO UTILISATEUR (id_user, nom, email, mot_de_passe, mot_de_passe_hash, entreprise, telephone) 
VALUES (1, 'Admin BTP', 'admin@btp.com', 'admin123', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYWOg6YzZ6yW', 'BTP Pro', '+229 90000000');

-- ABONNEMENT ADMIN (100 ans)
INSERT INTO ABONNEMENTS (id_user, statut, date_debut, date_fin, type_abonnement)
VALUES (1, 'actif', NOW(), DATE_ADD(NOW(), INTERVAL 100 YEAR), 'illimite');

-- SETTINGS ADMIN
INSERT INTO SETTINGS (id_user, company_name, created_at, updated_at)
VALUES (1, 'BTP Devis Pro', NOW(), NOW());

-- CONTRAINTES ANTI-DOUBLONS
ALTER TABLE CLIENT ADD UNIQUE INDEX unique_client (nom, email);
ALTER TABLE PROJET ADD UNIQUE INDEX unique_projet (nom_projet);