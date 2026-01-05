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

export async function apiGetSchemes() {
    const res = await fetch("/schemes");
    return await res.json();
}

export async function apiCreateScheme(name) {
    const res = await fetch(`/schemes?name=${encodeURIComponent(name)}`, {
        method: "POST"
    });
    return await res.json();
}

export async function apiDeleteScheme(id) {
    const res = await fetch(`/schemes/${id}`, {
        method: "DELETE"
    });
    return await res.json();
}

export async function apiStart(schemeId = null) {
    const url = schemeId !== null
        ? `/dialog/start?scheme_id=${schemeId}`
        : "/dialog/start";

    const res = await fetch(url, { method: "POST" });
    return await res.json();
}

export async function apiAnswer(text) {
    const res = await fetch("/dialog/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer: text })
    });
    return await res.json();
}
