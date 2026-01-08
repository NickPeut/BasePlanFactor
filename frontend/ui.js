import {
    apiGetSchemes,
    apiCreateScheme,
    apiDeleteScheme,
    apiStart,
    apiAnswer
} from "./api.js";

import {
    setActiveSchemeId,
    getSavedSchemeId,
    getActiveSchemeId,
    loadDialogHistory,
    saveDialogHistory,
    clearDialogHistory,
    setDialogActive,
    saveSchemeState,
    loadSchemeState,
    clearSchemeState
} from "./state.js";

import {
    initGraph,
    updateGraph,
    clearGraph,
    resizeGraph,
    setOseData,
    updateNodeLabels
} from "./graph.js";

let dialogHistory = [];

function renderMessage(text, sender) {
    const box = document.getElementById("dialog-box");
    const msg = document.createElement("div");
    msg.className = "message " + sender;
    msg.textContent = text;
    box.appendChild(msg);
    box.scrollTop = box.scrollHeight;
}

let oseResults = [];
let factors = [];
let factorColors = {};
let oseByGoal = {};
let activeFactors = new Set();

function addMessage(text, sender) {
    renderMessage(text, sender);
    dialogHistory.push({ text, sender });
    saveDialogHistory(getActiveSchemeId(), dialogHistory);
    setDialogActive(getActiveSchemeId(), true);
}

function clearDialog() {
    const box = document.getElementById("dialog-box");
    box.innerHTML = "";
    dialogHistory = [];
    clearDialogHistory(getActiveSchemeId());
    clearSchemeState(getActiveSchemeId());
}

function clearOseUi() {
    oseResults = [];
    factors = [];
    factorColors = {};
    oseByGoal = {};
    activeFactors = new Set();

    const legend = document.getElementById("factor-legend");
    if (legend) legend.innerHTML = "";

    const list = document.getElementById("ose-results");
    if (list) list.innerHTML = "";
}

function buildOse(results) {
    oseResults = results || [];
    oseByGoal = {};
    const fset = new Set();

    oseResults.forEach(r => {
        fset.add(r.factor);
        if (!oseByGoal[r.goal]) oseByGoal[r.goal] = {};
        oseByGoal[r.goal][r.factor] = r.H;
    });

    factors = [...fset];

    const palette = [
        "#f94144", "#f3722c", "#f8961e", "#f9c74f",
        "#90be6d", "#43aa8b", "#577590", "#b5179e"
    ];

    factorColors = {};
    factors.forEach((f, i) => factorColors[f] = palette[i % palette.length]);

    setOseData(oseByGoal, activeFactors);
}

function renderFactorLegend() {
    const box = document.getElementById("factor-legend");
    box.innerHTML = "<h3>Факторы:</h3>";

    factors.forEach(f => {
        const item = document.createElement("div");

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.onchange = () => {
            if (checkbox.checked) activeFactors.add(f);
            else activeFactors.delete(f);
            setOseData(oseByGoal, activeFactors);
            updateNodeLabels();
        };

        const colorBox = document.createElement("span");
        colorBox.style.background = factorColors[f];
        colorBox.style.display = "inline-block";
        colorBox.style.width = "10px";
        colorBox.style.height = "10px";
        colorBox.style.margin = "0 6px";

        const label = document.createElement("span");
        label.textContent = f;

        item.appendChild(checkbox);
        item.appendChild(colorBox);
        item.appendChild(label);
        box.appendChild(item);
    });
}

function renderOseList(results) {
    const box = document.getElementById("ose-results");
    box.innerHTML = "<h3>Результаты ОСЭ:</h3>";

    results.forEach(r => {
        const div = document.createElement("div");
        div.textContent = `${r.factor} → ${r.goal}: H = ${r.H}`;
        box.appendChild(div);
    });
}

function isYesNo(text) {
    return text.includes("(да/нет)");
}

function applySavedState(schemeId) {
    const st = loadSchemeState(schemeId);
    if (!st) return;

    if (st.tree) updateGraph(st.tree);

    if (st.ose_results) {
        buildOse(st.ose_results);
        renderFactorLegend();
        renderOseList(st.ose_results);
        updateNodeLabels();
    }
}

function persistStatePatch(schemeId, data) {
    const prev = loadSchemeState(schemeId) || {};
    saveSchemeState(schemeId, {
        tree: data.tree || prev.tree || null,
        ose_results: data.ose_results || prev.ose_results || null
    });
}

function applyDialogResponse(data) {
    addMessage(data.question, "bot");

    if (data.tree) updateGraph(data.tree);

    if (data.ose_results) {
        buildOse(data.ose_results);
        renderFactorLegend();
        renderOseList(data.ose_results);
        updateNodeLabels();
    }

    const yn = document.getElementById("yn-buttons");
    const input = document.getElementById("answer");
    const send = document.getElementById("send-btn");

    if (isYesNo(data.question)) {
        yn.style.display = "flex";
        input.disabled = true;
        send.disabled = true;
    } else {
        yn.style.display = "none";
        input.disabled = false;
        send.disabled = false;
    }

    persistStatePatch(getActiveSchemeId(), data);
}

async function sendAnswer(text) {
    const data = await apiAnswer(text);
    applyDialogResponse(data);
}

async function startForScheme(schemeId) {
    setActiveSchemeId(schemeId);
    clearGraph();
    clearOseUi();

    const saved = loadDialogHistory(schemeId);

    if (saved && saved.length) {
        const box = document.getElementById("dialog-box");
        box.innerHTML = "";
        dialogHistory = saved;
        for (const m of saved) renderMessage(m.text, m.sender);
        setDialogActive(schemeId, true);
        applySavedState(schemeId);
        return;
    }

    clearDialog();
    const data = await apiStart(schemeId);
    applyDialogResponse(data);
}

async function renderSchemes() {
    const box = document.getElementById("scheme-list");
    box.innerHTML = "";

    const schemes = await apiGetSchemes();
    const activeId = getSavedSchemeId();

    schemes.forEach(s => {
        const row = document.createElement("div");
        row.className = "scheme-row";

        const nameBtn = document.createElement("button");
        nameBtn.className = "scheme-select";
        nameBtn.textContent = s.name;
        if (Number(s.id) === Number(activeId)) nameBtn.classList.add("active");
        nameBtn.onclick = () => startForScheme(s.id);

        const delBtn = document.createElement("button");
        delBtn.className = "scheme-delete";
        delBtn.type = "button";
        delBtn.textContent = "🗑";
        delBtn.onclick = async e => {
            e.preventDefault();
            e.stopPropagation();
            await apiDeleteScheme(s.id);
            clearDialogHistory(s.id);
            clearSchemeState(s.id);
            await renderSchemes();
            const savedAfter = getSavedSchemeId();
            if (Number(savedAfter) === Number(s.id)) setActiveSchemeId(null);
        };

        row.appendChild(nameBtn);
        row.appendChild(delBtn);
        box.appendChild(row);
    });

    return schemes;
}

async function wireSchemeCreate() {
    const btn = document.getElementById("scheme-create");
    const input = document.getElementById("scheme-name");

    if (!btn || !input) return;

    btn.onclick = async () => {
        const name = input.value.trim();
        if (!name) return;

        btn.disabled = true;
        input.disabled = true;

        try {
            const created = await apiCreateScheme(name);
            input.value = "";
            await renderSchemes();
            await startForScheme(created.id);
        } catch (e) {
            console.error(e);
            addMessage("Ошибка при создании схемы. Смотри Console.", "bot");
        } finally {
            btn.disabled = false;
            input.disabled = false;
        }
    };
}

window.addEventListener("DOMContentLoaded", () => {
    (async () => {
        try {
            initGraph();

            await wireSchemeCreate();

            const saved = getSavedSchemeId();
            const schemes = await renderSchemes();

            if (schemes.length > 0) {
                const first = schemes.find(s => s.id === saved) || schemes[0];
                await startForScheme(first.id);
            }

            const yesBtn = document.getElementById("btn-yes");
            if (yesBtn) {
                yesBtn.onclick = () => {
                    addMessage("Да", "user");
                    sendAnswer("да");
                };
            }

            const noBtn = document.getElementById("btn-no");
            if (noBtn) {
                noBtn.onclick = () => {
                    addMessage("Нет", "user");
                    sendAnswer("нет");
                };
            }

            const sendBtn = document.getElementById("send-btn");
            if (sendBtn) {
                sendBtn.onclick = () => {
                    const i = document.getElementById("answer");
                    if (!i || !i.value.trim()) return;
                    addMessage(i.value, "user");
                    sendAnswer(i.value);
                    i.value = "";
                };
            }

            const answerInput = document.getElementById("answer");
            if (answerInput) {
                answerInput.addEventListener("keypress", e => {
                    if (e.key === "Enter") {
                        if (!e.target.value.trim()) return;
                        addMessage(e.target.value, "user");
                        sendAnswer(e.target.value);
                        e.target.value = "";
                    }
                });
            }

            const tabGraph = document.getElementById("tab-graph");
            if (tabGraph) tabGraph.onclick = () => resizeGraph();

            const tabOse = document.getElementById("tab-ose");
            if (tabOse) tabOse.onclick = () => {};
        } catch (e) {
            console.error("UI bootstrap failed:", e);
        }
    })();
});
