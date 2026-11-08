// Self-contained MUI-targeted Rediffmail Deep Extractor
(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  // 1. Target the exact Material-UI Scroll Container
  const scrollContainer = Array.from(document.querySelectorAll("*")).find(
    (e) => e.scrollHeight > e.clientHeight && e.clientHeight > 250 && e.querySelector("input[type='checkbox']")
  ) || Array.from(document.querySelectorAll("*")).find(
    (e) => e.scrollHeight > e.clientHeight && e.clientHeight > 250
  ) || document.scrollingElement;

  console.log("%c[⚡ REDIFF MUI ARCHIVER INITIALIZED]", "color:#2ea043; font-weight:bold; font-size:14px;");
  console.log("[*] Target Scroll Container:", scrollContainer.className || scrollContainer.tagName);

  const processedEmails = new Set();
  let downloadedCount = 0;
  let stagnantCount = 0;
  let lastScrollTop = -1;

  while (stagnantCount < 6) {
    // 2. Identify all loaded email checkboxes (skip header "select-all" checkbox)
    const allCheckboxes = Array.from(document.querySelectorAll("input[type='checkbox']")).filter(
      (cb) => !cb.closest("header, [class*='toolbar'], [class*='action']")
    );

    for (const cb of allCheckboxes) {
      const row = cb.closest("[class*='MuiGrid-container'], div[class*='MuiGrid-root']") || cb.parentElement?.parentElement;
      if (!row) continue;

      const rowText = (row.innerText || "").replace(/\s+/g, " ").trim();
      if (!rowText || processedEmails.has(rowText)) continue;
      processedEmails.add(rowText);

      // Check for attachments (paperclip, KB/MB indicator, or svg)
      const hasAttachment = row.innerHTML.includes("KB") || 
                            row.innerHTML.includes("MB") || 
                            row.innerHTML.toLowerCase().includes("clip") ||
                            row.innerHTML.toLowerCase().includes("attach");

      if (!hasAttachment) continue;

      // Highlight active row
      const origBg = row.style.backgroundColor;
      row.style.backgroundColor = "rgba(56, 139, 253, 0.35)";
      row.scrollIntoView({ behavior: "smooth", block: "center" });

      const snippet = rowText.substring(0, 45);
      console.log(`%c[Email #${processedEmails.size}] %c${snippet}...`, "color:#58a6ff; font-weight:bold;", "color:#c9d1d9;");

      // Click row (avoiding clicking directly on the checkbox so we open rather than select)
      const clickTarget = row.querySelector("[class*='MuiGrid-item']:not(:first-child)") || 
                          row.querySelector("span, div, p") || row;
      clickTarget.click();
      await sleep(2200); // Wait for preview pane render

      // Find attachment links
      const links = Array.from(document.querySelectorAll(`
        a[href*='download'],
        a[href*='attachment'],
        a[href*='ajaxprism'],
        a[download],
        [title*='Download' i]
      `)).filter(a => {
        const h = a.getAttribute("href") || "";
        return h && !h.startsWith("#") && !h.startsWith("javascript:void");
      });

      if (links.length > 0) {
        for (const link of links) {
          const dlUrl = link.href;
          const fileName = (link.innerText || link.getAttribute("download") || "attachment").trim();
          console.log(`  %c⬇ Downloading: %c${fileName}`, "color:#2ea043; font-weight:bold;", "color:#e3b341;");

          const a = document.createElement("a");
          a.href = dlUrl;
          a.download = fileName;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          downloadedCount++;
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
          downloadedCount++;
          await sleep(1500);
        }
      }

      row.style.backgroundColor = origBg;
      await sleep(500);
    }

    // Scroll down by 550px
    const prevScroll = scrollContainer.scrollTop;
    scrollContainer.scrollTop += 550;
    await sleep(2000); // Wait for MUI/Angular infinite scroll to populate next batch

    const currentScroll = scrollContainer.scrollTop;
    console.log(`[*] Scanned: ${processedEmails.size} emails | Downloaded: ${downloadedCount} attachments | ScrollPos: ${currentScroll}`);

    if (currentScroll === prevScroll || currentScroll === lastScrollTop) {
      stagnantCount++;
      if (stagnantCount >= 5) {
        console.log("%c=======================================================", "color:#2ea043;");
        console.log(`%c[✓] COMPLETE! Reached end of mailbox. Downloaded ${downloadedCount} files!`, "color:#2ea043; font-weight:bold; font-size:15px;");
        console.log("%c=======================================================", "color:#2ea043;");
        break;
      }
    } else {
      stagnantCount = 0;
    }
    lastScrollTop = currentScroll;
  }
})();
