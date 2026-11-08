chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "download_file") {
    chrome.downloads.download({
      url: message.url,
      filename: `ReddiffBackup/${message.filename || 'attachment'}`,
      saveAs: false,
      conflictAction: "uniquify"
    }, (downloadId) => {
      if (chrome.runtime.lastError) {
        sendResponse({ success: false, error: chrome.runtime.lastError.message });
      } else {
        sendResponse({ success: true, downloadId });
      }
    });
    return true; // Keep channel open for async response
  }
});
