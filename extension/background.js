const WS_URL = "ws://localhost:8000/ws/extension/harvester";
const RECONNECT_DELAY_MS = 3000;

let socket = null;
let pendingMessages = [];

function connect() {
  socket = new WebSocket(WS_URL);

  socket.addEventListener("open", () => {
    console.log("[D0mmy] Connected to orchestrator");
    pendingMessages.forEach((m) => socket.send(JSON.stringify(m)));
    pendingMessages = [];
  });

  socket.addEventListener("message", (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === "ack") {
        console.log("[D0mmy] Harvested:", msg.payload);
      }
    } catch (_) {}
  });

  socket.addEventListener("close", () => {
    console.warn("[D0mmy] Disconnected. Reconnecting in", RECONNECT_DELAY_MS, "ms");
    socket = null;
    setTimeout(connect, RECONNECT_DELAY_MS);
  });

  socket.addEventListener("error", () => {
    socket?.close();
  });
}

function send(message) {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(message));
  } else {
    pendingMessages.push(message);
  }
}

// Hotkey fires the harvest command
chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "harvest") return;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;

  const results = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) return null;
      const range = sel.getRangeAt(0);
      const div = document.createElement("div");
      div.appendChild(range.cloneContents());
      return { html: div.innerHTML, url: window.location.href };
    },
  });

  const result = results?.[0]?.result;
  if (!result?.html) return;

  // Convert in the service worker context
  const markdown = htmlToMarkdown(result.html);
  if (!markdown.trim()) return;

  send({
    type: "harvest",
    payload: { text: markdown, url: result.url },
    session_id: "harvester",
    timestamp: new Date().toISOString(),
  });
});

// Minimal HTML → Markdown converter (no DOM available in service worker)
function htmlToMarkdown(html) {
  return html
    .replace(/<h[1-6][^>]*>([\s\S]*?)<\/h[1-6]>/gi, (_, t) => `\n# ${stripTags(t)}\n`)
    .replace(/<strong[^>]*>([\s\S]*?)<\/strong>/gi, (_, t) => `**${stripTags(t)}**`)
    .replace(/<b[^>]*>([\s\S]*?)<\/b>/gi, (_, t) => `**${stripTags(t)}**`)
    .replace(/<em[^>]*>([\s\S]*?)<\/em>/gi, (_, t) => `_${stripTags(t)}_`)
    .replace(/<i[^>]*>([\s\S]*?)<\/i>/gi, (_, t) => `_${stripTags(t)}_`)
    .replace(/<code[^>]*>([\s\S]*?)<\/code>/gi, (_, t) => `\`${stripTags(t)}\``)
    .replace(/<a[^>]*href="([^"]*)"[^>]*>([\s\S]*?)<\/a>/gi, (_, href, text) => `[${stripTags(text)}](${href})`)
    .replace(/<li[^>]*>([\s\S]*?)<\/li>/gi, (_, t) => `- ${stripTags(t).trim()}\n`)
    .replace(/<p[^>]*>([\s\S]*?)<\/p>/gi, (_, t) => `${stripTags(t).trim()}\n\n`)
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#039;/g, "'")
    .replace(/&nbsp;/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function stripTags(html) {
  return html.replace(/<[^>]+>/g, "");
}

connect();
