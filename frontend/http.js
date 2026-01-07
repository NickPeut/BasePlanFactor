import { getAuthToken } from "./state.js";

function authHeaders() {
    const t = getAuthToken();
    return t ? { "Authorization": `Bearer ${t}` } : {};
}

export async function requestJson(path, options = {}) {
    const headers = {
        ...(options.headers || {}),
        ...authHeaders()
    };

    const res = await fetch(path, { ...options, headers });

    const ct = res.headers.get("content-type") || "";
    const isJson = ct.includes("application/json");
    const data = isJson ? await res.json() : await res.text();

    if (!res.ok) {
        const msg = typeof data === "string" ? data : (data?.detail || JSON.stringify(data));
        throw new Error(`${res.status} ${res.statusText}: ${msg}`);
    }

    return data;
}
