let cy = null;

export function initGraph() {
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

export function updateGraph(tree) {
    if (!cy) return;

    cy.elements().remove();

    const nodes = (tree || []).map(n => ({
        data: { id: String(n.id), label: n.name }
    }));

    const edges = (tree || [])
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

let oseByGoal = {};
let activeFactors = new Set();

export function setOseData(byGoal, factors) {
    oseByGoal = byGoal || {};
    activeFactors = new Set(factors || []);
}

export function updateNodeLabels() {
    if (!cy) return;

    cy.nodes().forEach(node => {
        const goal = node.data("label");
        const vals = oseByGoal[goal] || {};

        let lines = [goal];

        activeFactors.forEach(f => {
            if (vals[f] !== undefined) {
                lines.push(`${f}: ${vals[f]}`);
            }
        });

        node.style("label", lines.join("\n"));
        node.style("text-wrap", "wrap");
        node.style("text-max-width", "160px");
    });
}

export function clearGraph() {
    if (cy) cy.elements().remove();
}

export function resizeGraph() {
    if (!cy) return;
    cy.resize();
    cy.fit();
}
