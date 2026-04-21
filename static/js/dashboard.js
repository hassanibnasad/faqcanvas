const faqForm = document.getElementById("faq-form");
const faqIdInput = document.getElementById("faq-id");
const questionInput = document.getElementById("question");
const answerInput = document.getElementById("answer");
const faqList = document.getElementById("faq-list");
const messageBox = document.getElementById("message-box");
const resetButton = document.getElementById("reset-button");
const faqCount = document.getElementById("faq-count");
const faqImportForm = document.getElementById("faq-import-form");
const faqImportInput = document.getElementById("faq-import-file");
const faqImportButton = document.getElementById("faq-import-button");
const widgetToggleButton = document.getElementById("dashboard-widget-toggle");
const widgetLauncherButton = document.getElementById("dashboard-widget-launcher");
const widgetCloseButton = document.getElementById("dashboard-widget-close");
const widgetPanel = document.getElementById("dashboard-widget-panel");
const widgetFrame = document.getElementById("dashboard-widget-frame");
const widgetUrl = window.dashboardConfig.widgetUrl;

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showMessage(message, type = "success") {
  messageBox.textContent = message;
  messageBox.className =
    "mt-4 rounded-2xl px-4 py-3 text-sm " +
    (type === "success"
      ? "bg-emerald-50 text-emerald-700"
      : "bg-rose-50 text-rose-700");
  messageBox.classList.remove("hidden");
}

function clearForm() {
  faqIdInput.value = "";
  questionInput.value = "";
  answerInput.value = "";
}

function setImportState(isLoading) {
  if (!faqImportButton) return;

  faqImportButton.disabled = isLoading;
  faqImportButton.textContent = isLoading ? "Uploading..." : "Upload FAQs";
}

function openWidgetPreview() {
  if (!widgetPanel || !widgetFrame) return;

  if (!widgetFrame.src) {
    widgetFrame.src = widgetUrl;
  }

  widgetPanel.classList.remove("hidden");
  if (widgetLauncherButton) {
    widgetLauncherButton.classList.add("hidden");
    widgetLauncherButton.classList.remove("inline-flex");
  }

  if (widgetToggleButton) {
    widgetToggleButton.textContent = "Close Preview";
  }
}

function closeWidgetPreview() {
  if (!widgetPanel) return;

  widgetPanel.classList.add("hidden");
  if (widgetLauncherButton) {
    widgetLauncherButton.classList.remove("hidden");
    widgetLauncherButton.classList.add("inline-flex");
  }

  if (widgetToggleButton) {
    widgetToggleButton.textContent = "Open Preview";
  }
}

function toggleWidgetPreview() {
  if (!widgetPanel) return;

  if (widgetPanel.classList.contains("hidden")) {
    openWidgetPreview();
    return;
  }

  closeWidgetPreview();
}

function createFaqCard(faq) {
  const card = document.createElement("div");
  card.className = "rounded-3xl border border-slate-200 p-5";
  card.innerHTML = `
    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div class="max-w-3xl">
        <p class="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-700">Question</p>
        <h3 class="mt-2 text-lg font-bold text-slate-900">${escapeHtml(faq.question)}</h3>
        <p class="mt-4 text-sm font-semibold uppercase tracking-[0.2em] text-cyan-700">Answer</p>
        <p class="mt-2 text-slate-600">${escapeHtml(faq.answer)}</p>
      </div>
      <div class="flex gap-3">
        <button data-action="edit" data-id="${faq.id}" class="rounded-2xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Edit</button>
        <button data-action="delete" data-id="${faq.id}" class="rounded-2xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white">Delete</button>
      </div>
    </div>
  `;

  card.querySelector('[data-action="edit"]').addEventListener("click", () => {
    faqIdInput.value = faq.id;
    questionInput.value = faq.question;
    answerInput.value = faq.answer;
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  card.querySelector('[data-action="delete"]').addEventListener("click", async () => {
    const confirmed = window.confirm("Delete this FAQ?");
    if (!confirmed) return;

    const response = await fetch(`/api/faqs/${faq.id}`, {
      method: "DELETE",
    });
    const result = await response.json();

    if (!response.ok) {
      showMessage(result.error || "Could not delete FAQ.", "error");
      return;
    }

    showMessage(result.message);
    loadFaqs();
    clearForm();
  });

  return card;
}

async function loadFaqs() {
  faqList.innerHTML = '<p class="text-sm text-slate-500">Loading FAQs...</p>';

  const response = await fetch("/api/faqs");
  const faqs = await response.json();

  faqList.innerHTML = "";

  if (!Array.isArray(faqs) || faqs.length === 0) {
    if (faqCount) {
      faqCount.textContent = "0";
    }

    faqList.innerHTML =
      '<div class="rounded-3xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">No FAQs added yet. Create your first FAQ above.</div>';
    return;
  }

  if (faqCount) {
    faqCount.textContent = String(faqs.length);
  }

  faqs.forEach((faq) => {
    faqList.appendChild(createFaqCard(faq));
  });
}

faqForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const faqId = faqIdInput.value;
  const payload = {
    question: questionInput.value.trim(),
    answer: answerInput.value.trim(),
  };

  const response = await fetch(faqId ? `/api/faqs/${faqId}` : "/api/faqs", {
    method: faqId ? "PUT" : "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const result = await response.json();

  if (!response.ok) {
    showMessage(result.error || "Could not save FAQ.", "error");
    return;
  }

  showMessage(result.message || "FAQ saved successfully.");
  clearForm();
  loadFaqs();
});

resetButton.addEventListener("click", clearForm);

if (faqImportForm && faqImportInput) {
  faqImportForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const file = faqImportInput.files?.[0];
    if (!file) {
      showMessage("Please choose a CSV or JSON file first.", "error");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setImportState(true);

    try {
      const response = await fetch("/api/faqs/import", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        showMessage(result.error || "Could not import FAQs.", "error");
        return;
      }

      faqImportForm.reset();
      showMessage(result.message || "FAQs imported successfully.");
      loadFaqs();
    } catch (error) {
      showMessage("Could not import FAQs right now.", "error");
    } finally {
      setImportState(false);
    }
  });
}

if (widgetToggleButton) {
  widgetToggleButton.addEventListener("click", toggleWidgetPreview);
}

if (widgetLauncherButton) {
  widgetLauncherButton.addEventListener("click", openWidgetPreview);
}

if (widgetCloseButton) {
  widgetCloseButton.addEventListener("click", closeWidgetPreview);
}

loadFaqs();
