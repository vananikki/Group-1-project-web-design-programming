import { apiFetch, readResponse } from "./api.js?v=20261029a";
import { typesetMath } from "./latex.js?v=20261101b";
import { renderSubmissionHistory } from "./submission_history.js?v=20261102a";

const publicList = document.getElementById("public-problem-list");
const ownedList = document.getElementById("owned-problem-list");
const pageMessage = document.getElementById("page-message");
const solutionDialog = document.getElementById("solution-dialog");
const solutionForm = document.getElementById("solution-form");
let account;
let activeProblemId;
let languagesPromise;
const historyPageSize = 50;
let historyOffset = 0;

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;",
    })[character]);
}

function setMessage(element, text, isError = false) {
    element.textContent = text;
    element.classList.toggle("error", isError);
    element.classList.toggle("success", !isError && Boolean(text));
}

async function requestJson(path, options) {
    const response = await apiFetch(path, options);
    const data = await readResponse(response);
    if (!response.ok) {
        throw new Error(data.detail || `Yêu cầu thất bại (${response.status})`);
    }
    return data;
}

function problemCard(problem, { canEdit = false, isPublic = false } = {}) {
    const isPublicProblem = isPublic || problem.access_modifier === "public";
    const visibility = isPublicProblem ? "Public" : "Private";
    const source = canEdit ? "owner" : "public";
    return `<article class="problem-card">
        <div>
            <p class="class-card-kicker">BÀI TẬP · #${escapeHtml(problem.problem_id)} · ${visibility.toUpperCase()}</p>
            <h4>${escapeHtml(problem.problem_name)}</h4>
            ${problem.description?.trim() ? `<p>${escapeHtml(problem.description)}</p>` : ""}
        </div>
        <div class="button-row">
            <a class="button-link secondary" href="problem_statement.html?problem_id=${encodeURIComponent(problem.problem_id)}&source=${source}">Xem đề bài</a>
            ${isPublicProblem ? `<button type="button" data-solve-problem="${escapeHtml(problem.problem_id)}">Luyện tập</button>` : ""}
            ${canEdit ? `<a class="button-link secondary" href="create_problem.html?problem_id=${encodeURIComponent(problem.problem_id)}">Sửa bài</a>` : ""}
        </div>
    </article>`;
}

function renderList(element, problems, options = {}) {
    element.innerHTML = problems.length
        ? problems.map((problem) => problemCard(problem, options)).join("")
        : `<div class="empty-state"><p>${escapeHtml(options.emptyText)}</p></div>`;
    typesetMath(element).catch((error) => {
        console.error(error);
        setMessage(pageMessage, error.message || "Không thể hiển thị công thức LaTeX.", true);
    });
}

async function loadLanguages() {
    languagesPromise ??= requestJson("/student/languages");
    const languages = await languagesPromise;
    const selector = document.getElementById("solution-language");
    selector.innerHTML = languages.map((language) =>
        `<option value="${language.language_id}">${escapeHtml(language.name)}</option>`
    ).join("");
    if (!languages.length) {
        throw new Error("Chưa có ngôn ngữ chấm bài. Hãy đồng bộ danh sách Judge0 languages trước.");
    }
}

async function loadSubmissionHistory({ append = false } = {}) {
    const offset = append ? historyOffset : 0;
    const history = await requestJson(
        `/student/submissions?limit=${historyPageSize}&offset=${offset}`,
    );
    const list = document.getElementById("submission-history");
    renderSubmissionHistory(list, history, { append });
    historyOffset = offset + history.length;
    document.getElementById("submission-history-more").hidden =
        history.length < historyPageSize;
}

async function openProblem(problemId, button) {
    activeProblemId = Number(problemId);
    document.getElementById("solution-heading").textContent =
        button.closest(".problem-card").querySelector("h4").textContent;
    solutionForm.elements.source_code.value = "";
    setMessage(document.getElementById("submission-result"), "");
    await loadLanguages();
    solutionDialog.showModal();
}

async function initialize() {
    try {
        const accountResponse = await apiFetch("/auth/me");
        if (!accountResponse.ok) {
            window.location.replace("login.html");
            return;
        }
        account = await accountResponse.json();
        const publicProblems = await requestJson("/student/problems");
        renderList(publicList, publicProblems, {
            isPublic: true,
            emptyText: "Chưa có bài tập public nào.",
        });
        try {
            await loadSubmissionHistory();
        } catch (error) {
            console.error(error);
            setMessage(pageMessage, error.message || "Không thể tải lịch sử nộp bài.", true);
        }
        if (account.role === "ADMIN" || account.role === "SUPER_ADMIN") {
            document.getElementById("create-problem-link").hidden = false;
            document.getElementById("create-problem-main-link").hidden = false;
            document.getElementById("owned-problems-panel").hidden = false;
            const problems = await requestJson("/admin/judge/problems");
            const ownedProblems = problems.filter((problem) =>
                problem.created_by === account.account_id
            );
            renderList(ownedList, ownedProblems, {
                canEdit: true,
                emptyText: "Bạn chưa tạo bài tập nào.",
            });
        }
    } catch (error) {
        console.error(error);
        setMessage(pageMessage, error.message || "Không thể tải kho bài tập.", true);
    }
}

document.body.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-solve-problem]");
    if (!button) {
        return;
    }
    button.disabled = true;
    try {
        await openProblem(button.dataset.solveProblem, button);
    } catch (error) {
        console.error(error);
        setMessage(pageMessage, error.message || "Không thể mở bài tập.", true);
    } finally {
        button.disabled = false;
    }
});

document.getElementById("close-solution").addEventListener("click", () => {
    solutionDialog.close();
});

solutionDialog.addEventListener("click", (event) => {
    if (event.target === event.currentTarget) {
        solutionDialog.close();
    }
});

solutionForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = solutionForm.querySelector('[type="submit"]');
    const resultElement = document.getElementById("submission-result");
    const values = new FormData(solutionForm);
    button.disabled = true;
    setMessage(resultElement, "Đang gửi lời giải tới hệ thống chấm bài...");
    try {
        const result = await requestJson(
            `/student/problems/${activeProblemId}/submissions`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    language_id: Number(values.get("language_id")),
                    source_code: values.get("source_code"),
                }),
            },
        );
        setMessage(
            resultElement,
            `${result.status} · ${result.score} điểm · ${result.passed_testcases}/${result.total_testcases} test case · tổng ${result.runtime_ms == null ? "—" : `${result.runtime_ms} ms`} · bộ nhớ đỉnh ${result.memory_kb == null ? "—" : `${result.memory_kb} KB`}`,
            result.status !== "Accepted",
        );
        try {
            await loadSubmissionHistory();
        } catch (error) {
            console.error(error);
            setMessage(pageMessage, error.message || "Đã chấm bài nhưng không thể tải lại lịch sử.", true);
        }
    } catch (error) {
        setMessage(resultElement, error.message || "Không thể chấm lời giải.", true);
    } finally {
        button.disabled = false;
    }
});

document.getElementById("submission-history-more").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
        await loadSubmissionHistory({ append: true });
    } catch (error) {
        console.error(error);
        setMessage(pageMessage, error.message || "Không thể tải thêm lịch sử nộp bài.", true);
    } finally {
        button.disabled = false;
    }
});

document.getElementById("logout-button").addEventListener("click", async () => {
    try {
        const response = await apiFetch("/auth/logout", { method: "POST" });
        if (response.ok) {
            window.location.replace("login.html");
        } else {
            throw new Error(`Không thể đăng xuất (${response.status}).`);
        }
    } catch (error) {
        setMessage(pageMessage, error.message || "Không thể kết nối đến server.", true);
    }
});

initialize();
