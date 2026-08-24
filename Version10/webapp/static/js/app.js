(() => {
  const slots = ["general_notes", "framing", "reinforcement"];
  const state = {
    files: { general_notes: null, framing: null, reinforcement: null },
    runId: null,
    pollTimer: null,
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
      state.runId = data.run_id;
      show("process");
      el("process-message").textContent = "Processing drawing...";
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

  async function pollStatus() {
    if (!state.runId) return;
    try {
      const res = await fetch(`/api/status/${state.runId}`);
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Status check failed.");

      if (data.message) {
        el("process-message").textContent = data.message;
      }

      if (data.status === "success") {
        stopPolling();
        setUploadsDisabled(false);
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
        el("btn-download").href = `/api/download/${state.runId}`;
        show("success");
      } else if (data.status === "error") {
        stopPolling();
        setUploadsDisabled(false);
        show("error");
        el("error-message").textContent =
          data.error || "Estimation failed. Please verify the drawings and try again.";
      }
    } catch (err) {
      stopPolling();
      setUploadsDisabled(false);
      show("error");
      el("error-message").textContent = err.message || "Unexpected error.";
    }
  }

  function resetHome() {
    stopPolling();
    state.runId = null;
    slots.forEach((slot) => {
      state.files[slot] = null;
      el(`file-${slot}`).value = "";
      updateMeta(slot);
    });
    setError("");
    setUploadsDisabled(false);
    show("home");
  }

  el("btn-another").addEventListener("click", resetHome);
  el("btn-retry").addEventListener("click", resetHome);
})();
