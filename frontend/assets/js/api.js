function resolveApiBaseUrl() {
    const hostname = window.location.hostname;
    const origin = window.location.origin;

    if (!origin || !hostname) {
        return "http://localhost:8000";
    }

    if (hostname === "localhost" || hostname === "127.0.0.1") {
        return "http://localhost:8000";
    }

    return origin.replace(/:\d+$/, ":8000");
}

export const API_BASE_URL = resolveApiBaseUrl();

export function apiFetch(path, options = {}) {
    return fetch(`${API_BASE_URL}${path}`, {
        ...options,
        credentials: "include"
    });
}

export async function readResponse(response) {
    if (response.headers.get("content-type")?.includes("application/json")) {
        return response.json();
    }

    return {};
}
