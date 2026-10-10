function resolveApiBaseUrl() {
    const hostname = window.location.hostname;
    const origin = window.location.origin;

    if (!origin || !hostname) {
        return "http://127.0.0.1:8000";
    }

    if (hostname === "localhost") {
        return "http://localhost:8000";
    }

    if (hostname === "127.0.0.1") {
        return "http://127.0.0.1:8000";
    }

    if (hostname === "0.0.0.0") {
        return "http://127.0.0.1:8000";
    }

    if (hostname === "100.73.218.40" || hostname === "172.17.22.24" || hostname.startsWith("192.168.")) {
        return `http://${hostname}:8000`;
    }

    return origin.replace(/:\d+$/, ":8000");
}

export const API_BASE_URL = resolveApiBaseUrl();

export function apiFetch(path, options = {}) {
    return fetch(`${API_BASE_URL}${path}`, {
        ...options,
        credentials: options.credentials ?? "include"
    });
}

export async function readResponse(response) {
    if (response.headers.get("content-type")?.includes("application/json")) {
        return response.json();
    }

    return {};
}
