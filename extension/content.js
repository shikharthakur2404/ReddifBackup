(function () {
  if (document.getElementById("rediff-archiver-hud")) return;

  // Build HUD Element
  const hud = document.createElement("div");
  hud.id = "rediff-archiver-hud";
  hud.innerHTML = `
    <div id="rediff-archiver-header">
      <div id="rediff-archiver-title">
        <span>⚡ REDIFF ARCHIVER HUD</span>
      </div>
      <button id="rediff-archiver-toggle" style="background:none; border:none; color:#8b949e; cursor:pointer;">–</button>
    </div>
    <div id="rediff-archiver-body">
      <div id="rediff-archiver-stats">
        <span id="rediff-stat-items">Mails with Attachments: 0</span>
        <span id="rediff-stat-status">Status: Idle</span>
      </div>
      <button id="btn-scan" class="hud-btn secondary">🔍 Scan Mail List</button>
      <button id="btn-download" class="hud-btn">⬇ Download Attachments in View</button>
      <div id="rediff-archiver-logs">Ready. Click 'Scan Mail List' to inspect current view.</div>
    </div>
  `;
  document.body.appendChild(hud);

  const logsEl = document.getElementById("rediff-archiver-logs");
  const statsEl = document.getElementById("rediff-stat-items");
  const statusEl = document.getElementById("rediff-stat-status");
  const btnScan = document.getElementById("btn-scan");
  const btnDownload = document.getElementById("btn-download");
  const btnToggle = document.getElementById("rediff-archiver-toggle");
  const bodyEl = document.getElementById("rediff-archiver-body");

  let isRunning = false;

  function log(msg) {
    const time = new Date().toTimeString().split(" ")[0];
    logsEl.innerHTML += `[${time}] ${msg}\n`;
    logsEl.scrollTop = logsEl.scrollHeight;
  }

  btnToggle.addEventListener("click", () => {
    if (bodyEl.style.display === "none") {
      bodyEl.style.display = "flex";
      btnToggle.innerText = "–";
      hud.classList.remove("minimized");
    } else {
      bodyEl.style.display = "none";
      btnToggle.innerText = "+";
      hud.classList.add("minimized");
    }
  });

  function getMailRows() {
    // Rediffmail Pro vayu uses list rows with checkboxes and subject/sender
    const rows = Array.from(document.querySelectorAll("div[class*='mail_list'], div[class*='row'], tr, div.mail-item, [role='row']"));
    const validRows = rows.filter(r => {
      // Must contain a checkbox or subject/sender text
      const hasCheckbox = r.querySelector("input[type='checkbox']") || r.querySelector("[class*='chk']");
      const hasSubject = r.innerText && r.innerText.includes("\n");
      return hasCheckbox && hasSubject;
    });

    if (validRows.length > 0) return validRows;

    // Fallback: search for paperclip or subject containers
    const rowsByCheckbox = Array.from(document.querySelectorAll("input[type='checkbox']"))
      .map(cb => cb.closest("div[class*='row'], tr, div[class*='item'], div[style*='display']"))
      .filter(Boolean);
    
    return [...new Set(rowsByCheckbox)];
  }

  function hasAttachment(row) {
    // Check for paperclip icon or SVG or text
    const text = row.innerHTML.toLowerCase();
    return text.includes("attachment") || text.includes("paperclip") || text.includes("clip") || text.includes("fa-paperclip");
  }

  btnScan.addEventListener("click", () => {
    const rows = getMailRows();
    const withAtt = rows.filter(hasAttachment);
    statsEl.innerText = `Mails: ${rows.length} | With Attachments: ${withAtt.length || 'Detected'}`;
    log(`Scanned view: Found ${rows.length} email entries.`);
  });

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  btnDownload.addEventListener("click", async () => {
    if (isRunning) return;
    isRunning = true;
    btnDownload.disabled = true;
    statusEl.innerText = "Status: Running";

    try {
      const rows = getMailRows();
      log(`Starting sequential download for ${rows.length} emails...`);

      for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        
        // Highlight current row
        const originalBg = row.style.backgroundColor;
        row.style.backgroundColor = "rgba(56, 139, 253, 0.2)";

        // Get sender / subject snippet
        const snippet = (row.innerText || "").split("\n").filter(Boolean).slice(0, 2).join(" - ").trim();
        log(`[${i + 1}/${rows.length}] Opening: ${snippet.substring(0, 40)}...`);

        // Click row to open preview
        const clickTarget = row.querySelector("a, span, [class*='subject']") || row;
        clickTarget.click();
        await sleep(1800);

        // Scan preview pane for attachment download links
        const attLinks = Array.from(document.querySelectorAll("a[href*='download'], a[href*='attachment'], a[download], [title*='Download']"));
        const validLinks = attLinks.filter(a => {
          const href = a.getAttribute("href") || "";
          return href && !href.startsWith("#") && !href.startsWith("javascript:void");
        });

        if (validLinks.length > 0) {
          log(`  -> Found ${validLinks.length} attachment(s). Triggering download...`);
          for (const link of validLinks) {
            const url = link.href;
            const filename = (link.innerText || link.getAttribute("download") || "attachment").trim();
            chrome.runtime.sendMessage({
              action: "download_file",
              url: url,
              filename: `${i + 1}_${filename}`
            });
            await sleep(500);
          }
        } else {
          // Check for 'Download all' button
          const downloadAllBtn = Array.from(document.querySelectorAll("button, a, span")).find(el => 
            (el.innerText || "").toLowerCase().includes("download all")
          );
          if (downloadAllBtn) {
            log(`  -> Clicking 'Download all attachments' button...`);
            downloadAllBtn.click();
            await sleep(1000);
          } else {
            log(`  -> No direct attachment links found in preview.`);
          }
        }

        row.style.backgroundColor = originalBg;
        await sleep(1000);
      }

      log(`[✓] Batch complete for current view!`);
    } catch (err) {
      log(`[!] Error: ${err.message}`);
    } finally {
      isRunning = false;
      btnDownload.disabled = false;
      statusEl.innerText = "Status: Idle";
    }
  });

  log("Extension HUD initialized.");
})();
