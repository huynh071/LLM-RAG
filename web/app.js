const chat = document.getElementById("chat");
const form = document.getElementById("promptForm");
const promptInput = document.getElementById("prompt");
const sendButton = document.getElementById("sendButton");
const statusBadge = document.getElementById("statusBadge");
const statusText = document.getElementById("statusText");

let requestInProgress = false;

function scrollToBottom() {
  chat.scrollTop = chat.scrollHeight;
}

function resizePrompt() {
  promptInput.style.height = "auto";
  promptInput.style.height =
    `${Math.min(promptInput.scrollHeight, 180)}px`;
}

function createMessage(role, text, sources = []) {
  const message = document.createElement("article");
  message.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = role === "assistant" ? "R" : "Y";

  const body = document.createElement("div");
  body.className = "message-body";

  const label = document.createElement("p");
  label.className = "message-label";
  label.textContent = role === "assistant" ? "RAG Assistant" : "You";

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = text;

  body.append(label, bubble);

  if (sources.length > 0) {
    const details = document.createElement("details");
    details.className = "sources";

    const summary = document.createElement("summary");
    summary.textContent =
      `${sources.length} retrieved source${sources.length === 1 ? "" : "s"}`;

    const list = document.createElement("ol");

    for (const source of sources) {
      const item = document.createElement("li");
      item.textContent = source;
      list.appendChild(item);
    }

    details.append(summary, list);
    body.appendChild(details);
  }

  message.append(avatar, body);
  chat.appendChild(message);
  scrollToBottom();

  return message;
}

function createLoadingMessage() {
  const message = document.createElement("article");
  message.className = "message assistant";

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = "R";

  const body = document.createElement("div");
  body.className = "message-body";

  const label = document.createElement("p");
  label.className = "message-label";
  label.textContent = "RAG Assistant";

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  const dots = document.createElement("div");
  dots.className = "loading-dots";
  dots.setAttribute("aria-label", "Generating answer");

  for (let index = 0; index < 3; index += 1) {
    dots.appendChild(document.createElement("span"));
  }

  bubble.appendChild(dots);
  body.append(label, bubble);
  message.append(avatar, body);
  chat.appendChild(message);
  scrollToBottom();

  return message;
}

function setBusy(busy) {
  requestInProgress = busy;
  sendButton.disabled = busy;
  promptInput.disabled = busy;
  form.setAttribute("aria-busy", String(busy));
}

async function submitPrompt(question) {
  if (!question || requestInProgress) {
    return;
  }

  document.getElementById("welcome")?.remove();

  createMessage("user", question);

  promptInput.value = "";
  resizePrompt();
  setBusy(true);

  const loadingMessage = createLoadingMessage();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        prompt: question
      })
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail || `Request failed with status ${response.status}`
      );
    }

    loadingMessage.remove();
    createMessage("assistant", data.answer, data.sources || []);
  } catch (error) {
    loadingMessage.remove();

    createMessage(
      "assistant",
      `I couldn't generate an answer. ${error.message}`
    );
  } finally {
    setBusy(false);
    promptInput.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitPrompt(promptInput.value.trim());
});

promptInput.addEventListener("input", resizePrompt);

promptInput.addEventListener("keydown", (event) => {
  if (
    event.key === "Enter" &&
    !event.shiftKey &&
    !event.isComposing
  ) {
    event.preventDefault();
    form.requestSubmit();
  }
});

for (const suggestion of document.querySelectorAll(".suggestion")) {
  suggestion.addEventListener("click", () => {
    submitPrompt(suggestion.dataset.prompt);
  });
}

async function checkApiStatus() {
  try {
    const response = await fetch("/api/health", {
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error("Health check failed");
    }

    statusBadge.dataset.state = "online";
    statusText.textContent = "RAG online";
  } catch {
    statusBadge.dataset.state = "offline";
    statusText.textContent = "RAG offline";
  }
}

resizePrompt();
checkApiStatus();
promptInput.focus();