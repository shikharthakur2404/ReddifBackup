// =====================================================================
// Rediffmail Pro Deep Archive Extractor (Run in Edge/Chrome DevTools)
// =====================================================================
// 1. Open Rediffmail Pro in Edge/Chrome
// 2. Press Cmd + Option + I (or F12) to open DevTools
// 3. Click the 'Console' tab
// 4. Paste this code and press Enter
// =====================================================================

(async function startDeepArchive() {
  console.log("%c[⚡ REDIFF DEEP ARCHIVE INITIALIZED]", "color:#58a6ff; font-weight:bold; font-size:14px;");

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  // Find scrollable container for the mail list
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

  const container = getScrollContainer();
  console.log("[*] Detected mail list scroll container. Scrolling to load full historical archive (August - Present)...");

  // Step 1: Auto-Scroll to load all older emails (infinite scroll)
  let prevCount = 0;
  let sameCountRounds = 0;
  let maxScrollCycles = 50;

  for (let cycle = 1; cycle <= maxScrollCycles; cycle++) {
    const currentRows = document.querySelectorAll("input[type='checkbox']");
    const count = currentRows.length;
    console.log(`  [Scroll Cycle ${cycle}] Currently loaded: ${count} email rows...`);

    container.scrollTop = container.scrollHeight;
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(2000); // Allow Rediffmail AJAX to load next batch

    if (count === prevCount) {
      sameCountRounds++;
      if (sameCountRounds >= 3) {
        console.log("%c[✓] Reached the end of mailbox history!", "color:#2ea043; font-weight:bold;");
        break;
      }
    } else {
      sameCountRounds = 0;
    }
    prevCount = count;
  }

  // Step 2: Identify all rows with attachments
  const allRows = Array.from(document.querySelectorAll("div[class*='row'], tr, div.mail-item, [role='row']"))
    .filter(r => r.querySelector("input[type='checkbox']"));

  const attachmentRows = allRows.filter(r => {
    const html = r.innerHTML.toLowerCase();
    return html.includes("paperclip") || html.includes("attach") || html.includes("clip") || html.includes("ico_att");
  });

  console.log(`%c[*] Found ${allRows.length} total emails across entire history.`, "color:#58a6ff;");
  console.log(`%c[*] Found ${attachmentRows.length} emails containing attachments. Starting extraction...`, "color:#e3b341; font-weight:bold;");

  // Step 3: Trigger downloads
  let totalDownloaded = 0;

  for (let i = 0; i < attachmentRows.length; i++) {
    const row = attachmentRows[i];
    const originalBg = row.style.backgroundColor;
    row.style.backgroundColor = "rgba(56, 139, 253, 0.3)";

    // Scroll row into view
    row.scrollIntoView({ behavior: "smooth", block: "center" });

    // Click row to open preview
    const clickTarget = row.querySelector("a, span[class*='subject'], [class*='sender']") || row;
    clickTarget.click();
    await sleep(2000);

    // Look for attachment links in preview pane
    const attLinks = Array.from(document.querySelectorAll("a[href*='download'], a[href*='attachment'], a[download], [title*='Download']"))
      .filter(a => {
        const h = a.getAttribute("href") || "";
        return h && !h.startsWith("#") && !h.startsWith("javascript:void");
      });

    if (attLinks.length > 0) {
      console.log(`  [${i + 1}/${attachmentRows.length}] Found ${attLinks.length} attachment(s). Downloading...`);
      for (const link of attLinks) {
        const a = document.createElement("a");
        a.href = link.href;
        a.download = (link.innerText || link.getAttribute("download") || "attachment").trim();
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        totalDownloaded++;
        await sleep(800);
      }
    } else {
      // Check for 'Download all' button
      const downloadAllBtn = Array.from(document.querySelectorAll("button, a, span")).find(el => 
        (el.innerText || "").toLowerCase().includes("download all")
      );
      if (downloadAllBtn) {
        console.log(`  [${i + 1}/${attachmentRows.length}] Clicking 'Download all attachments' button...`);
        downloadAllBtn.click();
        totalDownloaded++;
        await sleep(1500);
      }
    }

    row.style.backgroundColor = originalBg;
    await sleep(1000);
  }

  console.log(`%c[✓] COMPLETE! Downloaded ${totalDownloaded} attachments from all months.`, "color:#2ea043; font-weight:bold; font-size:14px;");
})();
