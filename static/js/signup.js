function t(key) { return window.I18n ? I18n.t(key) : key; }

async function loadUniversities() {
    try {
        const response = await fetch('/auth/universities');
        const data = await response.json();
        const select = document.getElementById('university_id');
        data.universities.forEach(uni => {
            const option = document.createElement('option');
            option.value = uni.id;
            const arName = uni.name_ar ? ` — ${uni.name_ar}` : '';
            option.textContent = uni.name + (uni.city ? ` (${uni.city})` : '') + arName;
            select.appendChild(option);
        });

        if (window.TomSelect) {
            new TomSelect('#university_id', {
                create: false,
                sortField: { field: "text", direction: "asc" },
                placeholder: t('signup.uni_ph') || 'Select university'
            });
        }
    } catch (error) { console.error('Error loading universities:', error); }
}

async function loadFaculties(universityId) {
    const facSelect = document.getElementById('faculty_id');
    const deptSelect = document.getElementById('department_id');

    facSelect.innerHTML = `<option value="">${t('signup.fac_loading')}</option>`;
    facSelect.disabled = true;
    deptSelect.innerHTML = `<option value="">${t('signup.dept_first')}</option>`;
    deptSelect.disabled = true;

    try {
        const response = await fetch(`/auth/universities/${universityId}/faculties`);
        const data = await response.json();
        facSelect.innerHTML = `<option value="">${t('signup.fac_ph')}</option>`;
        data.faculties.forEach(fac => {
            const option = document.createElement('option');
            option.value = fac.id;
            option.textContent = fac.name + (fac.name_ar ? ` (${fac.name_ar})` : '');
            facSelect.appendChild(option);
        });
        facSelect.disabled = false;
    } catch (error) {
        console.error('Error loading faculties:', error);
        facSelect.innerHTML = `<option value="">${t('signup.fac_error')}</option>`;
        facSelect.disabled = false;
    }
}

async function loadDepartments(facultyId) {
    const deptSelect = document.getElementById('department_id');
    deptSelect.innerHTML = `<option value="">${t('signup.dept_loading')}</option>`;
    deptSelect.disabled = true;

    try {
        const response = await fetch(`/auth/faculties/${facultyId}/departments`);
        const data = await response.json();
        deptSelect.innerHTML = `<option value="">${t('signup.dept_ph')}</option>`;
        data.departments.forEach(dept => {
            const option = document.createElement('option');
            option.value = dept.id;
            option.textContent = dept.name + (dept.name_ar ? ` (${dept.name_ar})` : '');
            deptSelect.appendChild(option);
        });
        deptSelect.disabled = false;
    } catch (error) {
        console.error('Error loading departments:', error);
        deptSelect.innerHTML = `<option value="">${t('signup.dept_error')}</option>`;
        deptSelect.disabled = false;
    }
}

document.getElementById('university_id').addEventListener('change', e => {
    if (e.target.value) {
        loadFaculties(e.target.value);
    } else {
        const facSelect = document.getElementById('faculty_id');
        const deptSelect = document.getElementById('department_id');
        facSelect.innerHTML = `<option value="">${t('signup.fac_first')}</option>`;
        facSelect.disabled = true;
        deptSelect.innerHTML = `<option value="">${t('signup.dept_first')}</option>`;
        deptSelect.disabled = true;
    }
});

document.getElementById('faculty_id').addEventListener('change', e => {
    if (e.target.value) {
        loadDepartments(e.target.value);
    } else {
        const deptSelect = document.getElementById('department_id');
        deptSelect.innerHTML = `<option value="">${t('signup.dept_first')}</option>`;
        deptSelect.disabled = true;
    }
});

document.getElementById('signupForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const errorDiv = document.getElementById('errorMessage');
    const successDiv = document.getElementById('successMessage');

    if (!document.getElementById('agreeTerms').checked) {
        errorDiv.textContent = t('signup.error_terms');
        errorDiv.style.display = 'block';
        successDiv.style.display = 'none';
        return;
    }

    const password = document.getElementById('password').value;
    if (password.length < 8) {
        errorDiv.textContent = 'Password must be at least 8 characters long.';
        errorDiv.style.display = 'block';
        successDiv.style.display = 'none';
        return;
    }
    if (!/[A-Z]/.test(password)) {
        errorDiv.textContent = 'Password must contain at least one uppercase letter (A-Z).';
        errorDiv.style.display = 'block';
        successDiv.style.display = 'none';
        return;
    }
    if (!/[a-z]/.test(password)) {
        errorDiv.textContent = 'Password must contain at least one lowercase letter (a-z).';
        errorDiv.style.display = 'block';
        successDiv.style.display = 'none';
        return;
    }
    if (!/[0-9]/.test(password)) {
        errorDiv.textContent = 'Password must contain at least one number (0-9).';
        errorDiv.style.display = 'block';
        successDiv.style.display = 'none';
        return;
    }
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(password)) {
        errorDiv.textContent = 'Password must contain at least one special character (!@#$%^&*...).';
        errorDiv.style.display = 'block';
        successDiv.style.display = 'none';
        return;
    }

    const formData = {
        username: document.getElementById('username').value,
        email: document.getElementById('email').value,
        password: document.getElementById('password').value,
        full_name: document.getElementById('full_name').value,
        university_id: document.getElementById('university_id').value,
        faculty_id: document.getElementById('faculty_id').value,
        department_id: document.getElementById('department_id').value,
        student_id: document.getElementById('student_id').value
    };

    try {
        const response = await fetch('/auth/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (response.ok) {
            errorDiv.style.display = 'none';
            successDiv.textContent = data.message;
            successDiv.style.display = 'block';
            setTimeout(() => { window.location.href = '/auth/login'; }, 3000);
        } else {
            successDiv.style.display = 'none';
            errorDiv.textContent = data.error || t('signup.error_default');
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = t('signup.error_network');
        errorDiv.style.display = 'block';
    }
});

loadUniversities();
