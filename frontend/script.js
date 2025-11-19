let cy = null;

// ---------------- API ----------------
async function apiStart() {
    const res = await fetch("http://localhost:8000/dialog/start", { method: "POST" });
    return await res.json();
}

async function apiAnswer(text) {
    const res = await fetch("http://localhost:8000/dialog/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer: text })
    });
    return await res.json();
}

// ---------------- ГРАФ ----------------
function initGraph() {
    cy = cytoscape({
        container: document.getElementById('graph'),
        style: [
            {
                selector: 'node',
                style: {
                    'background-color': '#4a90e2',
                    'label': 'data(label)',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'color': '#fff',
                    'font-size': '14px'
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': '#999',
                    'target-arrow-color': '#999',
                    'target-arrow-shape': 'triangle'
                }
            }
        ],
        layout: { name: 'breadthfirst' }
    });
}

function updateGraph(tree) {
    cy.elements().remove();

    const nodes = tree.map(n => ({
        data: { id: n.id.toString(), label: n.name }
    }));

    const edges = tree
        .filter(n => n.parent !== null)
        .map(n => ({
            data: {
                id: `e${n.parent}-${n.id}`,
                source: n.parent.toString(),
                target: n.id.toString()
            }
        }));

    cy.add(nodes);
    cy.add(edges);
    cy.layout({ name: 'breadthfirst', directed: true, padding: 20 }).run();
}

// ---------------- ЧАТ ----------------
function addMessage(text, sender) {
    const box = document.getElementById("dialog-box");
    const msg = document.createElement("div");
    msg.className = "message " + sender;
    msg.textContent = text;
    box.appendChild(msg);
    box.scrollTop = box.scrollHeight;
}

function showYesNo(show) {
    document.getElementById("yn-buttons").style.display = show ? "flex" : "none";
}

function isYesNoQuestion(text) {
    return text.includes("(да/нет)");
}

// ---------------- ОТПРАВКА ОТВЕТА ----------------
async function sendAnswer(text) {
    const data = await apiAnswer(text);
    addMessage(data.question, "bot");

    if (data.tree) updateGraph(data.tree);
    renderOSE(data.ose_results);

    // включать/выключать кнопки Да/Нет
    if (isYesNoQuestion(data.question)) {
        showYesNo(true);
        document.getElementById("answer").disabled = true;
        document.getElementById("send-btn").disabled = true;
    } else {
        showYesNo(false);
        document.getElementById("answer").disabled = false;
        document.getElementById("send-btn").disabled = false;
    }
}

// ---------------- ОСЭ ----------------
function renderOSE(results) {
    const box = document.getElementById("ose-results");
    box.innerHTML = "<h3>Результаты ОСЭ:</h3>";

    results.forEach(r => {
        const line = document.createElement("div");
        line.textContent = `${r.factor} — ${r.goal}: H = ${r.H}`;
        box.appendChild(line);
    });
}

// ---------------- ИНИЦИАЛИЗАЦИЯ ----------------
window.onload = async () => {
    initGraph();
    const data = await apiStart();
    addMessage(data.question, "bot");

    // кнопки Да/Нет
    document.getElementById("btn-yes").onclick = () => {
        addMessage("Да", "user");
        sendAnswer("да");
    };

    document.getElementById("btn-no").onclick = () => {
        addMessage("Нет", "user");
        sendAnswer("нет");
    };

    // текстовый ввод
    document.getElementById("send-btn").onclick = () => {
        const input = document.getElementById("answer");
        const text = input.value.trim();
        if (!text) return;
        addMessage(text, "user");
        input.value = "";
        sendAnswer(text);
    };

    document.getElementById("answer").addEventListener("keypress", e => {
        if (e.key === "Enter") {
            const val = e.target.value.trim();
            if (!val) return;
            addMessage(val, "user");
            e.target.value = "";
            sendAnswer(val);
        }
    });
};
