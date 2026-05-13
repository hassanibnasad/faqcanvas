const chatBox = document.getElementById("chat-box");
const widgetForm = document.getElementById("widget-form");
const widgetQuestionInput = document.getElementById("widget-question");
const suggestionsPanel = document.getElementById("widget-suggestions-panel");
const suggestionsContainer = document.getElementById("widget-suggestions");
const widgetTitle = document.getElementById("widget-title");
const welcomeMessage = document.getElementById("widget-welcome-message");
const siteKey = window.widgetConfig.siteKey;

function addMessage(text, sender = "bot") {
  const bubble = document.createElement("div");
  bubble.className =
    sender === "user"
      ? "widget-fade-in ml-auto max-w-[88%] rounded-[1.25rem] rounded-br-md bg-slate-900 px-4 py-3 text-sm leading-6 text-white"
      : "widget-fade-in max-w-[88%] rounded-[1.25rem] rounded-tl-md bg-white px-4 py-3 text-sm leading-6 text-slate-700 shadow-sm";
  bubble.textContent = text;
  chatBox.appendChild(bubble);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function renderSuggestions(suggestions) {
  if (!suggestionsPanel || !suggestionsContainer) return;

  suggestionsContainer.innerHTML = "";

  if (!Array.isArray(suggestions) || suggestions.length === 0) {
    suggestionsPanel.classList.add("hidden");
    return;
  }

  suggestions.forEach((suggestion) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className =
      "widget-suggestion rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700";
    button.textContent = suggestion;
    button.addEventListener("click", async () => {
      widgetQuestionInput.value = suggestion;
      await sendQuestion(suggestion);
    });
    suggestionsContainer.appendChild(button);
  });

  suggestionsPanel.classList.remove("hidden");
}

async function loadWidgetConfig() {
  if (!siteKey) return;

  try {
    const response = await fetch(
      `/api/widget/config?site_key=${encodeURIComponent(siteKey)}`
    );
    const result = await response.json();

    if (widgetTitle && result.site_name) {
      widgetTitle.textContent = result.site_name;
    }

    if (welcomeMessage && result.welcome_message) {
      welcomeMessage.textContent = result.welcome_message;
    }

    renderSuggestions(result.suggestions || []);
  } catch (error) {
    renderSuggestions([]);
  }
}

async function sendQuestion(question) {
  if (!question) return;

  addMessage(question, "user");
  widgetQuestionInput.value = "";

  const response = await fetch("/api/widget/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      site_key: siteKey,
    }),
  });

  const result = await response.json();
  addMessage(result.answer || "Sorry, something went wrong.");
}

widgetForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await sendQuestion(widgetQuestionInput.value.trim());
});

loadWidgetConfig();
