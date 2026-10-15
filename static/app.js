// --- Storage Keys & Helpers ---
const STORAGE_KEYS = {
  infoHistory: "chatbot_history_info",
  guidanceHistory: "chatbot_history_guidance",
  guidanceGoal: "chatbot_guidance_goal",
  solutionHistory: "chatbot_history_solution",
  solutionAnalysis: "chatbot_solution_analysis",
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

function addBubble(role, text, sources, save = true) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role}`;
  bubble.textContent = text;

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
  bubble.textContent = text;

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

document.querySelectorAll("#tab-guidance-guru .prompt-chips .chip").forEach((chip) => {
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
  bubble.textContent = text;

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

document.querySelectorAll("#tab-solution-mate .prompt-chips .chip").forEach((chip) => {
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
// --- 4. Global Clear All Chats ---
// ==========================================
const clearAllBtn = document.getElementById("clear-all-chats-btn");
if (clearAllBtn) {
  clearAllBtn.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to clear all chat histories across all agents?")) {
      return;
    }

    // 1. Clear LocalStorage
    localStorage.removeItem(STORAGE_KEYS.infoHistory);
    localStorage.removeItem(STORAGE_KEYS.guidanceHistory);
    localStorage.removeItem(STORAGE_KEYS.guidanceGoal);
    localStorage.removeItem(STORAGE_KEYS.solutionHistory);
    localStorage.removeItem(STORAGE_KEYS.solutionAnalysis);

    // 2. Clear Information Escort UI
    if (messagesEl) messagesEl.innerHTML = "";

    // 3. Clear Guidance Guru UI
    if (guidanceMessagesEl) {
      guidanceMessagesEl.innerHTML = "";
      if (guidanceWelcomeEl) {
        guidanceWelcomeEl.style.display = "block";
        guidanceMessagesEl.appendChild(guidanceWelcomeEl);
      }
    }
    updateGoalHeader(null, false);

    // 4. Clear Solution Mate UI
    if (solutionMessagesEl) {
      solutionMessagesEl.innerHTML = "";
      if (solutionWelcomeEl) {
        solutionWelcomeEl.style.display = "block";
        solutionMessagesEl.appendChild(solutionWelcomeEl);
      }
    }
    updateSolutionHeader(null, false);

    // 5. Reset server-side session state
    try {
      await fetch("/api/clear_all", { method: "POST" });
    } catch (e) {
      console.error("Failed to clear server session", e);
    }
  });
}

// ==========================================
// --- 5. Restore Chat Histories on Load ---
// ==========================================
(function restoreChatHistories() {
  // Restore Information Escort
  const savedInfo = loadStorage(STORAGE_KEYS.infoHistory) || [];
  if (messagesEl) {
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
})();

refreshDocuments();
