const chatBox = document.getElementById("chat-box");
const widgetForm = document.getElementById("widget-form");
const widgetQuestionInput = document.getElementById("widget-question");
const suggestionButtons = document.querySelectorAll(".widget-suggestion");
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

suggestionButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    widgetQuestionInput.value = button.textContent.trim();
    await sendQuestion(widgetQuestionInput.value.trim());
  });
});
