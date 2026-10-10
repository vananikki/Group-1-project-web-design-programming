import { apiFetch, readResponse } from "./api.js";

const logoutButton = document.getElementById("logout-button");
const logoutError = document.getElementById("logout-error");
const accountName = document.getElementById("account-name");
const accountNameInput = document.getElementById("account-name-input");
const editNameButton = document.getElementById("edit-name-button");
const saveNameButton = document.getElementById("save-name-button");
const cancelNameButton = document.getElementById("cancel-name-button");
const deleteAccountButton = document.getElementById("delete-account-button");
const profileMessage = document.getElementById("profile-message");
let currentAccount;

function setNameEditMode(enabled) {
    accountName.hidden = enabled;
    accountNameInput.hidden = !enabled;
    editNameButton.hidden = enabled;
    saveNameButton.hidden = !enabled;
    cancelNameButton.hidden = !enabled;
    profileMessage.textContent = "";
}

async function loadAccount() {
    try {
        const response = await apiFetch("/auth/me");
        if (!response.ok) {
            if (response.status === 403) {
                window.location.replace("activate.html");
            } else {
                window.location.replace("login.html");
            }
            return;
        }

        currentAccount = await response.json();
        accountName.textContent = currentAccount.account_name;
        accountNameInput.value = currentAccount.account_name;
        document.getElementById("account-id").textContent =
            currentAccount.account_id;
        document.getElementById("account-email").textContent =
            currentAccount.account_email;
        document.getElementById("account-code").textContent =
            currentAccount.account_code;
        document.getElementById("account-role").textContent =
            currentAccount.role;

        const createdAt = new Date(currentAccount.created_at);
        const createdAtElement = document.getElementById("account-created-at");
        createdAtElement.dateTime = currentAccount.created_at;
        createdAtElement.textContent = Number.isNaN(createdAt.getTime())
            ? currentAccount.created_at
            : createdAt.toLocaleString();

        document.getElementById("manage-accounts-link").hidden =
            currentAccount.role !== "SUPER_ADMIN";
    } catch (error) {
        console.error(error);
        window.location.replace("login.html");
    }
}

editNameButton.addEventListener("click", () => {
    accountNameInput.value = currentAccount.account_name;
    setNameEditMode(true);
    accountNameInput.focus();
});

cancelNameButton.addEventListener("click", () => {
    accountNameInput.value = currentAccount.account_name;
    setNameEditMode(false);
});

saveNameButton.addEventListener("click", async () => {
    const name = accountNameInput.value.trim();
    if (name.length < 3) {
        profileMessage.textContent = "Tên phải có ít nhất 3 ký tự";
        return;
    }

    saveNameButton.disabled = true;
    profileMessage.textContent = "";

    try {
        const response = await apiFetch("/auth/me", {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ account_name: name })
        });
        const data = await readResponse(response);

        if (response.status === 401) {
            window.location.replace("login.html");
            return;
        }
        if (!response.ok) {
            profileMessage.textContent =
                data.detail || `Không thể cập nhật tên (${response.status})`;
            return;
        }

        currentAccount = data;
        accountName.textContent = currentAccount.account_name;
        accountNameInput.value = currentAccount.account_name;
        setNameEditMode(false);
        profileMessage.textContent = "Đã cập nhật tên tài khoản";
    } catch (error) {
        console.error(error);
        profileMessage.textContent = "Không thể kết nối đến server";
    } finally {
        saveNameButton.disabled = false;
    }
});

deleteAccountButton.addEventListener("click", async () => {
    if (currentAccount.role === "SUPER_ADMIN") {
        profileMessage.textContent = "Super admin không thể tự xóa tài khoản.";
        return;
    }

    const confirmed = window.confirm("Bạn có chắc chắn muốn xóa tài khoản hiện tại? Hành động này không thể hoàn tác.");
    if (!confirmed) {
        return;
    }

    deleteAccountButton.disabled = true;
    profileMessage.textContent = "";

    try {
        const response = await apiFetch(`/admin/accounts/${currentAccount.account_id}`, {
            method: "DELETE"
        });
        const data = await readResponse(response);

        if (response.status === 401) {
            window.location.replace("login.html");
            return;
        }
        if (!response.ok) {
            profileMessage.textContent = data.detail || `Không thể xóa tài khoản (${response.status})`;
            return;
        }

        const logoutResponse = await apiFetch("/auth/logout", { method: "POST" });
        if (!logoutResponse.ok) {
            window.location.replace("login.html");
            return;
        }

        window.location.replace("login.html");
    } catch (error) {
        console.error(error);
        profileMessage.textContent = "Không thể kết nối đến server";
    } finally {
        deleteAccountButton.disabled = false;
    }
});

logoutButton.addEventListener("click", async () => {
    logoutError.textContent = "";
    logoutButton.disabled = true;

    try {
        const response = await apiFetch("/auth/logout", { method: "POST" });
        if (!response.ok) {
            logoutError.textContent = `Không thể đăng xuất (${response.status})`;
            logoutButton.disabled = false;
            return;
        }

        window.location.replace("login.html");
    } catch (error) {
        console.error(error);
        logoutError.textContent = "Không thể kết nối đến server";
        logoutButton.disabled = false;
    }
});

loadAccount();
