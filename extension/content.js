(function () {
  if (document.getElementById("rediff-archiver-hud")) return;

  // Build HUD Element
  const hud = document.createElement("div");
  hud.id = "rediff-archiver-hud";
  hud.innerHTML = `
    <div id="rediff-archiver-header">
      <div id="rediff-archiver-title">
        <span>⚡ REDIFF ARCHIVER HUD v3.0</span>
      </div>
      <button id="rediff-archiver-toggle" style="background:none; border:none; color:#8b949e; cursor:pointer;">–</button>
    </div>
    <div id="rediff-archiver-body">
      <div id="rediff-archiver-stats">
        <span id="rediff-stat-items">Downloaded: 0 files</span>
        <span id="rediff-stat-status">Status: Idle</span>
      </div>
      <button id="btn-deep-crawl" class="hud-btn" style="background:#238636; font-size:13px; padding:10px;">⚡ Auto-Crawl Full History (April - Nov)</button>
      <div style="display:flex; gap:6px;">
        <button id="btn-scan" class="hud-btn secondary" style="flex:1;">🔍 Scan View</button>
        <button id="btn-download-page" class="hud-btn secondary" style="flex:1;">⬇ Visible View</button>
      </div>
      <div id="rediff-archiver-logs">Ready. Scroll to the TOP of Inbox and click 'Auto-Crawl Full History'.</div>
    </div>
  `;
  document.body.appendChild(hud);

  const logsEl = document.getElementById("rediff-archiver-logs");
  const statsEl = document.getElementById("rediff-stat-items");
  const statusEl = document.getElementById("rediff-stat-status");
  const btnScan = document.getElementById("btn-scan");
  const btnDownloadPage = document.getElementById("btn-download-page");
  const btnDeepCrawl = document.getElementById("btn-deep-crawl");
  const btnToggle = document.getElementById("rediff-archiver-toggle");
  const bodyEl = document.getElementById("rediff-archiver-body");

  let isRunning = false;
  let shouldStop = false;

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

  function getScrollContainer() {
    const rows = document.querySelectorAll("div[class*='row'], tr, div.mail-item, [role='row']");
    for (const r of rows) {
      let p = r.parentElement;
      while (p && p !== document.body) {
        const style = window.getComputedStyle(p);
        if (style.overflowY === "auto" || style.overflowY === "scroll") return p;
        p = p.parentElement;
      }
    }
    return document.scrollingElement || document.body;
  }

  function getMailRows() {
    const rows = Array.from(document.querySelectorAll("div[class*='row'], tr, div.mail-item, [role='row']"));
    const valid = rows.filter(r => r.querySelector("input[type='checkbox']"));
    if (valid.length > 0) return valid;
    return Array.from(document.querySelectorAll("input[type='checkbox']"))
      .map(cb => cb.closest("div[class*='row'], tr, div[class*='item']"))
      .filter(Boolean);
  }

  function hasAttachment(row) {
    const html = row.innerHTML.toLowerCase();
    return html.includes("paperclip") || html.includes("attach") || html.includes("clip") || html.includes("ico_att");
  }

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  btnScan.addEventListener("click", () => {
    const rows = getMailRows();
    const withAtt = rows.filter(hasAttachment);
    statsEl.innerText = `Visible: ${rows.length} | Attachments: ${withAtt.length}`;
    log(`Scanned: Found ${rows.length} loaded emails (${withAtt.length} with attachments).`);
  });

  btnDeepCrawl.addEventListener("click", async () => {
    if (isRunning) {
      shouldStop = true;
      log(`[*] Halting crawler...`);
      return;
    }
    isRunning = true;
    shouldStop = false;
    btnDeepCrawl.innerText = "🛑 Stop Crawl";
    btnDeepCrawl.style.background = "#da3633";
    statusEl.innerText = "Status: Crawling Full Archive";

    const processedKeys = new Set();
    let totalDownloaded = 0;
    let scrollStagnantCount = 0;
    let lastScrollTop = -1;

    try {
      const container = getScrollContainer();
      log(`[*] Rolling crawler started. Unrolling from November down to April 2026...`);

      while (!shouldStop) {
        const currentRows = getMailRows();
        const rowsWithAttachments = currentRows.filter(hasAttachment);

        for (const row of rowsWithAttachments) {
          if (shouldStop) break;
          const rawText = (row.innerText || "").replace(/\s+/g, " ").trim();
          if (!rawText || processedKeys.has(rawText)) continue;
          processedKeys.add(rawText);

          const origBg = row.style.backgroundColor;
          row.style.backgroundColor = "rgba(56, 139, 253, 0.35)";
          row.scrollIntoView({ behavior: "smooth", block: "center" });

          const snippet = rawText.substring(0, 40);
          log(`[#${processedKeys.size}] Opening: ${snippet}...`);

          const clickTarget = row.querySelector("a, span[class*='subject'], [class*='sender']") || row;
          clickTarget.click();
          await sleep(2200);

          const attLinks = Array.from(document.querySelectorAll(`
            a[href*='download'],
            a[href*='attachment'],
            a[download],
            [title*='Download' i],
            a[href*='readmail'][href*='att'],
            a[href*='part=']
          `)).filter(a => {
            const h = a.getAttribute("href") || "";
            return h && !h.startsWith("#") && !h.startsWith("javascript:void");
          });

          if (attLinks.length > 0) {
            log(`  -> Downloading ${attLinks.length} attachment(s)...`);
            for (const link of attLinks) {
              const url = link.href;
              const filename = (link.innerText || link.getAttribute("download") || "attachment").trim();
              chrome.runtime.sendMessage({
                action: "download_file",
                url: url,
                filename: filename
              });
              totalDownloaded++;
              statsEl.innerText = `Downloaded: ${totalDownloaded} files`;
              await sleep(600);
            }
          } else {
            const dlAllBtn = Array.from(document.querySelectorAll("button, a, span")).find(el => 
              (el.innerText || "").toLowerCase().includes("download all")
            );
            if (dlAllBtn) {
              log(`  -> Clicking 'Download all attachments'...`);
              dlAllBtn.click();
              totalDownloaded++;
              statsEl.innerText = `Downloaded: ${totalDownloaded} files`;
              await sleep(1500);
            }
          }

          row.style.backgroundColor = origBg;
          await sleep(600);
        }

        // Scroll down 500px
        const prevScroll = container.scrollTop;
        container.scrollTop += 500;
        window.scrollBy(0, 500);
        await sleep(1800);

        const currentScroll = container.scrollTop;
        if (currentScroll === prevScroll || currentScroll === lastScrollTop) {
          scrollStagnantCount++;
          if (scrollStagnantCount >= 4) {
            log(`\n[✓] REACHED END OF MAILBOX (April 2026)!`);
            log(`[✓] Total attachments downloaded: ${totalDownloaded}`);
            break;
          }
        } else {
          scrollStagnantCount = 0;
        }
        lastScrollTop = currentScroll;
      }
    } catch (err) {
      log(`[!] Error: ${err.message}`);
    } finally {
      isRunning = false;
      btnDeepCrawl.innerText = "⚡ Auto-Crawl Full History (April - Nov)";
      btnDeepCrawl.style.background = "#238636";
      statusEl.innerText = "Status: Idle";
    }
  });

  log("Extension HUD v3.0 ready with Rolling Infinite-Scroll Engine.");
})();
