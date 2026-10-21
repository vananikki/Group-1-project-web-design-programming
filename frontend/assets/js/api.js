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

const configuredApiBaseUrl = resolveApiBaseUrl();
const FORWARDED_API_STORAGE_KEY = "online-judge-api-base-url";
const localHostname = window.location.hostname;
const savedApiBaseUrl = sessionStorage.getItem(FORWARDED_API_STORAGE_KEY);
const savedApiUrlIsValid =
    (localHostname === "localhost" || localHostname === "127.0.0.1") &&
    new RegExp(`^http://${localHostname.replaceAll(".", "\\.")}:800[1-9]$|^http://${localHostname.replaceAll(".", "\\.")}:8010$`).test(
        savedApiBaseUrl ?? "",
    );
let apiBaseUrl = savedApiUrlIsValid ? savedApiBaseUrl : configuredApiBaseUrl;
let forwardedApiDiscovery;

async function discoverForwardedApi() {
    const hostname = window.location.hostname;
    if (hostname !== "localhost" && hostname !== "127.0.0.1") {
        throw new Error("Automatic API port discovery is only available on localhost.");
    }

    const candidates = Array.from(
        { length: 10 },
        (_, index) => `http://${hostname}:${8001 + index}`,
    );
    try {
        return await Promise.any(
            candidates.map(async (candidate) => {
                try {
                    const response = await fetch(`${candidate}/`, {
                        credentials: "omit",
                        headers: { Accept: "application/json" },
                        signal: AbortSignal.timeout(1500),
                    });
                    if (!response.ok) {
                        throw new Error("Not the Online Judge API");
                    }

                    const payload = await response.json();
                    if (payload.message === "Hello Online Judge!") {
                        return candidate;
                    }
                    throw new Error("Not the Online Judge API");
                } catch (error) {
                    throw new Error(`Could not verify ${candidate}`, { cause: error });
                }
            }),
        );
    } catch {
        throw new Error("Could not find the forwarded Online Judge API on localhost ports 8001-8010.");
    }
}

function fetchFromApi(path, options) {
    return fetch(`${apiBaseUrl}${path}`, {
        ...options,
        credentials: options.credentials ?? "include"
    });
}

export async function apiFetch(path, options = {}) {
    try {
        return await fetchFromApi(path, options);
    } catch (error) {
        if (localHostname !== "localhost" && localHostname !== "127.0.0.1") {
            throw error;
        }

        forwardedApiDiscovery ??= discoverForwardedApi();
        try {
            apiBaseUrl = await forwardedApiDiscovery;
            sessionStorage.setItem(FORWARDED_API_STORAGE_KEY, apiBaseUrl);
        } catch (discoveryError) {
            throw new Error(
                `Cannot connect to the Online Judge API at ${configuredApiBaseUrl}. ${discoveryError.message}`,
                { cause: error },
            );
        }

        return fetchFromApi(path, options);
    }
}

export async function readResponse(response) {
    if (response.headers.get("content-type")?.includes("application/json")) {
        return response.json();
    }

    return {};
}
