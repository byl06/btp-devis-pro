// Configuration
const API_URL = 'http://localhost:5000';

// Récupérer le token
const token = localStorage.getItem('token');

if (!token) {
    window.location.href = 'login.html';
}

// Fonction pour les requêtes API
async function apiRequest(url, options = {}) {
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
    
    const response = await fetch(`${API_URL}${url}`, {
        ...options,
        headers: { ...headers, ...options.headers }
    });
    
    if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
        throw new Error('Non authentifié');
    }
    
    return response;
}
let app;

// ==================== TOAST NOTIFICATIONS ====================
class Toast {
    static container = null;
    
    static getContainer() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
        return this.container;
    }
    
    static show(message, type = 'info', title = '') {
        const container = this.getContainer();
        
        const titles = {
            success: '✅ Succès',
            error: '❌ Erreur',
            info: 'ℹ️ Information',
            warning: '⚠️ Attention'
        };
        
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            info: 'fa-info-circle',
            warning: 'fa-exclamation-triangle'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        toast.innerHTML = `
            <i class="fas ${icons[type]}"></i>
            <div class="toast-content">
                <div class="toast-title">${title || titles[type]}</div>
                <div class="toast-message">${message}</div>
            </div>
            <i class="fas fa-times toast-close"></i>
        `;
        
        container.appendChild(toast);
        
        // Fermeture manuelle
        toast.querySelector('.toast-close').addEventListener('click', (e) => {
            e.stopPropagation();
            this.remove(toast);
        });
        
        // Fermeture automatique après 4 secondes
        setTimeout(() => {
            this.remove(toast);
        }, 4000);
        
        return toast;
    }
    
    static remove(toast) {
        if (!toast.parentElement) return;
        toast.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }
    
    static success(message, title = '') {
        this.show(message, 'success', title);
    }
    
    static error(message, title = '') {
        this.show(message, 'error', title);
    }
    
    static info(message, title = '') {
        this.show(message, 'info', title);
    }
    
    static warning(message, title = '') {
        this.show(message, 'warning', title);
    }
}

// Application principale
class BTPDevisApp {
    constructor() {
        const savedUser = localStorage.getItem('user');
        this.currentUser = savedUser ? JSON.parse(savedUser) : null;
        this.allDevis = [];
        this.init();
    }
    
    init() {
        this.updateUserInfo();
        this.loadPage('dashboard');
        this.setupEventListeners();
        this.setupDesktopMenu();
        this.updateUserInfo();
        
        this.showNotifications();
    }
    
   updateUserInfo() {
    if (this.currentUser) {
        document.getElementById('user-name').textContent = this.currentUser.nom || this.currentUser.entreprise;
        document.getElementById('user-email').textContent = this.currentUser.email;
        
        // Ajouter le menu Admin si c'est l'admin
        this.updateAdminMenu();
    }
}

updateAdminMenu() {
    const navMenu = document.querySelector('.nav-menu');
    const adminExists = document.querySelector('.nav-item[data-page="admin"]');
    
    if (this.currentUser && (this.currentUser.email === 'admin@btp.com' || this.currentUser.email === 'bylgaitb@gmail.com')) {
        // Si admin et menu admin n'existe pas, l'ajouter
        if (!adminExists) {
            const adminLink = document.createElement('a');
            adminLink.href = '#';
            adminLink.className = 'nav-item';
            adminLink.setAttribute('data-page', 'admin');
            adminLink.innerHTML = '<i class="fas fa-chart-line"></i><span>Admin</span>';
            
            // Insérer avant Paramètres
            const paramsLink = document.querySelector('.nav-item[data-page="parametres"]');
            if (paramsLink) {
                navMenu.insertBefore(adminLink, paramsLink);
            } else {
                navMenu.appendChild(adminLink);
            }
            
            // Ajouter l'événement click
            adminLink.addEventListener('click', (e) => {
                e.preventDefault();
                const page = adminLink.dataset.page;
                this.loadPage(page);
                document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
                adminLink.classList.add('active');
            });
        }
    } else {
        // Si non admin, supprimer le menu admin s'il existe
        if (adminExists) {
            adminExists.remove();
        }
    }
}
    
    setupEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            this.loadPage(page);
            document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
        });
    });

    // Formulaires des paramètres
    document.addEventListener('submit', async (e) => {
        if (e.target.id === 'company-form') {
            e.preventDefault();
            await this.saveCompanySettings();
        }
        if (e.target.id === 'colors-form') {
            e.preventDefault();
            await this.saveColorSettings();
        }
        if (e.target.id === 'logo-form') {
            e.preventDefault();
            await this.uploadLogo();
        }
    });
    
    // ========== FILTRES POUR LA PAGE DEVIS ==========
    // Délégation d'événements pour la recherche et les filtres
    document.addEventListener('input', (e) => {
        if (e.target.id === 'search-devis') {
            console.log("🔍 Recherche en cours...");
            this.filterDevis();
        }
    });
    
    document.addEventListener('change', (e) => {
        if (e.target.id === 'filter-status' || e.target.id === 'filter-date') {
            console.log("📊 Filtre modifié");
            this.filterDevis();
        }
    });
}
    
    async loadPage(page) {
        const contentArea = document.getElementById('content-area');
        const pageTitle = document.getElementById('page-title');
        
        try {
            switch(page) {
                case 'dashboard':
                    pageTitle.textContent = 'Dashboard';
                    contentArea.innerHTML = await this.renderDashboard();
                    break;
                case 'devis':
                    pageTitle.textContent = 'Devis';
                    contentArea.innerHTML = await this.renderDevisList();
                    break;
                case 'clients':
                    pageTitle.textContent = 'Clients';
                    contentArea.innerHTML = await this.renderClients();
                    break;
                case 'projets':
                    pageTitle.textContent = 'Projets';
                    contentArea.innerHTML = await this.renderProjets();
                    break;
                case 'factures':
                    pageTitle.textContent = 'Factures';
                    contentArea.innerHTML = await this.renderFactures();
                    break;

                case 'admin':
    pageTitle.textContent = 'Administration';
    contentArea.innerHTML = await this.renderAdmin();
    break;
                case 'parametres':
    pageTitle.textContent = 'Paramètres';
    contentArea.innerHTML = await this.renderParametres();
    break;
                default:
                    contentArea.innerHTML = '<div class="glass-card">Page en construction</div>';
            }
        } catch (error) {
            contentArea.innerHTML = `<div class="glass-card">Erreur: ${error.message}</div>`;
        }
    }
    
    async fetchDevis() {
        try {
            const response = await apiRequest(`/api/devis?user_id=${this.currentUser.id}`);
            return await response.json();
        } catch (error) {
            return [];
        }
    }
    
    async fetchClients() {
        try {
            const response = await apiRequest('/api/clients');
            return await response.json();
        } catch (error) {
            return [];
        }
    }
    
    async fetchProjets() {
        try {
            const response = await apiRequest('/api/projets');
            return await response.json();
        } catch (error) {
            return [];
        }
    }

    async deleteDevis(id) {
    if (confirm('⚠️ Supprimer ce devis ? Cette action est irréversible.')) {
        try {
            console.log("Suppression devis ID:", id);
            const response = await apiRequest(`/api/devis/${id}`, { method: 'DELETE' });
            const result = await response.json();
            console.log("Réponse:", result);
            
            if (result.success) {
                alert('✅ Devis supprimé avec succès !');
                this.loadPage('devis');
            } else {
                alert('❌ ' + (result.message || 'Erreur lors de la suppression'));
            }
        } catch (error) {
            console.error('Erreur:', error);
            alert('❌ Erreur de connexion');
        }
    }
}
    
    async getStats() {
    const devis = await this.fetchDevis();
    const clients = await this.fetchClients();
    
    const totalDevis = devis.length;
    const totalClients = clients.length;
    
    // Calcul du CA - éviter NaN
    let chiffreAffaires = 0;
    if (devis.length > 0) {
        chiffreAffaires = devis.reduce((sum, d) => sum + (parseFloat(d.total) || 0), 0);
    }
    
    const devisValides = devis.filter(d => d.statut === 'validé').length;
    
    return { 
        totalDevis, 
        totalClients, 
        chiffreAffaires: chiffreAffaires || 0, 
        devisValides 
    };
}
    
    async renderDashboard() {
    const stats = await this.getStats();
    const devis = await this.fetchDevis();

    // Afficher le bandeau d'abonnement
    await this.showSubscriptionBanner();
    
    // Formater le chiffre d'affaires
    const formatCA = (value) => {
        if (!value || value === 0 || isNaN(value)) return '0 FCFA';
        return Math.round(value).toLocaleString('fr-FR') + ' FCFA';
    };
    
    return `
        <div class="page-content">
            <div class="cards-grid">
                <div class="glass-card">
                    <div class="card-icon"><i class="fas fa-file-invoice"></i></div>
                    <div class="card-title">Total Devis</div>
                    <div class="card-value">${stats.totalDevis}</div>
                </div>
                <div class="glass-card">
                    <div class="card-icon"><i class="fas fa-users"></i></div>
                    <div class="card-title">Clients</div>
                    <div class="card-value">${stats.totalClients}</div>
                </div>
                <div class="glass-card">
                    <div class="card-icon"><i class="fas fa-chart-line"></i></div>
                    <div class="card-title">Chiffre d'affaires</div>
                    <div class="card-value">${formatCA(stats.chiffreAffaires)}</div>
                </div>
                <div class="glass-card">
                    <div class="card-icon"><i class="fas fa-check-circle"></i></div>
                    <div class="card-title">Devis Validés</div>
                    <div class="card-value">${stats.devisValides}</div>
                </div>
            </div>
            <div class="table-container">
                <h3>Derniers Devis</h3>
                <table class="data-table">
                    <thead>
                        <tr><th>Réf</th><th>Client</th><th>Montant</th><th>Statut</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                        ${devis.slice(0,5).map(d => `
                            <tr>
                                <td>#${d.id_devis}</td>
                                <td>${d.client_nom}</td>
                                <td>${Math.round(d.total || 0).toLocaleString('fr-FR')} FCFA</div>
                                <td><span class="status-badge ${d.statut === 'validé' ? 'success' : 'warning'}">${d.statut}</span></div>
                                <td>
                                    <button class="btn-icon" onclick="app.viewDevis(${d.id_devis})"><i class="fas fa-eye"></i></button>
                                    <button class="btn-icon" onclick="app.downloadPDF(${d.id_devis})"><i class="fas fa-download"></i></button>
                                </div>
                            </tr>`).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}
    
    async renderDevisList() {
    const devis = await this.fetchDevis();
    
    // Stocker tous les devis pour le filtrage
    this.allDevis = devis;
    
    if (devis.length === 0) {
        return `
            <div class="glass-card" style="text-align:center; padding:60px;">
                <p>Aucun devis</p>
                <button class="btn-primary" onclick="app.openCreateDevisModal()">Créer un devis</button>
            </div>
        `;
    }
    
    return `
        <div class="table-container">
            <!-- Barre de recherche et filtres -->
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem; flex-wrap:wrap; gap:1rem;">
                <h3>Liste des devis</h3>
                <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                    <div class="search-box">
                        <i class="fas fa-search"></i>
                        <input type="text" id="search-devis" placeholder="Rechercher..." style="padding:8px 12px 8px 35px; border-radius:8px; border:1px solid #334155; background:#1E293B; color:white; width:200px;">
                    </div>
                    <select id="filter-status" class="filter-select" style="padding:8px 12px; border-radius:8px; background:#1E293B; color:white; border:1px solid #334155;">
                        <option value="all">📊 Tous les statuts</option>
                        <option value="brouillon">📝 Brouillons</option>
                        <option value="validé">✅ Validés</option>
                    </select>
                    <select id="filter-date" class="filter-select" style="padding:8px 12px; border-radius:8px; background:#1E293B; color:white; border:1px solid #334155;">
                        <option value="all">📅 Toutes les dates</option>
                        <option value="7">7 derniers jours</option>
                        <option value="30">30 derniers jours</option>
                        <option value="90">90 derniers jours</option>
                    </select>
                    <button class="btn-primary" onclick="app.openCreateDevisModal()">
                        <i class="fas fa-plus"></i> Nouveau devis
                    </button>
                    <button class="btn-secondary" onclick="app.exportDevisToExcel()" style="background:#10B981; border-color:#10B981;">
                        <i class="fas fa-file-excel"></i> Export Excel
                    </button>
                </div>
            </div>
            
            <!-- Compteur de résultats -->
            <div id="devis-count" style="margin-bottom:1rem; color:#94A3B8; font-size:0.9rem;">
                ${devis.length} devis trouvés
            </div>
            
            <!-- Tableau des devis -->
            <table class="data-table">
                <thead>
                    <tr>
                        <th style="cursor:pointer;" onclick="app.sortDevis('id_devis')">Réf <i class="fas fa-sort"></i></th>
                        <th style="cursor:pointer;" onclick="app.sortDevis('date_creation')">Date <i class="fas fa-sort"></i></th>
                        <th style="cursor:pointer;" onclick="app.sortDevis('client_nom')">Client <i class="fas fa-sort"></i></th>
                        <th>Projet</th>
                        <th style="cursor:pointer;" onclick="app.sortDevis('total')">Montant <i class="fas fa-sort"></i></th>
                        <th>Statut</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="devis-table-body">
                    ${this.renderDevisTableRows(devis)}
                </tbody>
            </table>
        </div>
    `;
}

renderDevisTableRows(devis) {
    if (!devis || devis.length === 0) {
        return '<tr><td colspan="7" style="text-align:center;">Aucun devis trouvé</td></tr>';
    }
    
    return devis.map(d => `
        <tr>
            <td>#${d.id_devis}</td>
            <td>${new Date(d.date_creation).toLocaleDateString()}</td>
            <td>${d.client_nom}</td>
            <td>${d.nom_projet}</td>
            <td>${Math.round(d.total || 0).toLocaleString('fr-FR')} FCFA</div>
            <td><span class="status-badge ${d.statut === 'validé' ? 'success' : 'warning'}">${d.statut}</span></div>
            <td>
                <button class="btn-icon" onclick="app.viewDevis(${d.id_devis})" title="Voir"><i class="fas fa-eye"></i></button>
                <button class="btn-icon" onclick="app.downloadPDF(${d.id_devis})" title="PDF"><i class="fas fa-download"></i></button>
                ${d.statut !== 'validé' ? `<button class="btn-icon" onclick="app.editDevis(${d.id_devis})" title="Modifier"><i class="fas fa-edit"></i></button>` : ''}
                ${d.statut !== 'validé' ? `<button class="btn-icon" onclick="app.deleteDevis(${d.id_devis})" title="Supprimer"><i class="fas fa-trash"></i></button>` : ''}
            </div>
        </tr>
    `).join('');
}

async exportClientsToExcel() {
    try {
        const clients = await this.fetchClients();
        
        if (clients.length === 0) {
            alert('Aucun client à exporter');
            return;
        }
        
        const data = clients.map(c => ({
            'Nom': c.nom,
            'Email': c.email || '',
            'Téléphone': c.telephone || '',
            'Adresse': c.adresse || ''
        }));
        
        const headers = Object.keys(data[0]);
        const csvRows = [headers.join(',')];
        
        for (const row of data) {
            const values = headers.map(header => {
                let value = row[header] || '';
                if (typeof value === 'string') {
                    value = value.replace(/"/g, '""');
                    if (value.includes(',') || value.includes('"')) {
                        value = `"${value}"`;
                    }
                }
                return value;
            });
            csvRows.push(values.join(','));
        }
        
        const blob = new Blob(["\uFEFF" + csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `clients_export_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        
        alert(`✅ ${clients.length} clients exportés !`);
    } catch (error) {
        alert('❌ Erreur lors de l\'export');
    }
}
    
   async renderClients() {
    // Forcer un nouveau fetch (pas de cache)
    const clients = await this.fetchClients();
    console.log("🟢 Rendu des clients:", clients.length);
    
    if (clients.length === 0) {
        return `
            <div>
                <div style="display:flex; justify-content:flex-end; margin-bottom:1rem;">
                    <button class="btn-secondary" onclick="app.exportClientsToExcel()" style="background:#10B981; border-color:#10B981;">
                        <i class="fas fa-file-excel"></i> Export Excel
                    </button>
                </div>
                <div class="glass-card" style="text-align:center;">
                    <p>Aucun client</p>
                    <button class="btn-primary" onclick="app.openCreateClientModal()">+ Ajouter un client</button>
                </div>
            </div>
        `;
    }
    
    return `
        <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; flex-wrap:wrap; gap:1rem;">
                <h3>Mes clients (${clients.length})</h3>
                <div style="display:flex; gap:0.5rem;">
                    <button class="btn-secondary" onclick="app.exportClientsToExcel()" style="background:#10B981; border-color:#10B981;">
                        <i class="fas fa-file-excel"></i> Export Excel
                    </button>
                    <button class="btn-primary" onclick="app.openCreateClientModal()">
                        <i class="fas fa-plus"></i> Ajouter
                    </button>
                </div>
            </div>
            <div class="cards-grid">
                ${clients.map(c => `
                    <div class="glass-card">
    <div class="card-icon"><i class="fas fa-user"></i></div>
    <div class="card-title">${c.nom}</div>
    <p style="word-break: break-all;">
        <i class="fas fa-envelope"></i> ${c.email || '-'}
    </p>
    <p><i class="fas fa-phone"></i> ${c.telephone || '-'}</p>
    <p style="word-break: break-word;">
        <i class="fas fa-map-marker-alt"></i> ${c.adresse || '-'}
    </p>
    <div style="margin-top:1rem; display:flex; gap:0.5rem">
        <button class="btn-icon" onclick="app.editClient(${c.id_client})"><i class="fas fa-edit"></i></button>
        <button class="btn-icon" onclick="app.deleteClient(${c.id_client})"><i class="fas fa-trash"></i></button>
    </div>
</div>
                `).join('')}
            </div>
        </div>
    `;
}


    async renderProjets() {
        const projets = await this.fetchProjets();
        
        if (projets.length === 0) {
            return `<div class="glass-card"><p>Aucun projet</p><button class="btn-primary" onclick="app.openCreateProjetModal()">+ Ajouter un projet</button></div>`;
        }
        
        return `
            <div class="cards-grid">
                ${projets.map(p => `
                    <div class="glass-card">
                        <div class="card-icon"><i class="fas fa-hard-hat"></i></div>
                        <div class="card-title">${p.nom_projet}</div>
                        <p>${p.description || ''}</p>
                        <p>${p.localisation || ''}</p>
                        <div style="margin-top:1rem; display:flex; gap:0.5rem">
                            <button class="btn-icon" onclick="app.editProjet(${p.id_projet})"><i class="fas fa-edit"></i></button>
                            <button class="btn-icon" onclick="app.deleteProjet(${p.id_projet})"><i class="fas fa-trash"></i></button>
                        </div>
                    </div>
                `).join('')}
                <div class="glass-card" style="display:flex; justify-content:center; align-items:center">
                    <button class="btn-primary" onclick="app.openCreateProjetModal()">+ Ajouter</button>
                </div>
            </div>
        `;
    }
    
    async renderFactures() {
    try {
        const userId = this.currentUser.id;
        console.log("Chargement factures pour user:", userId);
        
        const response = await apiRequest(`/api/factures/${userId}`);
        const factures = await response.json();
        
        console.log("Factures reçues:", factures);
        
        if (!factures || factures.length === 0) {
            return `
                <div class="glass-card" style="text-align:center; padding:60px;">
                    <i class="fas fa-receipt" style="font-size:48px; opacity:0.5;"></i>
                    <h3>Aucune facture</h3>
                    <p>Validez un devis pour générer une facture</p>
                </div>
            `;
        }
        
        return `
            <div class="table-container">
                <h3>Mes factures</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>N° Facture</th>
                            <th>Devis lié</th>
                            <th>Client</th>
                            <th>Date</th>
                            <th>Montant</th>
                            <th>Statut</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${factures.map(f => `
                            <tr>
                                <td>#${f.id_facture}</td>
                                <td>DEVIS-${f.id_devis}</td>
                                <td>${f.client_nom || '-'}</td>
                                <td>${new Date(f.date_facture).toLocaleDateString()}</td>
                                <td>${(f.montant || 0).toLocaleString()} FCFA</div>
                                <td>
                                    <span class="status-badge ${f.statut === 'payée' ? 'success' : 'warning'}">
                                        ${f.statut === 'payée' ? 'Payée' : 'Non payée'}
                                    </span>
                                </div>
                                <td>
                                    <button class="btn-icon" onclick="app.payFacture(${f.id_facture})" title="Marquer payée">
                                        <i class="fas fa-credit-card"></i>
                                    </button>
                                </div>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (error) {
        console.error('Erreur factures:', error);
        return '<div class="glass-card">Erreur chargement des factures</div>';
    }
}
    
    renderParametres() {
        return `
            <div class="glass-card">
                <h3>Paramètres du compte</h3>
                <p>Nom: ${this.currentUser?.nom}</p>
                <p>Email: ${this.currentUser?.email}</p>
                <p>Entreprise: ${this.currentUser?.entreprise}</p>
                <hr style="margin:1rem 0">
                <button class="btn-primary" onclick="app.logout()">Se déconnecter</button>
            </div>
        `;
    }
    
    // Actions rapides
   async viewDevis(id) {
    try {
        const response = await apiRequest(`/api/devis/${id}`);
        const devis = await response.json();
        
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'flex';
        modal.innerHTML = `
            <div class="modal-content" style="max-width:800px; max-height:90vh; overflow-y:auto;">
                <div class="modal-header">
                    <h2><i class="fas fa-file-invoice"></i> Détail du devis #${devis.id_devis}</h2>
                    <i class="fas fa-times close-modal" style="cursor:pointer;"></i>
                </div>
                <div class="modal-body">
                    <div style="margin-bottom:20px;">
                        <h3>Informations client</h3>
                        <p><strong>Nom:</strong> ${devis.client_nom}</p>
                        <p><strong>Email:</strong> ${devis.client_email || '-'}</p>
                        <p><strong>Téléphone:</strong> ${devis.client_telephone || '-'}</p>
                    </div>
                    
                    <div style="margin-bottom:20px;">
                        <h3>Informations projet</h3>
                        <p><strong>Nom:</strong> ${devis.nom_projet}</p>
                        <p><strong>Description:</strong> ${devis.projet_description || '-'}</p>
                    </div>
                    
                    <div style="margin-bottom:20px;">
                        <h3>Matériaux et travaux</h3>
                        <table style="width:100%; border-collapse:collapse;">
                            <thead>
                                <tr style="background:rgba(255,255,255,0.1);">
                                    <th style="padding:10px; text-align:left;">Désignation</th>
                                    <th style="padding:10px; text-align:center;">Qté</th>
                                    <th style="padding:10px; text-align:right;">Prix unitaire</th>
                                    <th style="padding:10px; text-align:right;">Total</th>
                                 </tr>
                            </thead>
                            <tbody>
                                ${devis.lignes.map(ligne => `
                                    <tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
                                        <td style="padding:10px;">${ligne.designation}</td>
                                        <td style="padding:10px; text-align:center;">${ligne.quantite}</td>
                                        <td style="padding:10px; text-align:right;">${ligne.prix_unitaire.toLocaleString()} FCFA</td>
                                        <td style="padding:10px; text-align:right;">${ligne.total_ligne.toLocaleString()} FCFA</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                            <tfoot>
                                <tr style="border-top:2px solid rgba(255,255,255,0.2);">
                                    <td colspan="3" style="padding:10px; text-align:right;"><strong>Sous-total:</strong></td>
                                    <td style="padding:10px; text-align:right;">${(devis.total / 1.2).toLocaleString()} FCFA</td>
                                </tr>
                                <tr>
                                    <td colspan="3" style="padding:10px; text-align:right;"><strong>Main d'œuvre (20%):</strong></td>
                                    <td style="padding:10px; text-align:right;">${(devis.total - devis.total / 1.2).toLocaleString()} FCFA</td>
                                </tr>
                                <tr style="background:rgba(6,182,212,0.2);">
                                    <td colspan="3" style="padding:10px; text-align:right;"><strong>TOTAL TTC:</strong></td>
                                    <td style="padding:10px; text-align:right; font-size:1.2rem; font-weight:bold; color:#06B6D4;">${devis.total.toLocaleString()} FCFA</td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                    
                    <div style="display:flex; gap:10px; justify-content:flex-end; margin-top:20px; flex-wrap:wrap;">
    <button onclick="app.downloadPDF(${devis.id_devis})" class="btn-primary">
        <i class="fas fa-download"></i> Télécharger PDF
    </button>
    
    ${devis.statut === 'brouillon' ? `
        <button onclick="app.validateDevis(${devis.id_devis})" class="btn-secondary" style="background:#F59E0B; border-color:#F59E0B;">
            <i class="fas fa-check"></i> Valider le devis
        </button>
    ` : `
        <button onclick="app.createFacture(${devis.id_devis})" class="btn-secondary" style="background:#8B5CF6; border-color:#8B5CF6;">
            <i class="fas fa-receipt"></i> Générer facture
        </button>
    `}
</div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const closeBtns = modal.querySelectorAll('.close-modal');
        closeBtns.forEach(btn => btn.addEventListener('click', () => modal.remove()));
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
        
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du chargement du devis');
    }
}

async exportDevisToExcel() {
    try {
        const devis = await this.fetchDevis();
        
        if (devis.length === 0) {
            alert('Aucun devis à exporter');
            return;
        }
        
        // Préparer les données pour Excel
        const data = devis.map(d => ({
            'Référence': `#${d.id_devis}`,
            'Date': new Date(d.date_creation).toLocaleDateString('fr-FR'),
            'Client': d.client_nom,
            'Projet': d.nom_projet,
            'Montant (FCFA)': Math.round(d.total || 0),
            'Statut': d.statut === 'validé' ? 'Validé' : 'Brouillon'
        }));
        
        // Ajouter une ligne de total
        const totalCA = devis.reduce((sum, d) => sum + (d.total || 0), 0);
        data.push({
            'Référence': 'TOTAL',
            'Date': '',
            'Client': '',
            'Projet': '',
            'Montant (FCFA)': Math.round(totalCA),
            'Statut': ''
        });
        
        // Convertir en CSV
        const headers = Object.keys(data[0]);
        const csvRows = [];
        
        // Ajouter les en-têtes
        csvRows.push(headers.join(','));
        
        // Ajouter les données
        for (const row of data) {
            const values = headers.map(header => {
                let value = row[header] || '';
                if (typeof value === 'string') {
                    value = value.replace(/"/g, '""');
                    if (value.includes(',') || value.includes('"')) {
                        value = `"${value}"`;
                    }
                }
                return value;
            });
            csvRows.push(values.join(','));
        }
        
        // Télécharger le fichier
        const blob = new Blob(["\uFEFF" + csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `devis_export_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        Toast.success(`${devis.length} devis exportés avec succès`);
        
    } catch (error) {
        console.error('Erreur export:', error);
        alert('❌ Erreur lors de l\'export');
    }
}
    
    downloadPDF(id) {
        window.open(`${API_URL}/api/devis/${id}/pdf`, '_blank');
    }
    
    async payFacture(id) {
        if (confirm('Marquer cette facture comme payée ?')) {
            await apiRequest(`/api/facture/${id}/pay`, { method: 'PUT' });
            alert('Facture payée');
            this.loadPage('factures');
        }
    }
    
    openCreateClientModal() {
        alert('Fonctionnalité à implémenter');
    }
    
    openCreateProjetModal() {
        alert('Fonctionnalité à implémenter');
    }
    
    openCreateDevisModal() {
        alert('Fonctionnalité à implémenter');
    }
    
    editClient(id) {
        alert(`Modifier client #${id}`);
    }
    
    editProjet(id) {
        alert(`Modifier projet #${id}`);
    }
    
    async deleteClient(id) {
    if (confirm('⚠️ Supprimer ce client ? Cette action est irréversible.')) {
        try {
            console.log("Suppression client ID:", id);
            const response = await apiRequest(`/api/clients/${id}`, { method: 'DELETE' });
            const result = await response.json();
            
            console.log("Résultat API:", result);
            
            if (result.success) {
    Toast.success('Client supprimé avec succès');
    window.location.reload();  // ← Recharge toute la page
} else {
                Toast.error(result.message);
            }
        } catch (error) {
            console.error('Erreur:', error);
            Toast.error('Erreur de connexion');
        }
    }
}
    
    async deleteProjet(id) {
        if (confirm('Supprimer ce projet ?')) {
            await apiRequest(`/api/projets/${id}`, { method: 'DELETE' });
            alert('Projet supprimé');
            this.loadPage('projets');
        }
    }
    
    logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    }

openCreateClientModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>Nouveau client</h2>
                <i class="fas fa-times close-modal" style="cursor:pointer;"></i>
            </div>
            <div class="modal-body">
                <form id="client-form">
                    <div class="form-group">
                        <label>Nom complet *</label>
                        <input type="text" id="client-nom" required>
                    </div>
                    <div class="form-group">
                        <label>Téléphone *</label>
                        <input type="tel" id="client-telephone" required>
                    </div>
                    <div class="form-group">
                        <label>Email *</label>
                        <input type="email" id="client-email" required>
                    </div>
                    <div class="form-group">
                        <label>Adresse</label>
                        <textarea id="client-adresse" rows="3"></textarea>
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">Enregistrer</button>
                        <button type="button" class="btn-secondary close-modal">Annuler</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Fermeture
    const closeBtns = modal.querySelectorAll('.close-modal');
    closeBtns.forEach(btn => btn.addEventListener('click', () => modal.remove()));
    
    // Soumission
    const form = modal.querySelector('#client-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const limitesOk = await this.checkLimites('client');
    if (!limitesOk) return;
        
        const clientData = {
            nom: document.getElementById('client-nom').value,
            telephone: document.getElementById('client-telephone').value,
            email: document.getElementById('client-email').value,
            adresse: document.getElementById('client-adresse').value
        };
        
        try {
            const response = await apiRequest('/api/clients', {
                method: 'POST',
                body: JSON.stringify(clientData)
            });
            const result = await response.json();
            
            if (result.success) {
    Toast.success('Client ajouté avec succès');
    modal.remove();
    setTimeout(() => this.loadPage('clients'), 1000);
} else {
    Toast.error(result.message || 'Erreur lors de la création');
}
        } catch (error) {
            alert('❌ Erreur de connexion');
        }
    });
}


openCreateProjetModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>Nouveau projet</h2>
                <i class="fas fa-times close-modal" style="cursor:pointer;"></i>
            </div>
            <div class="modal-body">
                <form id="projet-form">
                    <div class="form-group">
                        <label>Nom du projet *</label>
                        <input type="text" id="projet-nom" required>
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <textarea id="projet-description" rows="3"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Localisation</label>
                        <input type="text" id="projet-localisation">
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">Créer</button>
                        <button type="button" class="btn-secondary close-modal">Annuler</button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const closeBtns = modal.querySelectorAll('.close-modal');
    closeBtns.forEach(btn => btn.addEventListener('click', () => modal.remove()));
    
    const form = modal.querySelector('#projet-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const limitesOk = await this.checkLimites('projet');
    if (!limitesOk) return;
        
        const projetData = {
            nom_projet: document.getElementById('projet-nom').value,
            description: document.getElementById('projet-description').value,
            localisation: document.getElementById('projet-localisation').value
        };
        
        try {
            const response = await apiRequest('/api/projets', {
                method: 'POST',
                body: JSON.stringify(projetData)
            });
            const result = await response.json();
            
            if (result.success) {
    Toast.success('Devis créé avec succès');
    modal.remove();
    this.loadPage('devis');
} else {
    Toast.error(result.message || 'Erreur lors de la création');
}
        } catch (error) {
            alert('❌ Erreur de connexion');
        }
    });
}

openCreateDevisModal() {
    Promise.all([this.fetchClients(), this.fetchProjets()]).then(([clients, projets]) => {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'flex';
        modal.innerHTML = `
            <div class="modal-content" style="max-width:700px; max-height:90vh; overflow-y:auto;">
                <div class="modal-header">
                    <h2><i class="fas fa-file-invoice"></i> Nouveau devis</h2>
                    <i class="fas fa-times close-modal" style="cursor:pointer;"></i>
                </div>
                <div class="modal-body">
                    <form id="devis-form">
                        <div class="form-group">
                            <label>Client *</label>
                            <select id="devis-client" required>
                                <option value="">Sélectionner</option>
                                ${clients.map(c => `<option value="${c.id_client}">${c.nom}</option>`).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Projet *</label>
                            <select id="devis-projet" required>
                                <option value="">Sélectionner</option>
                                ${projets.map(p => `<option value="${p.id_projet}">${p.nom_projet}</option>`).join('')}
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label><i class="fas fa-tools"></i> Matériaux et travaux</label>
                            <div id="materiaux-list">
                                <div class="materiaux-item">
                                    <input type="text" placeholder="Désignation" class="designation" style="flex:2">
                                    <input type="number" placeholder="Quantité" class="quantite" value="1" style="flex:1">
                                    <input type="number" placeholder="Prix unitaire" class="prix" style="flex:1">
                                    <button type="button" class="remove-item" style="background:#EF4444; color:white; border:none; border-radius:6px; padding:8px; cursor:pointer;">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                            <button type="button" id="add-materiaux" class="btn-secondary" style="margin-top:10px; width:100%;">
                                <i class="fas fa-plus"></i> Ajouter un matériau
                            </button>
                        </div>
                        
                        <div class="form-group" style="background:rgba(0,0,0,0.3); padding:15px; border-radius:12px; margin-top:15px;">
                            <label><i class="fas fa-calculator"></i> Récapitulatif</label>
                            <div style="margin-top:10px;">
                                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                                    <span>Sous-total matériaux:</span>
                                    <span id="sous-total-materiaux" style="font-weight:bold;">0 FCFA</span>
                                </div>
                                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                                    <span>Main d'œuvre (20%):</span>
                                    <span id="main-oeuvre" style="font-weight:bold;">0 FCFA</span>
                                </div>
                                <div style="border-top:1px solid rgba(255,255,255,0.2); margin:10px 0; padding-top:10px;">
                                    <div style="display:flex; justify-content:space-between; font-size:1.2rem;">
                                        <strong>TOTAL TTC:</strong>
                                        <span id="total-estime" style="font-weight:bold; color:#06B6D4;">0 FCFA</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="form-actions">
                            <button type="submit" class="btn-primary">Créer le devis</button>
                            <button type="button" class="btn-secondary close-modal">Annuler</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Fonction de calcul
        const calculateTotal = () => {
            const items = modal.querySelectorAll('.materiaux-item');
            let totalMateriaux = 0;
            items.forEach(item => {
                const quantite = parseFloat(item.querySelector('.quantite')?.value) || 0;
                const prix = parseFloat(item.querySelector('.prix')?.value) || 0;
                totalMateriaux += quantite * prix;
            });
            const mainOeuvre = totalMateriaux * 0.2;
            const total = totalMateriaux + mainOeuvre;
            
            modal.querySelector('#sous-total-materiaux').textContent = totalMateriaux.toLocaleString() + ' FCFA';
            modal.querySelector('#main-oeuvre').textContent = mainOeuvre.toLocaleString() + ' FCFA';
            modal.querySelector('#total-estime').textContent = total.toLocaleString() + ' FCFA';
            return { totalMateriaux, mainOeuvre, total };
        };
        
        // Ajouter un matériau
        const addBtn = modal.querySelector('#add-materiaux');
        addBtn.addEventListener('click', () => {
            const container = modal.querySelector('#materiaux-list');
            const newItem = document.createElement('div');
            newItem.className = 'materiaux-item';
            newItem.style.display = 'flex';
            newItem.style.gap = '10px';
            newItem.style.marginBottom = '10px';
            newItem.innerHTML = `
                <input type="text" placeholder="Désignation" class="designation" style="flex:2; padding:8px; border-radius:6px; background:#0F172A; border:1px solid #334155; color:white;">
                <input type="number" placeholder="Quantité" class="quantite" value="1" style="flex:1; padding:8px; border-radius:6px; background:#0F172A; border:1px solid #334155; color:white;">
                <input type="number" placeholder="Prix unitaire" class="prix" style="flex:1; padding:8px; border-radius:6px; background:#0F172A; border:1px solid #334155; color:white;">
                <button type="button" class="remove-item" style="background:#EF4444; color:white; border:none; border-radius:6px; padding:8px; cursor:pointer;">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            newItem.querySelector('.remove-item').addEventListener('click', () => {
                newItem.remove();
                calculateTotal();
            });
            newItem.querySelectorAll('input').forEach(input => {
                input.addEventListener('input', () => calculateTotal());
            });
            container.appendChild(newItem);
            calculateTotal();
        });
        
        // Événements existants
        modal.querySelectorAll('.remove-item').forEach(btn => {
            btn.addEventListener('click', () => {
                btn.closest('.materiaux-item').remove();
                calculateTotal();
            });
        });
        modal.querySelectorAll('#materiaux-list input').forEach(input => {
            input.addEventListener('input', () => calculateTotal());
        });
        
        // Fermeture
        const closeBtns = modal.querySelectorAll('.close-modal');
        closeBtns.forEach(btn => btn.addEventListener('click', () => modal.remove()));
        
        // Soumission
        const form = modal.querySelector('#devis-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const limitesOk = await this.checkLimites('devis');
    if (!limitesOk) return;
            
            const id_client = modal.querySelector('#devis-client').value;
            const id_projet = modal.querySelector('#devis-projet').value;
            
            if (!id_client || !id_projet) {
                alert('Veuillez sélectionner un client et un projet');
                return;
            }
            
            const lignes = [];
            const items = modal.querySelectorAll('.materiaux-item');
            items.forEach(item => {
                const designation = item.querySelector('.designation')?.value;
                const quantite = parseFloat(item.querySelector('.quantite')?.value);
                const prix_unitaire = parseFloat(item.querySelector('.prix')?.value);
                if (designation && quantite > 0 && prix_unitaire > 0) {
                    lignes.push({ designation, quantite, prix_unitaire });
                }
            });
            
            if (lignes.length === 0) {
                alert('Veuillez ajouter au moins un matériau');
                return;
            }
            
            const devisData = {
                id_client: parseInt(id_client),
                id_user: this.currentUser.id,
                id_projet: parseInt(id_projet),
                lignes: lignes
            };
            
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Création...';
            submitBtn.disabled = true;
            
            try {
                const response = await apiRequest('/api/devis', { method: 'POST', body: JSON.stringify(devisData) });
                const result = await response.json();
                if (result.success) {
                    alert('✅ Devis créé avec succès !');
                    modal.remove();
                    this.loadPage('devis');
                } else {
                    alert('❌ ' + (result.message || 'Erreur lors de la création'));
                }
            } catch (error) {
                alert('❌ Erreur de connexion');
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });
        
        calculateTotal();
    });
}

async downloadPDF(id) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_URL}/api/devis/${id}/pdf`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.status === 401) {
            alert('Session expirée, veuillez vous reconnecter');
            window.location.href = 'login.html';
            return;
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `devis_${id}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Erreur téléchargement:', error);
        alert('Erreur lors du téléchargement du PDF');
    }
}

async validateDevis(id) {
    if (confirm('Valider ce devis ? Cette action est irréversible.')) {
        try {
            const response = await apiRequest(`/api/devis/${id}/validate`, { method: 'POST' });
            const result = await response.json();
            if (result.success) {
                alert('✅ Devis validé avec succès !');
                this.loadPage('devis');
            } else {
                alert('❌ Erreur: ' + (result.message || 'Validation échouée'));
            }
        } catch (error) {
            alert('❌ Erreur de connexion');
        }
    }
}

async createFacture(id_devis) {
    if (confirm('Générer une facture pour ce devis ?')) {
        try {
            const response = await apiRequest(`/api/facture/${id_devis}`, { method: 'POST' });
            const result = await response.json();
            if (result.success) {
    Toast.success('Devis validé avec succès');
    this.loadPage('devis');
} else {
    Toast.error(result.message);
}
        } catch (error) {
            alert('❌ Erreur de connexion');
        }
    }
}

async payFacture(id_facture) {
    if (confirm('Marquer cette facture comme payée ?')) {
        try {
            console.log("Paiement facture ID:", id_facture);
            const response = await apiRequest(`/api/facture/${id_facture}/pay`, { method: 'PUT' });
            const result = await response.json();
            
            if (result.success) {
                Toast.success('Facture marquée comme payée');
                // Recharger la page des factures
                this.loadPage('factures');
            } else {
                Toast.error(result.message || 'Erreur lors du paiement');
            }
        } catch (error) {
            console.error('Erreur:', error);
            Toast.error('Erreur de connexion');
        }
    }
}

async editClient(id) {
    try {
        // Récupérer les infos du client
        const clients = await this.fetchClients();
        const client = clients.find(c => c.id_client === id);
        
        if (!client) {
            alert('Client non trouvé');
            return;
        }
        
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'flex';
        modal.innerHTML = `
            <div class="modal-content" style="max-width:500px;">
                <div class="modal-header">
                    <h2><i class="fas fa-edit"></i> Modifier le client</h2>
                    <i class="fas fa-times close-modal" style="cursor:pointer;"></i>
                </div>
                <div class="modal-body">
                    <form id="edit-client-form">
                        <div class="form-group">
                            <label>Nom complet *</label>
                            <input type="text" id="edit-client-nom" value="${client.nom}" required>
                        </div>
                        <div class="form-group">
                            <label>Téléphone *</label>
                            <input type="tel" id="edit-client-telephone" value="${client.telephone || ''}" required>
                        </div>
                        <div class="form-group">
                            <label>Email *</label>
                            <input type="email" id="edit-client-email" value="${client.email || ''}" required>
                        </div>
                        <div class="form-group">
                            <label>Adresse</label>
                            <textarea id="edit-client-adresse" rows="3">${client.adresse || ''}</textarea>
                        </div>
                        <div class="form-actions">
                            <button type="submit" class="btn-primary">Enregistrer</button>
                            <button type="button" class="btn-secondary close-modal">Annuler</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Fermeture
        const closeBtns = modal.querySelectorAll('.close-modal');
        closeBtns.forEach(btn => btn.addEventListener('click', () => modal.remove()));
        
        // Soumission
        const form = modal.querySelector('#edit-client-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const clientData = {
                nom: document.getElementById('edit-client-nom').value,
                telephone: document.getElementById('edit-client-telephone').value,
                email: document.getElementById('edit-client-email').value,
                adresse: document.getElementById('edit-client-adresse').value
            };
            
            try {
                const response = await apiRequest(`/api/clients/${id}`, {
                    method: 'PUT',
                    body: JSON.stringify(clientData)
                });
                const result = await response.json();
                
                if (result.success) {
                    alert('✅ Client modifié avec succès !');
                    modal.remove();
                    this.loadPage('clients');
                } else {
                    alert('❌ Erreur: ' + result.message);
                }
            } catch (error) {
                alert('❌ Erreur de connexion');
            }
        });
        
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du chargement du client');
    }
}

async editProjet(id) {
    try {
        // Récupérer les infos du projet
        const projets = await this.fetchProjets();
        const projet = projets.find(p => p.id_projet === id);
        
        if (!projet) {
            alert('Projet non trouvé');
            return;
        }
        
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'flex';
        modal.innerHTML = `
            <div class="modal-content" style="max-width:500px;">
                <div class="modal-header">
                    <h2><i class="fas fa-edit"></i> Modifier le projet</h2>
                    <i class="fas fa-times close-modal" style="cursor:pointer;"></i>
                </div>
                <div class="modal-body">
                    <form id="edit-projet-form">
                        <div class="form-group">
                            <label>Nom du projet *</label>
                            <input type="text" id="edit-projet-nom" value="${projet.nom_projet}" required>
                        </div>
                        <div class="form-group">
                            <label>Description</label>
                            <textarea id="edit-projet-description" rows="3">${projet.description || ''}</textarea>
                        </div>
                        <div class="form-group">
                            <label>Localisation</label>
                            <input type="text" id="edit-projet-localisation" value="${projet.localisation || ''}">
                        </div>
                        <div class="form-actions">
                            <button type="submit" class="btn-primary">Enregistrer</button>
                            <button type="button" class="btn-secondary close-modal">Annuler</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Fermeture
        const closeBtns = modal.querySelectorAll('.close-modal');
        closeBtns.forEach(btn => btn.addEventListener('click', () => modal.remove()));
        
        // Soumission
        const form = modal.querySelector('#edit-projet-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const projetData = {
                nom_projet: document.getElementById('edit-projet-nom').value,
                description: document.getElementById('edit-projet-description').value,
                localisation: document.getElementById('edit-projet-localisation').value
            };
            
            try {
                const response = await apiRequest(`/api/projets/${id}`, {
                    method: 'PUT',
                    body: JSON.stringify(projetData)
                });
                const result = await response.json();
                
                if (result.success) {
                    alert('✅ Projet modifié avec succès !');
                    modal.remove();
                    this.loadPage('projets');
                } else {
                    alert('❌ Erreur: ' + result.message);
                }
            } catch (error) {
                alert('❌ Erreur de connexion');
            }
        });
        
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du chargement du projet');
    }
}

async editDevis(id) {
    try {
        // Récupérer les données du devis
        const response = await apiRequest(`/api/devis/${id}`);
        const devis = await response.json();
        
        if (devis.statut === 'validé') {
            alert('Impossible de modifier un devis validé');
            return;
        }
        
        // Récupérer les clients et projets
        const clients = await this.fetchClients();
        const projets = await this.fetchProjets();
        
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'flex';
        modal.innerHTML = `
            <div class="modal-content" style="max-width:700px; max-height:90vh; overflow-y:auto;">
                <div class="modal-header">
                    <h2><i class="fas fa-edit"></i> Modifier le devis #${devis.id_devis}</h2>
                    <i class="fas fa-times close-modal" style="cursor:pointer;"></i>
                </div>
                <div class="modal-body">
                    <form id="edit-devis-form">
                        <div class="form-group">
                            <label>Client *</label>
                            <select id="edit-devis-client" required>
                                <option value="">Sélectionner</option>
                                ${clients.map(c => `
                                    <option value="${c.id_client}" ${c.id_client === devis.id_client ? 'selected' : ''}>
                                        ${c.nom}
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Projet *</label>
                            <select id="edit-devis-projet" required>
                                <option value="">Sélectionner</option>
                                ${projets.map(p => `
                                    <option value="${p.id_projet}" ${p.id_projet === devis.id_projet ? 'selected' : ''}>
                                        ${p.nom_projet}
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label><i class="fas fa-tools"></i> Matériaux et travaux</label>
                            <div id="edit-materiaux-list">
                                ${devis.lignes.map((ligne, index) => `
                                    <div class="materiaux-item" data-index="${index}">
                                        <input type="text" placeholder="Désignation" class="designation" value="${ligne.designation}" style="flex:2">
                                        <input type="number" placeholder="Quantité" class="quantite" value="${ligne.quantite}" style="flex:1">
                                        <input type="number" placeholder="Prix unitaire" class="prix" value="${ligne.prix_unitaire}" style="flex:1">
                                        <button type="button" class="remove-item" style="background:#EF4444; color:white; border:none; border-radius:6px; padding:8px; cursor:pointer;">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </div>
                                `).join('')}
                            </div>
                            <button type="button" id="edit-add-materiaux" class="btn-secondary" style="margin-top:10px; width:100%;">
                                <i class="fas fa-plus"></i> Ajouter un matériau
                            </button>
                        </div>
                        
                        <div class="form-group" style="background:rgba(0,0,0,0.3); padding:15px; border-radius:12px; margin-top:15px;">
                            <label><i class="fas fa-calculator"></i> Récapitulatif</label>
                            <div style="margin-top:10px;">
                                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                                    <span>Sous-total matériaux:</span>
                                    <span id="edit-sous-total-materiaux" style="font-weight:bold;">0 FCFA</span>
                                </div>
                                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                                    <span>Main d'œuvre (20%):</span>
                                    <span id="edit-main-oeuvre" style="font-weight:bold;">0 FCFA</span>
                                </div>
                                <div style="border-top:1px solid rgba(255,255,255,0.2); margin:10px 0; padding-top:10px;">
                                    <div style="display:flex; justify-content:space-between; font-size:1.2rem;">
                                        <strong>TOTAL TTC:</strong>
                                        <span id="edit-total-estime" style="font-weight:bold; color:#06B6D4;">0 FCFA</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="form-actions">
                            <button type="submit" class="btn-primary">Enregistrer les modifications</button>
                            <button type="button" class="btn-secondary close-modal">Annuler</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Fonction de calcul
        const calculateTotal = () => {
            const items = modal.querySelectorAll('#edit-materiaux-list .materiaux-item');
            let totalMateriaux = 0;
            items.forEach(item => {
                const quantite = parseFloat(item.querySelector('.quantite')?.value) || 0;
                const prix = parseFloat(item.querySelector('.prix')?.value) || 0;
                totalMateriaux += quantite * prix;
            });
            const mainOeuvre = totalMateriaux * 0.2;
            const total = totalMateriaux + mainOeuvre;
            
            modal.querySelector('#edit-sous-total-materiaux').textContent = totalMateriaux.toLocaleString() + ' FCFA';
            modal.querySelector('#edit-main-oeuvre').textContent = mainOeuvre.toLocaleString() + ' FCFA';
            modal.querySelector('#edit-total-estime').textContent = total.toLocaleString() + ' FCFA';
        };
        
        // Ajouter un matériau
        const addBtn = modal.querySelector('#edit-add-materiaux');
        addBtn.addEventListener('click', () => {
            const container = modal.querySelector('#edit-materiaux-list');
            const newItem = document.createElement('div');
            newItem.className = 'materiaux-item';
            newItem.style.display = 'flex';
            newItem.style.gap = '10px';
            newItem.style.marginBottom = '10px';
            newItem.innerHTML = `
                <input type="text" placeholder="Désignation" class="designation" style="flex:2; padding:8px; border-radius:6px; background:#0F172A; border:1px solid #334155; color:white;">
                <input type="number" placeholder="Quantité" class="quantite" value="1" style="flex:1; padding:8px; border-radius:6px; background:#0F172A; border:1px solid #334155; color:white;">
                <input type="number" placeholder="Prix unitaire" class="prix" style="flex:1; padding:8px; border-radius:6px; background:#0F172A; border:1px solid #334155; color:white;">
                <button type="button" class="remove-item" style="background:#EF4444; color:white; border:none; border-radius:6px; padding:8px; cursor:pointer;">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            newItem.querySelector('.remove-item').addEventListener('click', () => {
                newItem.remove();
                calculateTotal();
            });
            newItem.querySelectorAll('input').forEach(input => {
                input.addEventListener('input', () => calculateTotal());
            });
            container.appendChild(newItem);
            calculateTotal();
        });
        
        // Événements existants
        modal.querySelectorAll('#edit-materiaux-list .remove-item').forEach(btn => {
            btn.addEventListener('click', () => {
                btn.closest('.materiaux-item').remove();
                calculateTotal();
            });
        });
        modal.querySelectorAll('#edit-materiaux-list input').forEach(input => {
            input.addEventListener('input', () => calculateTotal());
        });
        
        // Fermeture
        const closeBtns = modal.querySelectorAll('.close-modal');
        closeBtns.forEach(btn => btn.addEventListener('click', () => modal.remove()));
        
        // Soumission
        const form = modal.querySelector('#edit-devis-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const id_client = modal.querySelector('#edit-devis-client').value;
            const id_projet = modal.querySelector('#edit-devis-projet').value;
            
            if (!id_client || !id_projet) {
                alert('Veuillez sélectionner un client et un projet');
                return;
            }
            
            const lignes = [];
            const items = modal.querySelectorAll('#edit-materiaux-list .materiaux-item');
            items.forEach(item => {
                const designation = item.querySelector('.designation')?.value;
                const quantite = parseFloat(item.querySelector('.quantite')?.value);
                const prix_unitaire = parseFloat(item.querySelector('.prix')?.value);
                if (designation && quantite > 0 && prix_unitaire > 0) {
                    lignes.push({ designation, quantite, prix_unitaire });
                }
            });
            
            if (lignes.length === 0) {
                alert('Veuillez ajouter au moins un matériau');
                return;
            }
            
            const devisData = {
                id_client: parseInt(id_client),
                id_projet: parseInt(id_projet),
                lignes: lignes
            };
            
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enregistrement...';
            submitBtn.disabled = true;
            
            try {
                const response = await apiRequest(`/api/devis/${id}`, {
                    method: 'PUT',
                    body: JSON.stringify(devisData)
                });
                const result = await response.json();
                if (result.success) {
                    alert('✅ Devis modifié avec succès !');
                    modal.remove();
                    this.loadPage('devis');
                } else {
                    alert('❌ ' + (result.message || 'Erreur lors de la modification'));
                }
            } catch (error) {
                alert('❌ Erreur de connexion');
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });
        
        calculateTotal();
        
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors du chargement du devis');
    }
}



async renderParametres() {
    try {
        const response = await apiRequest('/api/settings');
        const data = await response.json();
        const settings = data.settings || {};
        
        return `
            <div class="page-content">
                <h2><i class="fas fa-sliders-h"></i> Personnalisation</h2>
                <p style="color:#94A3B8; margin-bottom:1.5rem;">Personnalisez votre application et gérez votre compte</p>
                
                <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(350px,1fr)); gap:1.5rem;">
                    
                    <!-- Informations entreprise -->
                    <div class="glass-card">
                        <h3><i class="fas fa-building"></i> Informations entreprise</h3>
                        <form id="company-form">
                            <div class="form-group">
                                <label>Nom de l'entreprise</label>
                                <input type="text" id="company-name" value="${settings.company_name || ''}" class="form-control" placeholder="Votre entreprise" oninput="app.updatePreview()">
                            </div>
                            <div class="form-group">
                                <label>Email</label>
                                <input type="email" id="company-email" value="${settings.company_email || ''}" class="form-control" placeholder="contact@entreprise.com" oninput="app.updatePreview()">
                            </div>
                            <div class="form-group">
                                <label>Téléphone</label>
                                <input type="tel" id="company-phone" value="${settings.company_phone || ''}" class="form-control" placeholder="01 23 45 67 89" oninput="app.updatePreview()">
                            </div>
                            <div class="form-group">
                                <label>Adresse</label>
                                <textarea id="company-address" rows="2" class="form-control" placeholder="Adresse complète" oninput="app.updatePreview()">${settings.company_address || ''}</textarea>
                            </div>
                            <button type="submit" class="btn-primary"><i class="fas fa-save"></i> Enregistrer</button>
                        </form>
                    </div>
                    
                    <!-- Logo -->
                    <div class="glass-card">
                        <h3><i class="fas fa-image"></i> Logo</h3>
                        <div style="text-align:center; margin-bottom:1rem;">
                            ${settings.company_logo ? 
                                `<img src="${API_URL}/uploads/${settings.company_logo}" id="logo-preview" style="max-width:150px; max-height:150px; border-radius:10px; object-fit:contain;">` : 
                                `<div id="logo-preview" style="width:150px; height:150px; background:#334155; border-radius:10px; margin:0 auto; display:flex; align-items:center; justify-content:center;">
                                    <i class="fas fa-image" style="font-size:48px; color:#64748B;"></i>
                                </div>`
                            }
                        </div>
                        <form id="logo-form" enctype="multipart/form-data">
                            <input type="file" id="company-logo" accept="image/*" class="form-control">
                            <button type="submit" class="btn-primary" style="margin-top:1rem;"><i class="fas fa-upload"></i> Télécharger logo</button>
                        </form>
                    </div>
                    
                    <!-- Couleurs -->
                    <div class="glass-card">
                        <h3><i class="fas fa-palette"></i> Couleurs personnalisées</h3>
                        <form id="colors-form">
                            <div class="form-group">
                                <label>Couleur principale</label>
                                <input type="color" id="primary-color" value="${settings.primary_color || '#1E3A8A'}" style="width:100%; height:40px;" oninput="app.updatePreview()">
                            </div>
                            <div class="form-group">
                                <label>Couleur secondaire</label>
                                <input type="color" id="secondary-color" value="${settings.secondary_color || '#7C3AED'}" style="width:100%; height:40px;" oninput="app.updatePreview()">
                            </div>
                            <div class="form-group">
                                <label>Couleur d'accent</label>
                                <input type="color" id="accent-color" value="${settings.accent_color || '#06B6D4'}" style="width:100%; height:40px;" oninput="app.updatePreview()">
                            </div>
                            <button type="submit" class="btn-primary"><i class="fas fa-palette"></i> Appliquer</button>
                        </form>
                    </div>
                </div>
                
                <!-- ========== APERÇU EN DIRECT ========== -->
                <div class="glass-card" style="margin-top:1.5rem;">
                    <h3><i class="fas fa-eye"></i> Aperçu en direct</h3>
                    <p style="font-size:0.85rem; color:#94A3B8; margin-bottom:1rem;">Voici à quoi ressemblera votre entreprise sur les devis et factures</p>
                    
                    <div style="background:linear-gradient(135deg, #0F172A 0%, #1E293B 100%); border-radius:15px; padding:1.5rem;">
                        <div style="display:flex; gap:1rem; align-items:center; flex-wrap:wrap; margin-bottom:1rem;">
                            ${settings.company_logo ? 
                                `<img src="${API_URL}/uploads/${settings.company_logo}" id="preview-logo" style="height:60px; border-radius:10px; object-fit:contain;">` : 
                                `<div id="preview-logo" style="width:60px; height:60px; background:#334155; border-radius:10px; display:flex; align-items:center; justify-content:center;">
                                    <i class="fas fa-building" style="font-size:24px; color:#64748B;"></i>
                                </div>`
                            }
                            <div>
                                <strong id="preview-company-name" style="color:${settings.primary_color || '#1E3A8A'}; font-size:1.2rem;">${settings.company_name || 'Votre entreprise'}</strong>
                                <p id="preview-contact" style="font-size:0.8rem; color:#94A3B8; margin-top:5px;">
                                    ${settings.company_email || 'email@entreprise.com'} | ${settings.company_phone || 'téléphone'}
                                </p>
                                <p id="preview-address" style="font-size:0.75rem; color:#64748B;">${settings.company_address || 'Adresse de votre entreprise'}</p>
                            </div>
                        </div>
                        
                        <!-- Aperçu du devis -->
                        <div style="border-top:1px solid #334155; padding-top:1rem; margin-top:0.5rem;">
                            <p style="font-size:0.8rem; color:#94A3B8;">📄 Exemple d'en-tête de devis :</p>
                            <div style="background:#1E293B; border-radius:10px; padding:0.75rem;">
                                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
                                    <div style="display:flex; align-items:center; gap:0.5rem;">
                                        ${settings.company_logo ? 
                                            `<img src="${API_URL}/uploads/${settings.company_logo}" style="height:30px;">` : 
                                            `<i class="fas fa-hard-hat" style="font-size:24px; color:${settings.primary_color || '#1E3A8A'}"></i>`
                                        }
                                        <span style="font-weight:bold; color:${settings.primary_color || '#1E3A8A'}">${settings.company_name || 'BTP Pro'}</span>
                                    </div>
                                    <span style="font-size:0.7rem; color:#64748B;">DEVIS PROFESSIONNEL</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section Backup/Restore -->
<div class="glass-card" style="margin-top:1.5rem;">
    <h3><i class="fas fa-database"></i> Sauvegarde des données</h3>
    <div style="display:flex; gap:1rem; flex-wrap:wrap; margin-top:1rem;">
        <button class="btn-primary" onclick="app.backupData()" style="background:#10B981; border-color:#10B981;">
            <i class="fas fa-download"></i> Télécharger sauvegarde
        </button>
        <button class="btn-secondary" onclick="app.restoreData()" style="background:#F59E0B; border-color:#F59E0B;">
            <i class="fas fa-upload"></i> Restaurer sauvegarde
        </button>
    </div>
    <p style="font-size:0.8rem; color:#94A3B8; margin-top:1rem;">
        <i class="fas fa-info-circle"></i> La sauvegarde contient tous vos clients, projets, devis, factures et paramètres.
    </p>
</div>
                
                <!-- ========== SECTION DÉCONNEXION STYLÉE ========== -->
                <div class="glass-card" style="margin-top:1.5rem; border:1px solid rgba(239,68,68,0.3);">
                    <h3><i class="fas fa-shield-alt" style="color:#F87171;"></i> Sécurité du compte</h3>
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; margin-top:1rem;">
                        <div>
                            <p style="margin-bottom:5px;">Connecté en tant que : <strong>${this.currentUser.nom || this.currentUser.email}</strong></p>
                            <p style="font-size:0.85rem; color:#94A3B8;">${this.currentUser.email}</p>
                            <p style="font-size:0.8rem; color:#64748B; margin-top:5px;">
                                <i class="fas fa-building"></i> ${this.currentUser.entreprise || 'BTP Pro'}
                            </p>
                        </div>
                        <button class="btn-logout" onclick="app.logout()">
                            <i class="fas fa-sign-out-alt"></i> Se déconnecter
                        </button>
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Erreur:', error);
        return '<div class="glass-card">Erreur chargement paramètres</div>';
    }
}

updatePreview() {
    const companyName = document.getElementById('company-name')?.value;
    const companyEmail = document.getElementById('company-email')?.value;
    const companyPhone = document.getElementById('company-phone')?.value;
    const companyAddress = document.getElementById('company-address')?.value;
    const primaryColor = document.getElementById('primary-color')?.value;
    
    const previewName = document.getElementById('preview-company-name');
    const previewContact = document.getElementById('preview-contact');
    const previewAddress = document.getElementById('preview-address');
    
    if (previewName) {
        previewName.textContent = companyName || 'Votre entreprise';
        if (primaryColor) previewName.style.color = primaryColor;
    }
    if (previewContact) {
        const email = companyEmail || 'email@entreprise.com';
        const phone = companyPhone || 'téléphone';
        previewContact.textContent = `${email} | ${phone}`;
    }
    if (previewAddress) {
        previewAddress.textContent = companyAddress || 'Adresse de votre entreprise';
    }
}

async uploadLogo() {
    const fileInput = document.getElementById('company-logo');
    const file = fileInput.files[0];
    if (!file) {
        alert('Veuillez sélectionner un fichier');
        return;
    }
    
    const formData = new FormData();
    formData.append('logo', file);
    
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_URL}/api/settings/logo`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        const result = await response.json();
        if (result.success) {
            alert('✅ Logo téléchargé avec succès !');
            this.loadPage('parametres');
        } else {
            alert('❌ ' + result.message);
        }
    } catch (error) {
        alert('❌ Erreur lors du téléchargement');
    }
}

async saveCompanySettings() {
    const settings = {
        company_name: document.getElementById('company-name').value,
        company_email: document.getElementById('company-email').value,
        company_phone: document.getElementById('company-phone').value,
        company_address: document.getElementById('company-address').value
    };
    
    try {
        const response = await apiRequest('/api/settings', { method: 'PUT', body: JSON.stringify(settings) });
        const result = await response.json();
        if (result.success) {
            alert('✅ Informations enregistrées');
            this.loadPage('parametres');
        }
    } catch (error) {
        alert('❌ Erreur');
    }
}

async saveColorSettings() {
    const settings = {
        primary_color: document.getElementById('primary-color').value,
        secondary_color: document.getElementById('secondary-color').value,
        accent_color: document.getElementById('accent-color').value
    };
    
    try {
        const response = await apiRequest('/api/settings', { method: 'PUT', body: JSON.stringify(settings) });
        const result = await response.json();
        if (result.success) {
            alert('✅ Couleurs appliquées');
            this.applyThemeColors(settings);
        }
    } catch (error) {
        alert('❌ Erreur');
    }
}

applyThemeColors(colors) {
    document.documentElement.style.setProperty('--primary', colors.primary_color);
    document.documentElement.style.setProperty('--secondary', colors.secondary_color);
    document.documentElement.style.setProperty('--accent', colors.accent_color);
}


// Récupérer et afficher les notifications
async fetchNotifications() {
    try {
        const response = await apiRequest('/api/notifications');
        return await response.json();
    } catch (error) {
        return [];
    }
}

// Afficher les notifications au chargement
async showNotifications() {
    const notifications = await this.fetchNotifications();
    
    if (notifications.length === 0) return;
    
    // Afficher une par une avec un délai
    for (const notif of notifications) {
        setTimeout(() => {
            this.showNotificationToast(notif);
        }, 1000);
    }
}

// Afficher une notification toast
showNotificationToast(notification) {
    const toast = document.createElement('div');
    toast.className = 'notification-toast';
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(135deg, #1E3A8A, #7C3AED);
        color: white;
        padding: 15px 20px;
        border-radius: 12px;
        z-index: 10001;
        max-width: 350px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        animation: slideInRight 0.5s ease;
        cursor: pointer;
    `;
    
    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px;">
            <i class="fas fa-bell" style="font-size: 20px;"></i>
            <div style="flex: 1;">
                <strong style="display: block; margin-bottom: 5px;">Renouvellement d'abonnement</strong>
                <span style="font-size: 0.85rem;">${notification.message}</span>
            </div>
            <i class="fas fa-times" style="cursor: pointer; opacity: 0.7;"></i>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Fermeture manuelle
    toast.querySelector('.fa-times').addEventListener('click', (e) => {
        e.stopPropagation();
        toast.remove();
        this.marquerNotificationLue(notification.id_notification);
    });
    
    // Fermeture automatique après 8 secondes
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideOutRight 0.5s ease';
            setTimeout(() => {
                toast.remove();
                this.marquerNotificationLue(notification.id_notification);
            }, 500);
        }
    }, 8000);
}

async marquerNotificationLue(id) {
    try {
        await apiRequest(`/api/notifications/${id}/lire`, { method: 'PUT' });
    } catch (error) {
        console.error('Erreur:', error);
    }
}

async checkLimites(operation) {
    const user = this.currentUser;
    if (user.email === 'admin@btp.com') return true;
    
    const abonnement = await this.getAbonnement();
    const offre = abonnement?.type_abonnement || 'starter';
    
    const limites = {
        starter: { clients: 10, projets: 10, devis: 20 },
        pro: { clients: 999999, projets: 999999, devis: 999999 },
        annuel: { clients: 999999, projets: 999999, devis: 999999 }
    };
    
    const counts = await this.getCurrentCounts();
    
    if (operation === 'client' && counts.clients >= limites[offre].clients) {
        Toast.warning(`Limite de clients atteinte (${limites[offre].clients}). Passez à l'offre Pro !`);
        return false;
    }
    if (operation === 'projet' && counts.projets >= limites[offre].projets) {
        Toast.warning(`Limite de projets atteinte (${limites[offre].projets}). Passez à l'offre Pro !`);
        return false;
    }
    if (operation === 'devis' && counts.devis >= limites[offre].devis) {
        Toast.warning(`Limite de devis atteinte (${limites[offre].devis}). Passez à l'offre Pro !`);
        return false;
    }
    return true;
}

// ==================== BACKUP & RESTORE ====================
async backupData() {
    try {
        console.log("🔵 Début de la sauvegarde...");
        const response = await apiRequest('/api/backup');
        const data = await response.json();
        
        console.log("📦 Données reçues:", data);
        
        // Vérifier que les données sont valides
        if (!data || !data.clients) {
            throw new Error('Données de sauvegarde invalides');
        }
        
        // Créer le fichier JSON
        const jsonString = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        // Créer le lien de téléchargement
        const a = document.createElement('a');
        a.href = url;
        a.download = `backup_btp_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        // Libérer l'URL
        URL.revokeObjectURL(url);
        
        Toast.success('Sauvegarde effectuée avec succès !');
    } catch (error) {
        console.error('❌ Erreur backup:', error);
        Toast.error('Erreur lors de la sauvegarde: ' + error.message);
    }
}

async restoreData() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        const reader = new FileReader();
        reader.onload = async (event) => {
            if (confirm('⚠️ RESTAURATION TOTALE : TOUTES les données actuelles seront REMPLACÉES. Continuer ?')) {
                try {
                    // Afficher le message de chargement
                    const loadingDiv = document.createElement('div');
                    loadingDiv.id = 'restore-loading';
                    loadingDiv.style.cssText = `
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0,0,0,0.9);
                        z-index: 20000;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        flex-direction: column;
                        color: white;
                        font-family: Arial, sans-serif;
                    `;
                    loadingDiv.innerHTML = `
                        <div style="background: #1E293B; padding: 30px 50px; border-radius: 20px; text-align: center; border: 1px solid #06B6D4;">
                            <i class="fas fa-spinner fa-spin" style="font-size: 48px; margin-bottom: 20px; color: #06B6D4;"></i>
                            <h3>Restauration en cours...</h3>
                            <p style="margin-top: 10px; color: #94A3B8;">Veuillez patienter, cette opération peut prendre quelques secondes.</p>
                            <p style="font-size: 12px; margin-top: 15px;">Ne fermez pas cette fenêtre</p>
                        </div>
                    `;
                    document.body.appendChild(loadingDiv);
                    
                    const data = JSON.parse(event.target.result);
                    
                    // Timeout de 30 secondes
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), 30000);
                    
                    const response = await fetch(`${API_URL}/api/restore`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${localStorage.getItem('token')}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data),
                        signal: controller.signal
                    });
                    
                    clearTimeout(timeoutId);
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        loadingDiv.innerHTML = `
                            <div style="background: #1E293B; padding: 30px 50px; border-radius: 20px; text-align: center; border: 1px solid #10B981;">
                                <i class="fas fa-check-circle" style="font-size: 48px; margin-bottom: 20px; color: #10B981;"></i>
                                <h3>✅ Restauration réussie !</h3>
                                <p style="margin-top: 10px;">Redirection vers la page de connexion...</p>
                            </div>
                        `;
                        
                        setTimeout(() => {
                            localStorage.removeItem('token');
                            localStorage.removeItem('user');
                            window.location.href = 'login.html';
                        }, 2000);
                    } else {
                        loadingDiv.remove();
                        alert('❌ Erreur: ' + result.error);
                    }
                } catch (error) {
                    document.getElementById('restore-loading')?.remove();
                    console.error('Erreur:', error);
                    if (error.name === 'AbortError') {
                        alert('❌ La restauration a pris trop de temps. Vérifiez votre connexion.');
                    } else {
                        alert('❌ Fichier invalide: ' + error.message);
                    }
                }
            }
        };
        reader.readAsText(file);
    };
    input.click();
}


// ==================== PAGE ADMIN ====================
async renderAdmin() {
    try {
        const user = this.currentUser;
        const isAdmin = user && (user.email === 'admin@btp.com' || user.email === 'bylgaitb@gmail.com');
        
        if (!isAdmin) {
            return '<div class="glass-card">Accès non autorisé</div>';
        }
        
        const abonnements = await this.fetchAbonnements();
        
        if (!abonnements || abonnements.length === 0) {
            return '<div class="glass-card">Aucun abonnement trouvé</div>';
        }
        
        return `
            <div class="page-content">
                <h2><i class="fas fa-chart-line"></i> Administration</h2>
                <p style="color:#94A3B8; margin-bottom:1.5rem;">Gestion des abonnements clients</p>
                
                <div style="display:flex; justify-content:space-between; margin-bottom:1rem; flex-wrap:wrap; gap:1rem;">
                    <div class="search-box">
                        <i class="fas fa-search"></i>
                        <input type="text" id="admin-search" placeholder="Rechercher..." oninput="app.filterAdminAbonnements()">
                    </div>
                    <button class="btn-secondary" onclick="app.exportAbonnements()" style="background:#10B981;">
                        <i class="fas fa-file-excel"></i> Export Excel
                    </button>
                </div>
                
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Client</th>
                                <th>Email</th>
                                <th>Entreprise</th>
                                <th>Offre</th>
                                <th>Statut</th>
                                <th>Expire le</th>
                                <th>Jours restants</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="admin-table-body">
                            ${abonnements.map(a => `
                                <tr>
                                    <td>${a.nom || '-'}</td>
                                    <td>${a.email}</td>
                                    <td>${a.entreprise || '-'}</td>
                                    <td>
                                        <select onchange="app.changerOffre(${a.id_user}, this.value)" class="filter-select">
                                            <option value="starter" ${a.type_abonnement === 'starter' ? 'selected' : ''}>🟢 Starter (15k)</option>
                                            <option value="pro" ${a.type_abonnement === 'pro' ? 'selected' : ''}>🔵 Pro (30k)</option>
                                            <option value="annuel" ${a.type_abonnement === 'annuel' ? 'selected' : ''}>🔴 Annuel (250k)</option>
                                        </select>
                                    </div>
                                    <td>
                                        <span class="status-badge ${a.statut === 'actif' ? 'success' : 'warning'}">
                                            ${a.statut || 'inactif'}
                                        </span>
                                    </div>
                                    <td>${a.date_fin ? new Date(a.date_fin).toLocaleDateString() : '-'}</div>
                                    <td>
                                        <span style="color:${a.jours_restants < 7 ? '#F87171' : '#10B981'}; font-weight:bold;">
                                            ${a.jours_restants > 0 ? a.jours_restants + ' jours' : 'Expiré'}
                                        </span>
                                    </div>
                                    <td>
    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
        <!-- Offre Starter (15k - 30 jours) -->
        <div class="admin-tooltip" data-tooltip="Starter: 10 clients, 10 projets, 20 devis max">
            <button class="btn-offer starter" onclick="app.prolongerAbonnement(${a.id_user}, 30, 15000, 'starter')">
                🟢 +30j <span class="offer-price">15k</span>
            </button>
        </div>
        
        <!-- Offre Pro (30k - 30 jours) -->
        <div class="admin-tooltip" data-tooltip="Pro: Illimité, export Excel, factures">
            <button class="btn-offer pro" onclick="app.prolongerAbonnement(${a.id_user}, 30, 30000, 'pro')">
                🔵 +30j <span class="offer-price">30k</span>
            </button>
        </div>
        
        <!-- Offre Annuel (250k - 365 jours) -->
        <div class="admin-tooltip" data-tooltip="Annuel: Illimité + support prioritaire">
            <button class="btn-offer annuel" onclick="app.prolongerAbonnement(${a.id_user}, 365, 250000, 'annuel')">
                🔴 +1an <span class="offer-price">250k</span>
            </button>
        </div>
        
        <!-- Menu déroulant pour changer l'offre -->
        <select onchange="app.changerOffre(${a.id_user}, this.value)" class="filter-select" style="padding: 8px; border-radius: 8px;">
            <option value="starter" ${a.type_abonnement === 'starter' ? 'selected' : ''}>🟢 Starter</option>
            <option value="pro" ${a.type_abonnement === 'pro' ? 'selected' : ''}>🔵 Pro</option>
            <option value="annuel" ${a.type_abonnement === 'annuel' ? 'selected' : ''}>🔴 Annuel</option>
        </select>
        
        <!-- Suspendre -->
        <button class="btn-icon suspend" onclick="app.suspendreAbonnement(${a.id_user})" title="Suspendre">
            <i class="fas fa-pause-circle"></i>
        </button>
        
        <!-- Historique -->
        <button class="btn-icon history" onclick="app.voirPaiements(${a.id_user})" title="Historique">
            <i class="fas fa-history"></i>
        </button>
    </div>
</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Erreur:', error);
        return '<div class="glass-card">Erreur chargement admin</div>';
    }
}

async fetchAbonnements() {
    try {
        const response = await apiRequest('/api/admin/abonnements');
        return await response.json();
    } catch (error) {
        console.error('Erreur:', error);
        return [];
    }
}

async prolongerAbonnement(id_user, jours, montant, offreType) {
    const methode = prompt(`💰 Confirmation paiement\n\nClient: ID ${id_user}\nOffre: ${offreType}\nDurée: ${jours} jours\nMontant: ${montant.toLocaleString()} FCFA\n\nMéthode de paiement reçue ?\n- Virement\n- Mobile Money\n- Espèces`, 'virement');
    if (!methode) return;
    
    if (confirm(`✅ Confirmer le paiement de ${montant.toLocaleString()} FCFA pour l'offre ${offreType} ?`)) {
        try {
            const response = await apiRequest(`/api/admin/abonnement/${id_user}/prolonger`, {
                method: 'POST',
                body: JSON.stringify({ jours, montant, methode, offreType })
            });
            const result = await response.json();
            if (result.success) {
                alert(`✅ Abonnement ${offreType} prolongé de ${jours} jours !`);
                this.loadPage('admin');
            } else {
                alert('❌ ' + result.error);
            }
        } catch (error) {
            alert('❌ Erreur');
        }
    }
}


// Afficher le bandeau d'abonnement dans le dashboard
translatePage() {
    // Traduire les éléments avec l'attribut data-i18n
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        el.textContent = t(key);
    });
}


// Dans app.js, après init()
setupDesktopMenu() {
    if (window.electronAPI) {
        console.log("💻 Application desktop détectée");
        
        window.electronAPI.onMenuBackup(() => {
            this.backupData();
        });
        
        window.electronAPI.onMenuRestore(() => {
            this.restoreData();
        });
        
        window.electronAPI.onMenuExportDevis(() => {
            this.exportDevisToExcel();
        });
    }
}

// Afficher la modale des offres
showPricingModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="pricing-modal">
            <div class="pricing-modal-header">
                <h2>Choisissez votre formule</h2>
                <p>Des tarifs adaptés à votre activité. Sans engagement.</p>
                <i class="fas fa-times close-modal"></i>
            </div>
            <div class="pricing-cards">
                <!-- Offre Starter -->
                <div class="pricing-card">
                    <div class="pricing-card-header">
                        <div class="pricing-icon">🟢</div>
                        <h3>Starter</h3>
                        <div class="pricing-price">15 000 <span>FCFA/mois</span></div>
                    </div>
                    <div class="pricing-features">
                        <div class="feature"><i class="fas fa-check-circle"></i> Jusqu'à 10 clients</div>
                        <div class="feature"><i class="fas fa-check-circle"></i> Jusqu'à 10 projets</div>
                        <div class="feature"><i class="fas fa-check-circle"></i> Jusqu'à 20 devis</div>
                        <div class="feature disabled"><i class="fas fa-times-circle"></i> Export Excel</div>
                        <div class="feature disabled"><i class="fas fa-times-circle"></i> Factures</div>
                        <div class="feature disabled"><i class="fas fa-times-circle"></i> Personnalisation</div>
                    </div>
                    <button class="pricing-btn" onclick="app.contactAdmin('starter')">Contacter l'admin</button>
                </div>

                <!-- Offre Pro (Populaire) -->
                <div class="pricing-card popular">
                    <div class="popular-badge">⭐ Le plus populaire</div>
                    <div class="pricing-card-header">
                        <div class="pricing-icon">🔵</div>
                        <h3>Pro</h3>
                        <div class="pricing-price">30 000 <span>FCFA/mois</span></div>
                    </div>
                    <div class="pricing-features">
                        <div class="feature"><i class="fas fa-check-circle"></i> Clients illimités</div>
                        <div class="feature"><i class="fas fa-check-circle"></i> Projets illimités</div>
                        <div class="feature"><i class="fas fa-check-circle"></i> Devis illimités</div>
                        <div class="feature"><i class="fas fa-check-circle"></i> Export Excel</div>
                        <div class="feature"><i class="fas fa-check-circle"></i> Factures</div>
                        <div class="feature"><i class="fas fa-check-circle"></i> Personnalisation</div>
                    </div>
                    <button class="pricing-btn" onclick="app.contactAdmin('pro')">Contacter l'admin</button>
                </div>

                <!-- Offre Annuel -->
                <div class="pricing-card">
                    <div class="pricing-card-header">
                        <div class="pricing-icon">🔴</div>
                        <h3>Annuel</h3>
                        <div class="pricing-price">250 000 <span>FCFA/an</span></div>
                        <div class="pricing-saving">Économie de 110 000 FCFA</div>
                    </div>
                    <div class="pricing-features">
                        <div class="feature"><i class="fas fa-check-circle"></i> Tout l'offre Pro</div>
                        <div class="feature"><i class="fas fa-check-circle"></i> 2 mois offerts</div>
                        <div class="feature"><i class="fas fa-check-circle"></i> Support prioritaire</div>
                        <div class="feature"><i class="fas fa-check-circle"></i> Formation incluse</div>
                        <div class="feature"><i class="fas fa-check-circle"></i> API dédiée</div>
                    </div>
                    <button class="pricing-btn" onclick="app.contactAdmin('annuel')">Contacter l'admin</button>
                </div>
            </div>
            <div class="pricing-footer">
                <p>Questions ? Contactez-nous à <strong>admin@btp.com</strong></p>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const closeBtns = modal.querySelectorAll('.close-modal');
    closeBtns.forEach(btn => btn.addEventListener('click', () => modal.remove()));
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
}

closeModal() {
    const modal = document.querySelector('.modal');
    if (modal) modal.remove();
}

// Méthode pour contacter l'admin
contactAdmin(offre) {
    const message = `Bonjour, je souhaite souscrire à l'offre ${offre}. Merci de me contacter pour le paiement.`;
    window.location.href = `mailto:admin@btp.com?subject=Abonnement ${offre}&body=${encodeURIComponent(message)}`;
    alert(`📧 Une demande d'abonnement ${offre} a été préparée. Envoyez l'email à l'administrateur.`);
    this.closeModal();
}

async changerOffre(id_user, type_offre) {
    if (confirm(`Changer l'offre vers ${type_offre} ?`)) {
        try {
            const response = await apiRequest(`/api/admin/abonnement/${id_user}/changer-offre`, {
                method: 'POST',
                body: JSON.stringify({ type_offre })
            });
            const result = await response.json();
            if (result.success) {
                alert('✅ Offre modifiée !');
                this.loadPage('admin');
            } else {
                alert('❌ ' + result.error);
            }
        } catch (error) {
            alert('❌ Erreur');
        }
    }
}

async suspendreAbonnement(id_user) {
    if (confirm('Suspendre cet abonnement ?')) {
        try {
            const response = await apiRequest(`/api/admin/abonnement/${id_user}/suspendre`, { method: 'POST' });
            const result = await response.json();
            if (result.success) {
                alert('✅ Abonnement suspendu !');
                this.loadPage('admin');
            } else {
                alert('❌ ' + result.error);
            }
        } catch (error) {
            alert('❌ Erreur');
        }
    }
}

async voirPaiements(id_user) {
    try {
        const response = await apiRequest(`/api/admin/paiements/${id_user}`);
        const paiements = await response.json();
        
        if (paiements.length === 0) {
            alert('Aucun paiement enregistré');
            return;
        }
        
        let message = '📊 Historique des paiements :\n\n';
        paiements.forEach(p => {
            message += `📅 ${new Date(p.date_paiement).toLocaleDateString()} : ${p.montant.toLocaleString()} FCFA (${p.methode})\n`;
            message += `   Réf: ${p.reference_paiement}\n\n`;
        });
        alert(message);
    } catch (error) {
        alert('Erreur chargement historique');
    }
}

async exportAbonnements() {
    try {
        const response = await apiRequest('/api/admin/export-abonnements');
        const data = await response.json();
        
        const headers = ['Nom', 'Email', 'Entreprise', 'Téléphone', 'Offre', 'Statut', 'Date début', 'Date fin', 'Jours restants'];
        const csvRows = [headers.join(',')];
        
        for (const row of data) {
            const values = [
                `"${row.nom || ''}"`,
                `"${row.email}"`,
                `"${row.entreprise || ''}"`,
                `"${row.telephone || ''}"`,
                row.type_abonnement || '-',
                row.statut || '-',
                row.date_debut ? new Date(row.date_debut).toLocaleDateString() : '-',
                row.date_fin ? new Date(row.date_fin).toLocaleDateString() : '-',
                row.jours_restants || 0
            ];
            csvRows.push(values.join(','));
        }
        
        const blob = new Blob(["\uFEFF" + csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `abonnements_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        
        alert('✅ Export terminé');
    } catch (error) {
        alert('❌ Erreur export');
    }
}

async refreshClientsPage() {
    // Vider le cache
    this.allClients = null;
    // Recharger la page
    await this.loadPage('clients');
}

// Filtrage des devis
filterDevis() {
    if (!this.allDevis) return;
    
    let filtered = [...this.allDevis];
    
    // Filtre par recherche (texte)
    const searchTerm = document.getElementById('search-devis')?.value.toLowerCase().trim() || '';
    if (searchTerm) {
        filtered = filtered.filter(d => {
            // Recherche par référence
            if (d.id_devis && d.id_devis.toString().includes(searchTerm)) return true;
            // Recherche par nom du client (normalisé)
            if (d.client_nom && d.client_nom.toLowerCase().includes(searchTerm)) return true;
            // Recherche par nom du projet
            if (d.nom_projet && d.nom_projet.toLowerCase().includes(searchTerm)) return true;
            return false;
        });
    }
    
    // Filtre par statut
    const statusFilter = document.getElementById('filter-status')?.value || 'all';
    if (statusFilter !== 'all') {
        filtered = filtered.filter(d => d.statut === statusFilter);
    }
    
    // Filtre par date
    const dateFilter = document.getElementById('filter-date')?.value || 'all';
    if (dateFilter !== 'all') {
        const days = parseInt(dateFilter);
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - days);
        filtered = filtered.filter(d => new Date(d.date_creation) >= cutoffDate);
    }
    
    // Mettre à jour l'affichage
    const tbody = document.getElementById('devis-table-body');
    const countDiv = document.getElementById('devis-count');
    
    if (tbody) {
        tbody.innerHTML = this.renderDevisTableRows(filtered);
    }
    if (countDiv) {
        countDiv.innerHTML = `${filtered.length} devis sur ${this.allDevis.length}`;
    }
    
    console.log(`🔍 Recherche: "${searchTerm}" -> ${filtered.length} résultats`);
    console.log("Termes trouvés:", filtered.map(d => d.client_nom));
}

async showSubscriptionBanner() {
    console.log("🟢 showSubscriptionBanner appelée");
    
    try {
        const response = await apiRequest('/api/abonnement/statut');
        const data = await response.json();
        
        console.log("Données complètes:", data);
        
        if (!data.success || data.statut !== 'actif') {
            console.log("❌ Pas d'abonnement actif");
            return;
        }
        
        // Supprimer l'ancien bandeau
        const oldBanner = document.getElementById('subscription-banner');
        if (oldBanner) oldBanner.remove();
        
        // 👇 ICI LA CORRECTION : on utilise directement data.type
        const offre = data.type || 'starter';
        const joursRestants = data.jours_restants || 0;
        const dateFin = data.date_fin ? new Date(data.date_fin).toLocaleDateString() : 'inconnue';
        
        let bgColor = '';
        let icon = '';
        let message = '';
        let buttonHtml = '';
        
        // Essai gratuit
        if (offre === 'essai' && joursRestants > 0) {
            bgColor = 'linear-gradient(135deg, #1E3A8A, #7C3AED)';
            icon = 'fa-gift';
            message = `🎁 Période d'essai gratuite : plus que ${joursRestants} jour(s) !`;
            buttonHtml = `<button class="btn-primary" onclick="app.showPricingModal()" style="background:#10B981;">S'abonner</button>`;
        }
        // Starter
        else if (offre === 'starter') {
            bgColor = 'linear-gradient(135deg, #059669, #10B981)';
            icon = 'fa-leaf';
            message = `🟢 Abonnement Starter actif - Expire le ${dateFin} (${joursRestants} jours restants)`;
            buttonHtml = `<button class="btn-secondary" onclick="app.showPricingModal()">Changer d'offre</button>`;
        }
        // Pro
        else if (offre === 'pro') {
            bgColor = 'linear-gradient(135deg, #1E3A8A, #06B6D4)';
            icon = 'fa-crown';
            message = `🔵 Abonnement Pro actif - Expire le ${dateFin} (${joursRestants} jours restants)`;
            buttonHtml = `<button class="btn-secondary" onclick="app.showPricingModal()">Changer d'offre</button>`;
        }
        // Annuel
        else if (offre === 'annuel') {
            bgColor = 'linear-gradient(135deg, #DC2626, #F59E0B)';
            icon = 'fa-gem';
            message = `🔴 Abonnement Annuel actif - Expire le ${dateFin} (${joursRestants} jours restants)`;
            buttonHtml = `<button class="btn-secondary" onclick="app.showPricingModal()">Changer d'offre</button>`;
        }
        // Autre
        else if (joursRestants > 0) {
            bgColor = 'linear-gradient(135deg, #1E3A8A, #7C3AED)';
            icon = 'fa-calendar-check';
            message = `✅ Abonnement actif - Expire le ${dateFin} (${joursRestants} jours restants)`;
            buttonHtml = `<button class="btn-secondary" onclick="app.showPricingModal()">Changer d'offre</button>`;
        }
        // Expiré
        else {
            bgColor = 'linear-gradient(135deg, #991B1B, #EF4444)';
            icon = 'fa-exclamation-triangle';
            message = `⛔ Votre abonnement est expiré. Renouvelez maintenant !`;
            buttonHtml = `<button class="btn-primary" onclick="app.showPricingModal()" style="background:#F59E0B;">Renouveler</button>`;
        }
        
        const banner = document.createElement('div');
        banner.id = 'subscription-banner';
        banner.style.cssText = `
            background: ${bgColor};
            border-radius: 15px;
            padding: 15px 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            animation: slideDown 0.5s ease;
        `;
        
        banner.innerHTML = `
            <div>
                <i class="fas ${icon}" style="margin-right: 10px;"></i>
                <strong>${message}</strong>
            </div>
            ${buttonHtml}
        `;
        
        // Insérer le bandeau
        const cardsGrid = document.querySelector('.cards-grid');
        if (cardsGrid && !document.getElementById('subscription-banner')) {
            cardsGrid.parentNode.insertBefore(banner, cardsGrid);
            console.log("✅ Bandeau ajouté");
        } else if (!document.getElementById('subscription-banner')) {
            const contentArea = document.getElementById('content-area');
            if (contentArea) {
                contentArea.insertBefore(banner, contentArea.firstChild);
                console.log("✅ Bandeau ajouté");
            }
        }
        
    } catch (error) {
        console.error("❌ Erreur:", error);
    }
}

async checkLimites(operation) {
    const user = this.currentUser;
    if (user.email === 'admin@btp.com') return true;
    
    try {
        const response = await apiRequest('/api/abonnement/statut');
        const data = await response.json();
        
        if (!data.success || data.statut !== 'actif') {
            Toast.warning('Abonnement inactif. Contactez l\'administrateur.');
            return false;
        }
        
        const offre = data.type_abonnement || 'starter';
        
        const limites = {
            starter: { clients: 10, projets: 10, devis: 20 },
            pro: { clients: 999999, projets: 999999, devis: 999999 },
            annuel: { clients: 999999, projets: 999999, devis: 999999 },
            essai: { clients: 999999, projets: 999999, devis: 999999 }
        };
        
        // Compter les éléments actuels
        const clients = await this.fetchClients();
        const projets = await this.fetchProjets();
        const devis = await this.fetchDevis();
        
        const counts = {
            clients: clients.length,
            projets: projets.length,
            devis: devis.length
        };
        
        if (operation === 'client' && counts.clients >= limites[offre].clients) {
            Toast.warning(`Limite de clients atteinte (${limites[offre].clients}). Passez à l'offre Pro !`);
            return false;
        }
        if (operation === 'projet' && counts.projets >= limites[offre].projets) {
            Toast.warning(`Limite de projets atteinte (${limites[offre].projets}). Passez à l'offre Pro !`);
            return false;
        }
        if (operation === 'devis' && counts.devis >= limites[offre].devis) {
            Toast.warning(`Limite de devis atteinte (${limites[offre].devis}). Passez à l'offre Pro !`);
            return false;
        }
        
        return true;
    } catch (error) {
        console.error('Erreur checkLimites:', error);
        return true;
    }
}

// Traduire les textes statiques

}
// Fonction de formatage des nombres
function formatMoney(amount) {
    if (!amount && amount !== 0) return '0 FCFA';
    const num = Math.round(parseFloat(amount));
    return num.toLocaleString('fr-FR') + ' FCFA';
}

// Initialisation
app = new BTPDevisApp();