import { apiFetch, readResponse } from "./api.js?v=20261021b";

const pageMessage = document.getElementById("page-message");
const adminHome = document.getElementById("admin-home");
const studentHome = document.getElementById("student-home");
const workspace = document.getElementById("class-workspace");
const adminTools = document.getElementById("admin-class-tools");
const createClassForm = document.getElementById("create-class-form");
const createProblemForm = document.getElementById("create-problem-form");
const problemMessage = document.getElementById("create-problem-message");
let currentAccount;
let activeClassId;
let activeProblemId;
let activeContestId;
let languagesPromise;

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

function addClassTestcase() {
    const container = document.getElementById("class-testcase-list");
    if (container.children.length >= 100) {
        document.getElementById("add-class-testcase").disabled = true;
        return;
    }
    const row = document.createElement("div");
    row.className = "testcase-row";
    row.innerHTML = `<div class="testcase-row-heading"><strong>Test case ${container.children.length + 1}</strong>
        <button class="secondary" type="button" data-action="remove-testcase">Xóa</button></div>
        <label>Input<textarea name="input_data" rows="3"></textarea></label>
        <label>Output mong đợi<textarea name="expected_output" rows="3"></textarea></label>
        <label>Điểm<input name="point" type="number" min="1" max="100" required></label>`;
    container.appendChild(row);
    const rows = [...container.querySelectorAll(".testcase-row")];
    const basePoints = Math.floor(100 / rows.length);
    const remainder = 100 % rows.length;
    rows.forEach((item, index) => {
        item.querySelector('[name="point"]').value = String(basePoints + (index < remainder ? 1 : 0));
        item.querySelector("strong").textContent = `Test case ${index + 1}`;
    });
    document.getElementById("add-class-testcase").disabled = rows.length >= 100;
}

function resetClassTestcases() {
    document.getElementById("class-testcase-list").replaceChildren();
    addClassTestcase();
}

async function requestJson(path, options) {
    const response = await apiFetch(path, options);
    const data = await readResponse(response);
    if (!response.ok) {
        throw new Error(data.detail || `Yêu cầu thất bại (${response.status})`);
    }
    return data;
}

function classCard(item, { joined = false, managed = false } = {}) {
    const actions = managed
        ? item.is_claimable
            ? `<button type="button" data-action="claim-class" data-class-id="${item.class_id}">Nhận quyền quản lý</button>`
            : `<button type="button" data-action="open-admin-class" data-class-id="${item.class_id}">Mở lớp</button>
               <button type="button" class="secondary" data-action="create-problem" data-class-id="${item.class_id}">Tạo bài tập</button>`
        : joined
            ? `<button type="button" data-action="open-student-class" data-class-id="${item.class_id}">Vào lớp</button>`
            : item.membership_status === "pending"
                ? `<span class="status-pill pending">Đang chờ duyệt</span>`
                : item.membership_status === "rejected"
                    ? `<button type="button" class="secondary" data-action="request-join" data-class-id="${item.class_id}">Gửi lại yêu cầu</button>`
                    : item.membership_status === "joined"
                        ? `<span class="status-pill">Đã tham gia</span>`
                        : `<button type="button" data-action="request-join" data-class-id="${item.class_id}">Xin tham gia</button>`;
    return `<article class="class-card">
        <div class="class-card-icon" aria-hidden="true">▤</div>
        <div class="class-card-main">
            <p class="class-card-kicker">LỚP HỌC ${item.class_id ? `· #${item.class_id}` : ""}</p>
            <h3>${escapeHtml(item.class_name)}</h3>
            <div class="class-card-actions">${actions}</div>
        </div>
    </article>`;
}

function renderCards(element, items, options = {}) {
    if (!items.length) {
        element.innerHTML = `<div class="empty-state"><span aria-hidden="true">✦</span><p>${escapeHtml(options.emptyText || "Chưa có lớp học.")}</p></div>`;
        return;
    }
    element.innerHTML = items.map((item) => classCard(item, options)).join("");
}

async function loadAdminClasses() {
    const classes = await requestJson("/admin/judge/academic-classes");
    renderCards(document.getElementById("managed-class-list"), classes, {
        managed: true,
        emptyText: "Chưa có lớp nào. Tạo lớp đầu tiên để bắt đầu.",
    });
}

async function loadStudentClasses() {
    const [joined, available] = await Promise.all([
        requestJson("/student/classes"),
        requestJson("/student/available-classes"),
    ]);
    renderCards(document.getElementById("my-class-list"), joined, {
        joined: true,
        emptyText: "Bạn chưa tham gia lớp nào.",
    });
    renderCards(document.getElementById("available-class-list"), available, {
        emptyText: "Hiện chưa có lớp nào để tham gia.",
    });
}

function showHome() {
    workspace.hidden = true;
    adminHome.hidden = currentAccount.role === "USER";
    studentHome.hidden = currentAccount.role !== "USER";
    document.getElementById("create-problem-form").hidden = true;
}

async function openClass(classId, isStudent) {
    activeClassId = Number(classId);
    activeContestId = null;
    pageMessage.textContent = "";
    const data = await requestJson(
        isStudent
            ? `/student/classes/${activeClassId}`
            : `/admin/judge/academic-classes/${activeClassId}`,
    );
    adminHome.hidden = true;
    studentHome.hidden = true;
    workspace.hidden = false;
    document.getElementById("workspace-title").textContent = data.class_name;
    document.getElementById("workspace-meta").textContent =
        `Lớp #${data.class_id} · ${(data.problems || []).length} bài tập · ${(data.contests || []).length} cuộc thi`;

    const canManage = !isStudent;
    const canManagePermissions = canManage && (
        currentAccount.role === "SUPER_ADMIN" || data.is_owner
    );
    document.getElementById("create-problem-toggle").hidden = !canManage;
    adminTools.hidden = !canManage;
    document.getElementById("manager-tools").hidden = !canManagePermissions;
    document.getElementById("member-heading").hidden = !canManage;
    document.getElementById("member-list").hidden = !canManage;
    document.getElementById("member-list").innerHTML = canManage
        ? (data.students || []).map((member) => `<div class="entity-row">
            <span><strong>${escapeHtml(member.account_name)}</strong><small>${escapeHtml(member.account_email)}</small></span>
            <button class="secondary" type="button" data-action="remove-member" data-account-id="${member.account_id}">Gỡ khỏi lớp</button>
        </div>`).join("") || `<p class="field-hint">Chưa có thành viên.</p>`
        : "";

    document.getElementById("class-problem-list").innerHTML = (data.problems || []).map((problem) => `
        <article class="problem-card">
            <div>
                <p class="class-card-kicker">BÀI TẬP · #${escapeHtml(problem.problem_id)}</p>
                <h4>${escapeHtml(problem.problem_name)}</h4>
                ${problem.description ? `<p>${escapeHtml(problem.description)}</p>` : ""}
                ${problem.is_required ? `<span class="status-pill">Bắt buộc</span>` : ""}
            </div>
            ${problem.description || problem.input_description || problem.output_description ? `
                <details class="problem-specification">
                    <summary>Xem đề bài</summary>
                    ${problem.input_description ? `<h5>Input</h5><p>${escapeHtml(problem.input_description)}</p>` : ""}
                    ${problem.output_description ? `<h5>Output</h5><p>${escapeHtml(problem.output_description)}</p>` : ""}
                </details>` : ""}
            ${isStudent ? `<button type="button" data-action="solve-problem" data-problem-id="${problem.problem_id}">Nộp lời giải</button>` : ""}
        </article>`).join("") || `<div class="empty-state"><p>Lớp chưa có bài tập.</p></div>`;
    document.getElementById("class-contest-list").innerHTML = (data.contests || []).map((contest) => `
        <article class="problem-card">
            <div><p class="class-card-kicker">CUỘC THI · ${escapeHtml(contest.status)}</p><h4>${escapeHtml(contest.contest_name)}</h4></div>
            <span>${new Date(contest.start_time).toLocaleString()} – ${new Date(contest.end_time).toLocaleString()}</span>
            ${isStudent ? `<button type="button" data-action="open-contest" data-contest-id="${contest.contest_id}">Mở cuộc thi</button>` : ""}
        </article>`).join("") || `<div class="empty-state"><p>Chưa có cuộc thi nào.</p></div>`;

    if (canManage) {
        const contestProblemSelect = document.getElementById("contest-problem-select");
        contestProblemSelect.innerHTML = (data.problems || []).map((problem) =>
            `<option value="${problem.problem_id}">${escapeHtml(problem.problem_name)}</option>`
        ).join("");
        document.getElementById("create-contest-form").querySelector('[type="submit"]').disabled =
            !data.problems?.length;
        document.getElementById("create-contest-message").textContent = data.problems?.length
            ? ""
            : "Thêm ít nhất một bài tập vào lớp trước khi tạo cuộc thi.";
        await loadJoinRequests(activeClassId);
        await loadManagers(activeClassId, canManagePermissions);
    } else {
        document.getElementById("submission-history").hidden = false;
        await loadSubmissionHistory(activeClassId);
    }
}

async function loadJoinRequests(classId) {
    const requests = await requestJson(`/admin/judge/academic-classes/${classId}/join-requests`);
    const list = document.getElementById("join-request-list");
    list.innerHTML = requests.map((item) => `<div class="entity-row">
        <span><strong>${escapeHtml(item.account_name)}</strong><small>${escapeHtml(item.account_email)}</small></span>
        <span class="button-row">
            <button type="button" data-action="decide-request" data-request-id="${item.join_request_id}" data-status="approved">Duyệt</button>
            <button class="secondary" type="button" data-action="decide-request" data-request-id="${item.join_request_id}" data-status="rejected">Từ chối</button>
        </span>
    </div>`).join("") || `<p class="field-hint">Không có yêu cầu nào đang chờ.</p>`;
}

async function loadManagers(classId, canManagePermissions) {
    const managers = await requestJson(`/admin/judge/academic-classes/${classId}/managers`);
    const list = document.getElementById("manager-list");
    list.innerHTML = managers.map((manager) => `<div class="entity-row">
        <span><strong>${escapeHtml(manager.account_name)}</strong><small>${escapeHtml(manager.account_email)} · ${manager.is_owner ? "Chủ lớp" : "Quản trị viên"}</small></span>
        ${canManagePermissions && !manager.is_owner ? `<button class="secondary" type="button" data-action="remove-manager" data-account-id="${manager.account_id}">Thu hồi quyền</button>` : ""}
    </div>`).join("");
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

async function loadSubmissionHistory(classId) {
    const history = await requestJson(`/student/classes/${classId}/submissions`);
    const list = document.getElementById("submission-history-list");
    list.innerHTML = history.map((submission) => `<div class="entity-row">
        <span>
            <strong>${escapeHtml(submission.problem_name)}</strong>
            <small>${submission.contest_name ? `${escapeHtml(submission.contest_name)} · ` : ""}${new Date(submission.submitted_at).toLocaleString()}</small>
        </span>
        <span class="submission-summary">
            <span class="status-pill ${submission.status === "Accepted" ? "" : "pending"}">${escapeHtml(submission.status)}</span>
            <strong>${escapeHtml(submission.score ?? 0)} điểm</strong>
        </span>
    </div>`).join("") || `<p class="field-hint">Bạn chưa nộp bài trong lớp này.</p>`;
}

async function openContest(contestId) {
    const [contest, standings] = await Promise.all([
        requestJson(`/student/classes/${activeClassId}/contests/${contestId}`),
        requestJson(`/student/classes/${activeClassId}/contests/${contestId}/standings`),
    ]);
    activeContestId = Number(contestId);
    document.getElementById("contest-heading").textContent = contest.contest_name;
    document.getElementById("contest-description").textContent = contest.description || "";
    document.getElementById("contest-status").textContent =
        contest.status === "active" ? "ĐANG DIỄN RA" : contest.status === "upcoming" ? "SẮP DIỄN RA" : "ĐÃ KẾT THÚC";
    document.getElementById("contest-time").textContent =
        `${new Date(contest.start_time).toLocaleString()} – ${new Date(contest.end_time).toLocaleString()}`;
    document.getElementById("contest-problem-list").innerHTML = contest.problems.map((problem) => `
        <article class="problem-card">
            <div>
                <p class="class-card-kicker">BÀI ${escapeHtml(problem.problem_order ?? "—")} · #${escapeHtml(problem.problem_id)}</p>
                <h4>${escapeHtml(problem.problem_name)} ${problem.is_solved ? "✓" : ""}</h4>
                ${problem.description ? `<p>${escapeHtml(problem.description)}</p>` : ""}
                <details class="problem-specification">
                    <summary>Xem đề bài và giới hạn</summary>
                    ${problem.input_description ? `<h5>Input</h5><p>${escapeHtml(problem.input_description)}</p>` : ""}
                    ${problem.output_description ? `<h5>Output</h5><p>${escapeHtml(problem.output_description)}</p>` : ""}
                    <p>Thời gian: ${escapeHtml(problem.time_limit)} giây · Bộ nhớ: ${escapeHtml(problem.memory_limit)} MB</p>
                </details>
            </div>
            ${contest.can_submit ? `<button type="button" data-action="solve-contest-problem" data-problem-id="${problem.problem_id}">Nộp bài</button>` : ""}
        </article>`).join("") || `<div class="empty-state"><p>Cuộc thi chưa có bài thi.</p></div>`;
    document.getElementById("contest-standings").innerHTML = standings.standings.map((participant) => `
        <div class="entity-row ${participant.is_current_user ? "current-participant" : ""}">
            <span><strong>#${participant.rank} · ${escapeHtml(participant.account_name)}</strong><small>${participant.solved} bài giải đúng · ${participant.penalty} lượt sai</small></span>
            <strong>${participant.score} điểm</strong>
        </div>`).join("") || `<p class="field-hint">Chưa có bài nộp nào.</p>`;
    document.getElementById("contest-dialog").showModal();
}

async function initialize() {
    try {
        const response = await apiFetch("/auth/me");
        if (!response.ok) {
            window.location.replace("login.html");
            return;
        }
        currentAccount = await response.json();
        if (currentAccount.role === "USER") {
            document.getElementById("page-heading").textContent = "Lớp học của tôi";
            document.getElementById("page-subtitle").textContent =
                "Xin tham gia lớp học để mở bài tập và cuộc thi được giao.";
            studentHome.hidden = false;
            await loadStudentClasses();
        } else {
            document.getElementById("advanced-admin-link").hidden = false;
            document.getElementById("page-heading").textContent = "Không gian quản lý lớp";
            document.getElementById("page-subtitle").textContent =
                "Tổ chức lớp học, quản lý quyền truy cập và chuẩn bị bài tập cho học viên.";
            adminHome.hidden = false;
            await loadAdminClasses();
        }
    } catch (error) {
        console.error(error);
        setMessage(pageMessage, error.message || "Không thể tải lớp học.", true);
    }
}

document.getElementById("show-create-class").addEventListener("click", () => {
    createClassForm.hidden = false;
    document.getElementById("new-class-name").focus();
});

document.getElementById("cancel-create-class").addEventListener("click", () => {
    createClassForm.reset();
    createClassForm.hidden = true;
});

createClassForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = createClassForm.querySelector('[type="submit"]');
    button.disabled = true;
    try {
        await requestJson("/admin/judge/academic-classes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ class_name: new FormData(createClassForm).get("class_name") }),
        });
        createClassForm.reset();
        createClassForm.hidden = true;
        setMessage(document.getElementById("create-class-message"), "Đã tạo lớp mới. Bạn đang là chủ lớp.");
        await loadAdminClasses();
    } catch (error) {
        setMessage(document.getElementById("create-class-message"), error.message, true);
    } finally {
        button.disabled = false;
    }
});

document.body.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    button.disabled = true;
    try {
        const classId = button.dataset.classId || activeClassId;
        switch (button.dataset.action) {
            case "remove-testcase":
                button.closest(".testcase-row").remove();
                [...document.querySelectorAll("#class-testcase-list .testcase-row")].forEach((row, index) => {
                    row.querySelector("strong").textContent = `Test case ${index + 1}`;
                });
                if (!document.querySelector("#class-testcase-list .testcase-row")) {
                    addClassTestcase();
                } else {
                    const rows = [...document.querySelectorAll("#class-testcase-list .testcase-row")];
                    const basePoints = Math.floor(100 / rows.length);
                    const remainder = 100 % rows.length;
                    rows.forEach((row, index) => {
                        row.querySelector('[name="point"]').value =
                            String(basePoints + (index < remainder ? 1 : 0));
                    });
                    document.getElementById("add-class-testcase").disabled = false;
                }
                break;
            case "open-admin-class":
                await openClass(classId, false);
                break;
            case "claim-class":
                await requestJson(`/admin/judge/academic-classes/${classId}/claim`, { method: "POST" });
                setMessage(pageMessage, "Bạn đã trở thành chủ lớp.");
                await loadAdminClasses();
                break;
            case "create-problem":
                await openClass(classId, false);
                createProblemForm.hidden = false;
                createProblemForm.scrollIntoView({ behavior: "smooth", block: "start" });
                break;
            case "open-student-class":
                await openClass(classId, true);
                break;
            case "solve-problem":
                activeProblemId = Number(button.dataset.problemId);
                activeContestId = null;
                document.getElementById("solution-heading").textContent =
                    button.closest(".problem-card").querySelector("h4").textContent;
                document.getElementById("solution-form").elements.source_code.value = "";
                setMessage(document.getElementById("submission-result"), "");
                await loadLanguages();
                document.getElementById("solution-dialog").showModal();
                break;
            case "open-contest":
                await openContest(button.dataset.contestId);
                break;
            case "solve-contest-problem":
                activeProblemId = Number(button.dataset.problemId);
                document.getElementById("contest-dialog").close();
                document.getElementById("solution-heading").textContent =
                    button.closest(".problem-card").querySelector("h4").textContent.replace("✓", "").trim();
                document.getElementById("solution-form").elements.source_code.value = "";
                setMessage(document.getElementById("submission-result"), "");
                await loadLanguages();
                document.getElementById("solution-dialog").showModal();
                break;
            case "request-join":
                await requestJson(`/student/classes/${classId}/join-requests`, { method: "POST" });
                setMessage(pageMessage, "Đã gửi yêu cầu. Bạn có thể vào lớp sau khi chủ lớp duyệt.");
                await loadStudentClasses();
                break;
            case "decide-request":
                await requestJson(
                    `/admin/judge/academic-classes/${activeClassId}/join-requests/${button.dataset.requestId}`,
                    {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ status: button.dataset.status }),
                    },
                );
                await openClass(activeClassId, false);
                break;
            case "remove-member":
                await requestJson(
                    `/admin/judge/academic-classes/${activeClassId}/students/${button.dataset.accountId}`,
                    { method: "DELETE" },
                );
                await openClass(activeClassId, false);
                break;
            case "remove-manager":
                await requestJson(
                    `/admin/judge/academic-classes/${activeClassId}/managers/${button.dataset.accountId}`,
                    { method: "DELETE" },
                );
                await loadManagers(activeClassId, true);
                break;
        }
    } catch (error) {
        setMessage(pageMessage, error.message || "Thao tác không thành công.", true);
    } finally {
        button.disabled = false;
    }
});

document.getElementById("close-solution").addEventListener("click", () => {
    document.getElementById("solution-dialog").close();
});

document.getElementById("close-contest").addEventListener("click", () => {
    document.getElementById("contest-dialog").close();
    activeContestId = null;
});

document.getElementById("contest-dialog").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) {
        event.currentTarget.close();
        activeContestId = null;
    }
});

document.getElementById("solution-dialog").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) event.currentTarget.close();
});

document.getElementById("solution-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('[type="submit"]');
    const resultElement = document.getElementById("submission-result");
    button.disabled = true;
    setMessage(resultElement, "Đang gửi lời giải tới hệ thống chấm bài...");
    const values = new FormData(form);
    try {
        const result = await requestJson(
            `/student/classes/${activeClassId}/problems/${activeProblemId}/submissions`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    language_id: Number(values.get("language_id")),
                    source_code: values.get("source_code"),
                    ...(activeContestId ? { contest_id: activeContestId } : {}),
                }),
            },
        );
        setMessage(
            resultElement,
            `${result.status} · ${result.score} điểm · ${result.passed_testcases}/${result.total_testcases} test case`,
            result.status !== "Accepted",
        );
        await loadSubmissionHistory(activeClassId);
    } catch (error) {
        setMessage(resultElement, error.message || "Không thể chấm lời giải.", true);
    } finally {
        button.disabled = false;
    }
});

document.getElementById("back-to-classes").addEventListener("click", showHome);
document.getElementById("create-problem-toggle").addEventListener("click", () => {
    createProblemForm.hidden = !createProblemForm.hidden;
});
document.getElementById("cancel-create-problem").addEventListener("click", () => {
    createProblemForm.reset();
    resetClassTestcases();
    createProblemForm.hidden = true;
    setMessage(problemMessage, "");
});

createProblemForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = createProblemForm.querySelector('[type="submit"]');
    button.disabled = true;
    const values = new FormData(createProblemForm);
    const payload = {
        problem_name: values.get("problem_name"),
        description: values.get("description"),
        input_description: values.get("input_description"),
        output_description: values.get("output_description"),
        time_limit: Number(values.get("time_limit")),
        memory_limit: Number(values.get("memory_limit")),
        access_modifier: "private",
        testcases: [...createProblemForm.querySelectorAll("#class-testcase-list .testcase-row")].map((row) => ({
            input_data: row.querySelector('[name="input_data"]').value,
            expected_output: row.querySelector('[name="expected_output"]').value,
            point: Number(row.querySelector('[name="point"]').value),
        })),
    };
    try {
        const problem = await requestJson(`/admin/judge/academic-classes/${activeClassId}/problems/create`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        createProblemForm.reset();
        resetClassTestcases();
        createProblemForm.hidden = true;
        setMessage(problemMessage, `Đã tạo và thêm "${problem.problem_name}" vào lớp.`);
        await openClass(activeClassId, false);
    } catch (error) {
        setMessage(problemMessage, error.message, true);
    } finally {
        button.disabled = false;
    }
});

document.getElementById("create-contest-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('[type="submit"]');
    button.disabled = true;
    const values = new FormData(form);
    try {
        const start = new Date(values.get("start_time"));
        const end = new Date(values.get("end_time"));
        if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end <= start) {
            throw new Error("Thời điểm kết thúc phải sau thời điểm bắt đầu.");
        }
        const contest = await requestJson(
            `/admin/judge/academic-classes/${activeClassId}/contests/create`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    contest_name: values.get("contest_name"),
                    description: values.get("description"),
                    start_time: start.toISOString(),
                    end_time: end.toISOString(),
                    problem_ids: values.getAll("problem_ids").map(Number),
                }),
            },
        );
        form.reset();
        setMessage(
            document.getElementById("create-contest-message"),
            `Đã tạo cuộc thi "${contest.contest_name}" với ${contest.problem_count} bài.`,
        );
        await openClass(activeClassId, false);
    } catch (error) {
        setMessage(document.getElementById("create-contest-message"), error.message, true);
    } finally {
        button.disabled = false;
    }
});

document.getElementById("add-manager-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('[type="submit"]');
    button.disabled = true;
    try {
        await requestJson(`/admin/judge/academic-classes/${activeClassId}/managers`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ account_id: Number(new FormData(form).get("account_id")) }),
        });
        form.reset();
        setMessage(document.getElementById("manager-message"), "Đã cấp quyền quản lý lớp.");
        await loadManagers(activeClassId, true);
    } catch (error) {
        setMessage(document.getElementById("manager-message"), error.message, true);
    } finally {
        button.disabled = false;
    }
});

document.getElementById("logout-button").addEventListener("click", async () => {
    try {
        const response = await apiFetch("/auth/logout", { method: "POST" });
        if (response.ok) window.location.replace("login.html");
        else setMessage(pageMessage, `Không thể đăng xuất (${response.status}).`, true);
    } catch (error) {
        setMessage(pageMessage, error.message || "Không thể kết nối đến server.", true);
    }
});

initialize();
document.getElementById("add-class-testcase").addEventListener("click", addClassTestcase);
resetClassTestcases();
