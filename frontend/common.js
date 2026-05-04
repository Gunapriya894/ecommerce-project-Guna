// ── GU Commerce · common.js ───────────────────────────────────────────────────
// Single source of truth for: API URLs, auth guard, logout, nav username
// Include in every protected page:  <script src="common.js"></script>
// ─────────────────────────────────────────────────────────────────────────────

// ── API URLs ──────────────────────────────────────────────────────────────────
const BASE_URL      = "https://s15c9rh1dc.execute-api.ap-southeast-1.amazonaws.com/dev";
const PRODUCT_URL   = BASE_URL + "/guproduct";
const CART_URL      = BASE_URL + "/gucart";
const REC_URL       = BASE_URL + "/gurecommend";
const AUTH_BASE     = BASE_URL;
const SIGNUP_URL    = AUTH_BASE + "/guauth/signup";
const LOGIN_URL     = AUTH_BASE + "/guauth/login";
const LOGOUT_URL    = AUTH_BASE + "/guauth/logout";

// ── Auth Guard ────────────────────────────────────────────────────────────────
// Runs immediately on every protected page.
// If no token in localStorage → redirect to login instantly.
// If token found → set window.GU_USER and show the page.
(function authGuard() {
    try {
        const token    = localStorage.getItem('gu_token');
        const username = localStorage.getItem('gu_username');
        const email    = localStorage.getItem('gu_email');

        if (!token) {
            window.location.replace('login.html');
            return;
        }

        // Expose globally so any page can read logged-in user details
        window.GU_USER = { token, username: username || '', email: email || '' };

        // Inject username into nav chip if element exists on the page
        const navEl = document.getElementById('navUsername');
        if (navEl) navEl.textContent = username || '—';

        // Make body visible (pages start with visibility:hidden to prevent flash)
        document.body.style.visibility = 'visible';

    } catch (e) {
        // If anything goes wrong reading storage, send to login safely
        localStorage.clear();
        window.location.replace('login.html');
    }
})();

// ── Logout ────────────────────────────────────────────────────────────────────
// Called by the ⏻ Logout button in every nav bar.
// Calls the Lambda logout endpoint, then clears localStorage.
async function doLogout() {
    try {
        const token = localStorage.getItem('gu_token');
        if (token) {
            await fetch(LOGOUT_URL, {
                method:  'POST',
                headers: {
                    'Content-Type':  'application/json',
                    'Authorization': 'Bearer ' + token
                }
            });
        }
    } catch (e) {
        // Ignore network errors on logout — clear session regardless
    } finally {
        localStorage.removeItem('gu_token');
        localStorage.removeItem('gu_username');
        localStorage.removeItem('gu_email');
        window.location.replace('login.html');
    }
}