let currentUser = null;
let currentFaculty = null;
let departments = [];

const ROLE_RANK = { super_admin: 5, university_admin: 4, faculty_admin: 3, department_admin: 2, student: 1 };
function canManage(t) { if (!currentUser || !t) return false; if (t.id === currentUser.id) return false; return (ROLE_RANK[currentUser.role] ?? 0) > (ROLE_RANK[t.role] ?? 0); }

document.addEventListener('DOMContentLoaded', async () => {
    await loadCurrentUser();
    if (!currentUser || currentUser.role !== 'faculty_admin') { window.location.href = '/auth/login'; return; }
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
        if (currentUser.faculty_id) await loadFacultyInfo(currentUser.faculty_id);
    } catch (e) { window.location.href = '/auth/login'; }
}

async function loadFacultyInfo(facultyId) {
    try {
        const { faculty: f } = await fetch(`/admin/faculties/${facultyId}`).then(r => r.json());
        currentFaculty = f;
        document.getElementById('facultyInfo').textContent = `${f.name}  —  ${f.university?.name || ''}`;
        document.getElementById('ovFacName').textContent = f.name;
        document.getElementById('ovFacUniversity').textContent = f.university?.name || '';
        document.getElementById('ovFacDean').textContent = f.dean || '';
        document.getElementById('ovFacEmail').textContent = f.email || '';
    } catch (e) { }
}

async function initializeDashboard() {
    await loadDepartments();
    await Promise.all([loadKnowledge(), loadUsers(), loadDeptAdmins(), loadStats()]);
}

function setupEventListeners() {
    document.querySelectorAll('.tab-button').forEach(btn =>
        btn.addEventListener('click', e => switchTab(e.currentTarget.dataset.tab, e.currentTarget)));

    document.getElementById('addDepartmentBtn').addEventListener('click', openAddDepartmentForm);
    document.getElementById('addKnowledgeBtn').addEventListener('click', openAddKnowledgeForm);
    document.getElementById('addDeptAdminBtn').addEventListener('click', openAddDeptAdminForm);
    document.getElementById('kbCategoryFilter').addEventListener('change', loadKnowledge);
    document.getElementById('userDeptFilter').addEventListener('change', loadUsers);
    document.getElementById('userFilter').addEventListener('change', loadUsers);
    document.getElementById('refreshBtn').addEventListener('click', initializeDashboard);
    document.getElementById('logoutBtn').addEventListener('click', logout);

    document.getElementById('departmentForm').addEventListener('submit', submitDepartmentForm);
    document.getElementById('knowledgeForm').addEventListener('submit', submitKnowledgeForm);
    document.getElementById('deptAdminForm').addEventListener('submit', submitDeptAdminForm);

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
        set('totalDepartments', d.departments_count || 0);
        set('activeDepartments', `${d.departments_count || 0} active`);
        set('totalUsers', d.users_count || 0);
        set('verifiedUsers', `${d.verified_users_count || 0} verified`);
        set('totalKnowledge', d.knowledge_count || 0);
        set('activeKnowledge', `${d.knowledge_count || 0} entries`);
        set('ovFacDepartments', d.departments_count || 0);
        set('ovFacUsers', d.users_count || 0);
    } catch (e) { }
}

async function loadDepartments() {
    const tbody = document.getElementById('departmentsTableBody');
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:30px">Loading...</td></tr>';
    try {
        const { departments: depts = [] } = await fetch('/admin/departments').then(r => r.json());
        departments = depts;

        const allDeptsText = window.I18n ? (window.I18n.current === 'ar' ? 'جميع الأقسام' : (window.I18n.current === 'fr' ? 'Tous les Départements' : 'All Departments')) : 'All Departments';
        populateDeptSelect('kbDeptFilter', depts, allDeptsText);
        populateDeptSelect('kbDeptSelect', depts, 'Faculty-wide');
        populateDeptSelect('userDeptFilter', depts, allDeptsText);
        populateDeptSelect('daDeptSelect', depts, 'Select Department');

        if (!depts.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:30px;color:#888">No departments yet</td></tr>'; return; }
        tbody.innerHTML = '';
        depts.forEach(d => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td><strong>${d.name}</strong></td><td>${d.name_ar || ''}</td><td>${d.code}</td><td>${d.head_of_department || ''}</td><td>${d.email || ''}</td><td><span class="status-badge ${d.is_active ? 'active' : 'inactive'}">${d.is_active ? 'Active' : 'Inactive'}</span></td><td class="action-btns"><button class="btn btn-sm btn-secondary" onclick="editDepartment(${d.id})">${window.I18n ? window.I18n.t('adm.edit') : 'Edit'}</button><button class="btn btn-sm btn-danger" onclick="deleteDepartment(${d.id},'${esc(d.name)}')">${window.I18n ? window.I18n.t('adm.delete') : 'Delete'}</button></td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#f56565;padding:30px">Failed to load</td></tr>'; }
}

function populateDeptSelect(id, depts, placeholder) {
    const sel = document.getElementById(id); if (!sel) return;
    const cur = sel.value;
    sel.innerHTML = `<option value="">${placeholder}</option>`;
    depts.forEach(d => { const o = document.createElement('option'); o.value = d.id; o.textContent = d.name; if (String(d.id) === cur) o.selected = true; sel.appendChild(o); });
}

function openAddDepartmentForm() {
    document.getElementById('departmentFormTitle').textContent = 'Add Department';
    document.getElementById('departmentId').value = '';
    document.getElementById('departmentForm').reset();
    document.getElementById('deptActive').checked = true;
    const facSelect = document.getElementById('deptFaculty');
    if (facSelect && currentFaculty) {
        facSelect.innerHTML = `<option value="${currentFaculty.id}" selected>${currentFaculty.name}</option>`;
        facSelect.disabled = true;
    }
    openModal('departmentFormModal');
}

async function editDepartment(id) {
    try {
        const { department: d } = await fetch(`/admin/departments/${id}`).then(r => r.json());
        document.getElementById('departmentFormTitle').textContent = 'Edit Department';
        document.getElementById('departmentId').value = d.id;
        document.getElementById('deptName').value = d.name || '';
        document.getElementById('deptCode').value = d.code || '';
        document.getElementById('deptNameAr').value = d.name_ar || '';
        document.getElementById('deptHead').value = d.head_of_department || '';
        document.getElementById('deptEmail').value = d.email || '';
        document.getElementById('deptPhone').value = d.phone || '';
        document.getElementById('deptBuilding').value = d.building || '';
        document.getElementById('deptWebsite').value = d.official_website || '';
        document.getElementById('deptDescription').value = d.description || '';
        document.getElementById('deptActive').checked = d.is_active;
        const facSelect = document.getElementById('deptFaculty');
        if (facSelect && currentFaculty) {
            facSelect.innerHTML = `<option value="${currentFaculty.id}" selected>${currentFaculty.name}</option>`;
            facSelect.disabled = true;
        }
        openModal('departmentFormModal');
    } catch (e) { UIDialogs.toast('Failed to load department', 'error'); }
}

async function submitDepartmentForm(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setBtnLoading(btn, true);
    const id = document.getElementById('departmentId').value;
    const payload = {
        name: document.getElementById('deptName').value.trim(),
        code: document.getElementById('deptCode').value.trim(),
        name_ar: document.getElementById('deptNameAr').value.trim(),
        head_of_department: document.getElementById('deptHead').value.trim(),
        email: document.getElementById('deptEmail').value.trim(),
        phone: document.getElementById('deptPhone').value.trim(),
        building: document.getElementById('deptBuilding').value.trim(),
        official_website: document.getElementById('deptWebsite').value.trim(),
        description: document.getElementById('deptDescription').value.trim(),
        is_active: document.getElementById('deptActive').checked,
        faculty_id: currentUser.faculty_id,
        university_id: currentUser.university_id,
    };
    try {
        const res = await fetch(id ? `/admin/departments/${id}` : '/admin/departments', {
            method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        if (!res.ok) { const err = await res.json(); throw new Error(err.error || 'Failed'); }
        UIDialogs.toast(`Department ${id ? 'updated' : 'created'}`, 'success');
        closeModal('departmentFormModal');
        await loadDepartments();
        await Promise.all([loadDeptAdmins(), loadStats()]);
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
    finally { setBtnLoading(btn, false); }
}

async function deleteDepartment(id, name) {
    if (!(await UIDialogs.confirm(`Delete department "${name}"?\nAll its knowledge entries will also be removed.`, { danger: true }))) return;
    try {
        const res = await fetch(`/admin/departments/${id}`, { method: 'DELETE' });
        if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Failed'); }
        UIDialogs.toast('Department deleted', 'success');
        await loadDepartments();
        await Promise.all([loadDeptAdmins(), loadStats()]);
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
}

async function loadKnowledge() {
    const tbody = document.getElementById('knowledgeTableBody');
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:30px">Loading...</td></tr>';
    try {
        const deptId = '';
        const category = document.getElementById('kbCategoryFilter').value;
        let url = '/admin/knowledge?';
        if (category) url += `category=${encodeURIComponent(category)}`;
        const { knowledge = [] } = await fetch(url).then(r => r.json());
        if (!knowledge.length) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px;color:#888">No knowledge entries yet</td></tr>'; loadKnowledgeCategories(); return; }
        tbody.innerHTML = '';
        knowledge.forEach(k => {
            const tr = document.createElement('tr');
            const updated = new Date(k.updated_at).toLocaleDateString();
            const tags = Array.isArray(k.tags) ? k.tags.join(', ') : (k.tags || '');
            tr.innerHTML = `<td><strong>${k.title}</strong></td><td><span class="badge" style="background:#667eea">${k.category || ''}</span></td><td><span class="badge" style="background:${k.priority >= 7 ? '#e53e3e' : k.priority >= 4 ? '#dd6b20' : '#48bb78'}">${k.priority}/10</span></td><td style="font-size:12px;color:#888">${tags}</td><td style="font-size:12px">${updated}</td><td class="action-btns"><button class="btn btn-sm btn-secondary" onclick="editKnowledge(${k.id})">${window.I18n ? window.I18n.t('adm.edit') : 'Edit'}</button><button class="btn btn-sm btn-danger" onclick="deleteKnowledge(${k.id},'${esc(k.title)}')">${window.I18n ? window.I18n.t('adm.delete') : 'Delete'}</button></td>`;
            tbody.appendChild(tr);
        });
        loadKnowledgeCategories();
    } catch (e) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#f56565;padding:30px">Failed to load</td></tr>'; }
}

async function loadKnowledgeCategories() {
    try {
        const { categories = [] } = await fetch(`/admin/knowledge/categories?university_id=${currentUser.university_id}`).then(r => r.json());
        const sel = document.getElementById('kbCategoryFilter'), cur = sel.value;
        const allCatsText = window.I18n ? (window.I18n.current === 'ar' ? 'جميع الفئات' : (window.I18n.current === 'fr' ? 'Toutes les Catégories' : 'All Categories')) : 'All Categories';
        sel.innerHTML = `<option value="">${allCatsText}</option>`;
        categories.forEach(cat => { const o = document.createElement('option'); o.value = cat; o.textContent = cat; if (cat === cur) o.selected = true; sel.appendChild(o); });
    } catch (e) { }
}

function openAddKnowledgeForm() {
    document.getElementById('knowledgeFormTitle').textContent = 'Add Knowledge Entry';
    document.getElementById('knowledgeId').value = '';
    document.getElementById('knowledgeForm').reset();
    document.getElementById('kbPriority').value = 5;
    const deptGroup = document.getElementById('kbDepartmentGroup');
    if (deptGroup) deptGroup.style.display = 'none';
    openModal('knowledgeFormModal');
}

async function editKnowledge(id) {
    try {
        const { knowledge = [] } = await fetch('/admin/knowledge').then(r => r.json());
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
        const deptGroup = document.getElementById('kbDepartmentGroup');
        if (deptGroup) deptGroup.style.display = 'none';
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
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:30px">Loading...</td></tr>';
    try {
        const filter = document.getElementById('userFilter').value;
        const deptId = document.getElementById('userDeptFilter').value;
        const params = new URLSearchParams();
        if (deptId) params.set('department_id', deptId);
        if (filter === 'verified') params.set('verified', 'true');
        if (filter === 'unverified') params.set('verified', 'false');
        const { users = [] } = await fetch(`/admin/users?${params}`).then(r => r.json());
        if (!users.length) { tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:30px;color:#888">No users found</td></tr>'; return; }
        tbody.innerHTML = '';
        users.forEach(u => {
            const tr = document.createElement('tr');
            const joined = new Date(u.created_at).toLocaleDateString();
            const dept = (u.department && u.department.name) || '';
            tr.innerHTML = `<td>${u.username}</td><td>${u.email}</td><td>${u.full_name || ''}</td><td>${dept}</td><td><span class="badge" style="background:#667eea;font-size:11px">${u.role}</span></td><td><span class="status-badge ${u.is_verified ? 'active' : 'inactive'}">${u.is_verified ? 'Verified' : 'Unverified'}</span></td><td>${joined}</td><td class="action-btns"><button class="btn btn-sm btn-secondary" onclick="viewUser(${u.id})">${window.I18n ? window.I18n.t('adm.view') : 'View'}</button><button class="btn btn-sm btn-danger" onclick="deleteUser(${u.id},'${esc(u.username)}')">${window.I18n ? window.I18n.t('adm.delete') : 'Delete'}</button></td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#f56565;padding:30px">Failed to load</td></tr>'; }
}

async function viewUser(userId) {
    try {
        const { user: u } = await fetch(`/admin/users/${userId}`).then(r => r.json());
        const r = (l, v) => `<tr style="border-bottom:1px solid var(--border)"><td style="padding:10px;color:var(--text-secondary);font-size:13px;width:40%">${l}</td><td style="padding:10px;font-size:14px">${v}</td></tr>`;
        document.getElementById('userViewBody').innerHTML = `<table style="width:100%;border-collapse:collapse">${r('Username', u.username)}${r('Full Name', u.full_name || '')}${r('Email', u.email)}${r('Role', `<span class="status-badge ${u.is_admin ? 'active' : 'inactive'}">${u.role}</span>`)}${r('Verified', u.is_verified ? 'Yes' : 'No')}${r('Department', (u.department && u.department.name) || '')}${r('Student ID', u.student_id || '')}${r('Joined', u.created_at ? new Date(u.created_at).toLocaleDateString() : '-')}${r('Last Login', u.last_login ? new Date(u.last_login).toLocaleString() : 'Never')}</table>`;
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

async function loadDeptAdmins() {
    const tbody = document.getElementById('adminsTableBody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px">Loading...</td></tr>';
    try {
        const { admins = [] } = await fetch('/admin/admins').then(r => r.json());
        const deptAdmins = admins.filter(a => a.role === 'department_admin');
        const countEl = document.getElementById('totalDeptAdmins');
        if (countEl) countEl.textContent = deptAdmins.length;
        if (!deptAdmins.length) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px;color:#888">No department admins yet</td></tr>'; return; }
        tbody.innerHTML = '';
        deptAdmins.forEach(a => {
            const tr = document.createElement('tr');
            const dept = departments.find(d => d.id === a.department_id)?.name || '';
            tr.innerHTML = `<td>${a.username}${a.id === currentUser.id ? ' <span style="color:#f6e05e;font-size:11px">(you)</span>' : ''}</td><td>${a.full_name || ''}</td><td>${a.email}</td><td>${dept}</td><td><span class="badge" style="background:#667eea;font-size:11px">Dept Admin</span></td><td>${new Date(a.created_at).toLocaleDateString()}</td><td class="action-btns">${canManage(a) ? `<button class="btn btn-sm btn-danger" onclick="deleteDeptAdmin(${a.id},'${esc(a.username)}')">${window.I18n ? window.I18n.t('adm.remove') : 'Remove'}</button>` : '<span style="color:#888;font-size:12px">—</span>'}</td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#f56565;padding:30px">Failed to load</td></tr>'; }
}

function openAddDeptAdminForm() {
    // A department is required before creating an admin
    if (!departments.length) {
        UIDialogs.toast('Please create a department first before adding a department admin.', 'error');
        return;
    }
    document.getElementById('deptAdminForm').reset();
    populateDeptSelect('daDeptSelect', departments, 'Select Department');
    openModal('deptAdminFormModal');
}

async function submitDeptAdminForm(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setBtnLoading(btn, true);
    const deptId = document.getElementById('daDeptSelect').value;
    if (!deptId) { UIDialogs.toast('Please select a department', 'error'); setBtnLoading(btn, false); return; }
    const payload = {
        username: document.getElementById('daUsername').value.trim(),
        email: document.getElementById('daEmail').value.trim(),
        password: document.getElementById('daPassword').value,
        full_name: document.getElementById('daFullName').value.trim(),
        department_id: parseInt(deptId),
        faculty_id: currentUser.faculty_id,
        university_id: currentUser.university_id,
    };
    try {
        const res = await fetch('/admin/users/create-admin', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        if (!res.ok) { const err = await res.json(); throw new Error(err.error || 'Failed'); }
        UIDialogs.toast('Department admin created', 'success');
        closeModal('deptAdminFormModal');
        await Promise.all([loadDeptAdmins(), loadStats()]);
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
    finally { setBtnLoading(btn, false); }
}

async function deleteDeptAdmin(id, username) {
    if (!(await UIDialogs.confirm(`Remove admin "${username}"?`, { danger: true }))) return;
    try {
        const res = await fetch(`/admin/admins/${id}`, { method: 'DELETE' });
        if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Failed'); }
        UIDialogs.toast('Admin removed', 'success');
        await Promise.all([loadDeptAdmins(), loadStats()]);
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
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
.status-badge{display:inline-flex;align-items:center;gap:6px;background:none!important;padding:0;font-size:13px;font-weight:500}
.status-badge::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%}
.status-badge.active{color:#48bb78}.status-badge.active::before{background:#48bb78}
.status-badge.inactive{color:#e53e3e}.status-badge.inactive::before{background:#e53e3e}
.btn-sm{padding:5px 10px;font-size:12px}
.btn-danger{background:#e53e3e;color:#fff;border:none;border-radius:6px;cursor:pointer;padding:5px 10px;font-size:12px;font-weight:600;transition:opacity .2s}
.btn-danger:hover{opacity:.85}
.action-btns{display:flex;gap:6px;flex-wrap:wrap}
.form-group{margin-bottom:16px}
.form-group label{display:block;margin-bottom:6px;font-size:13px;color:var(--text-secondary)}
.form-group input,.form-group textarea,.form-group select{width:100%;padding:10px 14px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:8px;color:var(--text-primary);font-size:14px;box-sizing:border-box}
.form-group textarea{resize:vertical}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.form-actions{display:flex;gap:12px;margin-top:20px}
@media(max-width:600px){.form-row{grid-template-columns:1fr}}
`;
document.head.appendChild(_s);
