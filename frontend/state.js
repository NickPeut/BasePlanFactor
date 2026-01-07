let activeSchemeId = null;
const ACTIVE_SCHEME_KEY = "activeSchemeId";

export function setActiveSchemeId(id) {
    activeSchemeId = id;
    if (id === null || id === undefined) {
        localStorage.removeItem(ACTIVE_SCHEME_KEY);
    } else {
        localStorage.setItem(ACTIVE_SCHEME_KEY, String(id));
    }
}

export function getSavedSchemeId() {
    const v = localStorage.getItem(ACTIVE_SCHEME_KEY);
    if (!v) return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
}

export function getActiveSchemeId() {
    return activeSchemeId;
}

export function setAuthToken(token) {
    if (token === null || token === undefined || String(token).trim() === "") {
        localStorage.removeItem("AUTH_TOKEN");
    } else {
        localStorage.setItem("AUTH_TOKEN", String(token));
    }
}

export function getAuthToken() {
    return localStorage.getItem("AUTH_TOKEN");
}
