document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-text");
const uploadForm = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const uploadStatus = document.getElementById("upload-status");
const reindexBtn = document.getElementById("reindex-btn");
const docCountEl = document.getElementById("doc-count");
const docListEl = document.getElementById("doc-list");

function addBubble(role, text, sources) {
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

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  addBubble("user", message);
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
      addBubble("error", data.error || "Something went wrong.");
    } else {
      addBubble("assistant", data.answer, data.sources);
    }
  } catch (err) {
    addBubble("error", "Network error — is the server running?");
  } finally {
    chatInput.disabled = false;
    chatInput.focus();
  }
});

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

refreshDocuments();

// --- Guidance Guru Client Logic ---
const guidanceMessagesEl = document.getElementById("guidance-messages");
const guidanceForm = document.getElementById("guidance-chat-form");
const guidanceInput = document.getElementById("guidance-chat-text");
const goalHeaderEl = document.getElementById("guidance-goal-header");
const goalTitleEl = document.getElementById("goal-title");
const goalProgressTextEl = document.getElementById("goal-progress-text");
const goalStatusPillEl = document.getElementById("goal-status-pill");
const guidanceResetBtn = document.getElementById("guidance-reset-btn");
const guidanceWelcomeEl = document.getElementById("guidance-welcome");

function updateGoalHeader(goalState) {
  if (!goalState || !goalState.goal) {
    if (goalHeaderEl) goalHeaderEl.classList.add("hidden");
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
}

function addGuidanceBubble(role, text, sources) {
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
}

if (guidanceForm) {
  guidanceForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = guidanceInput.value.trim();
    if (!message) return;

    if (guidanceWelcomeEl) {
      guidanceWelcomeEl.style.display = "none";
    }

    addGuidanceBubble("user", message);
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
        addGuidanceBubble("error", data.error || "Something went wrong.");
      } else {
        addGuidanceBubble("assistant", data.answer, data.sources);
        if (data.goal_state) {
          updateGoalHeader(data.goal_state);
        }
      }
    } catch (err) {
      addGuidanceBubble("error", "Network error — is the server running?");
    } finally {
      guidanceInput.disabled = false;
      guidanceInput.focus();
    }
  });
}

document.querySelectorAll(".prompt-chips .chip").forEach((chip) => {
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
      updateGoalHeader(null);
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

// Check initial guidance state on load
(async function initGuidanceState() {
  try {
    const res = await fetch("/api/guidance/state");
    const data = await res.json();
    if (data.goal_state) {
      updateGoalHeader(data.goal_state);
    }
  } catch (e) {
    // optional initial state check
  }
})();

