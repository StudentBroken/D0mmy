// Content script — confirms harvest with a brief visual flash on the selection
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "harvest_ack") {
    flashSelection();
  }
});

function flashSelection() {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed) return;
  const range = sel.getRangeAt(0);
  const mark = document.createElement("mark");
  mark.style.cssText =
    "background:rgba(0,200,100,0.35);transition:background 0.6s;border-radius:2px;";
  try {
    range.surroundContents(mark);
    setTimeout(() => {
      const parent = mark.parentNode;
      if (parent) {
        while (mark.firstChild) parent.insertBefore(mark.firstChild, mark);
        parent.removeChild(mark);
      }
    }, 800);
  } catch (_) {
    // surroundContents fails on partial selections across elements — silently skip
  }
}
