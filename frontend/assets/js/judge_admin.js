import { apiFetch, readResponse } from "./api.js?v=20261021b";

const problemForm = document.getElementById("problem-form");
const problemEditForm = document.getElementById("problem-edit-form");
const classForm = document.getElementById("class-form");
const contestForm = document.getElementById("contest-form");
const classProblemForm = document.getElementById("class-problem-form");
const classContestForm = document.getElementById("class-contest-form");
const classStudentForm = document.getElementById("class-student-form");
const contestProblemForm = document.getElementById("contest-problem-form");
const classDetailForm = document.getElementById("class-detail-form");
const contestDetailForm = document.getElementById("contest-detail-form");

const messages = {
    problem: document.getElementById("problem-message"),
    problemEdit: document.getElementById("problem-edit-message"),
    class: document.getElementById("class-message"),
    contest: document.getElementById("contest-message"),
    classProblem: document.getElementById("class-problem-message"),
    classContest: document.getElementById("class-contest-message"),
    classStudent: document.getElementById("class-student-message"),
    contestProblem: document.getElementById("contest-problem-message"),
    classDetail: document.getElementById("class-detail-message"),
    contestDetail: document.getElementById("contest-detail-message"),
};

const lists = {
    problem: document.getElementById("problem-list"),
    class: document.getElementById("class-list"),
    contest: document.getElementById("contest-list"),
};

async function ensureAdminAccess() {
    const response = await apiFetch("/auth/me");
    if (!response.ok) {
        window.location.replace("login.html");
        return false;
    }
    const account = await response.json();
    if (account.role !== "ADMIN" && account.role !== "SUPER_ADMIN") {
        window.location.replace("index.html");
        return false;
    }
    return true;
}

function setMessage(key, text, isError = false) {
    messages[key].textContent = text;
    messages[key].style.color = isError ? "#b42318" : "#1d7a5d";
}

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;",
    })[character]);
}

function addTestcaseRow(editor) {
    const row = document.createElement("div");
    row.className = "testcase-row";

    for (const [name, labelText] of [
        ["input_data", "Input"],
        ["expected_output", "Expected output"],
    ]) {
        const label = document.createElement("label");
        label.textContent = labelText;
        const textarea = document.createElement("textarea");
        textarea.name = name;
        textarea.rows = 3;
        label.appendChild(textarea);
        row.appendChild(label);
    }

    const pointsLabel = document.createElement("label");
    pointsLabel.textContent = "Điểm";
    const pointsInput = document.createElement("input");
    pointsInput.name = "point";
    pointsInput.type = "number";
    pointsInput.min = "1";
    pointsInput.value = "100";
    pointsLabel.appendChild(pointsInput);
    row.appendChild(pointsLabel);

    const removeButton = document.createElement("button");
    removeButton.className = "secondary remove-testcase";
    removeButton.type = "button";
    removeButton.textContent = "Xóa test case";
    row.appendChild(removeButton);
    editor.appendChild(row);
}

function readTestcases(form) {
    return [...form.querySelectorAll(".testcase-row")].map((row) => ({
        input_data: row.querySelector('[name="input_data"]').value,
        expected_output: row.querySelector('[name="expected_output"]').value,
        point: Number(row.querySelector('[name="point"]').value),
    }));
}

function renderList(element, items, formatter) {
    element.innerHTML = "";
    if (!items.length) {
        const item = document.createElement("li");
        item.textContent = "Chưa có dữ liệu";
        element.appendChild(item);
        return;
    }

    items.forEach((item) => {
        const row = document.createElement("li");
        row.innerHTML = formatter(item);
        element.appendChild(row);
    });
}

async function loadProblems() {
    const response = await apiFetch("/admin/judge/problems");
    const data = await readResponse(response);
    if (!response.ok) {
        setMessage("problem", data.detail || "Không thể tải problem", true);
        return;
    }
    renderList(lists.problem, data, (problem) => `<strong>#${escapeHtml(problem.problem_id)}</strong> ${escapeHtml(problem.problem_name)} <span>(${escapeHtml(problem.access_modifier)})</span>`);
}

async function loadClasses() {
    const response = await apiFetch("/admin/judge/academic-classes");
    const data = await readResponse(response);
    if (!response.ok) {
        setMessage("class", data.detail || "Không thể tải lớp học", true);
        return;
    }
    renderList(lists.class, data, (item) => `<strong>#${escapeHtml(item.class_id)}</strong> ${escapeHtml(item.class_name)}`);
}

async function loadContests() {
    const response = await apiFetch("/admin/judge/contests");
    const data = await readResponse(response);
    if (!response.ok) {
        setMessage("contest", data.detail || "Không thể tải contest", true);
        return;
    }
    renderList(lists.contest, data, (item) => `<strong>#${escapeHtml(item.contest_id)}</strong> ${escapeHtml(item.contest_name)} <span>(${escapeHtml(item.status)})</span>`);
}

problemForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(problemForm);
    const body = Object.fromEntries(formData.entries());
    delete body.input_data;
    delete body.expected_output;
    delete body.point;
    body.testcases = readTestcases(problemForm);

    try {
        const response = await apiFetch("/admin/judge/problems", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await readResponse(response);
        if (!response.ok) {
            setMessage("problem", data.detail || "Không thể tạo problem", true);
            return;
        }
        setMessage("problem", `Đã tạo problem #${data.problem_id}: ${data.problem_name}`);
        problemForm.reset();
        await loadProblems();
    } catch (error) {
        console.error(error);
        setMessage("problem", "Không thể kết nối đến server", true);
    }
});

problemEditForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(problemEditForm);
    const id = Number(formData.get("problem_id"));
    const body = Object.fromEntries(formData.entries());
    delete body.problem_id;
    delete body.input_data;
    delete body.expected_output;
    delete body.point;
    const testcases = readTestcases(problemEditForm);
    if (testcases.length) {
        body.testcases = testcases;
    }

    try {
        const response = await apiFetch(`/admin/judge/problems/${id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await readResponse(response);
        if (!response.ok) {
            setMessage("problemEdit", data.detail || "Không thể cập nhật problem", true);
            return;
        }
        setMessage("problemEdit", `Đã cập nhật problem #${data.problem_id}: ${data.problem_name}`);
        await loadProblems();
    } catch (error) {
        console.error(error);
        setMessage("problemEdit", "Không thể kết nối đến server", true);
    }
});

classForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(classForm);
    const body = Object.fromEntries(formData.entries());

    try {
        const response = await apiFetch("/admin/judge/academic-classes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await readResponse(response);
        if (!response.ok) {
            setMessage("class", data.detail || "Không thể tạo lớp học", true);
            return;
        }
        setMessage("class", `Đã tạo lớp #${data.class_id}: ${data.class_name}`);
        classForm.reset();
        await loadClasses();
    } catch (error) {
        console.error(error);
        setMessage("class", "Không thể kết nối đến server", true);
    }
});

contestForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(contestForm);
    const body = Object.fromEntries(formData.entries());
    body.start_time = new Date(body.start_time).toISOString();
    body.end_time = new Date(body.end_time).toISOString();

    try {
        const response = await apiFetch("/admin/judge/contests", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await readResponse(response);
        if (!response.ok) {
            setMessage("contest", data.detail || "Không thể tạo contest", true);
            return;
        }
        setMessage("contest", `Đã tạo contest #${data.contest_id}: ${data.contest_name}`);
        contestForm.reset();
        await loadContests();
    } catch (error) {
        console.error(error);
        setMessage("contest", "Không thể kết nối đến server", true);
    }
});

classProblemForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(classProblemForm);
    const body = Object.fromEntries(formData.entries());
    body.is_required = formData.get("is_required") === "on";

    try {
        const response = await apiFetch(`/admin/judge/academic-classes/${body.class_id}/problems`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ problem_id: body.problem_id, is_required: body.is_required }),
        });
        const data = await readResponse(response);
        if (!response.ok) {
            setMessage("classProblem", data.detail || "Không thể gắn bài vào lớp", true);
            return;
        }
        setMessage("classProblem", `Đã gắn bài #${data.problem_id} vào lớp #${data.class_id}`);
        classProblemForm.reset();
    } catch (error) {
        console.error(error);
        setMessage("classProblem", "Không thể kết nối đến server", true);
    }
});

classContestForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(classContestForm);
    const body = Object.fromEntries(formData.entries());

    try {
        const response = await apiFetch(`/admin/judge/academic-classes/${body.class_id}/contests`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ contest_id: body.contest_id }),
        });
        const data = await readResponse(response);
        if (!response.ok) {
            setMessage("classContest", data.detail || "Không thể gắn contest vào lớp", true);
            return;
        }
        setMessage("classContest", `Đã gắn contest #${data.contest_id} vào lớp #${data.class_id}`);
        classContestForm.reset();
    } catch (error) {
        console.error(error);
        setMessage("classContest", "Không thể kết nối đến server", true);
    }
});

classStudentForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(classStudentForm);
    const classId = Number(formData.get("class_id"));
    const accountId = Number(formData.get("account_id"));

    try {
        const response = await apiFetch(`/admin/judge/academic-classes/${classId}/students`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ account_id: accountId }),
        });
        const data = await readResponse(response);
        if (!response.ok) {
            setMessage("classStudent", data.detail || "Không thể thêm học viên vào lớp", true);
            return;
        }
        setMessage("classStudent", `Đã thêm ${data.account_name} vào lớp #${data.class_id}`);
        classStudentForm.reset();
        classDetailForm.elements.class_id.value = String(classId);
        classDetailForm.requestSubmit();
    } catch (error) {
        console.error(error);
        setMessage("classStudent", "Không thể kết nối đến server", true);
    }
});

contestProblemForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(contestProblemForm);
    const body = Object.fromEntries(formData.entries());

    try {
        const response = await apiFetch(`/admin/judge/contests/${body.contest_id}/problems`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ problem_id: body.problem_id, problem_order: body.problem_order || null }),
        });
        const data = await readResponse(response);
        if (!response.ok) {
            setMessage("contestProblem", data.detail || "Không thể gắn bài vào contest", true);
            return;
        }
        setMessage("contestProblem", `Đã gắn bài #${data.problem_id} vào contest #${data.contest_id}`);
        contestProblemForm.reset();
    } catch (error) {
        console.error(error);
        setMessage("contestProblem", "Không thể kết nối đến server", true);
    }
});

classDetailForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(classDetailForm);
    const classId = Number(formData.get("class_id"));
    const output = document.getElementById("class-detail-output");

    try {
        const response = await apiFetch(`/admin/judge/academic-classes/${classId}`);
        const data = await readResponse(response);
        if (!response.ok) {
            setMessage("classDetail", data.detail || "Không thể tải chi tiết lớp học", true);
            output.innerHTML = "";
            return;
        }

        const problemsHtml = (data.problems || []).map((problem) => `
            <li>
                <strong>#${escapeHtml(problem.problem_id)}</strong> ${escapeHtml(problem.problem_name)}
                <span>(${escapeHtml(problem.access_modifier)})</span>
                ${problem.is_required ? "<em>Bắt buộc</em>" : "<em>Không bắt buộc</em>"}
            </li>
        `).join("");

        const contestsHtml = (data.contests || []).map((contest) => `
            <li>
                <strong>#${escapeHtml(contest.contest_id)}</strong> ${escapeHtml(contest.contest_name)}
                <span>(${escapeHtml(contest.status)})</span>
            </li>
        `).join("");

        const studentsHtml = (data.students || []).map((student) => `
            <li>
                <strong>#${escapeHtml(student.account_id)}</strong> ${escapeHtml(student.account_name)}
                <span>${escapeHtml(student.account_email)}</span>
                <button class="secondary remove-class-student" type="button" data-account-id="${escapeHtml(student.account_id)}">Xóa khỏi lớp</button>
            </li>
        `).join("");

        output.innerHTML = `
            <div>
                <strong>${escapeHtml(data.class_name)}</strong>
                <p>Tổng số học viên: ${(data.students || []).length}</p>
                <p>Tổng số bài: ${(data.problems || []).length}</p>
                <p>Tổng số contest: ${(data.contests || []).length}</p>
                <h4>Học viên</h4>
                <ul>${studentsHtml || "<li>Chưa có học viên</li>"}</ul>
                <h4>Exercises</h4>
                <ul>${problemsHtml || "<li>Chưa có bài tập</li>"}</ul>
                <h4>Contests</h4>
                <ul>${contestsHtml || "<li>Chưa có contest</li>"}</ul>
            </div>
        `;
        setMessage("classDetail", `Đã tải chi tiết lớp #${data.class_id}`);
    } catch (error) {
        console.error(error);
        setMessage("classDetail", "Không thể kết nối đến server", true);
    }
});

contestDetailForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(contestDetailForm);
    const contestId = Number(formData.get("contest_id"));
    const output = document.getElementById("contest-detail-output");

    try {
        const response = await apiFetch(`/admin/judge/contests/${contestId}`);
        const data = await readResponse(response);
        if (!response.ok) {
            setMessage("contestDetail", data.detail || "Không thể tải chi tiết contest", true);
            output.innerHTML = "";
            return;
        }

        const problemList = (data.problems || []).map((problem) => `
            <li>
                <strong>#${escapeHtml(problem.problem_id)}</strong> ${escapeHtml(problem.problem_name)}
                <span>(Vị trí: ${escapeHtml(problem.problem_order ?? "Chưa xếp")})</span>
            </li>
        `).join("");

        output.innerHTML = `
            <div>
                <strong>${escapeHtml(data.contest_name)}</strong>
                <p>Trạng thái: ${escapeHtml(data.status)}</p>
                <p>Thời gian: ${escapeHtml(data.start_time)} → ${escapeHtml(data.end_time)}</p>
                <p>Số bài: ${escapeHtml(data.problem_count)}</p>
                <h4>Problems</h4>
                <ul>${problemList || "<li>Chưa có bài</li>"}</ul>
            </div>
        `;
        setMessage("contestDetail", `Đã tải chi tiết contest #${data.contest_id}`);
    } catch (error) {
        console.error(error);
        setMessage("contestDetail", "Không thể kết nối đến server", true);
    }
});

document.getElementById("class-detail-output").addEventListener("click", async (event) => {
    const button = event.target.closest(".remove-class-student");
    if (!button) {
        return;
    }

    const classId = Number(classDetailForm.elements.class_id.value);
    const accountId = Number(button.dataset.accountId);
    try {
        const response = await apiFetch(
            `/admin/judge/academic-classes/${classId}/students/${accountId}`,
            { method: "DELETE" },
        );
        const data = await readResponse(response);
        if (!response.ok) {
            setMessage("classDetail", data.detail || "Không thể xóa học viên khỏi lớp", true);
            return;
        }
        classDetailForm.requestSubmit();
    } catch (error) {
        console.error(error);
        setMessage("classDetail", "Không thể kết nối đến server", true);
    }
});

document.querySelectorAll(".add-testcase").forEach((button) => {
    button.addEventListener("click", () => {
        addTestcaseRow(document.getElementById(button.dataset.target));
    });
});

document.querySelectorAll(".testcase-editor > div").forEach((editor) => {
    editor.addEventListener("click", (event) => {
        if (event.target.closest(".remove-testcase")) {
            event.target.closest(".testcase-row").remove();
        }
    });
});

addTestcaseRow(document.getElementById("problem-testcases"));

document.getElementById("logout-button").addEventListener("click", async () => {
    const response = await apiFetch("/auth/logout", { method: "POST" });
    if (response.ok) {
        window.location.replace("login.html");
    }
});

async function init() {
    if (!(await ensureAdminAccess())) {
        return;
    }
    await Promise.all([loadProblems(), loadClasses(), loadContests()]);
}

init();
