import { apiFetch, readResponse } from "./api.js?v=20261029a";

const publicList = document.getElementById("public-problem-list");
const ownedList = document.getElementById("owned-problem-list");
const pageMessage = document.getElementById("page-message");
const publicProblems = [];
let ownedProblems = [];
let account;

async function requestJson(path) {
    const response = await apiFetch(path);
    const data = await readResponse(response);
    if (!response.ok) {
        throw new Error(data.detail || `Yêu cầu thất bại (${response.status})`);
    }
    return data;
}

function renderProblemPicker(element, problems, { isPublic = false, query = "" } = {}) {
    const normalizedQuery = query.toLocaleLowerCase();
    const filtered = problems.filter((problem) =>
        `${problem.problem_name} ${problem.problem_id}`
            .toLocaleLowerCase()
            .includes(normalizedQuery)
    );
    element.replaceChildren();
    if (!filtered.length) {
        const empty = document.createElement("p");
        empty.className = "field-hint";
        empty.textContent = query ? "Không tìm thấy bài phù hợp." : "Chưa có bài tập nào.";
        element.append(empty);
        return;
    }

    for (const problem of filtered) {
        const row = document.createElement("div");
        row.className = "problem-picker-row";
        const open = document.createElement("a");
        const params = new URLSearchParams({
            problem_id: String(problem.problem_id),
            source: isPublic ? "public" : "owner",
        });
        open.className = "problem-picker-item";
        open.href = `problem_submit.html?${params}`;
        open.textContent = problem.problem_name;
        row.append(open);

        if (!isPublic && problem.created_by === account.account_id) {
            const edit = document.createElement("a");
            edit.className = "problem-picker-edit";
            edit.href = `create_problem.html?problem_id=${encodeURIComponent(problem.problem_id)}`;
            edit.textContent = "Sửa";
            edit.setAttribute("aria-label", `Sửa ${problem.problem_name}`);
            row.append(edit);
        }
        element.append(row);
    }
}

function setMessage(text) {
    pageMessage.textContent = text;
    pageMessage.classList.add("error");
}

async function initialize() {
    try {
        const accountResponse = await apiFetch("/auth/me");
        if (!accountResponse.ok) {
            window.location.replace("login.html");
            return;
        }
        account = await accountResponse.json();
        const problems = await requestJson("/student/problems");
        publicProblems.push(...problems);
        renderProblemPicker(publicList, publicProblems, { isPublic: true });

        if (account.role === "ADMIN" || account.role === "SUPER_ADMIN") {
            document.getElementById("create-problem-link").hidden = false;
            document.getElementById("create-problem-main-link").hidden = false;
            document.getElementById("owned-problems-panel").hidden = false;
            ownedProblems = await requestJson("/admin/judge/problems");
            renderProblemPicker(
                ownedList,
                ownedProblems.filter((problem) => problem.created_by === account.account_id),
            );
        }
    } catch (error) {
        console.error(error);
        setMessage(error instanceof Error ? error.message : "Không thể tải kho bài tập.");
    }
}

document.getElementById("problem-filter").addEventListener("input", (event) => {
    const query = event.currentTarget.value.trim();
    renderProblemPicker(publicList, publicProblems, { isPublic: true, query });
    if (!document.getElementById("owned-problems-panel").hidden) {
        renderProblemPicker(
            ownedList,
            ownedProblems.filter((problem) => problem.created_by === account.account_id),
            { query },
        );
    }
});

document.getElementById("logout-button").addEventListener("click", async () => {
    try {
        const response = await apiFetch("/auth/logout", { method: "POST" });
        if (!response.ok) {
            throw new Error(`Không thể đăng xuất (${response.status}).`);
        }
        window.location.replace("login.html");
    } catch (error) {
        console.error(error);
        setMessage(error instanceof Error ? error.message : "Không thể đăng xuất.");
    }
});

initialize();
