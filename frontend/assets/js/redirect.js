import { apiFetch } from "./api.js";

async function redirectBySession() {
    try {
        const response = await apiFetch("/auth/me");
        if (response.ok) {
            window.location.replace("modules/index.html");
            return;
        }

        if (response.status === 403) {
            window.location.replace("modules/activate.html");
            return;
        }

        window.location.replace("modules/login.html");
    } catch (error) {
        console.error("Could not check the current session:", error);
        window.location.replace("modules/login.html");
    }
}

redirectBySession();
