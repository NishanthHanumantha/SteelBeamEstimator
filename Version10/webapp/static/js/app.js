(() => {
  const slots = ["general_notes", "framing", "reinforcement"];
  const RUN_KEY = "steel_beam_estimator_run_id";
  const state = {
    files: { general_notes: null, framing: null, reinforcement: null },
    runId: null,
    pollTimer: null,
    pollMisses: 0,
    completed: false,
  };

  const el = (id) => document.getElementById(id);

  function show(view) {
    ["home", "process", "success", "error"].forEach((v) => {
      el(`view-${v}`).classList.toggle("hidden", v !== view);
    });
  }

  function setError(msg) {
    const box = el("home-error");
    if (!msg) {
      box.classList.add("hidden");
      box.textContent = "";
      return;
    }
    box.textContent = msg;
    box.classList.remove("hidden");
  }

  function setDownloadError(msg) {
    const box = el("download-error");
    if (!box) return;
    if (!msg) {
      box.classList.add("hidden");
      box.textContent = "";
      return;
    }
    box.textContent = msg;
    box.classList.remove("hidden");
  }

  function persistRun(runId) {
    state.runId = runId;
    try { sessionStorage.setItem(RUN_KEY, runId); } catch (err) { /* ignore */ }
    try {
      const url = new URL(window.location.href);
      if (runId) url.searchParams.set("run", runId);
      else url.searchParams.delete("run");
      history.replaceState({}, "", url);
    } catch (err) { /* ignore */ }
  }

  function clearRun() {
    state.runId = null;
    state.completed = false;
    try { sessionStorage.removeItem(RUN_KEY); } catch (err) { /* ignore */ }
    try {
      const url = new URL(window.location.href);
      url.searchParams.delete("run");
      history.replaceState({}, "", url);
    } catch (err) { /* ignore */ }
  }

  function isDxf(file) {
    if (!file || !file.name) return false;
    return file.name.toLowerCase().endsWith(".dxf");
  }

  function updateMeta(slot) {
    const meta = el(`meta-${slot}`);
    const replaceBtn = document.querySelector(`.replace-btn[data-slot="${slot}"]`);
    const file = state.files[slot];
    if (!file) {
      meta.textContent = "No file selected";
      meta.classList.remove("ok");
      replaceBtn.classList.add("hidden");
      return;
    }
    meta.textContent = `${file.name} (${Math.round(file.size / 1024)} KB) — Ready`;
    meta.classList.add("ok");
    replaceBtn.classList.remove("hidden");
  }

  function setUploadsDisabled(disabled) {
    slots.forEach((slot) => {
      el(`file-${slot}`).disabled = disabled;
      document.querySelectorAll(`.pick-btn[data-slot="${slot}"], .replace-btn[data-slot="${slot}"]`)
        .forEach((b) => { b.disabled = disabled; });
    });
    el("btn-generate").disabled = disabled;
  }

  slots.forEach((slot) => {
    const input = el(`file-${slot}`);
    document.querySelectorAll(`.pick-btn[data-slot="${slot}"], .replace-btn[data-slot="${slot}"]`)
      .forEach((btn) => {
        btn.addEventListener("click", () => input.click());
      });
    input.addEventListener("change", () => {
      const file = input.files && input.files[0];
      if (!file) return;
      if (!isDxf(file)) {
        setError("Only .dxf files are allowed.");
        input.value = "";
        state.files[slot] = null;
        updateMeta(slot);
        return;
      }
      if (file.size <= 0) {
        setError("The selected file is empty.");
        input.value = "";
        state.files[slot] = null;
        updateMeta(slot);
        return;
      }
      setError("");
      state.files[slot] = file;
      updateMeta(slot);
    });
  });

  el("estimate-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    setError("");

    for (const slot of slots) {
      if (!state.files[slot]) {
        setError("All three DXF drawings are mandatory before estimation.");
        return;
      }
      if (!isDxf(state.files[slot])) {
        setError("Only .dxf files are allowed.");
        return;
      }
      if (state.files[slot].size <= 0) {
        setError("One or more selected files are empty.");
        return;
      }
    }

    const form = new FormData();
    form.append("general_notes", state.files.general_notes);
    form.append("framing", state.files.framing);
    form.append("reinforcement", state.files.reinforcement);

    setUploadsDisabled(true);

    try {
      const res = await fetch("/api/estimate", { method: "POST", body: form });
      const data = await res.json();
      if (res.status === 409) {
        setUploadsDisabled(false);
        setError(data.error || "An estimation is currently running. Please wait and try again.");
        return;
      }
      if (!res.ok || !data.ok) {
        setUploadsDisabled(false);
        setError(data.error || "Unable to start estimation.");
        return;
      }
      state.pollMisses = 0;
      state.completed = false;
      persistRun(data.run_id);
      show("process");
      el("process-message").textContent = "Processing drawing...";
      if (el("process-detail")) el("process-detail").textContent = "";
      startPolling();
    } catch (err) {
      setUploadsDisabled(false);
      show("error");
      el("error-message").textContent = err.message || "Unexpected error.";
    }
  });

  function startPolling() {
    stopPolling();
    state.pollTimer = setInterval(pollStatus, 2000);
    pollStatus();
  }

  function stopPolling() {
    if (state.pollTimer) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  function formatSteel(kg) {
    if (kg == null || kg === "") return "—";
    const n = Number(kg);
    if (Number.isNaN(n)) return String(kg);
    return `${n} kg`;
  }

  function formatElapsed(seconds) {
    const n = Number(seconds);
    if (!Number.isFinite(n) || n < 0) return "";
    if (n < 60) return `${Math.round(n)} seconds elapsed`;
    const m = Math.floor(n / 60);
    const s = Math.round(n % 60);
    return `${m} min ${s}s elapsed`;
  }

  function renderSuccess(data) {
    el("success-workbook").textContent = data.workbook_name || "Estimation_Output.xlsx";
    el("success-duration").textContent =
      data.duration_s != null ? `${data.duration_s} seconds` : "—";
    const summary = data.summary || {};
    el("success-beams").textContent =
      summary.total_beams != null ? String(summary.total_beams) : "—";
    el("success-steel").textContent = formatSteel(summary.total_steel_kg);
    const warnBox = el("success-warnings");
    if (data.warnings && data.warnings.length) {
      warnBox.textContent = data.warnings.join(" ");
      warnBox.classList.remove("hidden");
    } else {
      warnBox.classList.add("hidden");
      warnBox.textContent = "";
    }
    if (data.download_ready === false || data.excel_exists === false) {
      setDownloadError(
        data.error ||
          "The estimation completed but the workbook is no longer available."
      );
    } else {
      setDownloadError("");
    }
    show("success");
  }

  async function pollStatus() {
    if (!state.runId) return;
    try {
      const res = await fetch(`/api/status/${state.runId}`);
      if (res.status === 404) {
        if (state.completed) {
          setDownloadError(
            "Status lookup failed, but this result is still on this page. Try Download Excel again."
          );
          return;
        }
        stopPolling();
        setUploadsDisabled(false);
        show("error");
        el("error-message").textContent =
          "This estimation is no longer available. If the server restarted, please try again.";
        return;
      }
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Status check failed.");
      state.pollMisses = 0;

      if (data.message) {
        el("process-message").textContent = data.message;
      }
      const detail = el("process-detail");
      if (detail) {
        const parts = [];
        if (data.elapsed_s != null) parts.push(formatElapsed(data.elapsed_s));
        const progress = data.progress || {};
        if (progress.beam_id && progress.total) {
          parts.push(`beam ${progress.beam_id} (${progress.index} of ${progress.total})`);
        }
        detail.textContent = parts.join(" · ");
      }

      if (data.status === "success") {
        stopPolling();
        setUploadsDisabled(false);
        state.completed = true;
        persistRun(state.runId);
        renderSuccess(data);
      } else if (data.status === "error") {
        if (state.completed) {
          setDownloadError(
            data.error || "A later status check failed. The completed result is still available — try Download Excel again."
          );
          return;
        }
        stopPolling();
        setUploadsDisabled(false);
        show("error");
        el("error-message").textContent =
          data.error || "Estimation failed. Please verify the drawings and try again.";
      }
    } catch (err) {
      state.pollMisses += 1;
      if (state.completed) {
        setDownloadError(
          "Lost connection after completion. The result is still available — try Download Excel again."
        );
        return;
      }
      if (state.pollMisses < 5) return;
      stopPolling();
      setUploadsDisabled(false);
      show("error");
      el("error-message").textContent =
        "Lost connection while the estimation was running. Please refresh and try again if the workbook is not ready.";
    }
  }

  async function downloadExcel() {
    if (!state.runId) {
      setDownloadError("No completed estimation is available to download.");
      return;
    }
    setDownloadError("");
    const btn = el("btn-download");
    const previous = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Downloading…";
    try {
      const res = await fetch(`/api/download/${state.runId}`);
      if (!res.ok) {
        let msg = "Download failed. The workbook is still available — try again.";
        try {
          const data = await res.json();
          if (data && data.error) msg = data.error;
        } catch (parseErr) { /* keep default */ }
        setDownloadError(msg);
        return;
      }
      const blob = await res.blob();
      if (!blob || blob.size <= 0) {
        setDownloadError("Download failed: empty file. The result is still available — try again.");
        return;
      }
      const header = res.headers.get("Content-Disposition") || "";
      let name = `Estimation_Output_${state.runId}.xlsx`;
      const star = /filename\*=UTF-8''([^;]+)/i.exec(header);
      const plain = /filename="?([^";]+)"?/i.exec(header);
      if (star) {
        try { name = decodeURIComponent(star[1]); } catch (err) { name = star[1]; }
      } else if (plain) {
        name = plain[1];
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setDownloadError(
        "Download failed due to a network error. The result is still available — try again."
      );
    } finally {
      btn.disabled = false;
      btn.textContent = previous || "Download Excel";
    }
  }

  function resetHome() {
    stopPolling();
    clearRun();
    slots.forEach((slot) => {
      state.files[slot] = null;
      el(`file-${slot}`).value = "";
      updateMeta(slot);
    });
    setError("");
    setDownloadError("");
    setUploadsDisabled(false);
    show("home");
  }

  el("btn-download").addEventListener("click", (e) => {
    e.preventDefault();
    downloadExcel();
  });
  el("btn-another").addEventListener("click", resetHome);
  el("btn-retry").addEventListener("click", resetHome);

  function restoreCompletedRun() {
    let rid = null;
    try {
      const url = new URL(window.location.href);
      rid = url.searchParams.get("run");
    } catch (err) { /* ignore */ }
    if (!rid) {
      try { rid = sessionStorage.getItem(RUN_KEY); } catch (err) { rid = null; }
    }
    if (!rid) return;
    persistRun(rid);
    show("process");
    el("process-message").textContent = "Restoring estimation result...";
    startPolling();
  }

  restoreCompletedRun();
})();
