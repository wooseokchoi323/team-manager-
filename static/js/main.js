
// Sidebar Toggle
document.getElementById("sidebarToggle")?.addEventListener("click", () => {
  document.getElementById("sidebar").classList.toggle("open");
});

// ── Kanban Drag & Drop ──────────────────────────
function initKanban() {
  const cards = document.querySelectorAll(".task-card[data-id]");
  const cols = document.querySelectorAll(".k-col[data-status]");
  let dragged = null;

  cards.forEach(card => {
    card.setAttribute("draggable", "true");
    card.addEventListener("dragstart", e => {
      dragged = card; card.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("dragging"); dragged = null;
      cols.forEach(c => c.classList.remove("drag-over"));
    });
  });

  cols.forEach(col => {
    col.addEventListener("dragover", e => { e.preventDefault(); col.classList.add("drag-over"); });
    col.addEventListener("dragleave", () => col.classList.remove("drag-over"));
    col.addEventListener("drop", async e => {
      e.preventDefault(); col.classList.remove("drag-over");
      if (!dragged) return;
      const id = dragged.dataset.id;
      const newStatus = col.dataset.status;
      const oldStatus = dragged.dataset.status;
      if (newStatus === oldStatus) return;
      try {
        const res = await fetch("/api/tasks/" + id + "/status", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({status: newStatus})
        });
        if (res.ok) {
          col.querySelector(".k-cards").appendChild(dragged);
          dragged.dataset.status = newStatus;
          const fill = dragged.querySelector(".prog-fill");
          if (fill && newStatus === "done") fill.style.width = "100%";
          updateCounts();
          toast("✅ 업무 상태가 변경되었습니다.");
        }
      } catch(err) { toast("❌ 오류가 발생했습니다.", "e"); }
    });
  });
}

function updateCounts() {
  document.querySelectorAll(".k-col[data-status]").forEach(col => {
    const n = col.querySelectorAll(".task-card").length;
    const el = col.querySelector(".k-cnt");
    if (el) el.textContent = n;
  });
}

// ── Toast ──────────────────────────────────────
function toast(msg, type = "s") {
  const el = document.createElement("div");
  el.className = "toast-n toast-" + type;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.classList.add("show"), 10);
  setTimeout(() => { el.classList.remove("show"); setTimeout(() => el.remove(), 300); }, 2800);
}

// ── Progress Slider ─────────────────────────────
function initSlider() {
  const s = document.getElementById("progress");
  const d = document.getElementById("prog-display");
  if (s && d) {
    s.addEventListener("input", () => { d.textContent = s.value + "%"; });
  }
}

// ── Quick Status Update ─────────────────────────
async function quickStatus(tid, status) {
  const res = await fetch("/api/tasks/" + tid + "/status", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({status: status})
  });
  if (res.ok) { toast("✅ 상태가 변경되었습니다."); location.reload(); }
}

// ── Init ────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  if (document.querySelector(".kanban-grid")) initKanban();
  initSlider();
});
