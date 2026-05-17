let currentUser = null;

const ROLE_RANK = { super_admin: 5, university_admin: 4, faculty_admin: 3, department_admin: 2, student: 1 };

function canManage(t) {
    if (!currentUser || !t) return false;
    if (t.id === currentUser.id) return false;
    return (ROLE_RANK[currentUser.role] ?? 0) > (ROLE_RANK[t.role] ?? 0);
}

document.addEventListener('DOMContentLoaded', async () => {
    await loadCurrentUser();
    if (!currentUser || !currentUser.is_super_admin) { window.location.href = '/auth/login'; return; }
    await initializeDashboard();
    setupEventListeners();
});

async function loadCurrentUser() {
    try {
        const res = await fetch('/auth/me');
        if (!res.ok) { window.location.href = '/auth/login'; return; }
        const data = await res.json();
        currentUser = data.user;
        if (!currentUser) { window.location.href = '/auth/login'; return; }
        document.getElementById('adminNameDisplay').textContent = currentUser.full_name || currentUser.username;
    } catch (e) { window.location.href = '/auth/login'; }
}

async function initializeDashboard() {
    await Promise.all([loadStats(), loadUniversities(), loadFaculties(), loadDepartments(), loadUsers(), loadAdmins(), populateUniversityFilters()]);
}

function setupEventListeners() {
    document.querySelectorAll('.tab-button').forEach(btn =>
        btn.addEventListener('click', e => switchTab(e.currentTarget.dataset.tab, e.currentTarget)));

    const addUniBtn = document.getElementById('addUniversityBtn');
    const addAdminBtn = document.getElementById('addAdminBtn');
    if (addUniBtn) addUniBtn.addEventListener('click', openAddUniversityForm);
    if (addAdminBtn) addAdminBtn.addEventListener('click', openAddAdminForm);

    document.getElementById('facultyUnivFilter').addEventListener('change', loadFaculties);
    document.getElementById('deptUnivFilter').addEventListener('change', loadDepartments);
    document.getElementById('userUnivFilter').addEventListener('change', loadUsers);
    document.getElementById('userFilter').addEventListener('change', loadUsers);
    document.getElementById('refreshBtn').addEventListener('click', initializeDashboard);
    document.getElementById('logoutBtn').addEventListener('click', logout);
    document.getElementById('universityForm').addEventListener('submit', submitUniversityForm);
    document.getElementById('adminForm').addEventListener('submit', submitAdminForm);
    document.getElementById('adminRoleSelect').addEventListener('change', function () {
        document.getElementById('adminUniversityGroup').style.display = this.value === 'university_admin' ? 'block' : 'none';
    });
    document.querySelectorAll('.modal').forEach(m => m.addEventListener('click', e => { if (e.target === m) m.style.display = 'none'; }));
}

function switchTab(tabName, btn) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(el => el.classList.remove('active'));
    document.getElementById(tabName + '-tab').classList.add('active');
    btn.classList.add('active');
}

let userDistChart = null;
let structChart = null;

async function loadStats() {
    try {
        const res = await fetch('/admin/system-stats');
        if (!res.ok) return;
        const d = await res.json();
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        set('totalUniversities', d.universities_count || 0);
        set('activeUniversities', `${d.active_universities_count || 0} active`);
        set('totalFaculties', d.faculties_count || 0);
        set('activeFaculties', `${d.active_faculties_count || 0} active`);
        set('totalDepartments', d.departments_count || 0);
        set('activeDepartments', `${d.active_departments_count || 0} active`);
        set('totalUsers', d.users_count || 0);
        set('verifiedUsers', `${d.verified_users_count || 0} verified`);
        set('sysUniversities', d.universities_count || 0);
        set('sysFaculties', d.faculties_count || 0);
        set('sysDepartments', d.departments_count || 0);
        set('sysUsers', d.users_count || 0);
        set('sysAdmins', d.admins_count || 0);
        set('sysActiveUnis', d.active_universities_count || 0);

        renderCharts(d);
    } catch (e) { console.error(e); }
}

function renderCharts(d) {
    if (typeof Chart === 'undefined') return;

    const isDark = document.documentElement.classList.contains('dark');
    const textColor = isDark ? '#cbd5e1' : '#475569';
    const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';

    // -- Doughnut: User Distribution --
    const students = (d.users_count || 0) - (d.admins_count || 0);
    const verified = d.verified_users_count || 0;
    const unverified = (d.users_count || 0) - verified;

    const ctx1 = document.getElementById('userDistributionChart');
    if (ctx1) {
        if (userDistChart) userDistChart.destroy();
        userDistChart = new Chart(ctx1, {
            type: 'doughnut',
            data: {
                labels: ['Students', 'Admins', 'Unverified'],
                datasets: [{
                    data: [Math.max(students - unverified, 0), d.admins_count || 0, unverified],
                    backgroundColor: ['#3b82f6', '#8b5cf6', '#f59e0b'],
                    borderColor: isDark ? '#1e293b' : '#ffffff',
                    borderWidth: 3,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '62%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: textColor, padding: 16, font: { size: 13, family: 'Inter' }, usePointStyle: true, pointStyleWidth: 10 }
                    }
                }
            }
        });
    }

    // -- Bar: Structure Overview --
    const ctx2 = document.getElementById('structureChart');
    if (ctx2) {
        if (structChart) structChart.destroy();

        const activeUnis = d.active_universities_count || 0;
        const inactiveUnis = (d.universities_count || 0) - activeUnis;
        const activeFacs = d.active_faculties_count || 0;
        const inactiveFacs = (d.faculties_count || 0) - activeFacs;
        const activeDepts = d.active_departments_count || 0;
        const inactiveDepts = (d.departments_count || 0) - activeDepts;

        structChart = new Chart(ctx2, {
            type: 'bar',
            data: {
                labels: ['Universities', 'Faculties', 'Departments'],
                datasets: [
                    {
                        label: 'Active',
                        data: [activeUnis, activeFacs, activeDepts],
                        backgroundColor: '#10b981',
                        borderRadius: 6,
                        barPercentage: 0.6
                    },
                    {
                        label: 'Inactive',
                        data: [inactiveUnis, inactiveFacs, inactiveDepts],
                        backgroundColor: '#ef4444',
                        borderRadius: 6,
                        barPercentage: 0.6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: textColor, padding: 16, font: { size: 13, family: 'Inter' }, usePointStyle: true, pointStyleWidth: 10 }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: textColor, font: { size: 12, family: 'Inter' } },
                        grid: { display: false }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { color: textColor, font: { size: 12, family: 'Inter' }, stepSize: 1 },
                        grid: { color: gridColor }
                    }
                }
            }
        });
    }
}

async function loadUniversities() {
    const tbody = document.getElementById('universitiesTableBody');
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:30px">Loading...</td></tr>';
    try {
        const { universities = [] } = await fetch('/admin/universities').then(r => r.json());
        if (!universities.length) { tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:30px;color:#888">No universities found</td></tr>'; return; }
        tbody.innerHTML = '';
        universities.forEach(u => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${u.name}</strong>${u.name_ar ? '<br><small style="color:#888">' + u.name_ar + '</small>' : ''}</td>
                <td>${u.code}</td><td>${u.city || ''}</td>
                <td><span>${u.faculties_count || 0}</span></td>
                <td><span>${u.departments_count || 0}</span></td>
                <td><span>${u.users_count || 0}</span></td>
                <td><span class="status-badge ${u.is_active ? 'active' : 'inactive'}">${u.is_active ? 'Active' : 'Inactive'}</span></td>
                <td class="action-btns">
                    <button class="btn btn-sm btn-secondary" onclick="editUniversity(${u.id})">${window.I18n ? window.I18n.t('adm.edit') : 'Edit'}</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteUniversity(${u.id},'${esc(u.name)}')">${window.I18n ? window.I18n.t('adm.delete') : 'Delete'}</button>
                </td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#f56565;padding:30px">Failed to load</td></tr>'; }
}

function openAddUniversityForm() {
    document.getElementById('universityForm').reset();
    document.getElementById('universityId').value = '';
    document.getElementById('uniCode').readOnly = false;
    document.getElementById('universityFormTitle').textContent = 'Add University';
    openSuperModal('universityFormModal');
}

async function editUniversity(uniId) {
    try {
        const { university: u } = await fetch(`/admin/universities/${uniId}`).then(r => r.json());
        document.getElementById('universityId').value = u.id;
        document.getElementById('uniName').value = u.name;
        document.getElementById('uniNameAr').value = u.name_ar || '';
        document.getElementById('uniCode').value = u.code;
        document.getElementById('uniCity').value = u.city || '';
        document.getElementById('uniProvince').value = u.province || '';
        document.getElementById('uniEmail').value = u.email || '';
        document.getElementById('uniPhone').value = u.phone || '';
        document.getElementById('uniWebsite').value = u.website || '';
        document.getElementById('uniAddress').value = u.address || '';
        document.getElementById('uniDescription').value = u.description || '';
        document.getElementById('uniActive').checked = u.is_active;
        document.getElementById('uniCode').readOnly = true;
        document.getElementById('universityFormTitle').textContent = 'Edit University';
        openSuperModal('universityFormModal');
    } catch (e) { UIDialogs.toast('Failed to load university', 'error'); }
}

async function deleteUniversity(uniId, name) {
    if (!(await UIDialogs.confirm(`Delete university "${name}"?\nAll its faculties, departments and data will also be removed.`, { danger: true }))) return;
    try {
        const res = await fetch(`/admin/universities/${uniId}`, { method: 'DELETE' });
        if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Failed'); }
        UIDialogs.toast('University deleted', 'success');
        await Promise.all([loadUniversities(), loadFaculties(), loadDepartments(), loadUsers(), loadStats(), populateUniversityFilters()]);
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
}

async function submitUniversityForm(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setBtnLoading(btn, true);
    const uniId = document.getElementById('universityId').value;
    const data = {
        name: document.getElementById('uniName').value.trim(),
        name_ar: document.getElementById('uniNameAr').value.trim(),
        code: document.getElementById('uniCode').value.trim().toUpperCase(),
        city: document.getElementById('uniCity').value.trim(),
        province: document.getElementById('uniProvince').value.trim(),
        email: document.getElementById('uniEmail').value.trim(),
        phone: document.getElementById('uniPhone').value.trim(),
        website: document.getElementById('uniWebsite').value.trim(),
        address: document.getElementById('uniAddress').value.trim(),
        description: document.getElementById('uniDescription').value.trim(),
        is_active: document.getElementById('uniActive').checked
    };
    try {
        const res = await fetch(uniId ? `/admin/universities/${uniId}` : '/admin/universities', {
            method: uniId ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
        });
        if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Failed'); }
        UIDialogs.toast(uniId ? 'University updated' : 'University created', 'success');
        closeSuperModal('universityFormModal');
        await Promise.all([loadUniversities(), loadStats(), populateUniversityFilters()]);
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
    finally { setBtnLoading(btn, false); }
}

async function loadFaculties() {
    const tbody = document.getElementById('facultiesTableBody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px">Loading...</td></tr>';
    try {
        const univId = document.getElementById('facultyUnivFilter').value;
        const { faculties = [] } = await fetch(univId ? `/admin/faculties?university_id=${univId}` : '/admin/faculties').then(r => r.json());
        if (!faculties.length) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px;color:#888">No faculties found</td></tr>'; return; }
        tbody.innerHTML = '';
        faculties.forEach(f => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td><strong>${f.name}</strong></td><td>${f.university ? f.university.name : '-'}</td><td>${f.code}</td><td>${f.dean || ''}</td><td><span>${f.departments_count || 0}</span></td><td><span class="status-badge ${f.is_active ? 'active' : 'inactive'}">${f.is_active ? 'Active' : 'Inactive'}</span></td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#f56565;padding:30px">Failed to load</td></tr>'; }
}

async function loadDepartments() {
    const tbody = document.getElementById('departmentsTableBody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px">Loading...</td></tr>';
    try {
        const univId = document.getElementById('deptUnivFilter').value;
        const { departments = [] } = await fetch(univId ? `/admin/departments?university_id=${univId}` : '/admin/departments').then(r => r.json());
        if (!departments.length) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px;color:#888">No departments found</td></tr>'; return; }
        tbody.innerHTML = '';
        departments.forEach(d => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td><strong>${d.name}</strong></td><td>${d.university ? d.university.name : '-'}</td><td>${d.faculty ? d.faculty.name : '-'}</td><td>${d.code}</td><td>${d.head_of_department || ''}</td><td><span class="status-badge ${d.is_active ? 'active' : 'inactive'}">${d.is_active ? 'Active' : 'Inactive'}</span></td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#f56565;padding:30px">Failed to load</td></tr>'; }
}

async function loadUsers() {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:30px">Loading...</td></tr>';
    try {
        const univId = document.getElementById('userUnivFilter').value;
        const filter = document.getElementById('userFilter').value;
        const params = new URLSearchParams();
        if (univId) params.set('university_id', univId);
        if (filter === 'verified') params.set('verified', 'true');
        if (filter === 'unverified') params.set('verified', 'false');
        const { users = [] } = await fetch(`/admin/users?${params}`).then(r => r.json());
        if (!users.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:30px;color:#888">No users found</td></tr>'; return; }
        tbody.innerHTML = '';
        users.forEach(u => {
            const tr = document.createElement('tr');
            const joined = new Date(u.created_at).toLocaleDateString();
            const dept = u.department ? u.department.name : (u.department_id ? 'Assigned' : 'None');
            tr.innerHTML = `<td>${u.username}</td><td>${u.email}</td><td>${u.university ? u.university.name : '-'}</td><td>${dept}</td><td><span class="status-badge ${u.is_verified ? 'active' : 'inactive'}">${u.is_verified ? 'Verified' : 'Unverified'}</span></td><td>${joined}</td><td class="action-btns"><button class="btn btn-sm btn-secondary" onclick="viewUser(${u.id})">${window.I18n ? window.I18n.t('adm.view') : 'View'}</button><button class="btn btn-sm btn-danger" onclick="deleteUser(${u.id},'${esc(u.username)}')">${window.I18n ? window.I18n.t('adm.delete') : 'Delete'}</button></td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#f56565;padding:30px">Failed to load</td></tr>'; }
}

async function viewUser(userId) {
    try {
        const { user } = await fetch(`/admin/users/${userId}`).then(r => r.json());
        const joined = user.created_at ? new Date(user.created_at).toLocaleDateString() : '-';
        const lastLogin = user.last_login ? new Date(user.last_login).toLocaleString() : 'Never';
        document.getElementById('userViewBody').innerHTML = `<table style="width:100%;border-collapse:collapse">
            ${uRow('Username', user.username)}${uRow('Full Name', user.full_name || '')}${uRow('Email', user.email)}
            ${uRow('Role', '<span class="status-badge ' + (user.is_admin ? 'active' : 'inactive') + '">' + user.role + '</span>')}
            ${uRow('Verified', user.is_verified ? 'Yes' : 'No')}
            ${uRow('University', (user.university && user.university.name) || '')}
            ${uRow('Faculty', (user.faculty && user.faculty.name) || '')}
            ${uRow('Department', (user.department && user.department.name) || '')}
            ${uRow('Student ID', user.student_id || '')}${uRow('Joined', joined)}${uRow('Last Login', lastLogin)}
        </table>`;
        openSuperModal('userViewModal');
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
}

function uRow(l, v) { return `<tr style="border-bottom:1px solid var(--border,#2a2a2a)"><td style="padding:10px;color:var(--text-secondary,#888);font-size:13px;width:40%">${l}</td><td style="padding:10px;font-size:14px">${v}</td></tr>`; }

async function deleteUser(userId, username) {
    if (!(await UIDialogs.confirm(`Delete user "${username}"?\nThis cannot be undone.`, { danger: true }))) return;
    try {
        const res = await fetch(`/admin/users/${userId}`, { method: 'DELETE' });
        if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Failed'); }
        UIDialogs.toast('User deleted', 'success');
        await Promise.all([loadUsers(), loadStats()]);
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
}

async function loadAdmins() {
    const tbody = document.getElementById('adminsTableBody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px">Loading...</td></tr>';
    try {
        const { admins = [] } = await fetch('/admin/admins').then(r => r.json());
        if (!admins.length) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:30px;color:#888">No admins found</td></tr>'; return; }
        tbody.innerHTML = '';
        admins.forEach(a => {
            const isSelf = a.id === currentUser.id, allow = canManage(a);
            const label = { super_admin: 'Super Admin', university_admin: 'University Admin', faculty_admin: 'Faculty Admin', department_admin: 'Dept Admin' }[a.role] || a.role;
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${a.username}${isSelf ? ' <span style="color:#f6e05e;font-size:11px">(you)</span>' : ''}</td><td>${a.email}</td><td><span class="badge badge-admin">${label}</span></td><td>${a.university ? a.university.name : 'System-wide'}</td><td>${new Date(a.created_at).toLocaleDateString()}</td><td class="action-btns">${allow ? `<button class="btn btn-sm btn-secondary" onclick="editAdmin(${a.id})">${window.I18n ? window.I18n.t('adm.edit') : 'Edit'}</button><button class="btn btn-sm btn-danger" onclick="deleteAdmin(${a.id},'${esc(a.username)}')">${window.I18n ? window.I18n.t('adm.delete') : 'Delete'}</button>` : '<span style="color:#888;font-size:12px">—</span>'}</td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#f56565;padding:30px">Failed to load</td></tr>'; }
}

async function openAddAdminForm() {
    document.getElementById('adminForm').reset();
    document.getElementById('adminId').value = '';
    document.getElementById('adminPassword').required = true;
    document.getElementById('adminPasswordNote').textContent = '* Required';
    document.getElementById('adminUniversityGroup').style.display = 'block';
    document.getElementById('adminFormTitle').textContent = 'Create Admin';
    await populateAdminUniversitySelect();
    openSuperModal('adminFormModal');
}

async function editAdmin(adminId) {
    try {
        const { admin: a } = await fetch(`/admin/admins/${adminId}`).then(r => r.json());
        document.getElementById('adminId').value = a.id;
        document.getElementById('adminUsername').value = a.username;
        document.getElementById('adminEmail').value = a.email;
        document.getElementById('adminFullName').value = a.full_name || '';
        document.getElementById('adminRoleSelect').value = a.role;
        document.getElementById('adminPassword').value = '';
        document.getElementById('adminPassword').required = false;
        document.getElementById('adminPasswordNote').textContent = '(leave blank to keep current)';
        document.getElementById('adminUniversityGroup').style.display = a.role === 'university_admin' ? 'block' : 'none';
        await populateAdminUniversitySelect(a.university_id);
        document.getElementById('adminFormTitle').textContent = 'Edit Admin';
        openSuperModal('adminFormModal');
    } catch (e) { UIDialogs.toast('Failed to load admin', 'error'); }
}

async function populateAdminUniversitySelect(selectedId = null) {
    const sel = document.getElementById('adminUniversity');
    sel.innerHTML = '<option value="">Loading...</option>';
    try {
        const { universities = [] } = await fetch('/admin/universities').then(r => r.json());
        sel.innerHTML = '<option value="">Select University</option>';
        universities.forEach(u => {
            const opt = document.createElement('option');
            opt.value = u.id; opt.textContent = u.name;
            if (selectedId && u.id === selectedId) opt.selected = true;
            sel.appendChild(opt);
        });
    } catch (e) { sel.innerHTML = '<option value="">Failed to load</option>'; }
}

async function submitAdminForm(e) {
    e.preventDefault();
    const btn = e.target.querySelector('button[type="submit"]');
    setBtnLoading(btn, true);
    const adminId = document.getElementById('adminId').value;
    const role = document.getElementById('adminRoleSelect').value;
    const uniId = document.getElementById('adminUniversity').value;
    const pass = document.getElementById('adminPassword').value;
    const data = {
        username: document.getElementById('adminUsername').value.trim(),
        email: document.getElementById('adminEmail').value.trim(),
        full_name: document.getElementById('adminFullName').value.trim(),
        role, university_id: role === 'university_admin' ? (parseInt(uniId) || null) : null
    };
    if (pass) data.password = pass;
    try {
        const res = await fetch(adminId ? `/admin/admins/${adminId}` : '/admin/admins', {
            method: adminId ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
        });
        if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Failed'); }
        UIDialogs.toast(adminId ? 'Admin updated' : 'Admin created', 'success');
        closeSuperModal('adminFormModal');
        await Promise.all([loadAdmins(), loadStats()]);
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
    finally { setBtnLoading(btn, false); }
}

async function deleteAdmin(adminId, username) {
    if (!(await UIDialogs.confirm(`Delete admin "${username}"?\nThis cannot be undone.`, { danger: true }))) return;
    try {
        const res = await fetch(`/admin/admins/${adminId}`, { method: 'DELETE' });
        if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'Failed'); }
        UIDialogs.toast('Admin deleted', 'success');
        await Promise.all([loadAdmins(), loadStats()]);
    } catch (e) { UIDialogs.toast(e.message, 'error'); }
}

async function populateUniversityFilters() {
    try {
        const { universities = [] } = await fetch('/admin/universities').then(r => r.json());
        ['facultyUnivFilter', 'deptUnivFilter', 'userUnivFilter'].forEach(id => {
            const el = document.getElementById(id), cur = el.value;
            const text = window.I18n ? window.I18n.t('super.all_unis') : 'All Universities';
            el.innerHTML = `<option value="">${text}</option>`;
            universities.forEach(u => {
                const opt = document.createElement('option');
                opt.value = u.id; opt.textContent = u.name;
                if (String(u.id) === cur) opt.selected = true;
                el.appendChild(opt);
            });
        });
    } catch (e) { }
}

async function logout() { await fetch('/auth/logout', { method: 'POST' }); window.location.href = '/auth/login'; }

function openSuperModal(id) { openModal(id); }
function closeSuperModal(id) { closeModal(id); }
function openModal(id) { const m = document.getElementById(id); if (m) { m.style.display = 'flex'; m.style.alignItems = 'center'; m.style.justifyContent = 'center'; } }
function closeModal(id) { const m = document.getElementById(id); if (m) m.style.display = 'none'; }
function esc(str) { return String(str).replace(/'/g, "\\'"); }

function setBtnLoading(btn, loading) {
    if (!btn) return;
    btn.disabled = loading;
    if (loading) { btn._orig = btn.textContent; btn.textContent = 'Saving...'; }
    else { btn.textContent = btn._orig || 'Save'; }
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') document.querySelectorAll('.modal').forEach(m => { if (m.style.display !== 'none') closeModal(m.id); });
});

const _s = document.createElement('style');
_s.textContent = `
.badge{display:inline-block;background:var(--accent-primary,#2dd4bf);color:#fff;padding:3px 8px;border-radius:4px;font-size:12px;font-weight:bold}
.badge-admin{background:none!important}
.status-badge{display:inline-flex;align-items:center;gap:6px;background:none!important;padding:0;font-size:13px;font-weight:500}
.status-badge::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%}
.status-badge.active{color:#48bb78}.status-badge.active::before{background:#48bb78}
.status-badge.inactive{color:#e53e3e}.status-badge.inactive::before{background:#e53e3e}
.btn-sm{padding:5px 10px;font-size:12px}
.btn-danger{background:#e53e3e;color:#fff;border:none;border-radius:6px;cursor:pointer;padding:5px 10px;font-size:12px;font-weight:600;transition:opacity .2s}
.btn-danger:hover{opacity:.85}
.action-btns{display:flex;gap:6px;flex-wrap:wrap}
`;
document.head.appendChild(_s);
