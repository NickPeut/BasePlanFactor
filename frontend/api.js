import { requestJson } from "./http.js";

export function apiGetSchemes() {
    return requestJson("/api/schemes");
}

export function apiCreateScheme(name) {
    return requestJson(`/api/schemes?name=${encodeURIComponent(name)}`, {
        method: "POST"
    });
}

export function apiDeleteScheme(id) {
    return requestJson(`/api/schemes/${id}`, {
        method: "DELETE"
    });
}

export function apiStart(schemeId = null) {
    const url = schemeId !== null
        ? `/api/dialog/start?scheme_id=${schemeId}`
        : "/api/dialog/start";

    return requestJson(url, { method: "POST" });
}

export function apiAnswer(text) {
    return requestJson("/api/dialog/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer: text })
    });
}
