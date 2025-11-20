let cy = null;

// =======================================
// API
// =======================================

async function apiStart() {
    const res = await fetch("/dialog/start", { method: "POST" });
    return await res.json();
}

async function apiAnswer(text) {
    const res = await fetch("/dialog/answer", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({answer: text})
    });
    return await res.json();
}

// =======================================
// Инициализация графа
// =======================================

function initGraph() {
    cy = cytoscape({
        container: document.getElementById("graph"),

        style: [
            {
                selector: "node",
                style: {
                    "background-color": "#4a90e2",
                    "color": "#fff",
                    "label": "data(label)",
                    "font-size": "12px",
                    "text-wrap": "wrap",
                    "text-max-width": "150px",
                    "text-valign": "center",
                    "text-halign": "center",
                    "shape": "round-rectangle",
                    "border-radius": "22px",
                    "width": "label",
                    "height": "label",
                    "padding": "10px",
                    "min-width": "60px",
                    "max-width": "200px",
                }
            },
            {
                selector: "edge",
                style: {
                    "width": 2,
                    "line-color": "#999",
                    "target-arrow-color": "#999",
                    "target-arrow-shape": "triangle"
                }
            }
        ],

        layout: {
            name: "breadthfirst",
            directed: true,
            spacingFactor: 1.2
        }
    });
}

function updateGraph(tree) {
    if (!cy) return;

    cy.elements().remove();

    const nodes = tree.map(n => ({
        data: { id: String(n.id), label: n.name }
    }));

    const edges = tree
        .filter(n => n.parent)
        .map(n => ({
            data: { source: String(n.parent), target: String(n.id) }
        }));

    cy.add(nodes);
    cy.add(edges);

    cy.layout({
        name: "breadthfirst",
        directed: true,
        spacingFactor: 1.2
    }).run();

    setTimeout(() => {
        cy.resize();
        cy.fit();
        updateNodeLabels();
    }, 100);
}

// =======================================
// ОСЭ
// =======================================

let oseResults = [];
let factors = [];
let factorColors = {};
let oseByGoal = {};
let activeFactors = new Set();

function buildOse(results) {
    oseResults = results || [];
    oseByGoal = {};
    const fset = new Set();

    results.forEach(r => {
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
    factors.forEach((f,i)=> factorColors[f] = palette[i % palette.length]);
}

function renderFactorLegend() {
    const box = document.getElementById("factor-legend");
    box.innerHTML = "<h3>Факторы:</h3>";

    if (factors.length === 0) {
        box.innerHTML += "<p>Нет данных</p>";
        return;
    }

    factors.forEach(f => {
        const item = document.createElement("div");
        item.className = "factor-item";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";

        checkbox.onchange = () => {
            if (checkbox.checked) activeFactors.add(f);
            else activeFactors.delete(f);
            updateNodeLabels();
        };

        const colorBox = document.createElement("span");
        colorBox.className = "factor-color";
        colorBox.style.background = factorColors[f];

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

    if (!results || results.length === 0) {
        box.innerHTML += "<p>Пока нет.</p>";
        return;
    }

    results.forEach(r => {
        const div = document.createElement("div");
        div.textContent = `${r.factor} → ${r.goal}: H = ${r.H}`;
        box.appendChild(div);
    });
}

// =======================================
// Подписи значений H
// =======================================

function updateNodeLabels() {
    if (!cy) return;

    cy.nodes().forEach(node => {
        const goal = node.data("label");
        const vals = oseByGoal[goal] || {};

        let lines = [goal];

        activeFactors.forEach(f => {
            if (vals[f] !== undefined) {
                const H = vals[f];
                lines.push(`${f}: ${H}`);
            }
        });

        node.style("label", lines.join("\n"));
        node.style("text-wrap", "wrap");
        node.style("text-max-width", "160px");
    });
}

// =======================================
// ЧАТ
// =======================================

function addMessage(text, sender) {
    const box = document.getElementById("dialog-box");
    const msg = document.createElement("div");
    msg.className = "message " + sender;
    msg.textContent = text;
    box.appendChild(msg);
    box.scrollTop = box.scrollHeight;
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

// =======================================
// Переключение вкладок
// =======================================

function showTab(name) {
    document.getElementById("tab-graph").classList.remove("active");
    document.getElementById("tab-ose").classList.remove("active");

    document.getElementById("graph-container").style.display =
        name === "graph" ? "block" : "none";

    document.getElementById("ose-container").style.display =
        name === "ose" ? "block" : "none";

    document.getElementById("tab-" + name).classList.add("active");

    if (name === "graph" && cy) {
        setTimeout(() => {
            cy.resize();
            cy.fit();
            updateNodeLabels();
        }, 100);
    }
}

// =======================================
// DRAGBAR
// =======================================

let dragging = false;
const dragbar = document.getElementById("dragbar");
const chat = document.getElementById("chat");

dragbar.addEventListener("mousedown", () => {
    dragging = true;
    document.body.style.cursor = "col-resize";
});

document.addEventListener("mousemove", e => {
    if (!dragging) return;

    const min = 200;
    const max = 600;
    let newW = e.clientX;

    if (newW < min) newW = min;
    if (newW > max) newW = max;

    chat.style.width = newW + "px";

    if (cy) setTimeout(() => {
        cy.resize();
        cy.fit();
        updateNodeLabels();
    }, 30);
});

document.addEventListener("mouseup", () => {
    dragging = false;
    document.body.style.cursor = "default";
});

// =======================================
// АВТОЗАПУСК ДИАЛОГА
// =======================================

window.onload = async () => {
    initGraph();

    const data = await apiStart();
    addMessage(data.question, "bot");

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
            const i = e.target;
            if (!i.value.trim()) return;
            addMessage(i.value, "user");
            sendAnswer(i.value);
            i.value = "";
        }
    });

    document.getElementById("tab-graph").onclick = () => showTab("graph");
    document.getElementById("tab-ose").onclick = () => showTab("ose");
};
