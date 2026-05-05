// translations.js
const translations = {
    fr: {
        'dashboard': 'Tableau de bord',
        'devis': 'Devis',
        'clients': 'Clients',
        'projets': 'Projets',
        'factures': 'Factures',
        'parametres': 'Paramètres',
        'admin': 'Administration',
        'nouveau_devis': 'Nouveau devis',
        'ajouter_client': 'Ajouter un client',
        'nouveau_projet': 'Nouveau projet',
        'exporter_excel': 'Export Excel',
        'telecharger_pdf': 'Télécharger PDF',
        'valider': 'Valider',
        'modifier': 'Modifier',
        'supprimer': 'Supprimer',
        'annuler': 'Annuler',
        'enregistrer': 'Enregistrer',
        'rechercher': 'Rechercher...',
        'client_cree': 'Client créé avec succès',
        'client_modifie': 'Client modifié avec succès',
        'client_supprime': 'Client supprimé avec succès',
        'projet_cree': 'Projet créé avec succès',
        'projet_modifie': 'Projet modifié avec succès',
        'projet_supprime': 'Projet supprimé avec succès',
        'devis_cree': 'Devis créé avec succès',
        'devis_modifie': 'Devis modifié avec succès',
        'devis_supprime': 'Devis supprimé avec succès',
        'devis_valide': 'Devis validé avec succès',
        'facture_cree': 'Facture générée avec succès',
        'facture_payee': 'Facture marquée comme payée',
        'total_devis': 'Total Devis',
        'total_clients': 'Total Clients',
        'chiffre_affaires': 'Chiffre d\'affaires',
        'devis_valides': 'Devis validés'
    },
    en: {
        'dashboard': 'Dashboard',
        'devis': 'Quotes',
        'clients': 'Clients',
        'projets': 'Projects',
        'factures': 'Invoices',
        'parametres': 'Settings',
        'admin': 'Admin',
        'nouveau_devis': 'New quote',
        'ajouter_client': 'Add client',
        'nouveau_projet': 'New project',
        'exporter_excel': 'Export Excel',
        'telecharger_pdf': 'Download PDF',
        'valider': 'Validate',
        'modifier': 'Edit',
        'supprimer': 'Delete',
        'annuler': 'Cancel',
        'enregistrer': 'Save',
        'rechercher': 'Search...',
        'client_cree': 'Client created successfully',
        'client_modifie': 'Client updated successfully',
        'client_supprime': 'Client deleted successfully',
        'projet_cree': 'Project created successfully',
        'projet_modifie': 'Project updated successfully',
        'projet_supprime': 'Project deleted successfully',
        'devis_cree': 'Quote created successfully',
        'devis_modifie': 'Quote updated successfully',
        'devis_supprime': 'Quote deleted successfully',
        'devis_valide': 'Quote validated successfully',
        'facture_cree': 'Invoice generated successfully',
        'facture_payee': 'Invoice marked as paid',
        'total_devis': 'Total Quotes',
        'total_clients': 'Total Clients',
        'chiffre_affaires': 'Revenue',
        'devis_valides': 'Validated Quotes'
    }
};

let currentLang = localStorage.getItem('language') || 'fr';

function t(key) {
    return translations[currentLang][key] || key;
}

function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('language', lang);
    // Recharger la page pour appliquer la traduction
    location.reload();
}