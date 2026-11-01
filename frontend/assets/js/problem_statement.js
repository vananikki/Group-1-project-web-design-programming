import { apiFetch, readResponse } from "./api.js?v=20261029a";
import { typesetMath } from "./latex.js?v=20261101b";

const query = new URLSearchParams(window.location.search);
const problemId = query.get("problem_id");
const source = query.get("source");
const classId = query.get("class_id");
const statement = document.getElementById("problem-statement");
const pageMessage = document.getElementById("page-message");

function setMessage(text, isError = false) {
    pageMessage.textContent = text;
    pageMessage.classList.toggle("error", isError);
}

async function requestJson(path) {
    const response = await apiFetch(path);
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
    if (problem.time_limit) {
        limits.push(`Thời gian: ${problem.time_limit} giây`);
    }
    if (problem.memory_limit) {
        limits.push(`Bộ nhớ: ${problem.memory_limit} MB`);
    }
    document.getElementById("statement-limits").textContent = limits.join(" · ");
    document.getElementById("statement-limits-section").hidden = !limits.length;
    statement.hidden = false;
}

async function loadProblem(account) {
    if (!problemId || !/^\d+$/.test(problemId)) {
        throw new Error("Đường dẫn bài tập không hợp lệ.");
    }

    if (source === "public") {
        return requestJson(`/student/problems/${encodeURIComponent(problemId)}`);
    }
    if (source === "owner") {
        if (account.role !== "ADMIN" && account.role !== "SUPER_ADMIN") {
            throw new Error("Bạn không có quyền xem bài tập này.");
        }
        return requestJson(`/admin/judge/problems/${encodeURIComponent(problemId)}`);
    }
    if (source === "class" && classId && /^\d+$/.test(classId)) {
        const isAdmin = account.role === "ADMIN" || account.role === "SUPER_ADMIN";
        const classPath = isAdmin
            ? `/admin/judge/academic-classes/${encodeURIComponent(classId)}`
            : `/student/classes/${encodeURIComponent(classId)}`;
        const academicClass = await requestJson(classPath);
        const problem = academicClass.problems.find(
            (item) => String(item.problem_id) === problemId,
        );
        if (!problem) {
            throw new Error("Không tìm thấy bài tập trong lớp này.");
        }
        return problem;
    }

    throw new Error("Thiếu thông tin phạm vi truy cập bài tập.");
}

async function initialize() {
    document.getElementById("back-link").href =
        source === "class" ? "classroom.html" : "problems.html";
    try {
        const accountResponse = await apiFetch("/auth/me");
        if (!accountResponse.ok) {
            window.location.replace("login.html");
            return;
        }
        const account = await accountResponse.json();
        const problem = await loadProblem(account);
        renderStatement(problem);

        await typesetMath(statement);
    } catch (error) {
        console.error(error);
        setMessage(error.message || "Không thể tải đề bài.", true);
    }
}

document.getElementById("logout-button").addEventListener("click", async () => {
    try {
        const response = await apiFetch("/auth/logout", { method: "POST" });
        if (!response.ok) {
            throw new Error(`Không thể đăng xuất (${response.status}).`);
        }
        window.location.replace("login.html");
    } catch (error) {
        setMessage(error.message || "Không thể kết nối đến server.", true);
    }
});

initialize();
