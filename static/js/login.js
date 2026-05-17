// If already logged in, redirect immediately
(async () => {
    try {
        const res = await fetch('/auth/me');
        if (res.ok) {
            const { user } = await res.json();
            const adminRoles = ['super_admin', 'university_admin', 'faculty_admin', 'department_admin'];
            window.location.replace(adminRoles.includes(user.role) ? '/admin' : '/chat/');
            return;
        }
    } catch (e) { /* not logged in, show form */ }
})();

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const email     = document.getElementById('email').value;
    const password  = document.getElementById('password').value;
    const errorDiv  = document.getElementById('errorMessage');

    errorDiv.style.display = 'none';

    try {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            const role = data.user.role;
            const adminRoles = ["super_admin", "university_admin", "faculty_admin", "department_admin"];
            window.location.replace(adminRoles.includes(role) ? "/admin" : "/chat/");
        } else {
            errorDiv.textContent = data.error || (window.I18n ? I18n.t('login.error_default') : 'Invalid login credentials');
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = window.I18n ? I18n.t('login.error_network') : 'An error occurred. Please try again.';
        errorDiv.style.display = 'block';
    }
});
