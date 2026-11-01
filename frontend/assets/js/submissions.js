import { apiFetch, readResponse } from "./api.js?v=20261029a";
import { renderSubmissionHistory } from "./submission_history.js?v=20261102a";

const pageSize = 50;
const query = new URLSearchParams(window.location.search);
const filterForm = document.getElementById("history-filter-form");
const filteredCard = document.getElementById("filtered-history-card");
const historyGrid = document.getElementById("submission-history-grid");
const filteredList = document.getElementById("filtered-submission-history");
const serverList = document.getElementById("server-submission-history");
const filteredMore = document.getElementById("filtered-history-more");
const serverMore = document.getElementById("server-history-more");
const filters = {
    problem_id: query.get("problem_id")?.trim() || "",
    account_id: query.get("account_id")?.trim() || "",
};
const offsets = { filtered: 0, server: 0 };
const messages = {
    filtered: document.getElementById("filtered-history-message"),
    server: document.getElementById("server-history-message"),
};

function setMessage(element, text) {
    element.textContent = text;
    element.classList.toggle("error", Boolean(text));
}

function buildHistoryUrl(filter, offset) {
    const params = new URLSearchParams({ limit: String(pageSize), offset: String(offset) });
    for (const [name, value] of Object.entries(filter)) {
        if (value) params.set(name, value);
    }
    return `/student/submissions?${params}`;
}

async function loadHistory(scope, { append = false } = {}) {
    const isFiltered = scope === "filtered";
    const list = isFiltered ? filteredList : serverList;
    const moreButton = isFiltered ? filteredMore : serverMore;
    const filter = isFiltered ? filters : {};
    const offset = append ? offsets[scope] : 0;
    moreButton.disabled = true;
    setMessage(messages[scope], "");
    try {
        const response = await apiFetch(buildHistoryUrl(filter, offset));
        const data = await readResponse(response);
        if (!response.ok) {
            throw new Error(data.detail || `Không thể tải lịch sử (${response.status})`);
        }
        renderSubmissionHistory(list, data, { append });
        offsets[scope] = offset + data.length;
        moreButton.hidden = data.length < pageSize;
    } catch (error) {
        console.error(error);
        setMessage(
            messages[scope],
            error instanceof Error ? error.message : "Không thể tải lịch sử bài nộp.",
        );
    } finally {
        moreButton.disabled = false;
    }
}

function initializeFilters() {
    for (const [name, value] of Object.entries(filters)) {
        const input = filterForm.elements.namedItem(name);
        input.value = value;
        if (!value) continue;
        if (!/^[1-9]\d*$/.test(value) || !Number.isSafeInteger(Number(value))) {
            throw new Error(`Giá trị ${name} không hợp lệ.`);
        }
    }
    const hasFilters = Object.values(filters).some(Boolean);
    filteredCard.hidden = !hasFilters;
    historyGrid.classList.toggle("has-filtered-history", hasFilters);
    if (hasFilters) {
        const descriptions = [];
        if (filters.problem_id) descriptions.push(`Bài tập #${filters.problem_id}`);
        if (filters.account_id) descriptions.push(`Tài khoản #${filters.account_id}`);
        document.getElementById("filtered-history-heading").textContent =
            `Lịch sử: ${descriptions.join(" · ")}`;
        document.getElementById("filtered-history-hint").textContent =
            "Kết quả đã lọc theo các mã trong URL.";
    }
    return hasFilters;
}

filterForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const params = new URLSearchParams();
    for (const name of ["problem_id", "account_id"]) {
        const value = filterForm.elements.namedItem(name).value.trim();
        if (value) params.set(name, value);
    }
    window.location.href = `submissions.html${params.size ? `?${params}` : ""}`;
});

filteredMore.addEventListener("click", () => loadHistory("filtered", { append: true }));
serverMore.addEventListener("click", () => loadHistory("server", { append: true }));

document.getElementById("logout-button").addEventListener("click", async () => {
    try {
        const response = await apiFetch("/auth/logout", { method: "POST" });
        if (!response.ok) {
            throw new Error(`Không thể đăng xuất (${response.status}).`);
        }
        window.location.replace("login.html");
    } catch (error) {
        console.error(error);
        setMessage(messages.server, error instanceof Error ? error.message : "Không thể đăng xuất.");
    }
});

async function initialize() {
    try {
        const accountResponse = await apiFetch("/auth/me");
        if (!accountResponse.ok) {
            window.location.replace("login.html");
            return;
        }
        let hasFilters = false;
        try {
            hasFilters = initializeFilters();
        } catch (error) {
            console.error(error);
            filteredCard.hidden = false;
            historyGrid.classList.add("has-filtered-history");
            setMessage(
                messages.filtered,
                error instanceof Error ? error.message : "Bộ lọc lịch sử không hợp lệ.",
            );
        }
        await Promise.all([
            loadHistory("server"),
            hasFilters ? loadHistory("filtered") : Promise.resolve(),
        ]);
    } catch (error) {
        console.error(error);
        setMessage(messages.server, error instanceof Error ? error.message : "Không thể tải lịch sử.");
    }
}

initialize();
