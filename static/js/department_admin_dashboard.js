let currentUser = null;
let currentDept = null;

document.addEventListener('DOMContentLoaded', async () => {
    await loadCurrentUser();
    if (!currentUser || currentUser.role !== 'department_admin') { window.location.href = '/auth/login'; return; }
    await initializeDashboard();
    setupEventListeners();
});

async function loadCurrentUser() {
    try {
        const res = await fetch('/auth/me');
        if (!res.ok) { window.location.href = '/auth/login'; return; }
        const { user } = await res.json();
        currentUser = user;
        if (!currentUser) { window.location.href = '/auth/login'; return; }
        document.getElementById('adminNameDisplay').textContent = currentUser.full_name || currentUser.username;
        if (currentUser.department_id) await loadDeptInfo(currentUser.department_id);
    } catch (e) { window.location.href = '/auth/login'; }
}

async function loadDeptInfo(deptId) {
    try {
        const { department: d } = await fetch(`/admin/departments/${deptId}`).then(r => r.json());
        currentDept = d;
        document.getElementById('deptInfo').textContent = `${d.name}  —  ${d.faculty?.name || ''}  —  ${d.university?.name || ''}`;
        const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
        set('ovDeptName', d.name);
        set('ovDeptFaculty', d.faculty?.name || '');
        set('ovDeptUniversity', d.university?.name || '');
        set('ovDeptHead', d.head_of_department || '');
        set('ovDeptEmail', d.email || '');
        set('ovDeptBuilding', d.building || '');
        const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
        setVal('editDeptName', d.name || '');
        setVal('editDeptNameAr', d.name_ar || '');
        setVal('editDeptHead', d.head_of_department || '');
        setVal('editDeptEmail', d.email || '');
        setVal('editDeptPhone', d.phone || '');
        setVal('editDeptBuilding', d.building || '');
        setVal('editDeptWebsite', d.official_website || '');
        setVal('editDeptDescription', d.description || '');
    } catch (e) { console.error(e); }
}

async function initializeDashboard() {
    await Promise.all([loadStats(), loadKnowledge(), loadUsers()]);
}

function setupEventListeners() {
    document.querySelectorAll('.tab-button').forEach(btn =>
        btn.addEventListener('click', e => switchTab(e.currentTarget.dataset.tab, e.currentTarget)));

    document.getElementById('addKnowledgeBtn').addEventListener('click', openAddKnowledgeForm);
    document.getElementById('kbCategoryFilter').addEventListener('change', loadKnowledge);
    document.getElementById('userFilter').addEventListener('change', loadUsers);
    document.getElementById('refreshBtn').addEventListener('click', initializeDashboard);
    document.getElementById('logoutBtn').addEventListener('click', logout);

    document.getElementById('knowledgeForm').addEventListener('submit', submitKnowledgeForm);
    document.getElementById('deptInfoForm').addEventListener('submit', submitDeptInfoForm);

    document.querySelectorAll('.modal').forEach(m =>
        m.addEventListener('click', e => { if (e.target === m) m.style.display = 'none'; }));
}

function switchTab(tabName, btn) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(el => el.classList.remove('active'));
    document.getElementById(tabName + '-tab').classList.add('active');
    btn.classList.add('active');
}

async function loadStats() {
    try {
        const d = await fetch('/admin/dashboard/stats').then(r => r.json());
        const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
        set('totalKnowledge', d.knowledge_count || 0);
        set('knowledgeDetail', `${d.knowledge_count || 0} entries`);
        set('totalUsers', d.users_count || 0);
        set('verifiedUsers', `${d.verified_users_count || 0} verified`);
        set('verifiedCount', d.verified_users_count || 0);
        set('unverifiedCount', `${(d.users_count || 0) - (d.verified_users_count || 0)} unverified`);

        const verified = d.verified_users_count || 0;
        const unverified = Math.max((d.users_count || 0) - verified, 0);
        AdminCharts.doughnut('userDistributionChart',
            ['Verified', 'Unverified'],
            [verified, unverified],
            ['#10b981', '#f59e0b']
        );
        AdminCharts.horizontalBar('structureChart',
            ['Knowledge', 'Users'],
            [d.knowledge_count || 0, d.users_count || 0],
            ['#6366f1', '#10b981']
        );
    } catch (e) { }
}

async function loadKnowledge() {
    const tbody = document.getElementById('knowledgeTableBody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px">Loading...</td></tr>';
    try {
        const category = document.getElementById('kbCategoryFilter').value;
        let url = `/admin/knowledge?department_id=${currentUser.department_id}`;
        if (category) url += `&category=${encodeURIComponent(category)}`;
        const { knowledge = [] } = await fetch(url).then(r => r.json());
        if (!knowledge.length) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px;color:#888">No knowledge entries yet. Add your first entry!</td></tr>'; loadKnowledgeCategories(); return; }
        tbody.innerHTML = '';
        knowledge.forEach(k => {
            const tr = document.createElement('tr');
            const updated = new Date(k.updated_at).toLocaleDateString();
            const tags = Array.isArray(k.tags) ? k.tags.join(', ') : (k.tags || '');
            tr.innerHTML = `<td><strong>${k.title}</strong></td><td><span class="badge" style="background:#667eea">${k.category || ''}</span></td><td><span class="badge" style="background:${k.priority >= 7 ? '#e53e3e' : k.priority >= 4 ? '#dd6b20' : '#48bb78'}">${k.priority}/10</span></td><td style="font-size:12px;color:#888">${tags}</td><td style="font-size:12px">${updated}</td><td class="action-btns"><button class="btn btn-sm btn-secondary" onclick="editKnowledge(${k.id})">${window.I18n ? window.I18n.t('adm.edit') : 'Edit'}</button><button class="btn btn-sm btn-danger" onclick="deleteKnowledge(${k.id},'${esc(k.title)}')">${window.I18n ? window.I18n.t('adm.delete') : 'Delete'}</button></td>`;
            tbody.appendChild(tr);
        });
        loadKnowledgeCategories();
    } catch (e) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#f56565;padding:30px">Failed to load knowledge entries</td></tr>'; }
}

async function loadKnowledgeCategories() {
    try {
        const { categories = [] } = await fetch(`/admin/knowledge/categories?university_id=${currentUser.university_id}`).then(r => r.json());
        const sel = document.getElementById('kbCategoryFilter'), cur = sel.value;
        const allCatsText = window.I18n ? (window.I18n.current === 'ar' ? 'جميع الفئات' : (window.I18n.current === 'fr' ? 'Toutes les Catégories' : 'All Categories')) : 'All Categories';
        sel.innerHTML = `<option value="">${allCatsText}</option>`;
        categories.forEach(cat => { const o = document.createElement('option'); o.value = cat; o.textContent = cat; if (cat === cur) o.selected = true; sel.appendChild(o); });
        const countEl = document.getElementById('totalCategories');
        if (countEl) countEl.textContent = categories.length;
    } catch (e) { }
}

function openAddKnowledgeForm() {
    document.getElementById('knowledgeFormTitle').textContent = 'Add Knowledge Entry';
    document.getElementById('knowledgeId').value = '';
    document.getElementById('knowledgeForm').reset();
    document.getElementById('kbPriority').value = 5;
    if (document.getElementById('kbDepartmentGroup')) {
        document.getElementById('kbDepartmentGroup').style.display = 'none';
    }
    openModal('knowledgeFormModal');
}

async function editKnowledge(id) {
    try {
        const { knowledge = [] } = await fetch(`/admin/knowledge?department_id=${currentUser.department_id}`).then(r => r.json());
        const k = knowledge.find(x => x.id === id);
        if (!k) throw new Error('Entry not found');
        document.getElementById('knowledgeFormTitle').textContent = 'Edit Knowledge Entry';
        document.getElementById('knowledgeId').value = k.id;
        document.getElementById('kbTitle').value = k.title || '';
        document.getElementById('kbContent').value = k.content || '';
        document.getElementById('kbContentAr').value = k.content_ar || '';
        document.getElementById('kbCategory').value = k.category || '';
        document.getElementById('kbPriority').value = k.priority || 5;
        document.getElementById('kbTags').value = Array.isArray(k.tags) ? k.tags.join(', ') : (k.tags || '');
        document.getElementById('kbSourceUrl').value = k.source_url || '';
        if (document.getElementById('kbDepartmentGroup')) {
            document.getElementById('kbDepartmentGroup').style.display = 'none';
        }
        openModal('knowledgeFormModal');
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
}

async function submitKnowledgeForm(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setBtnLoading(btn, true);
    const id = document.getElementById('knowledgeId').value;
    const payload = {
        title: document.getElementById('kbTitle').value.trim(),
        content: document.getElementById('kbContent').value.trim(),
        content_ar: document.getElementById('kbContentAr').value.trim(),
        category: document.getElementById('kbCategory').value.trim(),
        priority: parseInt(document.getElementById('kbPriority').value) || 5,
        tags: document.getElementById('kbTags').value.trim(),
        source_url: document.getElementById('kbSourceUrl').value.trim(),
        university_id: currentUser.university_id,
        faculty_id: currentUser.faculty_id,
        department_id: currentUser.department_id,
    };
    try {
        const res = await fetch(id ? `/admin/knowledge/${id}` : '/admin/knowledge', {
            method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        if (!res.ok) { const err = await res.json(); throw new Error(err.error || 'Failed'); }
        UIDialogs.toast(`Entry ${id ? 'updated' : 'created'}`, 'success');
        closeModal('knowledgeFormModal');
        await Promise.all([loadKnowledge(), loadStats()]);
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
    finally { setBtnLoading(btn, false); }
}

async function deleteKnowledge(id, title) {
    if (!(await UIDialogs.confirm(`Delete knowledge entry "${title}"?`, { danger: true }))) return;
    try {
        const res = await fetch(`/admin/knowledge/${id}`, { method: 'DELETE' });
        if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Failed'); }
        UIDialogs.toast('Entry deleted', 'success');
        await Promise.all([loadKnowledge(), loadStats()]);
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
}


async function loadUsers() {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:30px">Loading...</td></tr>';
    try {
        const filter = document.getElementById('userFilter').value;
        const params = new URLSearchParams({ department_id: currentUser.department_id });
        if (filter === 'verified') params.set('verified', 'true');
        if (filter === 'unverified') params.set('verified', 'false');
        const { users = [] } = await fetch(`/admin/users?${params}`).then(r => r.json());
        if (!users.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:30px;color:#888">No users in this department</td></tr>'; return; }
        tbody.innerHTML = '';
        users.forEach(u => {
            const tr = document.createElement('tr');
            const joined = new Date(u.created_at).toLocaleDateString();
            tr.innerHTML = `<td>${u.username}</td><td>${u.email}</td><td>${u.full_name || ''}</td><td>${u.student_id || ''}</td><td><span class="status-badge ${u.is_verified ? 'active' : 'inactive'}">${u.is_verified ? 'Verified' : 'Unverified'}</span></td><td>${joined}</td><td class="action-btns"><button class="btn btn-sm btn-secondary" onclick="viewUser(${u.id})">${window.I18n ? window.I18n.t('adm.view') : 'View'}</button><button class="btn btn-sm btn-danger" onclick="deleteUser(${u.id},'${esc(u.username)}')">${window.I18n ? window.I18n.t('adm.delete') : 'Delete'}</button></td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#f56565;padding:30px">Failed to load users</td></tr>'; }
}

async function viewUser(userId) {
    try {
        const { user: u } = await fetch(`/admin/users/${userId}`).then(r => r.json());
        const r = (l, v) => `<tr style="border-bottom:1px solid var(--border)"><td style="padding:10px;color:var(--text-secondary);font-size:13px;width:40%">${l}</td><td style="padding:10px;font-size:14px">${v}</td></tr>`;
        document.getElementById('userViewBody').innerHTML = `<table style="width:100%;border-collapse:collapse">${r('Username', u.username)}${r('Full Name', u.full_name || '')}${r('Email', u.email)}${r('Verified', u.is_verified ? 'Yes' : 'No')}${r('Student ID', u.student_id || '')}${r('Joined', u.created_at ? new Date(u.created_at).toLocaleDateString() : '-')}${r('Last Login', u.last_login ? new Date(u.last_login).toLocaleString() : 'Never')}</table>`;
        openModal('userViewModal');
    } catch (e) { UIDialogs.toast('Failed to load user', 'error'); }
}

async function deleteUser(userId, username) {
    if (!(await UIDialogs.confirm(`Delete user "${username}"? This cannot be undone.`, { danger: true }))) return;
    try {
        const res = await fetch(`/admin/users/${userId}`, { method: 'DELETE' });
        if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Failed'); }
        UIDialogs.toast('User deleted', 'success');
        await Promise.all([loadUsers(), loadStats()]);
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
}

async function submitDeptInfoForm(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setBtnLoading(btn, true);
    const payload = {
        name: document.getElementById('editDeptName').value.trim(),
        name_ar: document.getElementById('editDeptNameAr').value.trim(),
        head_of_department: document.getElementById('editDeptHead').value.trim(),
        email: document.getElementById('editDeptEmail').value.trim(),
        phone: document.getElementById('editDeptPhone').value.trim(),
        building: document.getElementById('editDeptBuilding').value.trim(),
        official_website: document.getElementById('editDeptWebsite').value.trim(),
        description: document.getElementById('editDeptDescription').value.trim(),
    };
    try {
        const res = await fetch(`/admin/departments/${currentUser.department_id}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        if (!res.ok) { const err = await res.json(); throw new Error(err.error || 'Failed'); }
        UIDialogs.toast('Department info updated', 'success');
        await loadDeptInfo(currentUser.department_id);
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
    finally { setBtnLoading(btn, false); }
}

async function logout() { await fetch('/auth/logout', { method: 'POST' }); window.location.href = '/auth/login'; }
function esc(str) { return String(str).replace(/'/g, "\\'"); }
function setBtnLoading(btn, loading) { if (!btn) return; btn.disabled = loading; if (loading) { btn._orig = btn.textContent; btn.textContent = 'Saving...'; } else { btn.textContent = btn._orig || 'Save'; } }
function openModal(id) { const m = document.getElementById(id); if (m) { m.style.display = 'flex'; m.style.alignItems = 'center'; m.style.justifyContent = 'center'; } }
function closeModal(id) { const m = document.getElementById(id); if (m) m.style.display = 'none'; }

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') document.querySelectorAll('.modal').forEach(m => { if (m.style.display !== 'none') closeModal(m.id); });
});

const _s = document.createElement('style');
_s.textContent = `
.badge{display:inline-block;background:var(--accent-primary,#2dd4bf);color:#fff;padding:3px 8px;border-radius:4px;font-size:12px;font-weight:bold}
.status-badge{display:inline-block;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:500}
.status-badge.active{background:#c6f6d5;color:#22543d}
.status-badge.inactive{background:#fed7d7;color:#742a2a}
.btn-sm{padding:5px 10px;font-size:12px}
.btn-danger{background:#e53e3e;color:#fff;border:none;border-radius:6px;cursor:pointer;padding:5px 10px;font-size:12px;font-weight:600;transition:opacity .2s}
.btn-danger:hover{opacity:.85}
.action-btns{display:flex;gap:6px;flex-wrap:wrap}
`;
document.head.appendChild(_s);
