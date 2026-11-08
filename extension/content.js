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
        <span id="rediff-stat-items">Page: 1 | Mails: 0</span>
        <span id="rediff-stat-status">Status: Idle</span>
      </div>
      <div style="display:flex; gap:6px;">
        <button id="btn-scan" class="hud-btn secondary" style="flex:1;">🔍 Scan View</button>
        <button id="btn-download-page" class="hud-btn" style="flex:1;">⬇ Current Page</button>
      </div>
      <button id="btn-download-all-pages" class="hud-btn" style="background:#1f6feb;">⚡ Auto-Download ALL Pages</button>
      <div id="rediff-archiver-logs">Ready. Click 'Auto-Download ALL Pages' to crawl every page.</div>
    </div>
  `;
  document.body.appendChild(hud);

  const logsEl = document.getElementById("rediff-archiver-logs");
  const statsEl = document.getElementById("rediff-stat-items");
  const statusEl = document.getElementById("rediff-stat-status");
  const btnScan = document.getElementById("btn-scan");
  const btnDownloadPage = document.getElementById("btn-download-page");
  const btnDownloadAll = document.getElementById("btn-download-all-pages");
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

  function getMailRows() {
    const rows = Array.from(document.querySelectorAll("div[class*='mail_list'], div[class*='row'], tr, div.mail-item, [role='row']"));
    const validRows = rows.filter(r => {
      const hasCheckbox = r.querySelector("input[type='checkbox']") || r.querySelector("[class*='chk']");
      const hasSubject = r.innerText && r.innerText.includes("\n");
      return hasCheckbox && hasSubject;
    });

    if (validRows.length > 0) return validRows;

    const rowsByCheckbox = Array.from(document.querySelectorAll("input[type='checkbox']"))
      .map(cb => cb.closest("div[class*='row'], tr, div[class*='item'], div[style*='display']"))
      .filter(Boolean);
    
    return [...new Set(rowsByCheckbox)];
  }

  function findNextPageButton() {
    // 1. Check title/aria attributes
    const byAttr = document.querySelector("[title*='Next' i], [aria-label*='Next' i], [title*='next page' i]");
    if (byAttr && !isElementDisabled(byAttr)) return byAttr;

    // 2. Check pagination container buttons/links
    const candidates = Array.from(document.querySelectorAll(".pagination a, .paginate a, [class*='page'] a, [class*='page'] button, .next, .pg-next"));
    for (const el of candidates) {
      const txt = (el.innerText || "").trim();
      if ((txt === ">" || txt === "»" || txt.toLowerCase() === "next") && !isElementDisabled(el)) {
        return el;
      }
    }

    // 3. Fallback: Search all clickable elements with arrow symbols
    const allClickable = Array.from(document.querySelectorAll("a, button, span[onclick]"));
    for (const el of allClickable) {
      const txt = (el.innerText || "").trim();
      const title = (el.getAttribute("title") || "").toLowerCase();
      if ((txt === ">" || txt === "»" || title.includes("next")) && !isElementDisabled(el)) {
        return el;
      }
    }

    return null;
  }

  function isElementDisabled(el) {
    if (!el) return true;
    if (el.disabled || el.getAttribute("disabled") !== null) return true;
    const cls = el.className || "";
    if (typeof cls === "string" && (cls.includes("disabled") || cls.includes("inactive"))) return true;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") return true;
    return false;
  }

  const sleep = (ms) => new Promise(r => setTimeout(r, ms));

  async function processCurrentPage(pageNumber = 1) {
    const rows = getMailRows();
    log(`[Page ${pageNumber}] Processing ${rows.length} email entries...`);
    statsEl.innerText = `Page: ${pageNumber} | Mails: ${rows.length}`;

    for (let i = 0; i < rows.length; i++) {
      if (shouldStop) break;
      const row = rows[i];

      const originalBg = row.style.backgroundColor;
      row.style.backgroundColor = "rgba(56, 139, 253, 0.25)";

      const snippet = (row.innerText || "").split("\n").filter(Boolean).slice(0, 2).join(" - ").trim();
      log(`  [${i + 1}/${rows.length}] Opening: ${snippet.substring(0, 35)}...`);

      const clickTarget = row.querySelector("a, span, [class*='subject']") || row;
      clickTarget.click();
      await sleep(1800);

      const attLinks = Array.from(document.querySelectorAll("a[href*='download'], a[href*='attachment'], a[download], [title*='Download']"));
      const validLinks = attLinks.filter(a => {
        const href = a.getAttribute("href") || "";
        return href && !href.startsWith("#") && !href.startsWith("javascript:void");
      });

      if (validLinks.length > 0) {
        log(`    -> Found ${validLinks.length} attachment(s). Downloading...`);
        for (const link of validLinks) {
          const url = link.href;
          const filename = (link.innerText || link.getAttribute("download") || "attachment").trim();
          chrome.runtime.sendMessage({
            action: "download_file",
            url: url,
            filename: `P${pageNumber}_${i + 1}_${filename}`
          });
          await sleep(500);
        }
      } else {
        const downloadAllBtn = Array.from(document.querySelectorAll("button, a, span")).find(el => 
          (el.innerText || "").toLowerCase().includes("download all")
        );
        if (downloadAllBtn) {
          log(`    -> Clicking 'Download all attachments'...`);
          downloadAllBtn.click();
          await sleep(1000);
        }
      }

      row.style.backgroundColor = originalBg;
      await sleep(800);
    }
  }

  btnScan.addEventListener("click", () => {
    const rows = getMailRows();
    const nextBtn = findNextPageButton();
    statsEl.innerText = `Mails: ${rows.length} | Next Page: ${nextBtn ? 'Found' : 'End'}`;
    log(`Scanned view: Found ${rows.length} emails. Next Page button: ${nextBtn ? 'Yes' : 'Not detected/Last page'}`);
  });

  btnDownloadPage.addEventListener("click", async () => {
    if (isRunning) return;
    isRunning = true;
    shouldStop = false;
    btnDownloadPage.disabled = true;
    statusEl.innerText = "Status: Running";
    try {
      await processCurrentPage(1);
      log(`[✓] Current page download completed.`);
    } catch (err) {
      log(`[!] Error: ${err.message}`);
    } finally {
      isRunning = false;
      btnDownloadPage.disabled = false;
      statusEl.innerText = "Status: Idle";
    }
  });

  btnDownloadAll.addEventListener("click", async () => {
    if (isRunning) {
      shouldStop = true;
      log(`[*] Stopping auto-page crawl...`);
      return;
    }
    isRunning = true;
    shouldStop = false;
    btnDownloadAll.innerText = "🛑 Stop Crawl";
    btnDownloadAll.style.background = "#da3633";
    statusEl.innerText = "Status: Crawling All Pages";

    let currentPage = 1;

    try {
      while (!shouldStop) {
        log(`\n=== STARTING PAGE ${currentPage} ===`);
        await processCurrentPage(currentPage);

        const nextBtn = findNextPageButton();
        if (!nextBtn) {
          log(`[✓] No further 'Next Page' button found. Reached the final page!`);
          break;
        }

        log(`[*] Clicking 'Next Page' -> Moving to page ${currentPage + 1}...`);
        nextBtn.click();
        await sleep(3500); // Wait for AJAX page render

        currentPage++;
      }
      log(`\n[✓] ALL PAGES CRAWLED! Total pages processed: ${currentPage}`);
    } catch (err) {
      log(`[!] Crawler encountered error: ${err.message}`);
    } finally {
      isRunning = false;
      btnDownloadAll.innerText = "⚡ Auto-Download ALL Pages";
      btnDownloadAll.style.background = "#1f6feb";
      statusEl.innerText = "Status: Idle";
    }
  });

  log("Extension HUD ready with Multi-Page Crawl engine.");
})();
