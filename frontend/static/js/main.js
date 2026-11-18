// Submission and diagnostic results client script

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("bug-submission-form");
    if (form) {
        form.addEventListener("submit", handleBugSubmission);
    }

    const feedbackForm = document.getElementById("feedback-form");
    if (feedbackForm) {
        feedbackForm.addEventListener("submit", handleFeedbackSubmission);
    }
});

async function handleBugSubmission(event) {
    event.preventDefault();
    const form = event.target;
    const submitBtn = document.getElementById("submit-btn");
    const spinner = document.getElementById("submit-spinner");
    const fileInput = document.getElementById("file");

    submitBtn.disabled = true;
    spinner.classList.remove("d-none");

    try {
        let bugId = null;

        // If file is selected, upload via multipart
        if (fileInput && fileInput.files.length > 0) {
            const formData = new FormData(form);
            const response = await fetch("/api/bugs/upload", {
                method: "POST",
                body: formData
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "File upload failed.");
            bugId = data.bug.bug_id;
        } else {
            // Direct JSON submission
            const payload = {
                title: document.getElementById("title").value,
                description: document.getElementById("description").value,
                stack_trace: document.getElementById("stack_trace").value,
                log_content: document.getElementById("log_content").value,
                language: document.getElementById("language").value,
                severity: document.getElementById("severity").value
            };
            const response = await fetch("/api/bugs", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Submission failed.");
            bugId = data.bug.bug_id;
        }

        // Trigger diagnosis immediately
        await fetch(`/api/bugs/${bugId}/analyze`, { method: "POST" });

        // Redirect to results view
        window.location.href = `/results/${bugId}`;
    } catch (err) {
        alert("Submission Error: " + err.message);
        submitBtn.disabled = false;
        spinner.classList.add("d-none");
    }
}

async function loadBugResults(bugId) {
    const banner = document.getElementById("analysis-loading-banner");
    try {
        let response = await fetch(`/api/bugs/${bugId}/results`);
        let data = await response.json();

        // If unanalyzed, trigger analysis
        if (data.status === "NOT_ANALYZED" || data.status === "PENDING") {
            if (banner) banner.classList.remove("d-none");
            await fetch(`/api/bugs/${bugId}/analyze`, { method: "POST" });
            response = await fetch(`/api/bugs/${bugId}/results`);
            data = await response.json();
        }

        if (banner) banner.classList.add("d-none");
        renderDiagnosisReport(data);
    } catch (err) {
        if (banner) banner.classList.add("d-none");
        console.error("Error loading diagnosis report:", err);
    }
}

function renderDiagnosisReport(report) {
    if (!report) return;

    // Root Cause & Confidence
    const titleEl = document.getElementById("root-cause-title");
    const expEl = document.getElementById("root-cause-explanation");
    const confBadge = document.getElementById("confidence-badge");
    const evidenceList = document.getElementById("evidence-list");

    if (titleEl) titleEl.textContent = report.root_cause || "Pending diagnosis...";
    if (expEl) expEl.textContent = report.explanation || "";
    if (confBadge) confBadge.textContent = "Confidence: " + (report.confidence || "Medium");

    if (evidenceList) {
        evidenceList.innerHTML = "";
        (report.evidence || []).forEach(e => {
            const li = document.createElement("li");
            li.textContent = e;
            evidenceList.appendChild(li);
        });
    }

    // Fix & Remediation
    const fixEl = document.getElementById("fix-explanation");
    if (fixEl) fixEl.textContent = report.recommended_fix || "";

    const cmdSec = document.getElementById("commands-section");
    const cmdCode = document.getElementById("commands-code");
    if (cmdSec && cmdCode && report.execution_commands && report.execution_commands.length > 0) {
        cmdSec.classList.remove("d-none");
        cmdCode.textContent = report.execution_commands.join("\n");
    }

    const verSec = document.getElementById("verification-section");
    const verCode = document.getElementById("verification-code");
    if (verSec && verCode && report.verification_steps) {
        verSec.classList.remove("d-none");
        verCode.textContent = report.verification_steps;
    }

    const riskSec = document.getElementById("risks-section");
    const riskText = document.getElementById("risks-text");
    if (riskSec && riskText && report.risks) {
        riskSec.classList.remove("d-none");
        riskText.textContent = report.risks;
    }

    // Agents Grid
    const raw = report.raw_agent_results || {};
    if (document.getElementById("agent-triage-body") && raw.triage) {
        document.getElementById("agent-triage-body").innerHTML = `
            <strong>Category:</strong> ${raw.triage.category || 'N/A'}<br>
            <strong>Severity:</strong> ${raw.triage.severity || 'N/A'}<br>
            <strong>Keywords:</strong> ${(raw.triage.keywords || []).join(', ')}
        `;
    }
    if (document.getElementById("agent-log-body") && raw.log_analysis) {
        document.getElementById("agent-log-body").innerHTML = `
            <strong>Exception:</strong> ${raw.log_analysis.exception || 'None'}<br>
            <strong>Location:</strong> ${raw.log_analysis.error_location || 'Unknown'}:${raw.log_analysis.line_number || '?'}<br>
            <strong>Frames:</strong> ${raw.log_analysis.call_depth || 0}
        `;
    }
    if (document.getElementById("agent-dup-body") && raw.duplicate_detection) {
        document.getElementById("agent-dup-body").innerHTML = `
            <strong>Matched Defect:</strong> ${(raw.duplicate_detection.similar_bugs && raw.duplicate_detection.similar_bugs[0]) ? raw.duplicate_detection.similar_bugs[0].defect_id : 'None'}<br>
            <strong>Candidates:</strong> ${raw.duplicate_detection.retrieved_count || 0}
        `;
    }
    if (document.getElementById("agent-rc-body") && raw.root_cause) {
        document.getElementById("agent-rc-body").innerHTML = `
            <strong>Diagnosis:</strong> ${raw.root_cause.root_cause || 'Identified'}<br>
            <strong>Mode:</strong> ${raw.root_cause.analysis_mode || 'Rule-Based'}
        `;
    }
    if (document.getElementById("agent-rem-body") && raw.remediation) {
        document.getElementById("agent-rem-body").innerHTML = `
            <strong>Action:</strong> ${raw.remediation.recommended_fix || 'Manual fix'}<br>
            <strong>Commands:</strong> ${(raw.remediation.commands && raw.remediation.commands.length > 0) ? 'Available' : 'None required'}
        `;
    }

    // Historical RAG Evidence
    const histContainer = document.getElementById("historical-defects-list");
    if (histContainer) {
        const defects = report.similar_historical_bugs || [];
        if (defects.length === 0) {
            histContainer.innerHTML = '<p class="p-3 text-muted">No historical defect matches with sufficient similarity score.</p>';
        } else {
            let html = '<table class="data-table"><thead><tr><th>Defect ID</th><th>Source</th><th>Similarity</th><th>Title</th><th>Resolution</th></tr></thead><tbody>';
            defects.forEach(d => {
                const scorePercent = Math.round((d.similarity_score || 0) * 100);
                html += `
                    <tr>
                        <td><code>${d.defect_id}</code></td>
                        <td><span class="tag tag-source">${d.source}</span></td>
                        <td><strong>${scorePercent}%</strong></td>
                        <td>${d.title}</td>
                        <td><small>${(d.resolution || '').substring(0, 140)}...</small></td>
                    </tr>
                `;
            });
            html += '</tbody></table>';
            histContainer.innerHTML = html;
        }
    }
}

async function triggerAnalysis(bugId) {
    const banner = document.getElementById("analysis-loading-banner");
    if (banner) banner.classList.remove("d-none");
    try {
        await fetch(`/api/bugs/${bugId}/analyze`, { method: "POST" });
        loadBugResults(bugId);
    } catch (err) {
        alert("Failed to re-run analysis: " + err.message);
    }
}

async function handleFeedbackSubmission(event) {
    event.preventDefault();
    const container = document.getElementById("results-container");
    if (!container) return;
    const bugId = container.dataset.bugId;

    const payload = {
        is_accurate: document.getElementById("is-accurate").value === "true",
        rating: parseFloat(document.getElementById("rating").value),
        feedback: document.getElementById("feedback-text").value
    };

    try {
        const response = await fetch(`/api/bugs/${bugId}/feedback`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (response.ok) {
            const successEl = document.getElementById("feedback-success");
            if (successEl) successEl.classList.remove("d-none");
        }
    } catch (err) {
        alert("Error saving feedback: " + err.message);
    }
}
