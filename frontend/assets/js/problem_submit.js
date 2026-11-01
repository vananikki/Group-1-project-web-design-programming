import { apiFetch, readResponse } from "./api.js?v=20261029a";
import { typesetMath } from "./latex.js?v=20261101b";

const query = new URLSearchParams(window.location.search);
const problemId = query.get("problem_id");
const source = query.get("source");
const statement = document.getElementById("problem-statement");
const form = document.getElementById("solution-form");
const pageMessage = document.getElementById("page-message");
let languagesPromise;

function showMessage(element, text, isError = false) {
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

function renderStatement(problem) {
    document.getElementById("statement-title").textContent = problem.problem_name;
    for (const [field, sectionId, contentId] of [
        ["description", "statement-description-section", "statement-description"],
        ["input_description", "statement-input-section", "statement-input"],
        ["output_description", "statement-output-section", "statement-output"],
        ["data_constraints", "statement-constraints-section", "statement-constraints"],
    ]) {
        const content = String(problem[field] ?? "");
        document.getElementById(contentId).textContent = content;
        document.getElementById(sectionId).hidden = !content.trim();
    }

    const limits = [];
    if (problem.time_limit) limits.push(`Thời gian: ${problem.time_limit} giây`);
    if (problem.memory_limit) limits.push(`Bộ nhớ: ${problem.memory_limit} MB`);
    document.getElementById("statement-limits").textContent = limits.join(" · ");
    document.getElementById("statement-limits-section").hidden = !limits.length;
    statement.hidden = false;
}

async function loadLanguages() {
    languagesPromise ??= requestJson("/student/languages");
    const languages = await languagesPromise;
    const selector = document.getElementById("solution-language");
    selector.replaceChildren();
    for (const language of languages) {
        const option = document.createElement("option");
        option.value = String(language.language_id);
        option.textContent = language.name;
        selector.append(option);
    }
    if (!languages.length) {
        throw new Error("Chưa có ngôn ngữ chấm bài. Hãy đồng bộ danh sách Judge0 languages trước.");
    }
}

async function initialize() {
    if (!problemId || !/^[1-9]\d*$/.test(problemId)) {
        showMessage(pageMessage, "Đường dẫn bài tập không hợp lệ.", true);
        return;
    }
    if (source !== "public" && source !== "owner") {
        showMessage(pageMessage, "Thiếu thông tin phạm vi truy cập bài tập.", true);
        return;
    }

    try {
        const accountResponse = await apiFetch("/auth/me");
        if (!accountResponse.ok) {
            window.location.replace("login.html");
            return;
        }
        const account = await accountResponse.json();
        if (source === "owner" && account.role !== "ADMIN" && account.role !== "SUPER_ADMIN") {
            throw new Error("Bạn không có quyền xem bài tập này.");
        }
        const problemPath = source === "public"
            ? `/student/problems/${encodeURIComponent(problemId)}`
            : `/admin/judge/problems/${encodeURIComponent(problemId)}`;
        const problem = await requestJson(problemPath);
        renderStatement(problem);
        await typesetMath(statement);
        document.getElementById("solution-heading").textContent = problem.problem_name;

        const historyLink = document.getElementById("problem-history-link");
        historyLink.href = `submissions.html?problem_id=${encodeURIComponent(problemId)}`;
        historyLink.hidden = false;
        const isPrivate = problem.access_modifier === "private";
        const submitButton = form.querySelector('[type="submit"]');
        if (isPrivate) {
            document.getElementById("solution-language").hidden = true;
            document.getElementById("solution-language").parentElement.hidden = true;
            form.elements.source_code.disabled = true;
            form.elements.source_code.placeholder = "Bài private cần được nộp từ trang lớp.";
            submitButton.hidden = true;
            showMessage(
                document.getElementById("submission-result"),
                "Bài tập private chỉ có thể nộp trong lớp được giao.",
            );
            return;
        }

        await loadLanguages();
        document.getElementById("solution-language").disabled = false;
        form.elements.source_code.disabled = false;
        submitButton.disabled = false;
    } catch (error) {
        console.error(error);
        showMessage(
            pageMessage,
            error instanceof Error ? error.message : "Không thể tải bài tập.",
            true,
        );
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitButton = form.querySelector('[type="submit"]');
    const result = document.getElementById("submission-result");
    const values = new FormData(form);
    submitButton.disabled = true;
    showMessage(result, "Đang gửi lời giải tới hệ thống chấm bài...");
    try {
        const submission = await requestJson(
            `/student/problems/${encodeURIComponent(problemId)}/submissions`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    language_id: Number(values.get("language_id")),
                    source_code: values.get("source_code"),
                }),
            },
        );
        showMessage(
            result,
            `${submission.status} · ${submission.score} điểm · ` +
                `${submission.passed_testcases}/${submission.total_testcases} test case · ` +
                `tổng ${submission.runtime_ms == null ? "—" : `${submission.runtime_ms} ms`} · ` +
                `bộ nhớ đỉnh ${submission.memory_kb == null ? "—" : `${submission.memory_kb} KB`}`,
            submission.status !== "Accepted",
        );
    } catch (error) {
        showMessage(
            result,
            error instanceof Error ? error.message : "Không thể chấm lời giải.",
            true,
        );
    } finally {
        submitButton.disabled = false;
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
        showMessage(pageMessage, error instanceof Error ? error.message : "Không thể đăng xuất.", true);
    }
});

initialize();
