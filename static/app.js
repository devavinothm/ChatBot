// --- Storage Keys & Helpers ---
const STORAGE_KEYS = {
  multiAgentHistory: "chatbot_history_multi_agent",
  infoHistory: "chatbot_history_info",
  guidanceHistory: "chatbot_history_guidance",
  guidanceGoal: "chatbot_guidance_goal",
  solutionHistory: "chatbot_history_solution",
  solutionAnalysis: "chatbot_solution_analysis",
  utilityHistory: "chatbot_history_utility",
  utilityDraft: "chatbot_utility_draft",
};

function loadStorage(key) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.error("Failed to read localStorage key:", key, e);
    return null;
  }
}

function saveStorage(key, data) {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (e) {
    console.error("Failed to write localStorage key:", key, e);
  }
}

function appendStorageMessage(key, item) {
  const list = loadStorage(key) || [];
  list.push(item);
  saveStorage(key, list);
}

function formatBubbleContent(bubble, role, text) {
  if (role === "assistant" && typeof marked !== "undefined" && marked.parse) {
    try {
      bubble.innerHTML = marked.parse(text);
      return;
    } catch (e) {
      console.warn("Markdown render error", e);
    }
  }
  bubble.textContent = text;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function createThinkingFlowWidget(flow) {
  if (!flow || !flow.flow_steps || !flow.flow_steps.length) return null;

  const card = document.createElement("div");
  card.className = "thinking-flow-card";

  // Header / toggle bar
  const header = document.createElement("div");
  header.className = "thinking-flow-header";

  const summary = document.createElement("div");
  summary.className = "thinking-flow-summary";

  const brain = document.createElement("span");
  brain.className = "thinking-brain-icon";
  brain.textContent = "🧠";

  const title = document.createElement("strong");
  title.className = "thinking-title";
  title.textContent = "Thinking & Routing Flow";

  const countBadge = document.createElement("span");
  const count = flow.metric_count || 0;
  countBadge.className = `metric-count-badge ${count === 1 ? "single-metric" : (count >= 2 ? "multi-metric" : "zero-metric")}`;
  if (count === 1) {
    countBadge.textContent = `1 Metric (${flow.detected_metrics && flow.detected_metrics[0] ? flow.detected_metrics[0] : "Focused"})`;
  } else if (count >= 2) {
    countBadge.textContent = `${count} Metrics (Multi-Metric)`;
  } else {
    countBadge.textContent = "0 Metrics (Policy / General)";
  }

  const tierBadge = document.createElement("span");
  const tierKey = (flow.cost_tier && flow.cost_tier.tier) || "tier1";
  tierBadge.className = `tier-cost-badge ${tierKey}`;
  tierBadge.textContent = (flow.cost_tier && flow.cost_tier.name) || "Cost Tier";

  summary.appendChild(brain);
  summary.appendChild(title);
  summary.appendChild(countBadge);
  summary.appendChild(tierBadge);

  const toggleBtn = document.createElement("button");
  toggleBtn.type = "button";
  toggleBtn.className = "thinking-toggle-btn";
  toggleBtn.innerHTML = `<span>Inspect Flow</span> <span class="toggle-arrow">▾</span>`;

  header.appendChild(summary);
  header.appendChild(toggleBtn);
  card.appendChild(header);

  // Expandable Body
  const body = document.createElement("div");
  body.className = "thinking-flow-body";
  body.style.display = "none";

  // 1. Pipeline path row
  if (flow.pipeline_path && flow.pipeline_path.length) {
    const pipelineRow = document.createElement("div");
    pipelineRow.className = "thinking-pipeline-row";

    const pLabel = document.createElement("span");
    pLabel.className = "pipeline-label";
    pLabel.textContent = "Path:";
    pipelineRow.appendChild(pLabel);

    flow.pipeline_path.forEach((node, idx) => {
      const nodeEl = document.createElement("span");
      nodeEl.className = "pipeline-node";
      nodeEl.textContent = node;
      pipelineRow.appendChild(nodeEl);

      if (idx < flow.pipeline_path.length - 1) {
        const arrow = document.createElement("span");
        arrow.className = "pipeline-arrow";
        arrow.textContent = "➔";
        pipelineRow.appendChild(arrow);
      }
    });
    body.appendChild(pipelineRow);
  }

  // 2. Metric Scope & Cost Optimization banner
  const banner = document.createElement("div");
  banner.className = "thinking-scope-banner";

  const metricBox = document.createElement("div");
  metricBox.className = "scope-metric-box";
  metricBox.innerHTML = `
    <span class="scope-label">Metric Scope</span>
    <span class="scope-val">${escapeHtml(flow.metric_scope || "Standard")}</span>
  `;

  const costBox = document.createElement("div");
  costBox.className = "scope-cost-box";
  const costReason = (flow.cost_tier && flow.cost_tier.cost_reason) || (flow.reasoning_summary || "");
  costBox.innerHTML = `
    <span class="scope-label">Cost Optimization</span>
    <span class="scope-val">${escapeHtml(costReason)}</span>
  `;

  banner.appendChild(metricBox);
  banner.appendChild(costBox);
  body.appendChild(banner);

  // 3. 4-Step Reasoned Flow Timeline
  const timeline = document.createElement("div");
  timeline.className = "thinking-steps-timeline";

  (flow.flow_steps || []).forEach((st) => {
    const item = document.createElement("div");
    item.className = "thinking-step-item";

    const circle = document.createElement("div");
    circle.className = "step-num-circle";
    circle.textContent = st.step;

    const content = document.createElement("div");
    content.className = "step-content-box";

    const head = document.createElement("div");
    head.className = "step-head-row";

    const stTitle = document.createElement("strong");
    stTitle.className = "step-title-text";
    stTitle.textContent = st.title;

    const stBadge = document.createElement("span");
    stBadge.className = "step-badge-pill";
    stBadge.textContent = st.badge;

    head.appendChild(stTitle);
    head.appendChild(stBadge);

    const stDetail = document.createElement("p");
    stDetail.className = "step-detail-text";
    stDetail.textContent = st.detail;

    content.appendChild(head);
    content.appendChild(stDetail);

    item.appendChild(circle);
    item.appendChild(content);
    timeline.appendChild(item);
  });

  body.appendChild(timeline);
  card.appendChild(body);

  let isExpanded = false;
  header.addEventListener("click", () => {
    isExpanded = !isExpanded;
    body.style.display = isExpanded ? "block" : "none";
    card.classList.toggle("is-expanded", isExpanded);
    toggleBtn.innerHTML = isExpanded
      ? `<span>Hide Flow</span> <span class="toggle-arrow">▴</span>`
      : `<span>Inspect Flow</span> <span class="toggle-arrow">▾</span>`;
  });

  return card;
}

// --- Tab Switching ---
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    const panel = document.getElementById(`tab-${btn.dataset.tab}`);
    if (panel) panel.classList.add("active");
  });
});

// ==========================================
// --- 0. Multi Agent Orchestrator Logic ---
// ==========================================
const multiAgentMessagesEl = document.getElementById("multi-agent-messages");
const multiAgentForm = document.getElementById("multi-agent-form");
const multiAgentInput = document.getElementById("multi-agent-text");
const multiAgentWelcomeEl = document.getElementById("multi-agent-welcome");

function addMultiAgentBubble(role, text, routingData, sources, save = true) {
  if (multiAgentWelcomeEl) multiAgentWelcomeEl.style.display = "none";
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;

  if (role === "assistant" && routingData) {
    const header = document.createElement("div");
    header.className = "agent-delegation-header";

    const badge = document.createElement("div");
    const isCollab = routingData.agent === "collaborative";
    badge.className = `agent-badge-pill ${isCollab ? "collab" : ""}`;
    badge.innerHTML = `<span>${routingData.agent_icon || "🤖"}</span> <span>${routingData.agent_name || "Specialist Agent"}</span>`;

    if (routingData.agent_role) {
      const roleTag = document.createElement("span");
      roleTag.className = "agent-role-tag";
      roleTag.textContent = `• ${routingData.agent_role}`;
      badge.appendChild(roleTag);
    }
    header.appendChild(badge);

    if (routingData.reasoning) {
      const reason = document.createElement("span");
      reason.className = "agent-reasoning-text";
      reason.textContent = `Why: ${routingData.reasoning}`;
      header.appendChild(reason);
    }

    if (routingData.tab_id && routingData.tab_id !== "multi-agent") {
      const jumpBtn = document.createElement("button");
      jumpBtn.type = "button";
      jumpBtn.className = "agent-jump-btn";
      jumpBtn.textContent = `Open in ${routingData.agent_name} ➔`;
      jumpBtn.addEventListener("click", () => {
        const tabBtn = document.querySelector(`.tab-btn[data-tab="${routingData.tab_id}"]`);
        if (tabBtn) tabBtn.click();
      });
      header.appendChild(jumpBtn);
    }

    bubble.appendChild(header);

    if (isCollab && routingData.collaborating_agents && routingData.collaborating_agents.length) {
      const collabRow = document.createElement("div");
      collabRow.className = "collab-pills-row";
      routingData.collaborating_agents.forEach((ag) => {
        const pill = document.createElement("span");
        pill.className = "collab-pill-item";
        pill.textContent = `${ag.icon} ${ag.name} (${ag.role})`;
        collabRow.appendChild(pill);
      });
      bubble.appendChild(collabRow);
    }
  }

  const textContainer = document.createElement("div");
  formatBubbleContent(textContainer, role, text);
  bubble.appendChild(textContainer);

  if (sources && sources.length) {
    const sourcesEl = document.createElement("div");
    sourcesEl.className = "sources";
    sources.forEach((s) => {
      const tag = document.createElement("span");
      tag.className = "source-tag";
      tag.textContent = s;
      sourcesEl.appendChild(tag);
    });
    bubble.appendChild(sourcesEl);
  }

  multiAgentMessagesEl.appendChild(bubble);
  multiAgentMessagesEl.scrollTop = multiAgentMessagesEl.scrollHeight;

  if (save) {
    appendStorageMessage(STORAGE_KEYS.multiAgentHistory, {
      role,
      text,
      routingData: routingData || null,
      sources: sources || [],
    });
  }
}

if (multiAgentForm) {
  multiAgentForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = multiAgentInput.value.trim();
    if (!message) return;

    if (multiAgentWelcomeEl) multiAgentWelcomeEl.style.display = "none";
    addMultiAgentBubble("user", message, null, null, true);
    multiAgentInput.value = "";
    multiAgentInput.disabled = true;

    try {
      const res = await fetch("/api/multi_agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();
      if (!res.ok) {
        addMultiAgentBubble("error", data.error || "Something went wrong.", null, null, true);
      } else {
        addMultiAgentBubble("assistant", data.answer, data, data.sources, true);
        if (data.metadata && data.metadata.goal_state) {
          updateGoalHeader(data.metadata.goal_state, true);
        }
        if (data.metadata && data.metadata.solution_analysis) {
          updateSolutionHeader(data.metadata.solution_analysis, true);
        }
      }
    } catch (err) {
      addMultiAgentBubble("error", "Network error — is the server running?", null, null, true);
    } finally {
      multiAgentInput.disabled = false;
      multiAgentInput.focus();
    }
  });
}

document.querySelectorAll("#tab-multi-agent .prompt-chips .chip, #tab-multi-agent .prompt-card").forEach((chip) => {
  chip.addEventListener("click", () => {
    const prompt = chip.dataset.prompt;
    if (prompt && multiAgentInput) {
      multiAgentInput.value = prompt;
      multiAgentForm.dispatchEvent(new Event("submit"));
    }
  });
});

// ==========================================
// --- 1. Information Escort Logic ---
// ==========================================
const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-text");
const uploadForm = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const uploadStatus = document.getElementById("upload-status");
const reindexBtn = document.getElementById("reindex-btn");
const docCountEl = document.getElementById("doc-count");
const docListEl = document.getElementById("doc-list");
const infoWelcomeEl = document.getElementById("info-welcome");

function addBubble(role, text, sources, save = true) {
  if (infoWelcomeEl) infoWelcomeEl.style.display = "none";
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  formatBubbleContent(bubble, role, text);

  if (sources && sources.length) {
    const sourcesEl = document.createElement("div");
    sourcesEl.className = "sources";
    sources.forEach((s) => {
      const tag = document.createElement("span");
      tag.className = "source-tag";
      tag.textContent = s;
      sourcesEl.appendChild(tag);
    });
    bubble.appendChild(sourcesEl);
  }

  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  if (save) {
    appendStorageMessage(STORAGE_KEYS.infoHistory, { role, text, sources: sources || [] });
  }
}

async function refreshDocuments() {
  try {
    const res = await fetch("/api/documents");
    const data = await res.json();
    docCountEl.textContent = `${data.documents.length} document(s), ${data.chunks_indexed} chunks indexed`;
    docListEl.innerHTML = "";
    data.documents.forEach((name) => {
      const li = document.createElement("li");
      li.textContent = name;
      docListEl.appendChild(li);
    });
  } catch (err) {
    docCountEl.textContent = "Unable to load documents.";
  }
}

if (chatForm) {
  chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;

    addBubble("user", message, null, true);
    chatInput.value = "";
    chatInput.disabled = true;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();
      if (!res.ok) {
        addBubble("error", data.error || "Something went wrong.", null, true);
      } else {
        addBubble("assistant", data.answer, data.sources, true);
      }
    } catch (err) {
      addBubble("error", "Network error — is the server running?", null, true);
    } finally {
      chatInput.disabled = false;
      chatInput.focus();
    }
  });
}

document.querySelectorAll(".chip-info, #tab-information-escort .prompt-card").forEach((chip) => {
  chip.addEventListener("click", () => {
    const prompt = chip.dataset.prompt;
    if (prompt && chatInput) {
      chatInput.value = prompt;
      chatForm.dispatchEvent(new Event("submit"));
    }
  });
});

if (uploadForm) {
  uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    uploadStatus.textContent = "Uploading…";
    try {
      const uploadRes = await fetch("/api/upload", { method: "POST", body: formData });
      const uploadData = await uploadRes.json();
      if (!uploadRes.ok) {
        uploadStatus.textContent = uploadData.error || "Upload failed.";
        return;
      }

      uploadStatus.textContent = "Reindexing…";
      await fetch("/api/reindex", { method: "POST" });
      uploadStatus.textContent = `Uploaded ${uploadData.filename} and reindexed.`;
      fileInput.value = "";
      refreshDocuments();
    } catch (err) {
      uploadStatus.textContent = "Upload failed — network error.";
    }
  });
}

if (reindexBtn) {
  reindexBtn.addEventListener("click", async () => {
    reindexBtn.disabled = true;
    reindexBtn.textContent = "Reindexing…";
    try {
      await fetch("/api/reindex", { method: "POST" });
      await refreshDocuments();
    } finally {
      reindexBtn.disabled = false;
      reindexBtn.textContent = "Reindex documents/ folder";
    }
  });
}

// ==========================================
// --- 2. Guidance Guru Logic ---
// ==========================================
const guidanceMessagesEl = document.getElementById("guidance-messages");
const guidanceForm = document.getElementById("guidance-chat-form");
const guidanceInput = document.getElementById("guidance-chat-text");
const goalHeaderEl = document.getElementById("guidance-goal-header");
const goalTitleEl = document.getElementById("goal-title");
const goalProgressTextEl = document.getElementById("goal-progress-text");
const goalStatusPillEl = document.getElementById("goal-status-pill");
const guidanceResetBtn = document.getElementById("guidance-reset-btn");
const guidanceWelcomeEl = document.getElementById("guidance-welcome");

function updateGoalHeader(goalState, save = true) {
  if (!goalState || !goalState.goal) {
    if (goalHeaderEl) goalHeaderEl.classList.add("hidden");
    if (save) localStorage.removeItem(STORAGE_KEYS.guidanceGoal);
    return;
  }
  if (!goalHeaderEl) return;
  goalHeaderEl.classList.remove("hidden");
  goalTitleEl.textContent = goalState.goal;
  const pct = goalState.progress_pct !== null && goalState.progress_pct !== undefined ? `${goalState.progress_pct}%` : "0%";
  goalProgressTextEl.textContent = `${goalState.current || "Current"} ➔ ${goalState.target || "Target"} (${pct})`;

  const status = (goalState.status || "On Track").trim();
  goalStatusPillEl.textContent = status;
  goalStatusPillEl.className = "goal-status-pill";
  if (status.toLowerCase().includes("risk")) {
    goalStatusPillEl.classList.add("status-risk");
  } else if (status.toLowerCase().includes("achieved") || status.toLowerCase().includes("done")) {
    goalStatusPillEl.classList.add("status-achieved");
  } else {
    goalStatusPillEl.classList.add("status-ontrack");
  }

  if (save) {
    saveStorage(STORAGE_KEYS.guidanceGoal, goalState);
  }
}

function addGuidanceBubble(role, text, sources, save = true) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  formatBubbleContent(bubble, role, text);

  if (sources && sources.length) {
    const sourcesEl = document.createElement("div");
    sourcesEl.className = "sources";
    sources.forEach((s) => {
      const tag = document.createElement("span");
      tag.className = "source-tag";
      tag.textContent = s;
      sourcesEl.appendChild(tag);
    });
    bubble.appendChild(sourcesEl);
  }

  guidanceMessagesEl.appendChild(bubble);
  guidanceMessagesEl.scrollTop = guidanceMessagesEl.scrollHeight;

  if (save) {
    appendStorageMessage(STORAGE_KEYS.guidanceHistory, { role, text, sources: sources || [] });
  }
}

if (guidanceForm) {
  guidanceForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = guidanceInput.value.trim();
    if (!message) return;

    if (guidanceWelcomeEl) {
      guidanceWelcomeEl.style.display = "none";
    }

    addGuidanceBubble("user", message, null, true);
    guidanceInput.value = "";
    guidanceInput.disabled = true;

    try {
      const res = await fetch("/api/guidance/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();
      if (!res.ok) {
        addGuidanceBubble("error", data.error || "Something went wrong.", null, true);
      } else {
        addGuidanceBubble("assistant", data.answer, data.sources, true);
        if (data.goal_state) {
          updateGoalHeader(data.goal_state, true);
        }
      }
    } catch (err) {
      addGuidanceBubble("error", "Network error — is the server running?", null, true);
    } finally {
      guidanceInput.disabled = false;
      guidanceInput.focus();
    }
  });
}

document.querySelectorAll("#tab-guidance-guru .prompt-chips .chip, #tab-guidance-guru .prompt-card").forEach((chip) => {
  chip.addEventListener("click", () => {
    const prompt = chip.dataset.prompt;
    if (prompt && guidanceInput) {
      guidanceInput.value = prompt;
      guidanceForm.dispatchEvent(new Event("submit"));
    }
  });
});

if (guidanceResetBtn) {
  guidanceResetBtn.addEventListener("click", async () => {
    if (!confirm("Reset the current goal and conversation history?")) return;
    try {
      await fetch("/api/guidance/reset", { method: "POST" });
      updateGoalHeader(null, true);
      localStorage.removeItem(STORAGE_KEYS.guidanceHistory);
      guidanceMessagesEl.innerHTML = "";
      if (guidanceWelcomeEl) {
        guidanceWelcomeEl.style.display = "block";
        guidanceMessagesEl.appendChild(guidanceWelcomeEl);
      }
    } catch (err) {
      console.error("Failed to reset guidance session", err);
    }
  });
}

// ==========================================
// --- 3. Solution Mate Logic ---
// ==========================================
const solutionMessagesEl = document.getElementById("solution-messages");
const solutionForm = document.getElementById("solution-chat-form");
const solutionInput = document.getElementById("solution-chat-text");
const solutionHeaderEl = document.getElementById("solution-insight-header");
const solutionTitleEl = document.getElementById("solution-title");
const solutionImpactTextEl = document.getElementById("solution-impact-text");
const solutionConfidencePillEl = document.getElementById("solution-confidence-pill");
const solutionResetBtn = document.getElementById("solution-reset-btn");
const solutionWelcomeEl = document.getElementById("solution-welcome");

function updateSolutionHeader(analysis, save = true) {
  if (!analysis || !analysis.primary_driver) {
    if (solutionHeaderEl) solutionHeaderEl.classList.add("hidden");
    if (save) localStorage.removeItem(STORAGE_KEYS.solutionAnalysis);
    return;
  }
  if (!solutionHeaderEl) return;
  solutionHeaderEl.classList.remove("hidden");
  solutionTitleEl.textContent = analysis.primary_driver;
  solutionImpactTextEl.textContent = analysis.expected_impact ? `Impact: ${analysis.expected_impact}` : "";

  const conf = (analysis.confidence || "High").trim();
  solutionConfidencePillEl.textContent = `${conf} Confidence`;
  solutionConfidencePillEl.className = "goal-status-pill";
  if (conf.toLowerCase().includes("low")) {
    solutionConfidencePillEl.classList.add("status-risk");
  } else if (conf.toLowerCase().includes("med")) {
    solutionConfidencePillEl.classList.add("status-ontrack");
  } else {
    solutionConfidencePillEl.classList.add("status-achieved");
  }

  if (save) {
    saveStorage(STORAGE_KEYS.solutionAnalysis, analysis);
  }
}

function addSolutionBubble(role, text, sources, save = true) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  formatBubbleContent(bubble, role, text);

  if (sources && sources.length) {
    const sourcesEl = document.createElement("div");
    sourcesEl.className = "sources";
    sources.forEach((s) => {
      const tag = document.createElement("span");
      tag.className = "source-tag";
      tag.textContent = s;
      sourcesEl.appendChild(tag);
    });
    bubble.appendChild(sourcesEl);
  }

  solutionMessagesEl.appendChild(bubble);
  solutionMessagesEl.scrollTop = solutionMessagesEl.scrollHeight;

  if (save) {
    appendStorageMessage(STORAGE_KEYS.solutionHistory, { role, text, sources: sources || [] });
  }
}

if (solutionForm) {
  solutionForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = solutionInput.value.trim();
    if (!message) return;

    if (solutionWelcomeEl) {
      solutionWelcomeEl.style.display = "none";
    }

    addSolutionBubble("user", message, null, true);
    solutionInput.value = "";
    solutionInput.disabled = true;

    try {
      const res = await fetch("/api/solution/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();
      if (!res.ok) {
        addSolutionBubble("error", data.error || "Something went wrong.", null, true);
      } else {
        addSolutionBubble("assistant", data.answer, data.sources, true);
        if (data.analysis) {
          updateSolutionHeader(data.analysis, true);
        }
      }
    } catch (err) {
      addSolutionBubble("error", "Network error — is the server running?", null, true);
    } finally {
      solutionInput.disabled = false;
      solutionInput.focus();
    }
  });
}

document.querySelectorAll("#tab-solution-mate .prompt-chips .chip, #tab-solution-mate .prompt-card").forEach((chip) => {
  chip.addEventListener("click", () => {
    const prompt = chip.dataset.prompt;
    if (prompt && solutionInput) {
      solutionInput.value = prompt;
      solutionForm.dispatchEvent(new Event("submit"));
    }
  });
});

if (solutionResetBtn) {
  solutionResetBtn.addEventListener("click", async () => {
    if (!confirm("Reset this solution analysis and conversation history?")) return;
    try {
      await fetch("/api/solution/reset", { method: "POST" });
      updateSolutionHeader(null, true);
      localStorage.removeItem(STORAGE_KEYS.solutionHistory);
      solutionMessagesEl.innerHTML = "";
      if (solutionWelcomeEl) {
        solutionWelcomeEl.style.display = "block";
        solutionMessagesEl.appendChild(solutionWelcomeEl);
      }
    } catch (err) {
      console.error("Failed to reset solution session", err);
    }
  });
}

// ==========================================
// --- 4. Utility Minion Logic ---
// ==========================================
const utilityMessagesEl = document.getElementById("utility-messages");
const utilityForm = document.getElementById("utility-chat-form");
const utilityInput = document.getElementById("utility-chat-text");
const utilityWelcomeEl = document.getElementById("utility-welcome");

function addUtilityBubble(role, text, draft, save = true) {
  if (utilityWelcomeEl) utilityWelcomeEl.style.display = "none";
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  formatBubbleContent(bubble, role, text);

  if (draft && draft.headline) {
    const draftBadge = document.createElement("div");
    draftBadge.className = "sources";
    const tag = document.createElement("span");
    tag.className = "source-tag";
    tag.textContent = `📋 Draft: ${draft.headline} (${draft.content_type || "Copy"})`;
    draftBadge.appendChild(tag);
    bubble.appendChild(draftBadge);
  }

  utilityMessagesEl.appendChild(bubble);
  utilityMessagesEl.scrollTop = utilityMessagesEl.scrollHeight;

  if (save) {
    appendStorageMessage(STORAGE_KEYS.utilityHistory, { role, text, draft: draft || null });
  }
}

if (utilityForm) {
  utilityForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = utilityInput.value.trim();
    if (!message) return;

    if (utilityWelcomeEl) utilityWelcomeEl.style.display = "none";
    addUtilityBubble("user", message, null, true);
    utilityInput.value = "";
    utilityInput.disabled = true;

    try {
      const res = await fetch("/api/utility/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();
      if (!res.ok) {
        addUtilityBubble("error", data.error || "Something went wrong.", null, true);
      } else {
        addUtilityBubble("assistant", data.answer, data.draft, true);
      }
    } catch (err) {
      addUtilityBubble("error", "Network error — is the server running?", null, true);
    } finally {
      utilityInput.disabled = false;
      utilityInput.focus();
    }
  });
}

document.querySelectorAll("#tab-utility-minion .prompt-chips .chip, #tab-utility-minion .prompt-card").forEach((chip) => {
  chip.addEventListener("click", () => {
    const prompt = chip.dataset.prompt;
    if (prompt && utilityInput) {
      utilityInput.value = prompt;
      utilityForm.dispatchEvent(new Event("submit"));
    }
  });
});

// ==========================================
// --- 5. Global Clear All Chats ---
// ==========================================
const clearAllBtn = document.getElementById("clear-all-chats-btn");
if (clearAllBtn) {
  clearAllBtn.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to clear all chat histories across all agents?")) {
      return;
    }

    // 1. Clear LocalStorage
    localStorage.removeItem(STORAGE_KEYS.multiAgentHistory);
    localStorage.removeItem(STORAGE_KEYS.infoHistory);
    localStorage.removeItem(STORAGE_KEYS.guidanceHistory);
    localStorage.removeItem(STORAGE_KEYS.guidanceGoal);
    localStorage.removeItem(STORAGE_KEYS.solutionHistory);
    localStorage.removeItem(STORAGE_KEYS.solutionAnalysis);
    localStorage.removeItem(STORAGE_KEYS.utilityHistory);
    localStorage.removeItem(STORAGE_KEYS.utilityDraft);

    // 2. Clear Multi Agent UI
    if (multiAgentMessagesEl) {
      multiAgentMessagesEl.innerHTML = "";
      if (multiAgentWelcomeEl) {
        multiAgentWelcomeEl.style.display = "block";
        multiAgentMessagesEl.appendChild(multiAgentWelcomeEl);
      }
    }

    // 3. Clear Information Escort UI
    if (messagesEl) {
      messagesEl.innerHTML = "";
      if (infoWelcomeEl) {
        infoWelcomeEl.style.display = "block";
        messagesEl.appendChild(infoWelcomeEl);
      }
    }

    // 4. Clear Guidance Guru UI
    if (guidanceMessagesEl) {
      guidanceMessagesEl.innerHTML = "";
      if (guidanceWelcomeEl) {
        guidanceWelcomeEl.style.display = "block";
        guidanceMessagesEl.appendChild(guidanceWelcomeEl);
      }
    }
    updateGoalHeader(null, false);

    // 5. Clear Solution Mate UI
    if (solutionMessagesEl) {
      solutionMessagesEl.innerHTML = "";
      if (solutionWelcomeEl) {
        solutionWelcomeEl.style.display = "block";
        solutionMessagesEl.appendChild(solutionWelcomeEl);
      }
    }
    updateSolutionHeader(null, false);

    // 6. Clear Utility Minion UI
    if (utilityMessagesEl) {
      utilityMessagesEl.innerHTML = "";
      if (utilityWelcomeEl) {
        utilityWelcomeEl.style.display = "block";
        utilityMessagesEl.appendChild(utilityWelcomeEl);
      }
    }

    // 7. Reset server-side session state
    try {
      await fetch("/api/clear_all", { method: "POST" });
    } catch (e) {
      console.error("Failed to clear server session", e);
    }
  });
}

// ==========================================
// --- 6. Restore Chat Histories on Load ---
// ==========================================
(function restoreChatHistories() {
  // Restore Multi Agent
  const savedMulti = loadStorage(STORAGE_KEYS.multiAgentHistory) || [];
  if (multiAgentMessagesEl) {
    if (savedMulti.length > 0 && multiAgentWelcomeEl) {
      multiAgentWelcomeEl.style.display = "none";
    }
    savedMulti.forEach((item) =>
      addMultiAgentBubble(item.role, item.text, item.routingData, item.sources, false)
    );
  }

  // Restore Information Escort
  const savedInfo = loadStorage(STORAGE_KEYS.infoHistory) || [];
  if (messagesEl) {
    if (savedInfo.length > 0 && infoWelcomeEl) {
      infoWelcomeEl.style.display = "none";
    }
    savedInfo.forEach((item) => addBubble(item.role, item.text, item.sources, false));
  }

  // Restore Guidance Guru
  const savedGuidance = loadStorage(STORAGE_KEYS.guidanceHistory) || [];
  if (guidanceMessagesEl) {
    if (savedGuidance.length > 0 && guidanceWelcomeEl) {
      guidanceWelcomeEl.style.display = "none";
    }
    savedGuidance.forEach((item) => addGuidanceBubble(item.role, item.text, item.sources, false));
  }

  // Restore Goal State
  const savedGoal = loadStorage(STORAGE_KEYS.guidanceGoal);
  if (savedGoal) {
    updateGoalHeader(savedGoal, false);
  } else {
    fetch("/api/guidance/state")
      .then((r) => r.json())
      .then((data) => {
        if (data && data.goal_state) updateGoalHeader(data.goal_state, true);
      })
      .catch(() => {});
  }

  // Restore Solution Mate
  const savedSolution = loadStorage(STORAGE_KEYS.solutionHistory) || [];
  if (solutionMessagesEl) {
    if (savedSolution.length > 0 && solutionWelcomeEl) {
      solutionWelcomeEl.style.display = "none";
    }
    savedSolution.forEach((item) => addSolutionBubble(item.role, item.text, item.sources, false));
  }

  // Restore Solution Analysis
  const savedAnalysis = loadStorage(STORAGE_KEYS.solutionAnalysis);
  if (savedAnalysis) {
    updateSolutionHeader(savedAnalysis, false);
  } else {
    fetch("/api/solution/state")
      .then((r) => r.json())
      .then((data) => {
        if (data && data.analysis) updateSolutionHeader(data.analysis, true);
      })
      .catch(() => {});
  }

  // Restore Utility Minion
  const savedUtility = loadStorage(STORAGE_KEYS.utilityHistory) || [];
  if (utilityMessagesEl) {
    if (savedUtility.length > 0 && utilityWelcomeEl) {
      utilityWelcomeEl.style.display = "none";
    }
    savedUtility.forEach((item) => addUtilityBubble(item.role, item.text, item.draft, false));
  }

  fetch("/api/store_info")
    .then((r) => r.json())
    .then((data) => {
      if (data) {
        const nameEl = document.getElementById("header-store-name");
        const revEl = document.getElementById("header-store-rev");
        const targetEl = document.getElementById("header-store-target");
        if (nameEl && data.store_name) nameEl.textContent = data.store_name;
        if (revEl && data.current_revenue) revEl.textContent = data.current_revenue;
        if (targetEl && data.target_revenue) targetEl.textContent = data.target_revenue;
      }
    })
    .catch(() => {});
})();

refreshDocuments();

// ==========================================
// --- 6. Visualizer Modal & 11 Questions Logic ---
// ==========================================
const visualizerModal = document.getElementById("visualizer-modal");
const openVisualizerBtn = document.getElementById("open-visualizer-btn");
const closeVisualizerBtn = document.getElementById("close-visualizer-btn");
const rawStoreJsonEl = document.getElementById("raw-store-json");

function openVisualizer() {
  if (visualizerModal) {
    visualizerModal.classList.remove("hidden");
    loadRawStoreJson();
  }
}

function closeVisualizer() {
  if (visualizerModal) {
    visualizerModal.classList.add("hidden");
  }
}

if (openVisualizerBtn) {
  openVisualizerBtn.addEventListener("click", openVisualizer);
}

if (closeVisualizerBtn) {
  closeVisualizerBtn.addEventListener("click", closeVisualizer);
}

if (visualizerModal) {
  visualizerModal.addEventListener("click", (e) => {
    if (e.target === visualizerModal) {
      closeVisualizer();
    }
  });
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && visualizerModal && !visualizerModal.classList.contains("hidden")) {
    closeVisualizer();
  }
});

// Modal tab switching
document.querySelectorAll(".vtab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".vtab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".vtab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    const targetPanel = document.getElementById(btn.dataset.vtab);
    if (targetPanel) targetPanel.classList.add("active");
  });
});

// Load Raw Store JSON
async function loadRawStoreJson() {
  if (!rawStoreJsonEl) return;
  try {
    const res = await fetch("/api/store_analytics");
    if (res.ok) {
      const data = await res.json();
      rawStoreJsonEl.textContent = JSON.stringify(data, null, 2);
    }
  } catch (err) {
    rawStoreJsonEl.textContent = "Error loading store analytics JSON.";
  }
}

// 11 Questions Click-to-Ask Handler
document.querySelectorAll(".btn-ask-q").forEach((btn) => {
  btn.addEventListener("click", () => {
    const targetTab = btn.dataset.tab;
    const prompt = btn.dataset.prompt;
    if (!targetTab || !prompt) return;

    // 1. Close modal
    closeVisualizer();

    // 2. Switch tab
    const tabBtn = document.querySelector(`.tab-btn[data-tab="${targetTab}"]`);
    if (tabBtn) tabBtn.click();

    // 3. Populate input and submit after small tick to ensure DOM is ready
    setTimeout(() => {
      if (targetTab === "multi-agent") {
        if (multiAgentInput && multiAgentForm) {
          multiAgentInput.value = prompt;
          multiAgentForm.dispatchEvent(new Event("submit"));
        }
      } else if (targetTab === "utility-minion") {
        if (utilityInput && utilityForm) {
          utilityInput.value = prompt;
          utilityForm.dispatchEvent(new Event("submit"));
        }
      } else if (targetTab === "information-escort") {
        if (chatInput && chatForm) {
          chatInput.value = prompt;
          chatForm.dispatchEvent(new Event("submit"));
        }
      } else if (targetTab === "guidance-guru") {
        if (guidanceInput && guidanceForm) {
          guidanceInput.value = prompt;
          guidanceForm.dispatchEvent(new Event("submit"));
        }
      } else if (targetTab === "solution-mate") {
        if (solutionInput && solutionForm) {
          solutionInput.value = prompt;
          solutionForm.dispatchEvent(new Event("submit"));
        }
      }
    }, 80);
  });
});
