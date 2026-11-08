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
        <span id="rediff-stat-items">Mails: 0 | Attachments: 0</span>
        <span id="rediff-stat-status">Status: Idle</span>
      </div>
      <button id="btn-deep-crawl" class="hud-btn" style="background:#238636; font-size:13px; padding:10px;">⚡ Auto-Scroll & Download ALL (Aug - Nov)</button>
      <div style="display:flex; gap:6px;">
        <button id="btn-scan" class="hud-btn secondary" style="flex:1;">🔍 Scan View</button>
        <button id="btn-download-page" class="hud-btn secondary" style="flex:1;">⬇ Current View</button>
      </div>
      <div id="rediff-archiver-logs">Ready. Click 'Auto-Scroll & Download ALL' to crawl the full infinite mailbox history.</div>
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
    statsEl.innerText = `Mails: ${rows.length} | Attachments: ${withAtt.length}`;
    log(`Scanned: Found ${rows.length} loaded emails (${withAtt.length} with attachments).`);
  });

  async function downloadFromRows(targetRows) {
    log(`Starting extraction for ${targetRows.length} emails with attachments...`);
    let downloaded = 0;

    for (let i = 0; i < targetRows.length; i++) {
      if (shouldStop) break;
      const row = targetRows[i];

      const originalBg = row.style.backgroundColor;
      row.style.backgroundColor = "rgba(56, 139, 253, 0.3)";
      row.scrollIntoView({ behavior: "smooth", block: "center" });

      const snippet = (row.innerText || "").split("\n").filter(Boolean).slice(0, 2).join(" - ").trim();
      log(`[${i + 1}/${targetRows.length}] Opening: ${snippet.substring(0, 35)}...`);

      const clickTarget = row.querySelector("a, span[class*='subject'], [class*='sender']") || row;
      clickTarget.click();
      await sleep(2200);

      const attLinks = Array.from(document.querySelectorAll("a[href*='download'], a[href*='attachment'], a[download], [title*='Download']"))
        .filter(a => {
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
            filename: `${i + 1}_${filename}`
          });
          downloaded++;
          await sleep(600);
        }
      } else {
        const downloadAllBtn = Array.from(document.querySelectorAll("button, a, span")).find(el => 
          (el.innerText || "").toLowerCase().includes("download all")
        );
        if (downloadAllBtn) {
          log(`  -> Triggering 'Download all attachments'...`);
          downloadAllBtn.click();
          downloaded++;
          await sleep(1500);
        }
      }

      row.style.backgroundColor = originalBg;
      await sleep(1000);
    }

    log(`[✓] Extraction round complete. Downloaded: ${downloaded} files.`);
  }

  btnDownloadPage.addEventListener("click", async () => {
    if (isRunning) return;
    isRunning = true;
    shouldStop = false;
    btnDownloadPage.disabled = true;
    statusEl.innerText = "Status: Running";
    try {
      const rows = getMailRows().filter(hasAttachment);
      await downloadFromRows(rows);
    } catch (err) {
      log(`[!] Error: ${err.message}`);
    } finally {
      isRunning = false;
      btnDownloadPage.disabled = false;
      statusEl.innerText = "Status: Idle";
    }
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
    statusEl.innerText = "Status: Auto-Scrolling Mailbox";

    try {
      const container = getScrollContainer();
      log(`[*] Auto-scrolling to unroll full history back to August...`);

      let prevCount = 0;
      let stationaryRounds = 0;

      for (let cycle = 1; cycle <= 60; cycle++) {
        if (shouldStop) break;
        const count = getMailRows().length;
        statsEl.innerText = `Scrolled: ${count} emails`;
        log(`  Cycle ${cycle}: Loaded ${count} emails...`);

        container.scrollTop = container.scrollHeight;
        window.scrollTo(0, document.body.scrollHeight);
        await sleep(2000);

        if (count === prevCount) {
          stationaryRounds++;
          if (stationaryRounds >= 3) {
            log(`[✓] Reached the oldest email in mailbox!`);
            break;
          }
        } else {
          stationaryRounds = 0;
        }
        prevCount = count;
      }

      if (!shouldStop) {
        statusEl.innerText = "Status: Downloading Attachments";
        const allLoaded = getMailRows();
        const withAttachments = allLoaded.filter(hasAttachment);
        log(`\n[*] Total emails loaded: ${allLoaded.length}`);
        log(`[*] Total with attachments: ${withAttachments.length}`);

        await downloadFromRows(withAttachments);
        log(`\n[✓] FULL DEEP ARCHIVE COMPLETED!`);
      }
    } catch (err) {
      log(`[!] Error during deep crawl: ${err.message}`);
    } finally {
      isRunning = false;
      btnDeepCrawl.innerText = "⚡ Auto-Scroll & Download ALL (Aug - Nov)";
      btnDeepCrawl.style.background = "#238636";
      statusEl.innerText = "Status: Idle";
    }
  });

  log("Extension HUD v2.0 initialized with Infinite-Scroll Deep Extractor.");
})();
