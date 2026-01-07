import {
    apiGetSchemes,
    apiCreateScheme,
    apiDeleteScheme,
    apiStart,
    apiAnswer
} from "./api.js";

import {
    setActiveSchemeId,
    getSavedSchemeId
} from "./state.js";

import {
    initGraph,
    updateGraph,
    clearGraph,
    resizeGraph,
    setOseData,
    updateNodeLabels
} from "./graph.js";

let oseResults = [];
let factors = [];
let factorColors = {};
let oseByGoal = {};
let activeFactors = new Set();

function addMessage(text, sender) {
    const box = document.getElementById("dialog-box");
    const msg = document.createElement("div");
    msg.className = "message " + sender;
    msg.textContent = text;
    box.appendChild(msg);
    box.scrollTop = box.scrollHeight;
}

function clearDialog() {
    const box = document.getElementById("dialog-box");
    box.innerHTML = "";
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

async function sendAnswer(text) {
    const data = await apiAnswer(text);
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
}

async function startForScheme(schemeId) {
    setActiveSchemeId(schemeId);
    clearDialog();
    clearGraph();

    const data = await apiStart(schemeId);
    addMessage(data.question, "bot");

    if (data.tree) updateGraph(data.tree);

    if (data.ose_results) {
        buildOse(data.ose_results);
        renderFactorLegend();
        renderOseList(data.ose_results);
        updateNodeLabels();
    }
}

async function renderSchemes() {
    const box = document.getElementById("scheme-list");
    box.innerHTML = "";

    const schemes = await apiGetSchemes();

    schemes.forEach(s => {
        const row = document.createElement("div");

        const nameBtn = document.createElement("button");
        nameBtn.textContent = s.name;
        nameBtn.onclick = () => startForScheme(s.id);

        const delBtn = document.createElement("button");
        delBtn.textContent = "🗑";
        delBtn.onclick = async e => {
            e.stopPropagation();
            await apiDeleteScheme(s.id);
            await renderSchemes();
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

    btn.onclick = async () => {
        const name = input.value.trim();
        if (!name) return;
        const created = await apiCreateScheme(name);
        input.value = "";
        await renderSchemes();
        await startForScheme(created.id);
    };
}

window.onload = async () => {
    initGraph();

    await wireSchemeCreate();

    const saved = getSavedSchemeId();
    const schemes = await renderSchemes();

    if (schemes.length > 0) {
        const first = schemes.find(s => s.id === saved) || schemes[0];
        await startForScheme(first.id);
    }

    document.getElementById("btn-yes").onclick = () => {
        addMessage("Да", "user");
        sendAnswer("да");
    };

    document.getElementById("btn-no").onclick = () => {
        addMessage("Нет", "user");
        sendAnswer("нет");
    };

    document.getElementById("send-btn").onclick = () => {
        const i = document.getElementById("answer");
        if (!i.value.trim()) return;
        addMessage(i.value, "user");
        sendAnswer(i.value);
        i.value = "";
    };

    document.getElementById("answer").addEventListener("keypress", e => {
        if (e.key === "Enter") {
            if (!e.target.value.trim()) return;
            addMessage(e.target.value, "user");
            sendAnswer(e.target.value);
            e.target.value = "";
        }
    });

    document.getElementById("tab-graph").onclick = () => resizeGraph();
    document.getElementById("tab-ose").onclick = () => {};
};
