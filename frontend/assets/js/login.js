import { apiFetch, readResponse } from "./api.js";

const form = document.getElementById("login-form");
const errorMessage = document.getElementById("error-message");

document.getElementById("register-button").addEventListener("click", () => {
    window.location.href = "register.html";
});

async function redirectIfLoggedIn() {
    try {
        const response = await apiFetch("/auth/me");
        if (response.ok) {
            window.location.replace("index.html");
            return;
        }

        if (response.status === 403) {
            window.location.replace("activate.html");
        }
    } catch (error) {
        console.error("Could not check the current session:", error);
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorMessage.textContent = "";

    try {
        const response = await apiFetch("/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                account_email: document.getElementById("email").value,
                password: document.getElementById("password").value
            })
        });

        const data = await readResponse(response);
        if (response.ok) {
            window.location.replace("index.html");
            return;
        }

        if (response.status === 403) {
            window.location.replace("activate.html");
            return;
        }

        errorMessage.textContent =
            data.detail || `Server error (${response.status})`;
    } catch (error) {
        console.error(error);
        errorMessage.textContent = "Không thể kết nối đến server";
    }
});

redirectIfLoggedIn();
