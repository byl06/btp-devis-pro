// Configuration
// Configuration API - détection automatique
const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_URL = isLocal ? 'http://localhost:5000' : 'https://btp-devis-pro-1.onrender.com';
const WHATSAPP_NUMBER = "2290143733706";
const WHATSAPP_URL = `https://wa.me/${WHATSAPP_NUMBER}`;

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
        setTimeout(() => {
        this.showSubscriptionBanner();
    }, 1000);
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

    // ===== FORMULAIRES =====
    document.addEventListener('submit', async (e) => {
        const target = e.target;
        
        if (target.id === 'company-form') {
            e.preventDefault();
            await this.saveCompanySettings();
        }
        else if (target.id === 'colors-form') {
            e.preventDefault();
            await this.saveColorSettings();
        }
        else if (target.id === 'logo-form') {
            e.preventDefault();
            await this.uploadLogo();
        }
        else if (target.id === 'change-password-form') {
            e.preventDefault();
            await this.changePassword();
        }
        else if (target.id === 'fiscal-form') {
            e.preventDefault();
            await this.saveFiscalSettings();
        }
        else if (target.id === 'header-form') {
            e.preventDefault();
            await this.saveHeaderSettings();
        }
    });
    
    // ===== FILTRES POUR LA PAGE DEVIS =====
    document.addEventListener('input', (e) => {
        if (e.target.id === 'search-devis') {
            console.log("🔍 Recherche en cours...");
            this.filterDevis();
        }
    });

    // ===== FORMULAIRES =====
document.addEventListener('submit', async (e) => {
    const target = e.target;
    
    if (target.id === 'company-form') {
        e.preventDefault();
        await this.saveCompanySettings();
    }
    else if (target.id === 'colors-form') {
        e.preventDefault();
        await this.saveColorSettings();
    }
    else if (target.id === 'logo-form') {
        e.preventDefault();
        await this.uploadLogo();
    }
    else if (target.id === 'change-password-form') {
        e.preventDefault();
        await this.changePassword();
    }
    else if (target.id === 'fiscal-form') {
        e.preventDefault();
        await this.saveFiscalSettings();
    }
    else if (target.id === 'import-header-form') {  // 🔥 AJOUT ICI
        e.preventDefault();
        await this.importHeader();
    }
});
    
    document.addEventListener('change', (e) => {
        if (e.target.id === 'filter-status' || e.target.id === 'filter-date') {
            console.log("📊 Filtre modifié");
            this.filterDevis();
        }
    });
}

async saveHeaderSettings() {
    const data = {
        slogan: document.getElementById('header-slogan')?.value || '',
        website: document.getElementById('header-website')?.value || '',
        footer_text: document.getElementById('header-footer')?.value || ''
    };
    
    try {
        const response = await apiRequest('/api/settings', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (result.success) {
            Toast.success('✅ En-tête personnalisé enregistré');
            this.loadPage('parametres');
        } else {
            Toast.error(result.message || '❌ Erreur');
        }
    } catch (error) {
        Toast.error('❌ Erreur de connexion');
    }
}
    async loadPage(page) {
        const contentArea = document.getElementById('content-area');
        const pageTitle = document.getElementById('page-title');
        
        try {
            switch(page) {
               case 'dashboard':
    pageTitle.textContent = 'Dashboard';
    contentArea.innerHTML = await this.renderDashboard();
    // 🔥 Attendre un peu que le DOM soit prêt
    setTimeout(() => {
        this.showSubscriptionBanner();
    }, 200);
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
        const data = await response.json();
        return this.normalizeResponse(data);
    } catch (error) {
        console.error("Erreur fetchDevis:", error);
        return [];
    }
}
    
    async fetchClients() {
    try {
        const response = await apiRequest('/api/clients');
        const data = await response.json();
        console.log("fetchClients brut:", data);
        return this.normalizeResponse(data);
    } catch (error) {
        console.error("Erreur fetchClients:", error);
        return [];
    }
}
    
    async fetchProjets() {
    try {
        const response = await apiRequest('/api/projets');
        const data = await response.json();
        return this.normalizeResponse(data);
    } catch (error) {
        console.error("Erreur fetchProjets:", error);
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
    const devisRaw = await this.fetchDevis();
    const devis = this.safeArray(devisRaw);
    
    // 🔥 NE PAS appeler showSubscriptionBanner() ici
    
    const formatCA = (value) => {
        if (!value || value === 0 || isNaN(value)) return '0 FCFA';
        return Math.round(value).toLocaleString('fr-FR') + ' FCFA';
    };
    
    const derniersDevis = devis.slice(0,5).map(d => ({
        id_devis: d.id_devis || d.id,
        client_nom: d.client_nom || d.nom || 'Client inconnu',
        total: parseFloat(d.total) || 0,
        statut: d.statut || 'brouillon'
    }));
    
    const html = `
        <div class="page-content">
            <div class="cards-grid">
                <div class="glass-card">
                    <div class="card-icon"><i class="fas fa-file-invoice"></i></div>
                    <div class="card-title">Total Devis</div>
                    <div class="card-value">${stats.totalDevis || 0}</div>
                </div>
                <div class="glass-card">
                    <div class="card-icon"><i class="fas fa-users"></i></div>
                    <div class="card-title">Clients</div>
                    <div class="card-value">${stats.totalClients || 0}</div>
                </div>
                <div class="glass-card">
                    <div class="card-icon"><i class="fas fa-chart-line"></i></div>
                    <div class="card-title">Chiffre d'affaires</div>
                    <div class="card-value">${formatCA(stats.chiffreAffaires)}</div>
                </div>
                <div class="glass-card">
                    <div class="card-icon"><i class="fas fa-check-circle"></i></div>
                    <div class="card-title">Devis Validés</div>
                    <div class="card-value">${stats.devisValides || 0}</div>
                </div>
            </div>
            <div class="table-container">
                <h3>Derniers Devis</h3>
                <table class="data-table">
                    <thead>
                        <tr><th>Réf</th><th>Client</th><th>Montant</th><th>Statut</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                        ${derniersDevis.length > 0 ? derniersDevis.map(d => `
                            <tr>
                                <td>#${d.id_devis}</td>
                                <td>${d.client_nom}</td>
                                <td>${Math.round(d.total).toLocaleString('fr-FR')} FCFA</td>
                                <td><span class="status-badge ${d.statut === 'validé' ? 'success' : 'warning'}">${d.statut}</span></td>
                                <td>
                                    <button class="btn-icon" onclick="app.viewDevis(${d.id_devis})"><i class="fas fa-eye"></i></button>
                                    <button class="btn-icon" onclick="app.downloadPDF(${d.id_devis})"><i class="fas fa-download"></i></button>
                                </td>
                            </tr>`).join('') : '<tr><td colspan="5" style="text-align:center;">Aucun devis</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    // 🔥 Retourner le HTML sans le bandeau
    return html;
}
    
    async renderDevisList() {
    const devisRaw = await this.fetchDevis();
    const devis = this.safeArray(devisRaw);
    
    console.log("📋 Devis reçus:", devis.length);
    
    // Normaliser chaque devis pour mobile
    const normalizedDevis = devis.map(d => ({
        id_devis: d.id_devis || d.id,
        date_creation: d.date_creation || new Date().toISOString(),
        client_nom: d.client_nom || d.nom || 'Client inconnu',
        nom_projet: d.nom_projet || d.projet || 'Projet inconnu',
        total: parseFloat(d.total) || 0,
        statut: d.statut || 'brouillon'
    }));
    
    // Stocker les devis normalisés pour le filtrage
    this.allDevis = normalizedDevis;
    
    if (normalizedDevis.length === 0) {
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
                ${normalizedDevis.length} devis trouvés
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
                    ${this.renderDevisTableRows(normalizedDevis)}
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
    const clients = this.safeArray(await this.fetchClients());
    console.log("🟢 Rendu des clients:", clients);
    console.log("Premier client:", clients[0]);
    
    // Toujours afficher le bouton Ajouter
    const addButtonHtml = `
        <button class="btn-primary" onclick="app.openCreateClientModal()">
            <i class="fas fa-plus"></i> Ajouter
        </button>
    `;
    
    if (!clients || clients.length === 0) {
        return `
            <div>
                <div style="display:flex; justify-content:flex-end; margin-bottom:1rem;">
                    ${addButtonHtml}
                </div>
                <div class="glass-card" style="text-align:center; padding:2rem;">
                    <p>Aucun client</p>
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
                    ${addButtonHtml}
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
    const projets = this.safeArray(await this.fetchProjets());
    
    if (projets.length === 0) {
        return `
            <div class="glass-card" style="text-align:center; padding:60px;">
                <p>Aucun projet</p>
                <button class="btn-primary" onclick="app.openCreateProjetModal()">+ Ajouter un projet</button>
            </div>
        `;
    }
    
    // Fonction pour le statut avec badge
    const getStatusBadge = (statut) => {
        const statusMap = {
            'en_attente': { label: '⏳ En attente', color: '#F59E0B' },
            'en_cours': { label: '🔄 En cours', color: '#06B6D4' },
            'termine': { label: '✅ Terminé', color: '#10B981' }
        };
        const s = statusMap[statut] || statusMap['en_attente'];
        return `<span style="background:${s.color}22; color:${s.color}; padding:4px 12px; border-radius:20px; font-size:0.75rem; font-weight:600;">${s.label}</span>`;
    };
    
    // Fonction pour la barre de progression
    const getProgressBar = (progression) => {
        const color = progression < 33 ? '#F59E0B' : progression < 66 ? '#06B6D4' : '#10B981';
        return `
            <div style="width:100%; background:#1E293B; border-radius:10px; height:8px; overflow:hidden;">
                <div style="width:${progression}%; background:${color}; height:100%; border-radius:10px; transition:width 0.5s;"></div>
            </div>
            <span style="font-size:0.7rem; color:#94A3B8; margin-top:2px;">${progression}%</span>
        `;
    };
    
    return `
        <div class="cards-grid">
            ${projets.map(p => `
                <div class="glass-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1rem;">
                        <div class="card-icon" style="background:linear-gradient(135deg, var(--primary), var(--secondary));">
                            <i class="fas fa-hard-hat"></i>
                        </div>
                        ${getStatusBadge(p.statut)}
                    </div>
                    <div class="card-title" style="font-size:1.1rem; font-weight:600;">${p.nom_projet}</div>
                    <p style="font-size:0.85rem; color:#94A3B8; margin:5px 0;">${p.description || ''}</p>
                    <p style="font-size:0.85rem; color:#94A3B8; margin:5px 0;">
                        <i class="fas fa-map-marker-alt"></i> ${p.localisation || 'Non renseignée'}
                    </p>
                    <div style="margin:10px 0; display:flex; gap:1rem; font-size:0.8rem; color:#94A3B8; flex-wrap:wrap;">
                        ${p.date_debut ? `<span><i class="fas fa-calendar-alt"></i> Début: ${new Date(p.date_debut).toLocaleDateString()}</span>` : ''}
                        ${p.date_fin ? `<span><i class="fas fa-calendar-check"></i> Fin: ${new Date(p.date_fin).toLocaleDateString()}</span>` : ''}
                    </div>
                    <div style="margin:10px 0;">
                        ${getProgressBar(p.progression || 0)}
                    </div>
                    <div style="margin-top:1rem; display:flex; gap:0.5rem; flex-wrap:wrap;">
                        <button class="btn-icon" onclick="app.editProjet(${p.id_projet})" title="Modifier">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-icon" onclick="app.deleteProjet(${p.id_projet})" title="Supprimer">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `).join('')}
            <div class="glass-card" style="display:flex; justify-content:center; align-items:center; min-height:200px; border:2px dashed #334155;">
                <button class="btn-primary" onclick="app.openCreateProjetModal()" style="padding:15px 30px;">
                    <i class="fas fa-plus"></i> Nouveau projet
                </button>
            </div>
        </div>
    `;
}
    
    async renderFactures() {
    try {
        const userId = this.currentUser.id;
        console.log("Chargement factures pour user:", userId);
        
        const response = await apiRequest(`/api/factures/${userId}`);
        const factures = this.safeArray(await response.json());
        
        console.log("Factures reçues:", factures);
        
        // Séparer les factures
        const facturesSimples = factures.filter(f => f.type_facture !== 'normalisee' && f.statut_fiscal !== 'normalisee' && !f.archivee);
        const facturesNormalisees = factures.filter(f => (f.type_facture === 'normalisee' || f.statut_fiscal === 'normalisee') && !f.archivee);
        const facturesArchivees = factures.filter(f => f.archivee === true);
        
        // Séparer les archives par type
        const archivesSimples = facturesArchivees.filter(f => f.type_facture !== 'normalisee' && f.statut_fiscal !== 'normalisee');
        const archivesNormalisees = facturesArchivees.filter(f => f.type_facture === 'normalisee' || f.statut_fiscal === 'normalisee');
        
        // Récupérer l'onglet actif
        const activeTab = this.currentFactureTab || 'simples';
        
        return `
            <div class="page-content">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem; flex-wrap:wrap; gap:1rem;">
                    <h3><i class="fas fa-receipt"></i> Mes factures</h3>
                    <div style="display:flex; gap:0.5rem;">
                        <button class="btn-primary" onclick="app.openCreateDevisModal()" style="background:var(--primary);">
                            <i class="fas fa-plus"></i> Facture simple
                        </button>
                        <button class="btn-primary" onclick="app.creerFactureNormalisee()" style="background:#F59E0B;">
                            <i class="fas fa-file-invoice"></i> Facture normalisée
                        </button>
                    </div>
                </div>
                
                <!-- Onglets principaux -->
                <div style="display:flex; gap:0; border-bottom:2px solid #334155; margin-bottom:1.5rem; flex-wrap:wrap;">
                    <div class="tab-facture ${activeTab === 'simples' ? 'active' : ''}" 
                         onclick="app.switchFactureTab('simples')" 
                         style="padding:10px 20px; cursor:pointer; border-bottom:3px solid ${activeTab === 'simples' ? '#06B6D4' : 'transparent'}; color:${activeTab === 'simples' ? 'white' : '#94A3B8'}; transition:all 0.3s;">
                        <i class="fas fa-file-alt"></i> Simples (${facturesSimples.length})
                    </div>
                    <div class="tab-facture ${activeTab === 'normalisees' ? 'active' : ''}" 
                         onclick="app.switchFactureTab('normalisees')" 
                         style="padding:10px 20px; cursor:pointer; border-bottom:3px solid ${activeTab === 'normalisees' ? '#F59E0B' : 'transparent'}; color:${activeTab === 'normalisees' ? '#F59E0B' : '#94A3B8'}; transition:all 0.3s;">
                        <i class="fas fa-check-circle"></i> Normalisées (${facturesNormalisees.length})
                    </div>
                    <div class="tab-facture ${activeTab === 'archives' ? 'active' : ''}" 
                         onclick="app.switchFactureTab('archives')" 
                         style="padding:10px 20px; cursor:pointer; border-bottom:3px solid ${activeTab === 'archives' ? '#6B7280' : 'transparent'}; color:${activeTab === 'archives' ? 'white' : '#94A3B8'}; transition:all 0.3s;">
                        <i class="fas fa-archive"></i> Archives (${facturesArchivees.length})
                    </div>
                </div>
                
                <!-- Contenu des onglets -->
                <div id="factures-content">
                    ${activeTab === 'simples' 
                        ? this.renderFactureTable(facturesSimples, 'simples') 
                        : activeTab === 'normalisees'
                        ? this.renderFactureTable(facturesNormalisees, 'normalisees')
                        : this.renderArchivesTable(archivesSimples, archivesNormalisees)}
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Erreur factures:', error);
        return '<div class="glass-card">❌ Erreur chargement des factures</div>';
    }
}

renderArchivesTable(archivesSimples, archivesNormalisees) {
    const totalArchives = archivesSimples.length + archivesNormalisees.length;
    
    if (totalArchives === 0) {
        return `
            <div class="glass-card" style="text-align:center; padding:60px;">
                <i class="fas fa-archive" style="font-size:48px; opacity:0.5;"></i>
                <h3>Aucune facture archivée</h3>
                <p style="color:#94A3B8;">Les factures que vous archivez apparaîtront ici</p>
            </div>
        `;
    }
    
    // Récupérer l'onglet actif des archives
    const activeArchiveTab = this.currentArchiveTab || 'simples';
    
    return `
        <div class="glass-card" style="padding:1.5rem;">
            <!-- Sous-onglets des archives -->
            <div style="display:flex; gap:0; border-bottom:2px solid #334155; margin-bottom:1.5rem; flex-wrap:wrap;">
                <div class="tab-archive ${activeArchiveTab === 'simples' ? 'active' : ''}" 
                     onclick="app.switchArchiveTab('simples')" 
                     style="padding:8px 16px; cursor:pointer; border-bottom:3px solid ${activeArchiveTab === 'simples' ? '#06B6D4' : 'transparent'}; color:${activeArchiveTab === 'simples' ? 'white' : '#94A3B8'}; transition:all 0.3s; font-size:0.85rem;">
                    <i class="fas fa-file-alt"></i> Simples archivées (${archivesSimples.length})
                </div>
                <div class="tab-archive ${activeArchiveTab === 'normalisees' ? 'active' : ''}" 
                     onclick="app.switchArchiveTab('normalisees')" 
                     style="padding:8px 16px; cursor:pointer; border-bottom:3px solid ${activeArchiveTab === 'normalisees' ? '#F59E0B' : 'transparent'}; color:${activeArchiveTab === 'normalisees' ? '#F59E0B' : '#94A3B8'}; transition:all 0.3s; font-size:0.85rem;">
                    <i class="fas fa-check-circle"></i> Normalisées archivées (${archivesNormalisees.length})
                </div>
            </div>
            
            <!-- Contenu des archives -->
            <div id="archives-content">
                ${activeArchiveTab === 'simples' 
                    ? this.renderArchiveTable(archivesSimples, 'simples')
                    : this.renderArchiveTable(archivesNormalisees, 'normalisees')}
            </div>
        </div>
    `;
}

renderArchiveTable(archives, type) {
    if (!archives || archives.length === 0) {
        return `
            <div style="text-align:center; padding:40px; color:#94A3B8;">
                <i class="fas fa-archive" style="font-size:32px; opacity:0.5;"></i>
                <p>Aucune facture ${type === 'simples' ? 'simple' : 'normalisée'} archivée</p>
            </div>
        `;
    }
    
    return `
        <div class="table-container" style="padding:0; background:transparent; backdrop-filter:none;">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>N° Facture</th>
                        <th>Client</th>
                        <th>Date</th>
                        <th>Montant</th>
                        <th>Statut</th>
                        <th>Date archivage</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${archives.map(f => `
                        <tr>
                            <td>#${f.id_facture}</td>
                            <td>${f.client_nom || '-'}</td>
                            <td>${new Date(f.date_facture).toLocaleDateString()}</td>
                            <td>${(f.montant || 0).toLocaleString()} FCFA</td>
                            <td>
                                <span class="status-badge ${f.statut === 'payée' ? 'success' : 'warning'}">
                                    ${f.statut === 'payée' ? '✅ Payée' : '⏳ Non payée'}
                                </span>
                                ${type === 'normalisees' ? '<span class="status-badge" style="background:rgba(16,185,129,0.2);color:#10B981;margin-left:5px;">📄 Normalisée</span>' : ''}
                            </td>
                            <td>${f.date_archivage ? new Date(f.date_archivage).toLocaleDateString() : '-'}</td>
                            <td>
                                <div style="display:flex; gap:4px; flex-wrap:wrap;">
                                    <!-- Restaurer -->
                                    <button class="btn-icon" onclick="app.desarchiverFacture(${f.id_facture})" title="Restaurer" style="background:#10B981;color:white;">
                                        <i class="fas fa-undo"></i>
                                    </button>
                                    <!-- PDF -->
                                    <button class="btn-icon" onclick="app.download${type === 'normalisees' ? 'PDFNormalisee' : 'FacturePDF'}(${f.id_facture})" title="PDF" style="background:#EF4444;color:white;">
                                        <i class="fas fa-file-pdf"></i>
                                    </button>
                                    ${type === 'normalisees' ? `
                                        <button class="btn-icon" onclick="app.viewFactureNormalisee(${f.id_facture})" title="Voir QR Code" style="background:#3B82F6;color:white;">
                                            <i class="fas fa-qrcode"></i>
                                        </button>
                                    ` : ''}
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// ==================== NAVIGATION ONGLETS ====================



switchArchiveTab(tab) {
    this.currentArchiveTab = tab;
    this.loadPage('factures');
}

renderFactureTable(factures, type) {
    if (!factures || factures.length === 0) {
        return `
            <div class="glass-card" style="text-align:center; padding:60px;">
                <i class="fas fa-receipt" style="font-size:48px; opacity:0.5;"></i>
                <h3>Aucune facture ${type === 'simples' ? 'simple' : 'normalisée'}</h3>
                <p>${type === 'simples' ? 'Validez un devis pour générer une facture' : 'Normalisez une facture simple existante'}</p>
            </div>
        `;
    }
    
    return `
        <div class="table-container">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; flex-wrap:wrap; gap:1rem;">
                <h3>${type === 'simples' ? 'Factures simples' : 'Factures normalisées'} (${factures.length})</h3>
            </div>
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
                    ${factures.map(f => this.renderFactureRow(f, type)).join('')}
                </tbody>
            </table>
        </div>
    `;
}

renderFactureRow(f, type) {
    const estPayee = f.statut === 'payée';
    const estNormalisee = type === 'normalisees' || f.type_facture === 'normalisee';
    const estArchivee = f.archivee === true;
    
    return `
        <tr>
            <td>#${f.id_facture}</td>
            <td>DEVIS-${f.id_devis}</td>
            <td>${f.client_nom || '-'}</td>
            <td>${new Date(f.date_facture).toLocaleDateString()}</td>
            <td>${(f.montant || 0).toLocaleString()} FCFA</td>
            <td>
                <span class="status-badge ${estPayee ? 'success' : 'warning'}">
                    ${estPayee ? '✅ Payée' : '⏳ Non payée'}
                </span>
                ${estNormalisee ? '<span class="status-badge" style="background:rgba(16,185,129,0.2);color:#10B981;margin-left:5px;">📄 Normalisée</span>' : ''}
            </td>
            <td>
                <div style="display:flex; gap:4px; flex-wrap:wrap;">
                    <!-- PDF -->
                    <button class="btn-icon" onclick="app.download${estNormalisee ? 'PDFNormalisee' : 'FacturePDF'}(${f.id_facture})" title="PDF" style="background:#EF4444;color:white;">
                        <i class="fas fa-file-pdf"></i>
                    </button>
                    
                    ${!estNormalisee ? `
                        <!-- Normaliser -->
                        <button class="btn-icon" onclick="app.normaliserFacture(${f.id_facture})" title="Normaliser" style="background:#F59E0B;color:white;">
                            <i class="fas fa-file-invoice"></i>
                        </button>
                    ` : `
                        <!-- Voir QR Code -->
                        <button class="btn-icon" onclick="app.viewFactureNormalisee(${f.id_facture})" title="Voir QR Code" style="background:#3B82F6;color:white;">
                            <i class="fas fa-qrcode"></i>
                        </button>
                    `}
                    
                    ${!estPayee ? `
                        <!-- Payer -->
                        <button class="btn-icon" onclick="app.payFacture(${f.id_facture})" title="Marquer payée" style="background:#10B981;color:white;">
                            <i class="fas fa-credit-card"></i>
                        </button>
                    ` : `
                        <!-- Déjà payée -->
                        <span style="background:rgba(16,185,129,0.2); color:#10B981; padding:4px 8px; border-radius:4px; font-size:0.7rem; display:inline-flex; align-items:center;">
                            <i class="fas fa-check-circle"></i> Payée
                        </span>
                    `}
                    
                    <!-- Archiver -->
                    <button class="btn-icon" onclick="app.archiverFacture(${f.id_facture})" title="Archiver" style="background:#6B7280;color:white;">
                        <i class="fas fa-archive"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;
}


viewFactureNormalisee(id_facture) {
    // Ouvrir le PDF normalisé avec le token
    this.downloadPDFNormalisee(id_facture);
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




    async renderFacturesArchivees() {
    try {
        const userId = this.currentUser.id;
        const response = await apiRequest(`/api/factures/${userId}`);
        const factures = this.safeArray(await response.json());
        const archivees = factures.filter(f => f.archivee);
        
        return `
            <div class="page-content">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem; flex-wrap:wrap; gap:1rem;">
                    <h3><i class="fas fa-archive"></i> Archives (${archivees.length})</h3>
                    <button class="btn-secondary" onclick="app.loadPage('factures')" style="background:#3B82F6; border-color:#3B82F6;">
                        <i class="fas fa-arrow-left"></i> Retour
                    </button>
                </div>
                
                ${archivees.length === 0 ? `
                    <div class="glass-card" style="text-align:center; padding:60px;">
                        <i class="fas fa-archive" style="font-size:48px; opacity:0.5;"></i>
                        <h3>Aucune facture archivée</h3>
                        <p style="color:#94A3B8;">Les factures que vous archiveront apparaîtront ici</p>
                    </div>
                ` : `
                    <div class="table-container">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>N° Facture</th>
                                    <th>Client</th>
                                    <th>Date</th>
                                    <th>Montant</th>
                                    <th>Statut</th>
                                    <th>Date archivage</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${archivees.map(f => `
                                    <tr>
                                        <td>#${f.id_facture}</td>
                                        <td>${f.client_nom || '-'}</td>
                                        <td>${new Date(f.date_facture).toLocaleDateString()}</td>
                                        <td>${(f.montant || 0).toLocaleString()} FCFA</td>
                                        <td>
                                            <span class="status-badge ${f.statut === 'payée' ? 'success' : 'warning'}">
                                                ${f.statut === 'payée' ? 'Payée' : 'Non payée'}
                                            </span>
                                        </td>
                                        <td>${f.date_archivage ? new Date(f.date_archivage).toLocaleDateString() : '-'}</td>
                                        <td>
                                            <div style="display:flex; gap:4px; flex-wrap:wrap;">
                                                <button class="btn-icon" onclick="app.desarchiverFacture(${f.id_facture})" title="Restaurer" style="background:#10B981;color:white;">
                                                    <i class="fas fa-undo"></i>
                                                </button>
                                                <button class="btn-icon" onclick="app.downloadFacturePDF(${f.id_facture})" title="PDF" style="background:#EF4444;color:white;">
                                                    <i class="fas fa-file-pdf"></i>
                                                </button>
                                                ${f.type_facture === 'normalisee' ? `
                                                    <button class="btn-icon" onclick="app.downloadPDFNormalisee(${f.id_facture})" title="PDF Normalisé" style="background:#10B981;color:white;">
                                                        <i class="fas fa-file-invoice"></i>
                                                    </button>
                                                ` : ''}
                                            </div>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `}
            </div>
        `;
    } catch (error) {
        console.error('Erreur archives:', error);
        return '<div class="glass-card">❌ Erreur chargement des archives</div>';
    }
}


    


    async reactiverAbonnement(id_user) {
    if (confirm(`Réactiver l'abonnement de l'utilisateur ID ${id_user} ?`)) {
        try {
            const response = await apiRequest(`/api/admin/abonnement/${id_user}/reactiver`, { method: 'POST' });
            const result = await response.json();
            if (result.success) {
                Toast.success('✅ Abonnement réactivé !');
                this.loadPage('admin');
            } else {
                Toast.error(result.error || 'Erreur');
            }
        } catch (error) {
            Toast.error('❌ Erreur de connexion');
        }
    }
}
    
    // Actions rapides
   async viewDevis(id) {
    // 🔥 Stocker l'ID du devis pour le rafraîchissement
    this.currentDevisId = id;
    
    try {
        console.log("🔍 Chargement du devis:", id);
        
        const response = await apiRequest(`/api/devis/${id}`);
        const devis = await response.json();
        console.log("✅ Devis chargé:", devis);
        
        // Récupérer les situations
        let situations = [];
        try {
            const situationsResponse = await apiRequest(`/api/devis/${id}/situations`);
            situations = await situationsResponse.json();
            console.log("✅ Situations chargées:", situations);
        } catch (e) {
            console.log("⚠️ Erreur chargement situations:", e.message);
            situations = [];
        }
        devis.situations = situations;
        
        // ============================================================
        // CALCUL DES MONTANTS
        // ============================================================
        const total = devis.total || 0;
        const acompte = devis.acompte_montant || 0;
        const montantRestant = total - acompte;
        
        // Calculer le total des situations payées
        const totalPaye = (devis.situations || [])
            .filter(s => s.statut === 'payee')
            .reduce((sum, s) => sum + (s.montant || 0), 0);
        
        const resteAPayer = montantRestant - totalPaye;
        const progression = montantRestant > 0 ? Math.round((totalPaye / montantRestant) * 100) : 0;
        
        // ============================================================
        // CRÉATION DU MODAL
        // ============================================================
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
                    <!-- Informations client -->
                    <div style="margin-bottom:20px;">
                        <h3>Informations client</h3>
                        <p><strong>Nom:</strong> ${devis.client_nom || 'Non renseigné'}</p>
                        <p><strong>Email:</strong> ${devis.client_email || '-'}</p>
                        <p><strong>Téléphone:</strong> ${devis.client_telephone || '-'}</p>
                    </div>
                    
                    <!-- Informations projet -->
                    <div style="margin-bottom:20px;">
                        <h3>Informations projet</h3>
                        <p><strong>Nom:</strong> ${devis.nom_projet || 'Non renseigné'}</p>
                        <p><strong>Description:</strong> ${devis.projet_description || '-'}</p>
                    </div>
                    
                    <!-- Tableau des articles -->
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
                                ${(devis.lignes || []).map(ligne => `
                                    <tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
                                        <td style="padding:10px;">${ligne.designation || 'Article'}</td>
                                        <td style="padding:10px; text-align:center;">${ligne.quantite || 0}</td>
                                        <td style="padding:10px; text-align:right;">${(ligne.prix_unitaire || 0).toLocaleString()} FCFA</td>
                                        <td style="padding:10px; text-align:right;">${(ligne.total_ligne || 0).toLocaleString()} FCFA</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                            <tfoot>
                                <tr style="border-top:2px solid rgba(255,255,255,0.2);">
                                    <td colspan="3" style="padding:10px; text-align:right;"><strong>Sous-total:</strong></td>
                                    <td style="padding:10px; text-align:right;">${((devis.total || 0) / 1.2).toLocaleString()} FCFA</td>
                                </tr>
                                <tr>
                                    <td colspan="3" style="padding:10px; text-align:right;"><strong>Main d'œuvre (20%):</strong></td>
                                    <td style="padding:10px; text-align:right;">${((devis.total || 0) - (devis.total || 0) / 1.2).toLocaleString()} FCFA</td>
                                </tr>
                                <tr style="background:rgba(6,182,212,0.2);">
                                    <td colspan="3" style="padding:10px; text-align:right;"><strong>TOTAL TTC:</strong></td>
                                    <td style="padding:10px; text-align:right; font-size:1.2rem; font-weight:bold; color:#06B6D4;">${(devis.total || 0).toLocaleString()} FCFA</td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                    
                    <!-- ========================================================== -->
                    <!-- BARRE DE PROGRESSION ET RÉCAPITULATIF                       -->
                    <!-- ========================================================== -->
                    <div style="margin:15px 0; padding:15px; background:rgba(255,255,255,0.05); border-radius:12px;">
                        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(120px,1fr)); gap:10px; margin-bottom:10px;">
                            <div>
                                <span style="color:#94A3B8; font-size:0.8rem;">Montant total</span>
                                <div style="font-weight:bold; font-size:1.1rem;">${total.toLocaleString()} FCFA</div>
                            </div>
                            <div>
                                <span style="color:#94A3B8; font-size:0.8rem;">Acompte</span>
                                <div style="font-weight:bold; color:#10B981;">${acompte.toLocaleString()} FCFA</div>
                            </div>
                            <div>
                                <span style="color:#94A3B8; font-size:0.8rem;">Payé</span>
                                <div style="font-weight:bold; color:#10B981;">${(acompte + totalPaye).toLocaleString()} FCFA</div>
                            </div>
                            <div>
                                <span style="color:#94A3B8; font-size:0.8rem;">Reste à payer</span>
                                <div style="font-weight:bold; color:#F59E0B;">${resteAPayer.toLocaleString()} FCFA</div>
                            </div>
                            <div>
                                <span style="color:#94A3B8; font-size:0.8rem;">Progression</span>
                                <div style="font-weight:bold; color:#06B6D4;">${progression}%</div>
                            </div>
                        </div>
                        <div style="background:#1E293B; border-radius:10px; height:8px; overflow:hidden;">
                            <div style="width:${progression}%; background:${progression < 33 ? '#F59E0B' : progression < 66 ? '#06B6D4' : '#10B981'}; height:100%; border-radius:10px; transition:width 0.5s;"></div>
                        </div>
                    </div>
                    
                    <!-- ========================================================== -->
                    <!-- SITUATIONS DE TRAVAUX                                       -->
                    <!-- ========================================================== -->
                    ${devis.situations && devis.situations.length > 0 ? `
                    <div style="margin:20px 0;">
                        <h3><i class="fas fa-chart-bar"></i> Situations de travaux</h3>
                        <table style="width:100%; border-collapse:collapse; margin-top:10px;">
                            <thead>
                                <tr style="background:rgba(255,255,255,0.05);">
                                    <th style="padding:10px; text-align:left;">N°</th>
                                    <th style="padding:10px; text-align:left;">Pourcentage</th>
                                    <th style="padding:10px; text-align:right;">Montant</th>
                                    <th style="padding:10px; text-align:left;">Statut</th>
                                    <th style="padding:10px; text-align:left;">Travaux</th>
                                    <th style="padding:10px; text-align:center;">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${devis.situations.map(s => `
                                    <tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
                                        <td style="padding:10px;">#${s.numero || 0}</td>
                                        <td style="padding:10px;">${s.pourcentage || 0}%</td>
                                        <td style="padding:10px; text-align:right;">${(s.montant || 0).toLocaleString()} FCFA</td>
                                        <td style="padding:10px;">
                                            <span class="status-badge ${s.statut === 'payee' ? 'success' : 'warning'}">
                                                ${s.statut === 'payee' ? '✅ Payée' : '⏳ En attente'}
                                            </span>
                                        </td>
                                        <td style="padding:10px; max-width:200px; word-wrap:break-word;">${s.travaux_realises || '-'}</td>
                                        <td style="padding:10px; text-align:center;">
                                            ${s.statut !== 'payee' ? `
                                                <button class="btn-icon" onclick="app.payerSituation(${s.id_situation})" title="Marquer payée" style="background:#10B981;color:white;">
                                                    <i class="fas fa-credit-card"></i>
                                                </button>
                                            ` : `
                                                <span style="color:#10B981;">✅ Payé</span>
                                            `}
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    ` : ''}
                    
                    <!-- ========================================================== -->
                    <!-- BOUTONS ACOMPTE ET SITUATIONS                              -->
                    <!-- ========================================================== -->
                    <div style="display:flex; gap:10px; justify-content:flex-end; margin-top:20px; flex-wrap:wrap; align-items:center;">
                        ${(devis.acompte_pourcentage || 0) === 0 ? `
                            <button onclick="app.configurerAcompte(${devis.id_devis})" class="btn-secondary" style="background:#F59E0B; border-color:#F59E0B;">
                                <i class="fas fa-hand-holding-usd"></i> Configurer l'acompte
                            </button>
                        ` : `
                            <span style="background:rgba(16,185,129,0.2); color:#10B981; padding:8px 16px; border-radius:8px; display:flex; align-items:center; gap:8px;">
                                <i class="fas fa-check-circle"></i> Acompte ${devis.acompte_pourcentage}% (${(devis.acompte_montant || 0).toLocaleString()} FCFA)
                                ${devis.acompte_paye ? '✅ Payé' : '⏳ En attente'}
                            </span>
                            ${!devis.acompte_paye ? `
                                <button onclick="app.payerAcompte(${devis.id_devis})" class="btn-secondary" style="background:#10B981; border-color:#10B981;">
                                    <i class="fas fa-credit-card"></i> Marquer payé
                                </button>
                            ` : ''}
                            <button onclick="app.creerSituation(${devis.id_devis})" class="btn-primary" style="background:#8B5CF6; border-color:#8B5CF6;">
                                <i class="fas fa-plus"></i> Ajouter une situation
                            </button>
                        `}
                    </div>
                    
                    <!-- ========================================================== -->
                    <!-- ACTIONS PRINCIPALES                                        -->
                    <!-- ========================================================== -->
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
        
        // Fermeture du modal
        const closeBtns = modal.querySelectorAll('.close-modal');
        closeBtns.forEach(btn => btn.addEventListener('click', () => modal.remove()));
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
        
    } catch (error) {
        console.error('❌ Erreur viewDevis:', error);
        Toast.error('Erreur lors du chargement du devis: ' + error.message);
    }
}


async ajouterEssai(id_user) {
    if (confirm(`Ajouter 14 jours d'essai gratuit à l'utilisateur ID ${id_user} ?`)) {
        try {
            const response = await apiRequest(`/api/admin/abonnement/${id_user}/trial`, { method: 'POST' });
            const result = await response.json();
            if (result.success) {
                Toast.success('✅ 14 jours d\'essai ajoutés avec succès !');
                this.loadPage('admin');
            } else {
                Toast.error(result.error || 'Erreur lors de l\'ajout');
            }
        } catch (error) {
            Toast.error('❌ Erreur de connexion');
        }
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
        if (confirm('Supprimer ce client ?')) {
            await apiRequest(`/api/clients/${id}`, { method: 'DELETE' });
            alert('Client supprimé');
            this.loadPage('clients');
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
                    
<div class="form-group">
    <label>IFU (Numéro d'Identification Fiscale)</label>
    <input type="text" id="client-ifu" placeholder="13 caractères">
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
    
    // Soumission avec verrou anti-doublon
const form = modal.querySelector('#client-form');
let isSubmitting = false;

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (isSubmitting) {
        console.log("⏳ Déjà en cours...");
        return;
    }

    const limitesOk = await this.checkLimites('client');
    if (!limitesOk) return;
    
    const clientData = {
        nom: document.getElementById('client-nom').value,
        telephone: document.getElementById('client-telephone').value,
        email: document.getElementById('client-email').value,
        adresse: document.getElementById('client-adresse').value,
        ifu: document.getElementById('client-ifu').value || ''  // Ajout  // Ajout de l'IFU avec valeur par défaut vide
    };
    
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    isSubmitting = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enregistrement...';
    submitBtn.disabled = true;
    
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
            isSubmitting = false;
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    } catch (error) {
        alert('❌ Erreur de connexion');
        isSubmitting = false;
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
});
}


openCreateProjetModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-content" style="max-width:600px;">
            <div class="modal-header">
                <h2><i class="fas fa-hard-hat"></i> Nouveau projet</h2>
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
                    <div class="form-group">
                        <label>Statut</label>
                        <select id="projet-statut">
                            <option value="en_attente">⏳ En attente</option>
                            <option value="en_cours">🔄 En cours</option>
                            <option value="termine">✅ Terminé</option>
                        </select>
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
                        <div class="form-group">
                            <label>Date de début</label>
                            <input type="date" id="projet-date-debut">
                        </div>
                        <div class="form-group">
                            <label>Date de fin</label>
                            <input type="date" id="projet-date-fin">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Progression (%)</label>
                        <input type="range" id="projet-progression" min="0" max="100" value="0" 
                               oninput="document.getElementById('progression-value').textContent = this.value + '%'">
                        <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#94A3B8;">
                            <span>0%</span>
                            <span id="progression-value">0%</span>
                            <span>100%</span>
                        </div>
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
    
    // Fermeture
    const closeBtns = modal.querySelectorAll('.close-modal');
    closeBtns.forEach(btn => btn.addEventListener('click', () => modal.remove()));
    
    // Soumission
    const form = modal.querySelector('#projet-form');
    let isSubmitting = false;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (isSubmitting) return;
        
        const limitesOk = await this.checkLimites('projet');
        if (!limitesOk) return;
        
        const projetData = {
            nom_projet: document.getElementById('projet-nom').value,
            description: document.getElementById('projet-description').value,
            localisation: document.getElementById('projet-localisation').value,
            statut: document.getElementById('projet-statut').value,
            date_debut: document.getElementById('projet-date-debut').value || null,
            date_fin: document.getElementById('projet-date-fin').value || null,
            progression: parseInt(document.getElementById('projet-progression').value) || 0
        };
        
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        isSubmitting = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Création...';
        submitBtn.disabled = true;
        
        try {
            const response = await apiRequest('/api/projets', {
                method: 'POST',
                body: JSON.stringify(projetData)
            });
            const result = await response.json();
            
            if (result.success) {
                Toast.success('Projet créé avec succès');
                modal.remove();
                this.loadPage('projets');
            } else {
                Toast.error(result.message || 'Erreur lors de la création');
                isSubmitting = false;
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        } catch (error) {
            Toast.error('❌ Erreur de connexion');
            isSubmitting = false;
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
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
        
        // Soumission avec verrou anti-doublon
const form = modal.querySelector('#devis-form');
let isSubmitting = false; // Verrou

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Empêcher les doubles clics
    if (isSubmitting) {
        console.log("⏳ Déjà en cours, veuillez patienter...");
        return;
    }
    
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
    
    // Verrouiller et désactiver le bouton
    isSubmitting = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Création...';
    submitBtn.disabled = true;
    
    try {
        const response = await apiRequest('/api/devis', { method: 'POST', body: JSON.stringify(devisData) });
        
        console.log('Status HTTP:', response.status);
        
        const result = await response.json();
        console.log('Résultat complet:', result);
        
        // Vérification
        if (result.success == true || result.success === "true" || result.id_devis) {
            alert('✅ Devis créé avec succès !');
            modal.remove();
            setTimeout(() => {
                this.loadPage('devis');
            }, 500);
        } else {
            if (result.message) {
                alert('❌ ' + result.message);
            }
            // Déverrouiller en cas d'erreur
            isSubmitting = false;
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    } catch (error) {
        console.error('Erreur détaillée:', error);
        alert('❌ Erreur de connexion: ' + error.message);
        isSubmitting = false;
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
    // Pas de finally ici car on ne veut pas déverrouiller en cas de succès
    // (la modale est fermée donc pas besoin)
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
            const response = await apiRequest(`/api/facture/${id_facture}/pay`, { method: 'PUT' });
            const result = await response.json();
            
            if (result.success) {
                Toast.success('Facture marquée comme payée');
                this.loadPage('factures');
            } else {
                Toast.error(result.message || 'Erreur lors du paiement');
            }
        } catch (error) {
            Toast.error('❌ Erreur de connexion');
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
        const projets = await this.fetchProjets();
        const projet = projets.find(p => p.id_projet === id);
        
        if (!projet) {
            Toast.error('Projet non trouvé');
            return;
        }
        
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'flex';
        modal.innerHTML = `
            <div class="modal-content" style="max-width:600px;">
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
                        <div class="form-group">
                            <label>Statut</label>
                            <select id="edit-projet-statut">
                                <option value="en_attente" ${projet.statut === 'en_attente' ? 'selected' : ''}>⏳ En attente</option>
                                <option value="en_cours" ${projet.statut === 'en_cours' ? 'selected' : ''}>🔄 En cours</option>
                                <option value="termine" ${projet.statut === 'termine' ? 'selected' : ''}>✅ Terminé</option>
                            </select>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
                            <div class="form-group">
                                <label>Date de début</label>
                                <input type="date" id="edit-projet-date-debut" value="${projet.date_debut || ''}">
                            </div>
                            <div class="form-group">
                                <label>Date de fin</label>
                                <input type="date" id="edit-projet-date-fin" value="${projet.date_fin || ''}">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Progression (%)</label>
                            <input type="range" id="edit-projet-progression" min="0" max="100" value="${projet.progression || 0}" 
                                   oninput="document.getElementById('edit-progression-value').textContent = this.value + '%'">
                            <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#94A3B8;">
                                <span>0%</span>
                                <span id="edit-progression-value">${projet.progression || 0}%</span>
                                <span>100%</span>
                            </div>
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
                localisation: document.getElementById('edit-projet-localisation').value,
                statut: document.getElementById('edit-projet-statut').value,
                date_debut: document.getElementById('edit-projet-date-debut').value || null,
                date_fin: document.getElementById('edit-projet-date-fin').value || null,
                progression: parseInt(document.getElementById('edit-projet-progression').value) || 0
            };
            
            try {
                const response = await apiRequest(`/api/projets/${id}`, {
                    method: 'PUT',
                    body: JSON.stringify(projetData)
                });
                const result = await response.json();
                
                if (result.success) {
                    Toast.success('✅ Projet modifié avec succès');
                    modal.remove();
                    this.loadPage('projets');
                } else {
                    Toast.error('❌ Erreur: ' + result.message);
                }
            } catch (error) {
                Toast.error('❌ Erreur de connexion');
            }
        });
        
    } catch (error) {
        console.error('Erreur:', error);
        Toast.error('Erreur lors du chargement du projet');
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

        // 🔥 Sauvegarder les settings pour les utiliser dans les onglets
        this.currentSettings = settings;
        
        // Onglet actif (par défaut: 'entreprise')
        let activeTab = 'entreprise';
        
        return `
            <div class="page-content">
                <h2><i class="fas fa-sliders-h"></i> Paramètres</h2>
                <p style="color:#94A3B8; margin-bottom:1.5rem;">Gérez les informations de votre entreprise et vos préférences.</p>
                
                <!-- ===== ONGLETS ===== -->
                <div style="display:flex; gap:0; border-bottom:2px solid #334155; margin-bottom:1.5rem; flex-wrap:wrap;">
                    <div class="tab-parametre ${activeTab === 'entreprise' ? 'active' : ''}" 
                         onclick="app.switchParametreTab('entreprise')" 
                         style="padding:10px 20px; cursor:pointer; border-bottom:3px solid ${activeTab === 'entreprise' ? '#06B6D4' : 'transparent'}; color:${activeTab === 'entreprise' ? 'white' : '#94A3B8'}; transition:all 0.3s;">
                        <i class="fas fa-building"></i> Entreprise
                    </div>
                    <div class="tab-parametre ${activeTab === 'fiscal' ? 'active' : ''}" 
                         onclick="app.switchParametreTab('fiscal')" 
                         style="padding:10px 20px; cursor:pointer; border-bottom:3px solid ${activeTab === 'fiscal' ? '#F59E0B' : 'transparent'}; color:${activeTab === 'fiscal' ? '#F59E0B' : '#94A3B8'}; transition:all 0.3s;">
                        <i class="fas fa-file-invoice"></i> Fiscal
                    </div>
                    <div class="tab-parametre ${activeTab === 'securite' ? 'active' : ''}" 
                         onclick="app.switchParametreTab('securite')" 
                         style="padding:10px 20px; cursor:pointer; border-bottom:3px solid ${activeTab === 'securite' ? '#EF4444' : 'transparent'}; color:${activeTab === 'securite' ? '#EF4444' : '#94A3B8'}; transition:all 0.3s;">
                        <i class="fas fa-key"></i> Sécurité
                    </div>
                    <div class="tab-parametre ${activeTab === 'backup' ? 'active' : ''}" 
                         onclick="app.switchParametreTab('backup')" 
                         style="padding:10px 20px; cursor:pointer; border-bottom:3px solid ${activeTab === 'backup' ? '#10B981' : 'transparent'}; color:${activeTab === 'backup' ? '#10B981' : '#94A3B8'}; transition:all 0.3s;">
                        <i class="fas fa-database"></i> Sauvegarde
                    </div>
                </div>
                
                <!-- ===== CONTENU DES ONGLETS ===== -->
                <div id="parametres-content">
                    ${this.renderParametreContent(activeTab, settings)}
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Erreur:', error);
        return '<div class="glass-card">❌ Erreur chargement des paramètres</div>';
    }
}
renderParametreContent(tab, settings) {
    // Si settings n'est pas passé, utiliser this.currentSettings
    if (!settings || Object.keys(settings).length === 0) {
        settings = this.currentSettings || {};
    }
    
    const tabs = {
        entreprise: `
            <!-- ===== ONGLET ENTREPRISE ===== -->
            <div class="glass-card">
                <h3><i class="fas fa-building"></i> Informations de l'entreprise</h3>
                <p style="font-size:0.85rem; color:#94A3B8; margin-bottom:1rem;">
                    Ces informations apparaîtront sur vos devis et factures.
                </p>
                <form id="company-form">
                    <div class="form-group">
                        <label>Nom de l'entreprise</label>
                        <input type="text" id="company-name" value="${settings.company_name || ''}" class="form-control" placeholder="Votre entreprise">
                    </div>
                    <div class="form-group">
                        <label>Email</label>
                        <input type="email" id="company-email" value="${settings.company_email || ''}" class="form-control" placeholder="contact@entreprise.com">
                    </div>
                    <div class="form-group">
                        <label>Téléphone</label>
                        <input type="tel" id="company-phone" value="${settings.company_phone || ''}" class="form-control" placeholder="01 23 45 67 89">
                    </div>
                    <div class="form-group">
                        <label>Adresse</label>
                        <textarea id="company-address" rows="2" class="form-control" placeholder="Adresse complète">${settings.company_address || ''}</textarea>
                    </div>
                    <div class="form-group">
                        <label>Slogan</label>
                        <input type="text" id="header-slogan" value="${settings.slogan || ''}" class="form-control" placeholder="Votre slogan (ex: Bâtisseurs de confiance)">
                    </div>
                    <div class="form-group">
                        <label>Site web</label>
                        <input type="text" id="header-website" value="${settings.website || ''}" class="form-control" placeholder="www.votre-site.com">
                    </div>
                    <div class="form-group">
                        <label>Pied de page personnalisé</label>
                        <input type="text" id="header-footer" value="${settings.footer_text || ''}" class="form-control" placeholder="Mentions légales ou message personnalisé">
                    </div>
                    <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                        <button type="submit" class="btn-primary" id="btn-save-company">
                            <i class="fas fa-save"></i> Enregistrer
                        </button>
                        <button type="button" class="btn-secondary" onclick="app.previewHeader()" style="background: linear-gradient(135deg, #8B5CF6, #6D28D9); color: white; border: none; padding: 10px 20px; border-radius: 10px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; display: inline-flex; align-items: center; gap: 8px;" onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                            <i class="fas fa-eye"></i> Aperçu PDF
                        </button>
                    </div>
                </form>
            </div>
            
            <!-- Logo -->
            <div class="glass-card" style="margin-top:1.5rem;">
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

            <!-- ===== IMPORTER EN-TÊTE ===== -->
<div class="glass-card" style="margin-top:1.5rem; border:2px dashed #8B5CF6; background:rgba(139,92,246,0.05);">
    <h3><i class="fas fa-file-import" style="color:#8B5CF6;"></i> Importer votre en-tête</h3>
    <p style="font-size:0.85rem; color:#94A3B8; margin-bottom:1rem;">
        Importez un fichier HTML ou PDF contenant votre en-tête personnalisé (logo, informations, design).
    </p>
    
    <form id="import-header-form" enctype="multipart/form-data">
        <div style="display:flex; gap:1rem; flex-wrap:wrap; align-items:center;">
            <div style="flex:1; min-width:200px;">
                <input type="file" id="import-header-file" accept="image/*" class="form-control" style="padding:8px; background:#0F172A; border:1px solid #334155; border-radius:8px; color:white; width:100%;">
                <p style="font-size:0.7rem; color:#64748B; margin-top:5px;">
    Formats acceptés : PNG, JPG, JPEG, GIF, WEBP
</p>
            </div>
            <button type="submit" class="btn-primary" style="background: linear-gradient(135deg, #8B5CF6, #6D28D9); padding:10px 24px; border-radius:10px; font-weight:600; cursor:pointer; border:none; color:white; display:inline-flex; align-items:center; gap:8px;">
                <i class="fas fa-upload"></i> Importer
            </button>
            
        </div>
    </form>
    
    <div style="margin-top:1rem; padding:1rem; background:rgba(139,92,246,0.08); border-radius:8px;">
        <p style="font-size:0.8rem; color:#94A3B8;">
            <i class="fas fa-info-circle" style="color:#8B5CF6;"></i>
            Votre en-tête importé sera utilisé sur tous vos devis et factures à la place des informations saisies ci-dessus.
        </p>
    </div>
</div>
            
            <!-- Couleurs -->
            <div class="glass-card" style="margin-top:1.5rem;">
                <h3><i class="fas fa-palette"></i> Couleurs personnalisées</h3>
                <form id="colors-form">
                    <div class="form-group">
                        <label>Couleur principale</label>
                        <input type="color" id="primary-color" value="${settings.primary_color || '#1E3A8A'}" style="width:100%; height:40px;">
                    </div>
                    <div class="form-group">
                        <label>Couleur secondaire</label>
                        <input type="color" id="secondary-color" value="${settings.secondary_color || '#7C3AED'}" style="width:100%; height:40px;">
                    </div>
                    <div class="form-group">
                        <label>Couleur d'accent</label>
                        <input type="color" id="accent-color" value="${settings.accent_color || '#06B6D4'}" style="width:100%; height:40px;">
                    </div>
                    <button type="submit" class="btn-primary"><i class="fas fa-palette"></i> Appliquer</button>
                </form>
            </div>
        `,
        
        fiscal: `
    <!-- ===== ONGLET FISCAL ===== -->
    <div class="glass-card" style="border:1px solid rgba(245,158,11,0.3);">
        <h3><i class="fas fa-file-invoice" style="color:#F59E0B;"></i> Informations fiscales</h3>
        <p style="font-size:0.85rem; color:#94A3B8; margin-bottom:1rem;">
            Ces informations sont obligatoires pour émettre des factures normalisées (e-MCF).
        </p>
        <form id="fiscal-form">
            <div class="form-group">
                <label>NIF (Numéro d'Identification Fiscale) *</label>
                <input type="text" id="nif" value="${settings.nif || ''}" placeholder="Ex: 0202347221089" required>
                <p style="font-size:0.7rem; color:#64748B; margin-top:5px;">
                    <i class="fas fa-info-circle"></i> 13 caractères (ex: 0202347221089)
                </p>
            </div>
            <div class="form-group">
                <label>Régime TVA</label>
                <select id="regime-tva">
                    <option value="non assujetti" ${settings.regime_tva === 'non assujetti' ? 'selected' : ''}>Non assujetti</option>
                    <option value="assujetti" ${settings.regime_tva === 'assujetti' ? 'selected' : ''}>Assujetti</option>
                </select>
            </div>
            <div class="form-group">
                <label>Numéro de contribuable</label>
                <input type="text" id="numero-contribuable" value="${settings.numero_contribuable || ''}" placeholder="Numéro de contribuable">
            </div>
            <div class="form-group">
                <label>Adresse fiscale</label>
                <input type="text" id="adresse-fiscale" value="${settings.adresse_fiscale || ''}" placeholder="Adresse fiscale">
            </div>
            <button type="submit" class="btn-primary" style="background: #F59E0B;">
                <i class="fas fa-save"></i> Enregistrer
            </button>
        </form>
        <p style="font-size:0.75rem; color:#94A3B8; margin-top:1rem;">
            <i class="fas fa-info-circle"></i> Le NIF est obligatoire pour la facturation normalisée.
        </p>
    </div>
    `,
        
        securite: `
            <!-- ===== ONGLET SÉCURITÉ ===== -->
            <div class="glass-card" style="border:1px solid rgba(6,182,212,0.2);">
                <h3><i class="fas fa-key" style="color:#06B6D4;"></i> Changer le mot de passe</h3>
                <p style="font-size:0.85rem; color:#94A3B8; margin-bottom:1rem;">
                    Modifiez votre mot de passe pour sécuriser votre compte.
                </p>
                <form id="change-password-form">
                    <div class="form-group">
                        <label>Ancien mot de passe</label>
                        <input type="password" id="old-password" class="form-control" placeholder="Votre mot de passe actuel" required>
                    </div>
                    <div class="form-group">
                        <label>Nouveau mot de passe</label>
                        <input type="password" id="new-password" class="form-control" placeholder="Nouveau mot de passe (min. 4 caractères)" required>
                    </div>
                    <div class="form-group">
                        <label>Confirmer le nouveau mot de passe</label>
                        <input type="password" id="confirm-password" class="form-control" placeholder="Confirmez le nouveau mot de passe" required>
                    </div>
                    <button type="submit" class="btn-primary" style="background: #06B6D4;">
                        <i class="fas fa-save"></i> Changer le mot de passe
                    </button>
                </form>
            </div>
            
            <!-- Déconnexion -->
            <div class="glass-card" style="margin-top:1.5rem; border:1px solid rgba(239,68,68,0.3);">
                <h3><i class="fas fa-shield-alt" style="color:#F87171;"></i> Sécurité du compte</h3>
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; margin-top:1rem;">
                    <div>
                        <p style="margin-bottom:5px;">Connecté en tant que : <strong>${this.currentUser.nom || this.currentUser.email}</strong></p>
                        <p style="font-size:0.85rem; color:#94A3B8;">${this.currentUser.email}</p>
                    </div>
                    <button class="btn-logout" onclick="app.logout()">
                        <i class="fas fa-sign-out-alt"></i> Se déconnecter
                    </button>
                </div>
            </div>
        `,
        
        backup: `
            <!-- ===== ONGLET SAUVEGARDE ===== -->
            <div class="glass-card">
                <h3><i class="fas fa-database"></i> Sauvegarde des données</h3>
                <p style="font-size:0.85rem; color:#94A3B8; margin-bottom:1rem;">
                    Sauvegardez ou restaurez l'intégralité de vos données (clients, projets, devis, factures).
                </p>
                <div style="display:flex; gap:1rem; flex-wrap:wrap;">
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
        `
    };
    
    return tabs[tab] || tabs.entreprise;
}
switchParametreTab(tab) {
    // Mettre à jour les onglets visuellement
    const tabs = document.querySelectorAll('.tab-parametre');
    const colors = ['#06B6D4', '#F59E0B', '#EF4444', '#10B981'];
    const tabNames = ['entreprise', 'fiscal', 'securite', 'backup'];
    
    tabs.forEach((t, i) => {
        t.style.borderBottom = '3px solid transparent';
        t.style.color = '#94A3B8';
        if (tabNames[i] === tab) {
            t.style.borderBottom = `3px solid ${colors[i]}`;
            t.style.color = 'white';
        }
    });
    
    // Mettre à jour le contenu sans recharger toute la page
    const settings = this.currentSettings || {};
    const contentArea = document.getElementById('parametres-content');
    if (contentArea) {
        contentArea.innerHTML = this.renderParametreContent(tab, settings);
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


// Importer un en-tête personnalisé
async importHeader() {
    const fileInput = document.getElementById('import-header-file');
    const file = fileInput.files[0];
    
    if (!file) {
        Toast.warning('⚠️ Veuillez sélectionner un fichier');
        return;
    }
    
    const formData = new FormData();
    formData.append('header_file', file);
    
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_URL}/api/settings/import-header`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        const result = await response.json();
        if (result.success) {
            Toast.success('✅ En-tête importé avec succès !');
            // Réinitialiser le champ file
            document.getElementById('import-header-file').value = '';
            this.loadPage('parametres');
        } else {
            Toast.error(result.message || '❌ Erreur lors de l\'import');
        }
    } catch (error) {
        console.error('Erreur importHeader:', error);
        Toast.error('❌ Erreur de connexion');
    }
}

async previewImportedHeader() {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            Toast.error('❌ Vous devez être connecté');
            return;
        }
        
        Toast.info('📄 Génération de l\'aperçu...');
        
        const response = await fetch(`${API_URL}/api/preview-imported-header`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            Toast.error(error.error || '❌ Erreur');
            return;
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'apercu_en-tete_importe.pdf';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        Toast.success('✅ Aperçu PDF téléchargé');
        
    } catch (error) {
        console.error('Erreur previewImportedHeader:', error);
        Toast.error('❌ Erreur génération aperçu');
    }
}

async configurerAcompte(id_devis) {
    try {
        const response = await apiRequest(`/api/devis/${id_devis}`);
        const devis = await response.json();
        
        const pourcentage = prompt(
            `💰 Configuration de l'acompte\n\n` +
            `Devis #${id_devis}\n` +
            `Montant total: ${devis.total.toLocaleString()} FCFA\n\n` +
            `Entrez le pourcentage d'acompte (0-100) :`,
            '20'
        );
        
        if (pourcentage === null) return;
        
        const pct = parseInt(pourcentage);
        if (isNaN(pct) || pct < 0 || pct > 100) {
            Toast.error('❌ Pourcentage invalide (0-100)');
            return;
        }
        
        const result = await apiRequest(`/api/devis/${id_devis}/acompte`, {
            method: 'POST',
            body: JSON.stringify({ pourcentage: pct })
        });
        const data = await result.json();
        
        if (data.success) {
            Toast.success(`✅ Acompte configuré : ${pct}% (${data.acompte_montant.toLocaleString()} FCFA)`);
            this.loadPage('devis');
        } else {
            Toast.error(data.message || '❌ Erreur');
        }
    } catch (error) {
        Toast.error('❌ Erreur de connexion');
    }
}

async creerSituation(id_devis) {
    try {
        // Récupérer les situations existantes
        const situationsResponse = await apiRequest(`/api/devis/${id_devis}/situations`);
        const situations = await situationsResponse.json();
        
        const devisResponse = await apiRequest(`/api/devis/${id_devis}`);
        const devis = await devisResponse.json();
        
        const total = devis.total || 0;
        const acompte = devis.acompte_montant || 0;
        const montantRestant = total - acompte;
        const situationsExistantes = situations.length;
        
        // Calculer le pourcentage automatique restant
        const totalSitPourcent = situations.reduce((sum, s) => sum + (s.pourcentage || 0), 0);
        const pourcentageRestant = 100 - totalSitPourcent;
        
        const pourcentage = prompt(
            `📊 Nouvelle situation de travaux\n\n` +
            `Devis #${id_devis}\n` +
            `Montant total: ${total.toLocaleString()} FCFA\n` +
            `Acompte: ${acompte.toLocaleString()} FCFA\n` +
            `Montant restant: ${montantRestant.toLocaleString()} FCFA\n` +
            `Situations déjà créées: ${situationsExistantes}\n` +
            `Pourcentage restant: ${pourcentageRestant}%\n\n` +
            `Entrez le pourcentage pour cette situation (0-${pourcentageRestant}) :`,
            Math.min(30, pourcentageRestant)
        );
        
        if (pourcentage === null) return;
        
        const pct = parseInt(pourcentage);
        if (isNaN(pct) || pct < 0 || pct > pourcentageRestant) {
            Toast.error(`❌ Pourcentage invalide (0-${pourcentageRestant})`);
            return;
        }
        
        const travaux = prompt(
            `📝 Travaux réalisés pour cette situation :\n` +
            `(Décrivez les travaux effectués)`,
            ''
        );
        
        if (travaux === null) return;
        
        const result = await apiRequest(`/api/devis/${id_devis}/situation`, {
            method: 'POST',
            body: JSON.stringify({ 
                pourcentage: pct,
                travaux_realises: travaux || ''
            })
        });
        const data = await result.json();
        
        if (data.success) {
            Toast.success(`✅ Situation ${data.numero} créée : ${data.montant.toLocaleString()} FCFA`);
            // 🔥 Rafraîchir automatiquement
            if (this.currentDevisId) {
                await this.viewDevis(this.currentDevisId);
            } else {
                this.loadPage('devis');
            }
        } else {
            Toast.error(data.message || '❌ Erreur');
        }
    } catch (error) {
        console.error('❌ Erreur creerSituation:', error);
        Toast.error('❌ Erreur de connexion');
    }
}


async payerSituation(id_situation) {
    if (!confirm('💰 Marquer cette situation comme payée ?')) return;
    
    try {
        const response = await apiRequest(`/api/situation/${id_situation}/payer`, {
            method: 'PUT'
        });
        const result = await response.json();
        
        if (result.success) {
            Toast.success('✅ Situation marquée comme payée');
            // 🔥 Rafraîchir automatiquement la vue du devis
            if (this.currentDevisId) {
                await this.viewDevis(this.currentDevisId);
            } else {
                this.loadPage('devis');
            }
        } else {
            Toast.error(result.message || '❌ Erreur');
        }
    } catch (error) {
        console.error('❌ Erreur payerSituation:', error);
        Toast.error('❌ Erreur de connexion');
    }
}

async payerAcompte(id_devis) {
    if (!confirm('💰 Marquer l\'acompte comme payé ?')) return;
    
    try {
        const response = await apiRequest(`/api/devis/${id_devis}/payer-acompte`, {
            method: 'PUT'
        });
        const result = await response.json();
        
        if (result.success) {
            Toast.success('✅ Acompte marqué comme payé');
            // 🔥 Rafraîchir automatiquement
            if (this.currentDevisId) {
                await this.viewDevis(this.currentDevisId);
            } else {
                this.loadPage('devis');
            }
        } else {
            Toast.error(result.message || '❌ Erreur');
        }
    } catch (error) {
        console.error('❌ Erreur payerAcompte:', error);
        Toast.error('❌ Erreur de connexion');
    }
}

async downloadFacturePDF(id_facture) {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            Toast.error('❌ Vous devez être connecté');
            return;
        }
        
        Toast.info('📄 Téléchargement de la facture...');
        
        const response = await fetch(`${API_URL}/api/facture/${id_facture}/pdf`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            Toast.error(error.error || '❌ Erreur');
            return;
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `facture_${id_facture}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        Toast.success('✅ Facture PDF téléchargée');
        
    } catch (error) {
        console.error('Erreur downloadFacturePDF:', error);
        Toast.error('❌ Erreur téléchargement');
    }
}
async uploadLogo() {
    const fileInput = document.getElementById('company-logo');
    const file = fileInput.files[0];
    if (!file) {
        Toast.warning('Veuillez sélectionner un fichier');
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
            Toast.success('✅ Logo téléchargé avec succès !');
            // 🔥 Forcer le rechargement de la page des paramètres
            setTimeout(() => {
                this.loadPage('parametres');
            }, 500);
        } else {
            Toast.error(result.message || 'Erreur lors du téléchargement');
        }
    } catch (error) {
        Toast.error('❌ Erreur de connexion');
    }
}

async saveCompanySettings() {
    const data = {
        company_name: document.getElementById('company-name')?.value || '',
        company_email: document.getElementById('company-email')?.value || '',
        company_phone: document.getElementById('company-phone')?.value || '',
        company_address: document.getElementById('company-address')?.value || '',
        slogan: document.getElementById('header-slogan')?.value || '',
        website: document.getElementById('header-website')?.value || '',
        footer_text: document.getElementById('header-footer')?.value || ''
    };
    
    try {
        const response = await apiRequest('/api/settings', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (result.success) {
            Toast.success('✅ Informations enregistrées');
            this.loadPage('parametres');
        } else {
            Toast.error(result.message || '❌ Erreur');
        }
    } catch (error) {
        Toast.error('❌ Erreur de connexion');
    }
}

async saveColorSettings() {
    const data = {
        primary_color: document.getElementById('primary-color')?.value || '#1E3A8A',
        secondary_color: document.getElementById('secondary-color')?.value || '#7C3AED',
        accent_color: document.getElementById('accent-color')?.value || '#06B6D4'
    };
    
    try {
        const response = await apiRequest('/api/settings', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (result.success) {
            Toast.success('✅ Couleurs appliquées');
            this.applyThemeColors(data);
            this.loadPage('parametres');
        } else {
            Toast.error(result.message || '❌ Erreur');
        }
    } catch (error) {
        Toast.error('❌ Erreur de connexion');
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
        // 🔥 L'admin ne récupère pas les notifications
        if (this.currentUser && (this.currentUser.email === 'admin@btp.com' || this.currentUser.email === 'bylgaitb@gmail.com')) {
            return [];
        }
        
        const response = await apiRequest('/api/notifications');
        const data = await response.json();
        console.log("📬 Notifications récupérées:", data);
        return data;
    } catch (error) {
        console.error("Erreur fetchNotifications:", error);
        return [];
    }
}
// Afficher les notifications au chargement
async showNotifications() {
    // 🔥 L'admin ne voit PAS les notifications
    if (this.currentUser && (this.currentUser.email === 'admin@btp.com' || this.currentUser.email === 'bylgaitb@gmail.com')) {
        console.log("👑 Admin - pas de notifications");
        return;
    }
    
    // Récupérer le statut de l'abonnement pour filtrer
    let abonnementStatut = 'actif';
    try {
        const response = await apiRequest('/api/abonnement/statut');
        const data = await response.json();
        abonnementStatut = data.statut || 'inactif';
        console.log("🔍 Statut abonnement:", abonnementStatut);
    } catch(e) {
        console.error("Erreur récupération abonnement:", e);
    }
    
    const notifications = await this.fetchNotifications();
    
    if (notifications.length === 0) return;
    
    // 🔥 Filtrer les notifications : ne montrer que celles du bon type
    for (const notif of notifications) {
        // Ne pas montrer les notifications de suspension si l'utilisateur n'est PAS suspendu
        if (notif.type === 'suspension' && abonnementStatut !== 'suspendu') {
            console.log("⏭️ Notification de suspension ignorée (utilisateur non suspendu)");
            continue;
        }
        // Ne pas montrer les notifications de renouvellement si l'utilisateur est suspendu
        if (notif.type === 'renouvellement' && abonnementStatut === 'suspendu') {
            console.log("⏭️ Notification de renouvellement ignorée (utilisateur suspendu)");
            continue;
        }
        
        setTimeout(() => {
            this.showNotificationToast(notif);
        }, 1000);
    }
}

// Afficher une notification toast
showNotificationToast(notification) {
    // 🔥 L'admin ne voit pas les notifications
    if (this.currentUser && (this.currentUser.email === 'admin@btp.com' || this.currentUser.email === 'bylgaitb@gmail.com')) {
        return;
    }
    
    // 🔥 Ne pas afficher les notifications de suspension si l'utilisateur n'est pas suspendu
    // (on le vérifie à nouveau pour être sûr)
    this.apiRequest('/api/abonnement/statut').then(response => response.json()).then(data => {
        if (notification.type === 'suspension' && data.statut !== 'suspendu') {
            console.log("⏭️ Notification de suspension ignorée (statut:", data.statut, ")");
            return;
        }
        
        // Afficher la notification
        this._showToast(notification);
    }).catch(() => {
        // En cas d'erreur, on affiche quand même
        this._showToast(notification);
    });
}

// Méthode helper pour l'affichage
_showToast(notification) {
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
    
    const icon = notification.type === 'suspension' ? 'fa-exclamation-triangle' : 'fa-bell';
    const bgColor = notification.type === 'suspension' ? 'linear-gradient(135deg, #991B1B, #EF4444)' : 'linear-gradient(135deg, #1E3A8A, #7C3AED)';
    toast.style.background = bgColor;
    
    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px;">
            <i class="fas ${icon}" style="font-size: 20px;"></i>
            <div style="flex: 1;">
                <strong style="display: block; margin-bottom: 5px;">
                    ${notification.type === 'suspension' ? '⛔ Abonnement suspendu' : 'Renouvellement d\'abonnement'}
                </strong>
                <span style="font-size: 0.85rem;">${notification.message}</span>
            </div>
            <i class="fas fa-times" style="cursor: pointer; opacity: 0.7;" onclick="this.closest('.notification-toast').remove()"></i>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Fermeture automatique après 8 secondes
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideOutRight 0.5s ease';
            setTimeout(() => toast.remove(), 500);
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
    
    // Admin = illimité
    if (user && (user.email === 'admin@btp.com' || user.email === 'bylgaitb@gmail.com')) {
        console.log("👑 Admin détecté - pas de limites");
        return true;
    }
    
    // Récupérer l'abonnement via l'API
    try {
        const response = await apiRequest('/api/abonnement/statut');
        const data = await response.json();
        
        console.log("🔍 checkLimites - data:", data);
        
        // 🔥 Gestion des différents statuts
        if (!data.success) {
            Toast.warning('⚠️ Abonnement non trouvé. Contactez l\'administrateur.');
            return false;
        }
        
        // Statut : expiré
        if (data.statut === 'expiré') {
            Toast.error('⛔ Votre abonnement a expiré. Contactez l\'administrateur pour le renouveler.');
            return false;
        }
        
        // Statut : suspendu
        if (data.statut === 'suspendu') {
            Toast.error('⛔ Votre abonnement est suspendu. Contactez l\'administrateur.');
            return false;
        }
        
        // Statut : inactif ou autre
        if (data.statut !== 'actif') {
            Toast.warning('⚠️ Abonnement inactif. Contactez l\'administrateur.');
            return false;
        }
        
        // Si l'abonnement est actif, vérifier les limites
        const offre = data.type || 'starter';
        
        const limites = {
            starter: { clients: 10, projets: 10, devis: 20 },
            pro: { clients: 999999, projets: 999999, devis: 999999 },
            annuel: { clients: 999999, projets: 999999, devis: 999999 },
            essai: { clients: 999999, projets: 999999, devis: 999999 },
            illimite: { clients: 999999, projets: 999999, devis: 999999 }
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
            Toast.warning(`❌ Limite de clients atteinte (${limites[offre].clients}). Passez à l'offre Pro !`);
            return false;
        }
        if (operation === 'projet' && counts.projets >= limites[offre].projets) {
            Toast.warning(`❌ Limite de projets atteinte (${limites[offre].projets}). Passez à l'offre Pro !`);
            return false;
        }
        if (operation === 'devis' && counts.devis >= limites[offre].devis) {
            Toast.warning(`❌ Limite de devis atteinte (${limites[offre].devis}). Passez à l'offre Pro !`);
            return false;
        }
        
        return true;
        
    } catch (error) {
        console.error('❌ Erreur checkLimites:', error);
        // En cas d'erreur, on autorise par défaut pour éviter de bloquer l'utilisateur
        return true;
    }
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


async getAbonnement() {
    try {
        const response = await apiRequest('/api/abonnement/statut');
        const data = await response.json();
        if (data.success) {
            return { type_abonnement: data.type };
        }
        return { type_abonnement: 'starter' };
    } catch (error) {
        console.error("Erreur getAbonnement:", error);
        return { type_abonnement: 'starter' };
    }
}

async getCurrentCounts() {
    try {
        const clients = await this.fetchClients();
        const projets = await this.fetchProjets();
        const devis = await this.fetchDevis();
        return {
            clients: clients.length,
            projets: projets.length,
            devis: devis.length
        };
    } catch (error) {
        return { clients: 0, projets: 0, devis: 0 };
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
                    
                    // 🔥 Lire la réponse en texte d'abord pour debug
                    const text = await response.text();
                    console.log("📊 Réponse brute restauration:", text);
                    
                    let result;
                    try {
                        result = JSON.parse(text);
                    } catch(e) {
                        console.error("❌ Erreur parsing JSON:", e);
                        loadingDiv.remove();
                        alert('❌ Erreur: La réponse du serveur n\'est pas valide. Vérifiez les logs.');
                        return;
                    }
                    
                    console.log("📊 Résultat restauration:", result);
                    
                    // 🔥 Vérification plus tolérante
                    if (result && (result.success === true || result.message === 'Restauration réussie')) {
                        loadingDiv.innerHTML = `
                            <div style="background: #1E293B; padding: 30px 50px; border-radius: 20px; text-align: center; border: 1px solid #10B981;">
                                <i class="fas fa-check-circle" style="font-size: 48px; margin-bottom: 20px; color: #10B981;"></i>
                                <h3>✅ Restauration réussie !</h3>
                                <p style="margin-top: 10px; color: #94A3B8;">
                                    ${result.data ? 
                                        `${result.data.clients || 0} clients, ${result.data.projets || 0} projets, ${result.data.devis || 0} devis restaurés` : 
                                        'Toutes vos données ont été restaurées'
                                    }
                                </p>
                                <p style="margin-top: 10px; color: #94A3B8;">Redirection vers la page de connexion...</p>
                            </div>
                        `;
                        
                        setTimeout(() => {
                            localStorage.removeItem('token');
                            localStorage.removeItem('user');
                            window.location.href = 'login.html';
                        }, 3000);
                    } else {
                        loadingDiv.remove();
                        alert('❌ Erreur: ' + (result?.error || result?.message || 'Erreur inconnue'));
                    }
                } catch (error) {
                    document.getElementById('restore-loading')?.remove();
                    console.error('❌ Erreur restauration:', error);
                    if (error.name === 'AbortError') {
                        alert('❌ La restauration a pris trop de temps. Vérifiez votre connexion.');
                    } else if (error.message.includes('Unexpected')) {
                        alert('❌ Le fichier sélectionné n\'est pas un fichier de sauvegarde valide.');
                    } else {
                        alert('❌ Erreur: ' + error.message);
                    }
                }
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// ==================== PAGE ADMIN ====================
async renderAdmin() {
    try {
        const user = this.currentUser;
        const isAdmin = user && (user.email === 'admin@btp.com' || user.email === 'bylgaitb@gmail.com');
        
        if (!isAdmin) {
            return `
                <div class="glass-card" style="text-align:center; padding:3rem;">
                    <i class="fas fa-shield-alt" style="font-size:48px; color:#EF4444; margin-bottom:1rem;"></i>
                    <h3 style="color:#EF4444;">⛔ Accès non autorisé</h3>
                    <p style="color:#94A3B8;">Vous n'avez pas les droits pour accéder à cette page.</p>
                </div>
            `;
        }
        
        // Récupérer les données
        const abonnements = this.safeArray(await this.fetchAbonnements());
        const totalUsers = abonnements.length;
        const actifs = abonnements.filter(a => a.statut === 'actif').length;
        const expiresSoon = abonnements.filter(a => a.jours_restants > 0 && a.jours_restants < 8).length;
        const suspendus = abonnements.filter(a => a.statut === 'suspendu').length;
        
        // Récupérer l'onglet actif
        const activeTab = this.currentAdminTab || 'overview';
        
        return `
            <div class="page-content">
                <!-- EN-TÊTE -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem;">
                    <div>
                        <h2 style="font-size: 1.8rem; font-weight: 700; display: flex; align-items: center; gap: 12px;">
                            <i class="fas fa-shield-alt" style="color: var(--accent, #06B6D4);"></i>
                            Administration
                        </h2>
                        <p style="color: var(--gray-light, #94A3B8); margin-top: 0.25rem;">
                            Gérez les utilisateurs, abonnements et paiements
                        </p>
                    </div>
                </div>

                <!-- ONGLETS -->
                <div style="display:flex; gap:0; border-bottom:2px solid #334155; margin-bottom:1.5rem; flex-wrap:wrap; background:rgba(255,255,255,0.03); border-radius:12px 12px 0 0; padding:0 0.5rem;">
                    <div class="tab-admin ${activeTab === 'overview' ? 'active' : ''}" 
                         onclick="app.switchAdminTab('overview')" 
                         style="padding:12px 20px; cursor:pointer; border-bottom:3px solid ${activeTab === 'overview' ? '#06B6D4' : 'transparent'}; color:${activeTab === 'overview' ? 'white' : '#94A3B8'}; transition:all 0.3s; font-weight:500; display:flex; align-items:center; gap:8px;">
                        <i class="fas fa-chart-pie"></i> Vue d'ensemble
                    </div>
                    <div class="tab-admin ${activeTab === 'users' ? 'active' : ''}" 
                         onclick="app.switchAdminTab('users')" 
                         style="padding:12px 20px; cursor:pointer; border-bottom:3px solid ${activeTab === 'users' ? '#06B6D4' : 'transparent'}; color:${activeTab === 'users' ? 'white' : '#94A3B8'}; transition:all 0.3s; font-weight:500; display:flex; align-items:center; gap:8px;">
                        <i class="fas fa-users"></i> Utilisateurs <span style="background:#334155; padding:2px 10px; border-radius:12px; font-size:0.7rem;">${totalUsers}</span>
                    </div>
                    <div class="tab-admin ${activeTab === 'subscriptions' ? 'active' : ''}" 
                         onclick="app.switchAdminTab('subscriptions')" 
                         style="padding:12px 20px; cursor:pointer; border-bottom:3px solid ${activeTab === 'subscriptions' ? '#06B6D4' : 'transparent'}; color:${activeTab === 'subscriptions' ? 'white' : '#94A3B8'}; transition:all 0.3s; font-weight:500; display:flex; align-items:center; gap:8px;">
                        <i class="fas fa-crown"></i> Abonnements
                    </div>
                    <div class="tab-admin ${activeTab === 'payments' ? 'active' : ''}" 
                         onclick="app.switchAdminTab('payments')" 
                         style="padding:12px 20px; cursor:pointer; border-bottom:3px solid ${activeTab === 'payments' ? '#06B6D4' : 'transparent'}; color:${activeTab === 'payments' ? 'white' : '#94A3B8'}; transition:all 0.3s; font-weight:500; display:flex; align-items:center; gap:8px;">
                        <i class="fas fa-credit-card"></i> Paiements
                    </div>
                    <div class="tab-admin ${activeTab === 'stats' ? 'active' : ''}" 
                         onclick="app.switchAdminTab('stats')" 
                         style="padding:12px 20px; cursor:pointer; border-bottom:3px solid ${activeTab === 'stats' ? '#06B6D4' : 'transparent'}; color:${activeTab === 'stats' ? 'white' : '#94A3B8'}; transition:all 0.3s; font-weight:500; display:flex; align-items:center; gap:8px;">
                        <i class="fas fa-chart-line"></i> Statistiques
                    </div>
                </div>

                <!-- CONTENU -->
                <div id="admin-content">
                    ${activeTab === 'overview' ? this.renderAdminOverview(abonnements, totalUsers, actifs, expiresSoon, suspendus) :
                      activeTab === 'users' ? this.renderAdminUsers(abonnements) :
                      activeTab === 'subscriptions' ? this.renderAdminSubscriptions(abonnements) :
                      activeTab === 'payments' ? this.renderAdminPayments() :
                      activeTab === 'stats' ? this.renderAdminStats(abonnements) :
                      this.renderAdminOverview(abonnements, totalUsers, actifs, expiresSoon, suspendus)}
                </div>
            </div>
        `;
    } catch (error) {
        console.error('❌ Erreur renderAdmin:', error);
        return `
            <div class="glass-card" style="text-align:center; padding:3rem;">
                <i class="fas fa-exclamation-triangle" style="font-size:48px; color:#F59E0B; margin-bottom:1rem;"></i>
                <h3>❌ Erreur chargement</h3>
                <p style="color:#94A3B8;">${error.message}</p>
            </div>
        `;
    }
}


renderAdminOverview(abonnements, totalUsers, actifs, expiresSoon, suspendus) {
    const revenusMensuels = this.calculerRevenusMensuels(abonnements);
    
    return `
        <div class="admin-overview">
            <!-- Cartes stats -->
            <div class="cards-grid" style="margin-bottom:2rem;">
                <div class="glass-card" style="text-align:center; border-left:4px solid #06B6D4;">
                    <div style="display:flex; align-items:center; justify-content:center; gap:12px; margin-bottom:0.5rem;">
                        <i class="fas fa-users" style="font-size:24px; color:#06B6D4;"></i>
                        <span style="font-size:0.8rem; color:#94A3B8;">Total utilisateurs</span>
                    </div>
                    <div style="font-size:2.5rem; font-weight:700; color:white;">${totalUsers}</div>
                </div>
                
                <div class="glass-card" style="text-align:center; border-left:4px solid #10B981;">
                    <div style="display:flex; align-items:center; justify-content:center; gap:12px; margin-bottom:0.5rem;">
                        <i class="fas fa-check-circle" style="font-size:24px; color:#10B981;"></i>
                        <span style="font-size:0.8rem; color:#94A3B8;">Abonnements actifs</span>
                    </div>
                    <div style="font-size:2.5rem; font-weight:700; color:#10B981;">${actifs}</div>
                </div>
                
                <div class="glass-card" style="text-align:center; border-left:4px solid #F59E0B;">
                    <div style="display:flex; align-items:center; justify-content:center; gap:12px; margin-bottom:0.5rem;">
                        <i class="fas fa-clock" style="font-size:24px; color:#F59E0B;"></i>
                        <span style="font-size:0.8rem; color:#94A3B8;">Expiration ≤ 7 jours</span>
                    </div>
                    <div style="font-size:2.5rem; font-weight:700; color:#F59E0B;">${expiresSoon}</div>
                </div>
                
                <div class="glass-card" style="text-align:center; border-left:4px solid #EF4444;">
                    <div style="display:flex; align-items:center; justify-content:center; gap:12px; margin-bottom:0.5rem;">
                        <i class="fas fa-pause-circle" style="font-size:24px; color:#EF4444;"></i>
                        <span style="font-size:0.8rem; color:#94A3B8;">Abonnements suspendus</span>
                    </div>
                    <div style="font-size:2.5rem; font-weight:700; color:#EF4444;">${suspendus}</div>
                </div>
            </div>

            <!-- Répartition des offres -->
            <div class="glass-card" style="margin-bottom:1.5rem;">
                <h3 style="margin-bottom:1rem; font-weight:600;">
                    <i class="fas fa-chart-pie" style="color:#06B6D4;"></i> Répartition des offres
                </h3>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(150px,1fr)); gap:1rem;">
                    ${this.getOffreRepartition(abonnements)}
                </div>
            </div>

            <!-- Revenus estimés -->
            <div class="glass-card" style="background:linear-gradient(135deg, rgba(6,182,212,0.1), rgba(124,58,237,0.1)); border:1px solid rgba(6,182,212,0.2);">
                <h3 style="margin-bottom:0.5rem; font-weight:600;">
                    <i class="fas fa-coins" style="color:#F59E0B;"></i> Revenus mensuels estimés
                </h3>
                <div style="font-size:2.5rem; font-weight:700; color:#06B6D4;">
                    ${revenusMensuels.toLocaleString()} FCFA
                </div>
                <p style="font-size:0.8rem; color:#94A3B8; margin-top:0.5rem;">
                    Basé sur les abonnements actifs du mois
                </p>
            </div>
        </div>
    `;
}

renderAdminUsers(abonnements) {
    if (!abonnements || abonnements.length === 0) {
        return `
            <div class="glass-card" style="text-align:center; padding:3rem;">
                <i class="fas fa-users" style="font-size:48px; opacity:0.3;"></i>
                <p>Aucun utilisateur trouvé</p>
            </div>
        `;
    }

    return `
        <div class="table-container">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem; flex-wrap:wrap; gap:1rem;">
                <h3 style="font-weight:600;">
                    <i class="fas fa-users"></i> Liste des utilisateurs
                </h3>
                <div class="search-box">
                    <i class="fas fa-search"></i>
                    <input type="text" id="admin-user-search" placeholder="Rechercher..." 
                           oninput="app.filterAdminUsers()" style="width:250px; padding:8px 12px 8px 35px; border-radius:8px; border:1px solid #334155; background:#1E293B; color:white;">
                </div>
            </div>
            
            <div style="overflow-x:auto;">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>#ID</th>
                            <th>Nom</th>
                            <th>Email</th>
                            <th>Entreprise</th>
                            <th>Offre</th>
                            <th>Statut</th>
                            <th>Jours restants</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${abonnements.map(a => `
                            <tr>
                                <td><span style="color:#94A3B8; font-size:0.8rem;">#${a.id_user}</span></td>
                                <td><strong>${this.escapeHtml(a.nom || '-')}</strong></td>
                                <td style="color:#94A3B8; font-size:0.85rem;">${this.escapeHtml(a.email)}</td>
                                <td>${this.escapeHtml(a.entreprise || '-')}</td>
                                <td>${this.getOffreBadge(a.type_abonnement)}</td>
                                <td>${this.getStatusBadge(a.statut)}</td>
                                <td>${this.getJoursRestantsBadge(a.jours_restants)}</td>
                                <td>
                                    <div style="display:flex; gap:4px; flex-wrap:wrap;">
                                        <button class="btn-icon" onclick="app.voirDetailsUser(${a.id_user})" title="Détails" style="background:#3B82F6;color:white;">
                                            <i class="fas fa-eye"></i>
                                        </button>
                                        <button class="btn-icon" onclick="app.editUserAbonnement(${a.id_user})" title="Modifier offre" style="background:#F59E0B;color:white;">
                                            <i class="fas fa-edit"></i>
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
}

renderAdminSubscriptions(abonnements) {
    if (!abonnements || abonnements.length === 0) {
        return `
            <div class="glass-card" style="text-align:center; padding:3rem;">
                <i class="fas fa-crown" style="font-size:48px; opacity:0.3;"></i>
                <p>Aucun abonnement trouvé</p>
            </div>
        `;
    }

    return `
        <div class="table-container">
            <h3 style="margin-bottom:1.5rem; font-weight:600;">
                <i class="fas fa-crown" style="color:#F59E0B;"></i> Gestion des abonnements
            </h3>
            
            <div style="overflow-x:auto;">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Client</th>
                            <th>Offre</th>
                            <th>Statut</th>
                            <th>Date début</th>
                            <th>Date fin</th>
                            <th>Jours restants</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${abonnements.map(a => `
                            <tr>
                                <td><strong>${this.escapeHtml(a.nom || '-')}</strong></td>
                                <td>${this.getOffreBadge(a.type_abonnement)}</td>
                                <td>${this.getStatusBadge(a.statut)}</td>
                                <td style="font-size:0.85rem;">${a.date_debut ? new Date(a.date_debut).toLocaleDateString() : '-'}</td>
                                <td style="font-size:0.85rem;">${a.date_fin ? new Date(a.date_fin).toLocaleDateString() : '-'}</td>
                                <td>${this.getJoursRestantsBadge(a.jours_restants)}</td>
                                <td>
                                    <div style="display:flex; gap:4px; flex-wrap:wrap;">
                                        ${this.getAbonnementActions(a)}
                                    </div>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

renderAdminPayments() {
    // Cette fonction sera implémentée quand on aura la route des paiements
    return `
        <div class="glass-card" style="text-align:center; padding:3rem;">
            <i class="fas fa-credit-card" style="font-size:48px; opacity:0.3;"></i>
            <h3>Historique des paiements</h3>
            <p style="color:#94A3B8;">Les paiements seront affichés ici</p>
            <button class="btn-primary" onclick="app.refreshPayments()" style="margin-top:1rem;">
                <i class="fas fa-sync"></i> Actualiser
            </button>
        </div>
    `;
}

renderAdminStats(abonnements) {
    const stats = this.getStatsAbonnements(abonnements);
    
    return `
        <div class="admin-stats">
            <div class="cards-grid" style="margin-bottom:1.5rem;">
                <div class="glass-card" style="text-align:center;">
                    <h4 style="color:#94A3B8; font-size:0.85rem;">Total utilisateurs</h4>
                    <div style="font-size:2rem; font-weight:700; color:white;">${stats.total}</div>
                </div>
                <div class="glass-card" style="text-align:center;">
                    <h4 style="color:#94A3B8; font-size:0.85rem;">Abonnements actifs</h4>
                    <div style="font-size:2rem; font-weight:700; color:#10B981;">${stats.actifs}</div>
                </div>
                <div class="glass-card" style="text-align:center;">
                    <h4 style="color:#94A3B8; font-size:0.85rem;">Taux d'activation</h4>
                    <div style="font-size:2rem; font-weight:700; color:#06B6D4;">${stats.tauxActivation}%</div>
                </div>
                <div class="glass-card" style="text-align:center;">
                    <h4 style="color:#94A3B8; font-size:0.85rem;">CA mensuel estimé</h4>
                    <div style="font-size:2rem; font-weight:700; color:#F59E0B;">${stats.caMensuel} FCFA</div>
                </div>
            </div>

            <!-- Répartition par offre -->
            <div class="glass-card">
                <h3 style="margin-bottom:1rem; font-weight:600;">
                    <i class="fas fa-chart-bar" style="color:#06B6D4;"></i> Répartition par offre
                </h3>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px,1fr)); gap:1rem;">
                    ${Object.entries(stats.repartition).map(([offre, count]) => `
                        <div style="background:rgba(255,255,255,0.05); border-radius:12px; padding:1rem; text-align:center;">
                            <div style="font-size:1.5rem; font-weight:700; color:white;">${count}</div>
                            <div style="font-size:0.85rem; color:#94A3B8;">${this.getOffreLabel(offre)}</div>
                            <div style="margin-top:0.5rem; height:4px; background:#1E293B; border-radius:4px; overflow:hidden;">
                                <div style="width:${stats.total > 0 ? (count/stats.total*100) : 0}%; height:100%; background:${this.getOffreColor(offre)}; border-radius:4px;"></div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
}

// ==================== FONCTIONS UTILITAIRES ADMIN ====================

getOffreBadge(type) {
    const configs = {
        artisan: { label: 'Artisan', color: '#D97706', icon: 'fa-hammer' },
        starter: { label: 'Starter', color: '#10B981', icon: 'fa-leaf' },
        pro: { label: 'Pro', color: '#3B82F6', icon: 'fa-crown' },
        annuel: { label: 'Annuel', color: '#F59E0B', icon: 'fa-gem' },
        essai: { label: 'Essai', color: '#8B5CF6', icon: 'fa-gift' },
        illimite: { label: 'Illimité', color: '#EF4444', icon: 'fa-infinity' }
    };
    const config = configs[type] || configs.starter;
    return `
        <span style="display:inline-flex; align-items:center; gap:6px; background:${config.color}22; color:${config.color}; padding:4px 12px; border-radius:20px; font-size:0.75rem; font-weight:600;">
            <i class="fas ${config.icon}"></i> ${config.label}
        </span>
    `;
}

getStatusBadge(statut) {
    const configs = {
        actif: { label: 'Actif', color: '#10B981', icon: 'fa-check-circle' },
        suspendu: { label: 'Suspendu', color: '#EF4444', icon: 'fa-pause-circle' },
        expiré: { label: 'Expiré', color: '#6B7280', icon: 'fa-clock' },
        inactif: { label: 'Inactif', color: '#6B7280', icon: 'fa-circle' }
    };
    const config = configs[statut] || configs.inactif;
    return `
        <span style="display:inline-flex; align-items:center; gap:6px; background:${config.color}22; color:${config.color}; padding:4px 12px; border-radius:20px; font-size:0.75rem; font-weight:600;">
            <i class="fas ${config.icon}"></i> ${config.label}
        </span>
    `;
}

getJoursRestantsBadge(jours) {
    if (jours === undefined || jours === null) return '<span style="color:#6B7280;">-</span>';
    if (jours < 0) return '<span style="color:#EF4444;">Expiré</span>';
    if (jours < 7) return `<span style="color:#F59E0B; font-weight:700;">${jours} jours ⚠️</span>`;
    return `<span style="color:#10B981;">${jours} jours</span>`;
}

getOffreRepartition(abonnements) {
    const repartition = {};
    abonnements.forEach(a => {
        const offre = a.type_abonnement || 'starter';
        repartition[offre] = (repartition[offre] || 0) + 1;
    });
    
    return Object.entries(repartition).map(([offre, count]) => `
        <div style="background:rgba(255,255,255,0.05); border-radius:12px; padding:1rem; text-align:center;">
            <div style="font-size:1.5rem; font-weight:700; color:white;">${count}</div>
            <div style="font-size:0.85rem; color:#94A3B8;">${this.getOffreLabel(offre)}</div>
        </div>
    `).join('');
}

getOffreLabel(offre) {
    const labels = {
        artisan: '🛠️ Artisan',
        starter: '🟢 Starter',
        pro: '🔵 Pro',
        annuel: '🔴 Annuel',
        essai: '🎁 Essai',
        illimite: '♾️ Illimité'
    };
    return labels[offre] || offre;
}

getOffreColor(offre) {
    const colors = {
        artisan: '#D97706',
        starter: '#10B981',
        pro: '#3B82F6',
        annuel: '#F59E0B',
        essai: '#8B5CF6',
        illimite: '#EF4444'
    };
    return colors[offre] || '#6B7280';
}

getAbonnementActions(a) {
    const actions = [];
    
    // 🔥 OFFRES DISPONIBLES AVEC ARTISAN
    const offres = [
        { type: 'artisan', icon: 'fa-hammer', color: '#D97706', label: 'Artisan', prix: '7 000' },
        { type: 'starter', icon: 'fa-leaf', color: '#10B981', label: 'Starter', prix: '15 000' },
        { type: 'pro', icon: 'fa-crown', color: '#3B82F6', label: 'Pro', prix: '30 000' },
        { type: 'annuel', icon: 'fa-gem', color: '#F59E0B', label: 'Annuel', prix: '250 000' }
    ];
    
    // Boutons pour chaque offre
    offres.forEach(o => {
        if (a.type_abonnement !== o.type) {
            actions.push(`
                <button class="btn-icon" onclick="app.prolongerAbonnement(${a.id_user}, ${this.getOffreDuree(o.type)}, ${this.getOffrePrix(o.type)}, '${o.type}')" 
                        title="Passer à ${o.label} (${o.prix} FCFA)" 
                        style="background:${o.color}; color:white; width:34px; height:34px; border-radius:8px; border:none; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; transition:all 0.3s;"
                        onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'">
                    <i class="fas ${o.icon}"></i>
                </button>
            `);
        }
    });
    
    // Bouton suspendre/réactiver
    if (a.statut === 'actif') {
        actions.push(`
            <button class="btn-icon" onclick="app.suspendreAbonnement(${a.id_user})" 
                    title="Suspendre" style="background:#EF4444; color:white; width:34px; height:34px; border-radius:8px; border:none; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; transition:all 0.3s;"
                    onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'">
                <i class="fas fa-pause"></i>
            </button>
        `);
    } else if (a.statut === 'suspendu') {
        actions.push(`
            <button class="btn-icon" onclick="app.reactiverAbonnement(${a.id_user})" 
                    title="Réactiver" style="background:#10B981; color:white; width:34px; height:34px; border-radius:8px; border:none; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; transition:all 0.3s;"
                    onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'">
                <i class="fas fa-play"></i>
            </button>
        `);
    }
    
    // Bouton historique
    actions.push(`
        <button class="btn-icon" onclick="app.voirPaiements(${a.id_user})" 
                title="Historique" style="background:#6B7280; color:white; width:34px; height:34px; border-radius:8px; border:none; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; transition:all 0.3s;"
                onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'">
            <i class="fas fa-history"></i>
        </button>
    `);
    
    return actions.join('');
}
getOffreDuree(type) {
    const durees = {
        artisan: 30,
        starter: 30,
        pro: 30,
        annuel: 365
    };
    return durees[type] || 30;
}

getOffrePrix(type) {
    const prix = {
        artisan: 7000,
        starter: 15000,
        pro: 30000,
        annuel: 250000
    };
    return prix[type] || 0;
}


calculerRevenusMensuels(abonnements) {
    const prix = {
        artisan: 7000,
        starter: 15000,
        pro: 30000,
        annuel: 250000 / 12,
        essai: 0,
        illimite: 0
    };
    
    let total = 0;
    abonnements.forEach(a => {
        if (a.statut === 'actif') {
            total += (prix[a.type_abonnement] || 0);
        }
    });
    return Math.round(total);
}

getStatsAbonnements(abonnements) {
    const total = abonnements.length;
    const actifs = abonnements.filter(a => a.statut === 'actif').length;
    const tauxActivation = total > 0 ? Math.round((actifs / total) * 100) : 0;
    const caMensuel = this.calculerRevenusMensuels(abonnements);
    
    const repartition = {};
    abonnements.forEach(a => {
        const offre = a.type_abonnement || 'starter';
        repartition[offre] = (repartition[offre] || 0) + 1;
    });
    
    return { total, actifs, tauxActivation, caMensuel, repartition };
}

// ==================== NAVIGATION ADMIN ====================

switchAdminTab(tab) {
    this.currentAdminTab = tab;
    this.loadPage('admin');
}

filterAdminUsers() {
    const search = document.getElementById('admin-user-search')?.value.toLowerCase() || '';
    // La logique de filtrage sera implémentée via le re-rendu
    // Pour l'instant, on recharge la page avec le filtre
    this.loadPage('admin');
}

// ==================== ACTIONS ADMIN ====================

voirDetailsUser(id_user) {
    alert(`👤 Détails de l'utilisateur #${id_user}\n\nCette fonctionnalité affichera les détails complets.`);
}

editUserAbonnement(id_user) {
    alert(`✏️ Modification de l'abonnement de l'utilisateur #${id_user}\n\nSélectionnez la nouvelle offre.`);
}

refreshPayments() {
    Toast.info('🔄 Actualisation des paiements...');
    this.loadPage('admin');
}

async fetchAbonnements() {
    try {
        const response = await apiRequest('/api/admin/abonnements');
        const data = await response.json();
        return this.normalizeResponse(data);
    } catch (error) {
        console.error("Erreur fetchAbonnements:", error);
        return [];
    }
}

async prolongerAbonnement(id_user, jours, montant, offreType) {
    const methode = prompt(
        `💰 Confirmation paiement\n\n` +
        `Client: ID ${id_user}\n` +
        `Offre: ${this.getOffreLabel(offreType)}\n` +
        `Durée: ${jours} jours\n` +
        `Montant: ${montant.toLocaleString()} FCFA\n\n` +
        `Méthode de paiement reçue ?\n` +
        `- Virement\n` +
        `- Mobile Money\n` +
        `- Espèces`,
        'virement'
    );
    
    if (!methode) return;
    
    if (confirm(`✅ Confirmer le paiement de ${montant.toLocaleString()} FCFA pour l'offre ${this.getOffreLabel(offreType)} ?`)) {
        try {
            const response = await apiRequest(`/api/admin/abonnement/${id_user}/prolonger`, {
                method: 'POST',
                body: JSON.stringify({ jours, montant, methode, offreType })
            });
            const result = await response.json();
            if (result.success) {
                Toast.success(`✅ Abonnement ${this.getOffreLabel(offreType)} prolongé de ${jours} jours !`);
                this.loadPage('admin');
            } else {
                Toast.error(result.error || 'Erreur');
            }
        } catch (error) {
            Toast.error('❌ Erreur de connexion');
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

// Normaliser la réponse API (si elle est encapsulée)
normalizeResponse(data) {
    if (Array.isArray(data)) return data;
    if (data && typeof data === 'object') {
        // Chercher un tableau dans les propriétés
        if (data.data && Array.isArray(data.data)) return data.data;
        if (data.clients && Array.isArray(data.clients)) return data.clients;
        if (data.projets && Array.isArray(data.projets)) return data.projets;
        if (data.devis && Array.isArray(data.devis)) return data.devis;
        // Sinon, prendre toutes les valeurs
        return Object.values(data);
    }
    return [];
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
    // Sécurisation mobile
    if (!this.allDevis || !Array.isArray(this.allDevis)) {
        console.warn("allDevis n'est pas un tableau sur mobile");
        this.allDevis = [];
        const tbody = document.getElementById('devis-table-body');
        if (tbody) tbody.innerHTML = '<tr><td colspan="7">Aucun devis trouvé</td></tr>';
        return;
    }
    
    let filtered = [...this.allDevis];
    
    const searchTerm = document.getElementById('search-devis')?.value.toLowerCase().trim() || '';
    if (searchTerm) {
        filtered = filtered.filter(d => {
            if (d.id_devis && d.id_devis.toString().includes(searchTerm)) return true;
            if (d.client_nom && d.client_nom.toLowerCase().includes(searchTerm)) return true;
            if (d.nom_projet && d.nom_projet.toLowerCase().includes(searchTerm)) return true;
            return false;
        });
    }
    
    const statusFilter = document.getElementById('filter-status')?.value || 'all';
    if (statusFilter !== 'all') {
        filtered = filtered.filter(d => d.statut === statusFilter);
    }
    
    const dateFilter = document.getElementById('filter-date')?.value || 'all';
    if (dateFilter !== 'all') {
        const days = parseInt(dateFilter);
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - days);
        filtered = filtered.filter(d => new Date(d.date_creation) >= cutoffDate);
    }
    
    const tbody = document.getElementById('devis-table-body');
    const countDiv = document.getElementById('devis-count');
    
    if (tbody) {
        tbody.innerHTML = this.renderDevisTableRows(filtered);
    }
    if (countDiv) {
        countDiv.innerHTML = `${filtered.length} devis sur ${this.allDevis.length}`;
    }
}

async showSubscriptionBanner() {
    console.log("🟢 showSubscriptionBanner appelée");
    
    try {
        const response = await apiRequest('/api/abonnement/statut');
        const data = await response.json();
        
        console.log("📊 Données abonnement:", data);
        
        // 🔥 ADMIN : ne voit JAMAIS de bandeau
        if (this.currentUser && (this.currentUser.email === 'admin@btp.com' || this.currentUser.email === 'bylgaitb@gmail.com')) {
            console.log("👑 Admin - pas de bandeau");
            // Supprimer le bandeau s'il existe
            const oldBanner = document.getElementById('subscription-banner');
            if (oldBanner) oldBanner.remove();
            return;
        }
        
        // 🔥 Si l'abonnement est suspendu → afficher le bandeau de suspension
        if (data.success && data.statut === 'suspendu') {
            this.showSuspendedBanner();
            return;
        }
        
        // 🔥 Si l'abonnement est inactif ou expiré → pas de bandeau
        if (!data.success || data.statut !== 'actif') {
            console.log("❌ Pas d'abonnement actif");
            const oldBanner = document.getElementById('subscription-banner');
            if (oldBanner) oldBanner.remove();
            return;
        }
        
        // 🔥 ICI : abonnement actif → afficher le bandeau normal
        // Supprimer l'ancien bandeau
        const oldBanner = document.getElementById('subscription-banner');
        if (oldBanner) oldBanner.remove();
        
        const offre = data.type || 'starter';
        const joursRestants = data.jours_restants || 0;
        const dateFin = data.date_fin ? new Date(data.date_fin).toLocaleDateString('fr-FR') : 'inconnue';
        
        // Configuration des couleurs et icônes
        const configs = {
            essai: { bg: 'linear-gradient(135deg, #1E3A8A, #7C3AED)', icon: 'fa-gift', label: 'Essai gratuit' },
            starter: { bg: 'linear-gradient(135deg, #059669, #10B981)', icon: 'fa-leaf', label: 'Starter' },
            pro: { bg: 'linear-gradient(135deg, #1E3A8A, #06B6D4)', icon: 'fa-crown', label: 'Pro' },
            annuel: { bg: 'linear-gradient(135deg, #DC2626, #F59E0B)', icon: 'fa-gem', label: 'Annuel' }
        };
        
        const config = configs[offre] || configs.starter;
        const isExpiringSoon = joursRestants < 7 && joursRestants > 0;
        
        const banner = document.createElement('div');
        banner.id = 'subscription-banner';
        banner.style.cssText = `
            background: ${config.bg};
            border-radius: 16px;
            padding: 16px 24px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            animation: slideDown 0.5s ease;
            border: 1px solid rgba(255,255,255,0.15);
        `;
        
        let message = '';
        if (offre === 'essai') {
            message = `🎁 Période d'essai gratuite : plus que ${joursRestants} jour${joursRestants > 1 ? 's' : ''} !`;
        } else if (isExpiringSoon) {
            message = `⚠️ Votre abonnement ${config.label} expire dans ${joursRestants} jour${joursRestants > 1 ? 's' : ''} (le ${dateFin})`;
        } else {
            message = `✅ Abonnement ${config.label} actif jusqu'au ${dateFin} (${joursRestants} jours restants)`;
        }
        
        const WHATSAPP_URL = "https://wa.me/2290143733706";
        let buttonHtml = '';
        if (offre === 'essai') {
            buttonHtml = `
                <a href="${WHATSAPP_URL}?text=Bonjour%20BTP%20Devis%20Pro%2C%20je%20souhaite%20m%27abonner%20apr%C3%A8s%20mon%20essai%20gratuit" 
                   target="_blank" 
                   style="background:rgba(255,255,255,0.2);border:1px solid rgba(255,255,255,0.3);color:white;padding:8px 20px;border-radius:8px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block;font-size:0.85rem;">
                    🚀 S'abonner
                </a>
            `;
        } else if (isExpiringSoon) {
            buttonHtml = `
                <a href="${WHATSAPP_URL}?text=Bonjour%20BTP%20Devis%20Pro%2C%20je%20souhaite%20renouveler%20mon%20abonnement" 
                   target="_blank" 
                   style="background:#F59E0B;border:none;color:#1A1A18;padding:8px 20px;border-radius:8px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block;font-size:0.85rem;">
                    🔄 Renouveler
                </a>
            `;
        } else {
            buttonHtml = `
                <a href="${WHATSAPP_URL}?text=Bonjour%20BTP%20Devis%20Pro%2C%20je%20souhaite%20changer%20d%27offre" 
                   target="_blank" 
                   style="background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.25);color:white;padding:8px 18px;border-radius:8px;font-weight:500;cursor:pointer;text-decoration:none;display:inline-block;font-size:0.8rem;">
                    Changer d'offre
                </a>
            `;
        }
        
        banner.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
                <div style="width:40px;height:40px;background:rgba(255,255,255,0.15);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.2rem;flex-shrink:0;">
                    <i class="fas ${config.icon}"></i>
                </div>
                <div>
                    <div style="font-weight:600;font-size:0.95rem;color:white;line-height:1.3;">${message}</div>
                    <div style="font-size:0.75rem;color:rgba(255,255,255,0.7);margin-top:2px;">
                        ${offre === 'essai' ? 'Profitez de toutes les fonctionnalités' : 'Gérez vos devis en toute sérénité'}
                    </div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:10px;flex-shrink:0;">
                ${buttonHtml}
                <span onclick="this.closest('#subscription-banner').remove()" style="cursor:pointer;opacity:0.5;font-size:1.1rem;color:white;padding:4px 8px;">✕</span>
            </div>
        `;
        
        const contentArea = document.getElementById('content-area');
        if (contentArea) {
            contentArea.insertBefore(banner, contentArea.firstChild);
            console.log("✅ Bandeau ajouté");
        }
        
    } catch (error) {
        console.error("❌ Erreur showSubscriptionBanner:", error);
    }
}

showSuspendedBanner() {
    console.log("🟢 showSuspendedBanner appelée");
    
    // 🔥 L'admin ne voit PAS ce bandeau
    if (this.currentUser && (this.currentUser.email === 'admin@btp.com' || this.currentUser.email === 'bylgaitb@gmail.com')) {
        console.log("👑 Admin - pas de bandeau suspension");
        // Supprimer le bandeau s'il existe
        const oldBanner = document.getElementById('subscription-banner');
        if (oldBanner) oldBanner.remove();
        return;
    }
    
    // Supprimer l'ancien bandeau
    const oldBanner = document.getElementById('subscription-banner');
    if (oldBanner) oldBanner.remove();
    
    const WHATSAPP_URL = "https://wa.me/2290143733706";
    const message = "Bonjour%20BTP%20Devis%20Pro%2C%20mon%20abonnement%20a%20%C3%A9t%C3%A9%20suspendu%2C%20je%20souhaite%20le%20r%C3%A9activer";
    
    const banner = document.createElement('div');
    banner.id = 'subscription-banner';
    banner.style.cssText = `
        background: linear-gradient(135deg, #991B1B, #EF4444);
        border-radius: 16px;
        padding: 16px 24px;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        animation: slideDown 0.5s ease;
        border: 1px solid rgba(255,255,255,0.15);
    `;
    
    banner.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
            <div style="width:40px;height:40px;background:rgba(255,255,255,0.15);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.2rem;flex-shrink:0;">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <div>
                <div style="font-weight:600;font-size:0.95rem;color:white;">
                    ⛔ Abonnement suspendu
                </div>
                <div style="font-size:0.75rem;color:rgba(255,255,255,0.7);">
                    Vous ne pouvez pas créer de nouveaux clients, projets ou devis.
                </div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
            <a href="${WHATSAPP_URL}?text=${message}" 
               target="_blank" 
               style="background:rgba(255,255,255,0.2);border:1px solid rgba(255,255,255,0.3);color:white;padding:8px 20px;border-radius:8px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block;font-size:0.85rem;">
                📞 Nous contacter
            </a>
            <span onclick="this.closest('#subscription-banner').remove()" style="cursor:pointer;opacity:0.5;font-size:1.1rem;color:white;padding:4px 8px;">✕</span>
        </div>
    `;
    
    const contentArea = document.getElementById('content-area');
    if (contentArea) {
        contentArea.insertBefore(banner, contentArea.firstChild);
        console.log("✅ Bandeau suspension ajouté");
    }
}

// Sécuriser les données - garantit que c'est toujours un tableau
safeArray(data) {
    if (Array.isArray(data)) return data;
    if (data && typeof data === 'object') return Object.values(data);
    return [];
}

async checkLimites(operation) {
    const user = this.currentUser;
    
    if (user && (user.email === 'admin@btp.com' || user.email === 'bylgaitb@gmail.com')) {
        console.log("👑 Admin détecté - pas de limites");
        return true;
    }
    
    try {
        const response = await apiRequest('/api/abonnement/statut');
        const data = await response.json();
        
        console.log("🔍 checkLimites - data:", data);
        
        if (!data.success) {
            Toast.warning('⚠️ Aucun abonnement trouvé. Contactez l\'administrateur.');
            return false;
        }
        
        if (data.statut === 'expiré') {
            Toast.error('⛔ Votre abonnement a expiré. Contactez l\'administrateur pour le renouveler.');
            return false;
        }
        
        if (data.statut === 'suspendu') {
            Toast.error('⛔ Votre abonnement est suspendu. Vous ne pouvez pas effectuer cette action.');
            return false;
        }
        
        if (data.statut !== 'actif') {
            Toast.warning('⚠️ Abonnement inactif. Contactez l\'administrateur.');
            return false;
        }
        
        // ✅ ABONNEMENT ACTIF - Vérifier les limites
        const offre = data.type || 'starter';
        
        // 🔥 OFFRES AVEC ARTISAN
        const limites = {
            artisan: { clients: 5, projets: 5, devis: 10 },
            starter: { clients: 10, projets: 10, devis: 20 },
            pro: { clients: 999999, projets: 999999, devis: 999999 },
            annuel: { clients: 999999, projets: 999999, devis: 999999 },
            essai: { clients: 999999, projets: 999999, devis: 999999 },
            illimite: { clients: 999999, projets: 999999, devis: 999999 }
        };
        
        const clients = await this.fetchClients();
        const projets = await this.fetchProjets();
        const devis = await this.fetchDevis();
        
        const counts = {
            clients: clients.length,
            projets: projets.length,
            devis: devis.length
        };
        
        if (operation === 'client' && counts.clients >= limites[offre].clients) {
            const maxClients = limites[offre].clients;
            const maxDisplay = maxClients === 999999 ? 'illimité' : maxClients;
            Toast.warning(`❌ Limite de clients atteinte (${maxDisplay}). Passez à l'offre supérieure !`);
            return false;
        }
        if (operation === 'projet' && counts.projets >= limites[offre].projets) {
            const maxProjets = limites[offre].projets;
            const maxDisplay = maxProjets === 999999 ? 'illimité' : maxProjets;
            Toast.warning(`❌ Limite de projets atteinte (${maxDisplay}). Passez à l'offre supérieure !`);
            return false;
        }
        if (operation === 'devis' && counts.devis >= limites[offre].devis) {
            const maxDevis = limites[offre].devis;
            const maxDisplay = maxDevis === 999999 ? 'illimité' : maxDevis;
            Toast.warning(`❌ Limite de devis atteinte (${maxDisplay}). Passez à l'offre supérieure !`);
            return false;
        }
        
        return true;
        
    } catch (error) {
        console.error('❌ Erreur checkLimites:', error);
        return false;
    }
}

async changePassword() {
    const oldPassword = document.getElementById('old-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    
    // Vérifications
    if (newPassword !== confirmPassword) {
        Toast.error('❌ Les nouveaux mots de passe ne correspondent pas');
        return;
    }
    
    if (newPassword.length < 4) {
        Toast.error('❌ Le nouveau mot de passe doit contenir au moins 4 caractères');
        return;
    }
    
    if (oldPassword === newPassword) {
        Toast.warning('⚠️ Le nouveau mot de passe doit être différent de l\'ancien');
        return;
    }
    
    try {
        const response = await apiRequest('/api/change-password', {
            method: 'POST',
            body: JSON.stringify({
                ancien_mot_de_passe: oldPassword,
                nouveau_mot_de_passe: newPassword
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            Toast.success('✅ Mot de passe changé avec succès !');
            // Réinitialiser les champs
            document.getElementById('old-password').value = '';
            document.getElementById('new-password').value = '';
            document.getElementById('confirm-password').value = '';
        } else {
            Toast.error(result.message || '❌ Erreur lors du changement');
        }
    } catch (error) {
        Toast.error('❌ Erreur de connexion');
    }
}

// Changer d'onglet factures
switchFactureTab(tab) {
    const tabs = document.querySelectorAll('.tab-facture');
    const tabMap = {
        'simples': 0,
        'normalisees': 1
    };
    
    tabs.forEach((t, i) => {
        t.style.borderBottom = '3px solid transparent';
        t.style.color = '#94A3B8';
        if (i === tabMap[tab]) {
            t.style.borderBottom = '3px solid ' + (tab === 'simples' ? '#06B6D4' : '#F59E0B');
            t.style.color = (tab === 'simples' ? 'white' : '#F59E0B');
        }
    });
    
    // Recharger le contenu avec le bon onglet
    this.currentFactureTab = tab;
    this.loadPage('factures');
}

// Normaliser une facture
async normaliserFacture(id_facture) {
    if (!confirm('⚠️ Émettre cette facture comme facture normalisée ? Cette action est irréversible.')) return;
    
    try {
        const ifuClient = prompt('📋 Entrez l\'IFU du client (13 caractères) :');
        if (!ifuClient) return;
        
        if (ifuClient.length !== 13) {
            Toast.error('❌ L\'IFU doit contenir exactement 13 caractères');
            return;
        }
        
        const paymentMethod = prompt('💳 Méthode de paiement :', 'ESPECES');
        if (!paymentMethod) return;
        
        const response = await apiRequest(`/api/facture/${id_facture}/normaliser`, {
            method: 'POST',
            body: JSON.stringify({ 
                ifu_client: ifuClient,
                payment_method: paymentMethod
            })
        });
        const result = await response.json();
        
        if (result.success) {
            Toast.success('✅ Facture normalisée émise !');
            Toast.info(`📋 Numéro fiscal: ${result.num_fiscal}`);
            setTimeout(() => this.loadPage('factures'), 1500);
        } else {
            Toast.error(result.message || '❌ Erreur');
        }
    } catch (error) {
        console.error('Erreur normalisation:', error);
        Toast.error('❌ Erreur de connexion');
    }
}

// Créer une facture normalisée directement
async creerFactureNormalisee() {
    // Vérifier si le NIF est configuré
    try {
        const response = await apiRequest('/api/settings');
        const data = await response.json();
        const settings = data.settings || {};
        
        if (!settings.nif) {
            Toast.warning('⚠️ Veuillez configurer votre NIF dans les paramètres avant de créer une facture normalisée.');
            this.loadPage('parametres');
            return;
        }
    } catch(e) {
        Toast.error('❌ Erreur');
        return;
    }
    
    // Ouvrir l'interface e-MCF
    window.open('/facture-normalisee.html', '_blank');
}

// Télécharger PDF facture normalisée
async downloadPDFFacture(id_facture) {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            Toast.error('❌ Vous devez être connecté');
            return;
        }
        
        Toast.info('📄 Téléchargement de la facture...');
        
        // 🔥 Utiliser fetch avec le token dans les headers
        const response = await fetch(`${API_URL}/api/facture/${id_facture}/pdf`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            Toast.error(error.error || '❌ Erreur');
            return;
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `facture_${id_facture}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        Toast.success('✅ Facture PDF téléchargée');
        
    } catch (error) {
        console.error('Erreur downloadFacturePDF:', error);
        Toast.error('❌ Erreur téléchargement');
    }
}

// ==================== ARCHIVAGE ====================

async archiverFacture(id_facture) {
    if (!confirm('📦 Archiver cette facture ? Elle sera déplacée dans les archives.')) return;
    
    try {
        const response = await apiRequest(`/api/facture/${id_facture}/archiver`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            Toast.success('✅ Facture archivée avec succès');
            setTimeout(() => this.loadPage('factures'), 500);
        } else {
            Toast.error(result.message || '❌ Erreur');
        }
    } catch (error) {
        Toast.error('❌ Erreur de connexion');
    }
}

async desarchiverFacture(id_facture) {
    if (!confirm('📤 Restaurer cette facture depuis les archives ?')) return;
    
    try {
        const response = await apiRequest(`/api/facture/${id_facture}/desarchiver`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            Toast.success('✅ Facture restaurée');
            setTimeout(() => this.loadPage('factures'), 500);
        } else {
            Toast.error(result.message || '❌ Erreur');
        }
    } catch (error) {
        Toast.error('❌ Erreur de connexion');
    }
}

afficherArchivees() {
    this.loadPage('factures-archivees');
}

// ==================== PAIEMENT ====================

async payFacture(id_facture) {
    if (!confirm('💰 Marquer cette facture comme payée ? Cette action est irréversible.')) return;
    
    try {
        const response = await apiRequest(`/api/facture/${id_facture}/pay`, {
            method: 'PUT'
        });
        const result = await response.json();
        
        if (result.success) {
            Toast.success(`✅ Facture payée le ${new Date(result.date_paiement).toLocaleDateString()}`);
            setTimeout(() => this.loadPage('factures'), 500);
        } else {
            Toast.error(result.message || '❌ Erreur');
        }
    } catch (error) {
        Toast.error('❌ Erreur de connexion');
    }
}

async previewHeader() {
    try {
        const token = localStorage.getItem('token');
        if (!token) {
            Toast.error('❌ Vous devez être connecté');
            return;
        }
        
        // 🔥 Utiliser fetch pour télécharger le PDF
        Toast.info('📄 Génération de l\'aperçu...');
        
        const response = await fetch(`${API_URL}/api/preview-header`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            Toast.error(error.error || '❌ Erreur');
            return;
        }
        
        // Récupérer le blob du PDF
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'apercu_en-tete.pdf';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        Toast.success('✅ Aperçu PDF téléchargé');
        
    } catch (error) {
        console.error('Erreur preview:', error);
        Toast.error('❌ Erreur génération aperçu');
    }
}

async saveFiscalSettings() {
    const nif = document.getElementById('nif').value.trim();
    const regime_tva = document.getElementById('regime-tva').value;
    const numero_contribuable = document.getElementById('numero-contribuable').value.trim();
    const adresse_fiscale = document.getElementById('adresse-fiscale').value.trim();
    
    // Vérifier que le NIF est renseigné
    if (!nif) {
        Toast.warning('⚠️ Le NIF est obligatoire pour la facturation normalisée');
        document.getElementById('nif').focus();
        return;
    }
    
    // Vérifier la longueur du NIF (minimum 10 caractères)
    if (nif.length < 10) {
        Toast.warning('⚠️ Le NIF doit contenir au moins 10 caractères');
        document.getElementById('nif').focus();
        return;
    }
    
    const data = {
        nif: nif,
        regime_tva: regime_tva,
        numero_contribuable: numero_contribuable,
        adresse_fiscale: adresse_fiscale
    };
    
    try {
        const response = await apiRequest('/api/settings', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
        const result = await response.json();
        
        if (result.success) {
            Toast.success('✅ Informations fiscales enregistrées avec succès');
            // Mettre à jour l'affichage
            this.loadPage('parametres');
        } else {
            Toast.error(result.message || '❌ Erreur lors de l\'enregistrement');
        }
    } catch (error) {
        console.error('Erreur saveFiscalSettings:', error);
        Toast.error('❌ Erreur de connexion');
    }
}
    // ==================== PDF NORMALISÉ ====================
    
    async downloadPDFNormalisee(id_facture) {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                alert('❌ Vous devez être connecté');
                return;
            }
            
            console.log(`📄 Téléchargement PDF normalisé pour facture ${id_facture}`);
            
            const response = await fetch(`${API_URL}/api/facture/${id_facture}/pdf-normalise`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                const error = await response.json();
                alert('❌ Erreur: ' + (error.error || 'Erreur inconnue'));
                return;
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `facture_normalisee_${id_facture}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            console.log('✅ PDF normalisé téléchargé');
            
        } catch (error) {
            console.error('Erreur downloadPDFNormalisee:', error);
            alert('❌ Erreur lors du téléchargement');
        }
    }
    
    viewFactureNormalisee(id_facture) {
        console.log(`👁️ Visualisation facture normalisée ${id_facture}`);
        this.downloadPDFNormalisee(id_facture);
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
// Fin du fichier app.js - Ajoute ceci à la toute fin

// Fonction pour le menu mobile
function toggleMobileMenu() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('open');
    }
}

// Fermer le menu quand on clique sur un lien (mobile)
document.addEventListener('click', function(e) {
    const sidebar = document.querySelector('.sidebar');
    const menuBtn = document.querySelector('.mobile-menu-btn');
    if (window.innerWidth <= 768) {
        if (sidebar && menuBtn && !sidebar.contains(e.target) && !menuBtn.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    }
});