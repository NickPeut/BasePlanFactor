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

const DIALOG_HISTORY_PREFIX = "dialogHistory:";
const DIALOG_ACTIVE_PREFIX = "dialogActive:";
const SCHEME_STATE_PREFIX = "schemeState:";

function _dialogKey(prefix, schemeId) {
    const sid = (schemeId === null || schemeId === undefined) ? "null" : String(schemeId);
    return prefix + sid;
}

function _schemeKey(schemeId) {
    const sid = (schemeId === null || schemeId === undefined) ? "null" : String(schemeId);
    return SCHEME_STATE_PREFIX + sid;
}

export function saveDialogHistory(schemeId, items) {
    localStorage.setItem(_dialogKey(DIALOG_HISTORY_PREFIX, schemeId), JSON.stringify(items || []));
}

export function loadDialogHistory(schemeId) {
    const raw = localStorage.getItem(_dialogKey(DIALOG_HISTORY_PREFIX, schemeId));
    if (!raw) return null;
    try {
        const arr = JSON.parse(raw);
        return Array.isArray(arr) ? arr : null;
    } catch {
        return null;
    }
}

export function clearDialogHistory(schemeId) {
    localStorage.removeItem(_dialogKey(DIALOG_HISTORY_PREFIX, schemeId));
    localStorage.removeItem(_dialogKey(DIALOG_ACTIVE_PREFIX, schemeId));
}

export function saveSchemeState(schemeId, state) {
    localStorage.setItem(_schemeKey(schemeId), JSON.stringify(state || {}));
}

export function loadSchemeState(schemeId) {
    const raw = localStorage.getItem(_schemeKey(schemeId));
    if (!raw) return null;
    try {
        const obj = JSON.parse(raw);
        return obj && typeof obj === "object" ? obj : null;
    } catch {
        return null;
    }
}

export function clearSchemeState(schemeId) {
    localStorage.removeItem(_schemeKey(schemeId));
}

export function setDialogActive(schemeId, isActive) {
    const key = _dialogKey(DIALOG_ACTIVE_PREFIX, schemeId);
    if (isActive) localStorage.setItem(key, "1");
    else localStorage.removeItem(key);
}

export function isDialogActive(schemeId) {
    return localStorage.getItem(_dialogKey(DIALOG_ACTIVE_PREFIX, schemeId)) === "1";
}