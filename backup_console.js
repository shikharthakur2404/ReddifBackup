// ==============================================================================
// Rediffmail Pro Complete Historical Vault Extractor (April to November 2026)
// ==============================================================================
// ROLLING CRAWLER: Extracts attachments while continuously scrolling through
// April, May, June, July, August, September, October, and November.
// ==============================================================================
// Instructions:
// 1. Open Rediffmail Pro in Microsoft Edge (active tab)
// 2. Scroll to the TOP of your Inbox (November emails)
// 3. Press Cmd + Option + I (or right-click -> Inspect) -> click 'Console' tab
// 4. Paste this script and hit Enter.
// ==============================================================================

(async function runCompleteHistoricalExtractor() {
  console.log("%c=======================================================", "color:#58a6ff;");
  console.log("%c⚡ REDIFF COMPLETE HISTORICAL EXTRACTOR (APRIL - NOV 2026)", "color:#58a6ff; font-weight:bold; font-size:15px;");
  console.log("%c=======================================================", "color:#58a6ff;");

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

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

  const container = getScrollContainer();
  console.log("[*] Detected mail stream container. Starting rolling crawl from top to bottom...");

  const processedKeys = new Set();
  let totalDownloadedFiles = 0;
  let scrollStagnantCount = 0;
  let lastScrollTop = -1;
  let cycle = 0;

  while (true) {
    cycle++;
    const currentRows = getMailRows();
    const rowsWithAttachments = currentRows.filter(hasAttachment);

    // Process all unprocessed visible emails with attachments in this viewport
    for (const row of rowsWithAttachments) {
      // Create unique fingerprint for this email based on visible text
      const rawText = (row.innerText || "").replace(/\s+/g, " ").trim();
      if (!rawText || processedKeys.has(rawText)) continue;
      processedKeys.add(rawText);

      // Highlight row being processed
      const origBg = row.style.backgroundColor;
      row.style.backgroundColor = "rgba(56, 139, 253, 0.35)";
      row.scrollIntoView({ behavior: "smooth", block: "center" });

      const snippet = rawText.substring(0, 50);
      console.log(`%c[Processing Email #${processedKeys.size}] %c${snippet}...`, "color:#58a6ff; font-weight:bold;", "color:#c9d1d9;");

      // Click to open preview
      const clickTarget = row.querySelector("a, span[class*='subject'], [class*='sender']") || row;
      clickTarget.click();
      await sleep(2200); // Wait for preview pane AJAX to load

      // Collect all download links in preview pane
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
        for (const link of attLinks) {
          const dlUrl = link.href;
          const fileName = (link.innerText || link.getAttribute("download") || "attachment").trim();
          console.log(`  %c⬇ Downloading: %c${fileName}`, "color:#2ea043; font-weight:bold;", "color:#e3b341;");

          const a = document.createElement("a");
          a.href = dlUrl;
          a.download = fileName;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          totalDownloadedFiles++;
          await sleep(700);
        }
      } else {
        // Fallback: Check for 'Download all' button
        const dlAllBtn = Array.from(document.querySelectorAll("button, a, span")).find(el => 
          (el.innerText || "").toLowerCase().includes("download all")
        );
        if (dlAllBtn) {
          console.log(`  %c⬇ Clicking 'Download All Attachments' button...`, "color:#2ea043; font-weight:bold;");
          dlAllBtn.click();
          totalDownloadedFiles++;
          await sleep(1500);
        }
      }

      row.style.backgroundColor = origBg;
      await sleep(600);
    }

    // Scroll down by 500px to reveal older emails
    const prevScroll = container.scrollTop;
    container.scrollTop += 500;
    window.scrollBy(0, 500);
    await sleep(1800); // Allow Rediffmail AJAX to fetch next batch

    const currentScroll = container.scrollTop;
    console.log(`[*] Progress: Scanned ${processedKeys.size} emails with attachments | Total files downloaded: ${totalDownloadedFiles}`);

    // Check if scroll reached bottom
    if (currentScroll === prevScroll || currentScroll === lastScrollTop) {
      scrollStagnantCount++;
      if (scrollStagnantCount >= 4) {
        console.log("%c=======================================================", "color:#2ea043;");
        console.log(`%c[✓] CRAWL COMPLETED! Reached the oldest email in April 2026.`, "color:#2ea043; font-weight:bold; font-size:15px;");
        console.log(`%c[✓] Total attachments downloaded: ${totalDownloadedFiles}`, "color:#2ea043; font-weight:bold; font-size:14px;");
        console.log("%c=======================================================", "color:#2ea043;");
        break;
      }
    } else {
      scrollStagnantCount = 0;
    }
    lastScrollTop = currentScroll;
  }
})();
