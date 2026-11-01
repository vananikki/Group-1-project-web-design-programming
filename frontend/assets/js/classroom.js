import { apiFetch, readResponse } from "./api.js?v=20261029a";
import { typesetMath } from "./latex.js?v=20261101b";

const pageMessage = document.getElementById("page-message");
const adminHome = document.getElementById("admin-home");
const studentHome = document.getElementById("student-home");
const workspace = document.getElementById("class-workspace");
const adminTools = document.getElementById("admin-class-tools");
const createClassForm = document.getElementById("create-class-form");
let currentAccount;
let activeClassId;
let activeProblemId;
let activeContestId;
let languagesPromise;
let managerSearchTimer;
let managerSearchRequest = 0;

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

function renderProblemMath(element) {
    typesetMath(element).catch((error) => {
        console.error(error);
        setMessage(pageMessage, error.message || "Không thể hiển thị công thức LaTeX.", true);
    });
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
            : `<button type="button" data-action="open-admin-class" data-class-id="${item.class_id}">Mở lớp</button>`
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
}

async function openClass(classId, isStudent) {
    activeClassId = Number(classId);
    clearTimeout(managerSearchTimer);
    managerSearchRequest += 1;
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
    const canReviewJoinRequests = canManage && data.is_owner;
    adminTools.hidden = !canManage;
    document.getElementById("join-request-tools").hidden = !canReviewJoinRequests;
    document.getElementById("manager-tools").hidden = !canManagePermissions;
    document.getElementById("class-members-panel").hidden = !canManage;
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
                ${problem.description?.trim() ? `<p>${escapeHtml(problem.description)}</p>` : ""}
                ${problem.is_required ? `<span class="status-pill">Bắt buộc</span>` : ""}
            </div>
            <a class="button-link secondary" href="problem_statement.html?problem_id=${encodeURIComponent(problem.problem_id)}&source=class&class_id=${encodeURIComponent(activeClassId)}">Xem đề bài</a>
            ${isStudent ? `<button type="button" data-action="solve-problem" data-problem-id="${problem.problem_id}">Nộp lời giải</button>` : ""}
        </article>`).join("") || `<div class="empty-state"><p>Lớp chưa có bài tập.</p></div>`;
    renderProblemMath(document.getElementById("class-problem-list"));
    document.getElementById("class-contest-list").innerHTML = (data.contests || []).map((contest) => `
        <article class="problem-card">
            <div><p class="class-card-kicker">CUỘC THI · ${escapeHtml(contest.status)}</p><h4>${escapeHtml(contest.contest_name)}</h4></div>
            <span>${new Date(contest.start_time).toLocaleString()} – ${new Date(contest.end_time).toLocaleString()}</span>
            ${isStudent ? `<button type="button" data-action="open-contest" data-contest-id="${contest.contest_id}">Mở cuộc thi</button>` : ""}
        </article>`).join("") || `<div class="empty-state"><p>Chưa có cuộc thi nào.</p></div>`;
    renderProblemMath(document.getElementById("class-contest-list"));

    if (canManage) {
        await loadAttachableProblems(data.problems || []);
        const contestProblemSelect = document.getElementById("contest-problem-select");
        contestProblemSelect.innerHTML = (data.problems || []).map((problem) =>
            `<option value="${problem.problem_id}">${escapeHtml(problem.problem_name)}</option>`
        ).join("");
        document.getElementById("create-contest-form").querySelector('[type="submit"]').disabled =
            !data.problems?.length;
        document.getElementById("create-contest-message").textContent = data.problems?.length
            ? ""
            : "Thêm ít nhất một bài tập vào lớp trước khi tạo cuộc thi.";
        if (canReviewJoinRequests) {
            await loadJoinRequests(activeClassId);
        }
        await loadManagers(activeClassId, canManagePermissions);
    } else {
        document.getElementById("submission-history").hidden = false;
        await loadSubmissionHistory(activeClassId);
    }
}

async function loadAttachableProblems(classProblems) {
    const picker = document.getElementById("class-problem-picker");
    const button = document.getElementById("add-problem-button");
    const currentClassId = activeClassId;
    setMessage(document.getElementById("add-problem-message"), "");
    picker.innerHTML = `<option value="">Đang tải bài tập...</option>`;
    button.disabled = true;
    try {
        const library = await requestJson("/admin/judge/problems");
        if (currentClassId !== activeClassId) {
            return;
        }
        const attachedIds = new Set(classProblems.map((problem) => problem.problem_id));
        const candidates = library.filter((problem) => !attachedIds.has(problem.problem_id));
        picker.innerHTML = `<option value="">Chọn bài tập để thêm</option>${candidates.map((problem) =>
            `<option value="${problem.problem_id}">${escapeHtml(problem.problem_name)} · ${problem.access_modifier === "public" ? "Public" : "Private"}</option>`
        ).join("")}`;
        if (!candidates.length) {
            setMessage(document.getElementById("add-problem-message"), "Không còn bài trong kho của bạn hoặc bài public để thêm.");
        }
        button.disabled = !candidates.length;
    } catch (error) {
        console.error(error);
        picker.innerHTML = `<option value="">Không thể tải bài tập</option>`;
        setMessage(
            document.getElementById("add-problem-message"),
            error.message || "Không thể tải bài tập để thêm vào lớp.",
            true,
        );
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
    clearTimeout(managerSearchTimer);
    const requestId = ++managerSearchRequest;
    const managers = await requestJson(`/admin/judge/academic-classes/${classId}/managers`);
    if (classId !== activeClassId || requestId !== managerSearchRequest) {
        return;
    }
    const list = document.getElementById("manager-list");
    list.innerHTML = managers.map((manager) => `<div class="entity-row">
        <span><strong>${escapeHtml(manager.account_name)}</strong><small>${escapeHtml(manager.account_email)} · ${manager.is_owner ? "Chủ lớp" : "Quản trị viên"}</small></span>
        ${canManagePermissions && (!manager.is_owner || currentAccount.role === "SUPER_ADMIN") ? `<button class="secondary" type="button" data-action="remove-manager" data-account-id="${manager.account_id}">Thu hồi quyền</button>` : ""}
    </div>`).join("");
    const search = document.getElementById("manager-search");
    const availableList = document.getElementById("available-manager-list");
    availableList.replaceChildren();
    if (!canManagePermissions) {
        return;
    }

    availableList.innerHTML = `<p class="field-hint">Nhập tên hoặc email để tìm quản trị viên.</p>`;
    search.oninput = () => {
        clearTimeout(managerSearchTimer);
        const query = search.value.trim();
        managerSearchRequest += 1;
        const requestId = managerSearchRequest;
        if (query.length < 2) {
            availableList.innerHTML = `<p class="field-hint">Nhập ít nhất 2 ký tự để tìm.</p>`;
            return;
        }
        availableList.innerHTML = `<p class="field-hint">Đang tìm...</p>`;
        managerSearchTimer = setTimeout(async () => {
            try {
                const candidates = await requestJson(
                    `/admin/judge/academic-classes/${classId}/available-managers?search=${encodeURIComponent(query)}`,
                );
                if (requestId !== managerSearchRequest) {
                    return;
                }
                availableList.innerHTML = candidates.map((candidate) => `
                    <div class="entity-row">
                        <span><strong>${escapeHtml(candidate.account_name)}</strong><small>${escapeHtml(candidate.account_email)}</small></span>
                        <button type="button" data-action="add-manager" data-account-id="${candidate.account_id}">Mời</button>
                    </div>
                `).join("") || `<p class="field-hint">Không tìm thấy quản trị viên phù hợp.</p>`;
            } catch (error) {
                if (requestId !== managerSearchRequest) {
                    return;
                }
                console.error(error);
                availableList.innerHTML = `<p class="field-hint error">${escapeHtml(error.message || "Không thể tìm quản trị viên.")}</p>`;
            }
        }, 250);
    };
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
                ${problem.description?.trim() ? `<p>${escapeHtml(problem.description)}</p>` : ""}
                <a class="button-link secondary" href="problem_statement.html?problem_id=${encodeURIComponent(problem.problem_id)}&source=class&class_id=${encodeURIComponent(activeClassId)}">Xem đề bài</a>
            </div>
            ${contest.can_submit ? `<button type="button" data-action="solve-contest-problem" data-problem-id="${problem.problem_id}">Nộp bài</button>` : ""}
        </article>`).join("") || `<div class="empty-state"><p>Cuộc thi chưa có bài thi.</p></div>`;
    renderProblemMath(document.getElementById("contest-problem-list"));
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
            case "open-admin-class":
                await openClass(classId, false);
                break;
            case "claim-class":
                await requestJson(`/admin/judge/academic-classes/${classId}/claim`, { method: "POST" });
                setMessage(pageMessage, "Bạn đã trở thành chủ lớp.");
                await loadAdminClasses();
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
            case "add-manager":
                await requestJson(`/admin/judge/academic-classes/${activeClassId}/managers`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ account_id: Number(button.dataset.accountId) }),
                });
                setMessage(document.getElementById("manager-message"), "Đã mời quản trị viên vào lớp.");
                await loadManagers(activeClassId, true);
                document.getElementById("manager-search").dispatchEvent(new Event("input"));
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

document.getElementById("add-problem-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = document.getElementById("add-problem-button");
    const problemId = Number(new FormData(form).get("problem_id"));
    if (!problemId) {
        setMessage(document.getElementById("add-problem-message"), "Hãy chọn một bài tập.", true);
        return;
    }
    button.disabled = true;
    try {
        await requestJson(`/admin/judge/academic-classes/${activeClassId}/problems`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ problem_id: problemId, is_required: false }),
        });
        await openClass(activeClassId, false);
        setMessage(document.getElementById("add-problem-message"), "Đã thêm bài tập vào lớp.");
    } catch (error) {
        setMessage(
            document.getElementById("add-problem-message"),
            error.message || "Không thể thêm bài tập vào lớp.",
            true,
        );
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
