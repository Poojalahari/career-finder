document.querySelectorAll("[data-menu-toggle]").forEach((button) => {
  button.addEventListener("click", () => {
    const sidebar = document.getElementById("sidebar");
    const open = sidebar.classList.toggle("open");
    button.setAttribute("aria-expanded", String(open));
  });
});

const savedTheme = window.localStorage.getItem("careerpath-theme");
if (savedTheme === "light" || savedTheme === "dark") {
  document.documentElement.dataset.theme = savedTheme;
}

document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
  button.addEventListener("click", () => {
    const current = document.documentElement.dataset.theme === "light" ? "light" : "dark";
    const next = current === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    window.localStorage.setItem("careerpath-theme", next);
  });
});

document.querySelectorAll("[data-sidebar-nav] a").forEach((link) => {
  const interviewChild = link.pathname.endsWith("/growth/interview-prep") && window.location.pathname.startsWith("/growth/interview");
  if (link.pathname === window.location.pathname || interviewChild || (link.pathname !== "/" && window.location.pathname.startsWith(link.pathname))) {
    link.classList.add("active");
    link.setAttribute("aria-current", "page");
  }
});

document.querySelectorAll("[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm(form.dataset.confirm)) {
      event.preventDefault();
    }
  });
});

document.querySelectorAll("[data-loading-form]").forEach((form) => {
  let submitting = false;
  form.addEventListener("submit", (event) => {
    if (submitting) {
      event.preventDefault();
      return;
    }
    submitting = true;
    const button = form.querySelector("[data-submit-label]");
    if (button) {
      button.disabled = true;
      button.value = button.dataset.submitLabel;
      button.textContent = button.dataset.submitLabel;
    }
  });
});

document.querySelectorAll("[data-auth-callback]").forEach(async (panel) => {
  const status = panel.querySelector("[data-auth-callback-status]");
  const params = new URLSearchParams(window.location.hash.slice(1));
  const accessToken = params.get("access_token");
  const refreshToken = params.get("refresh_token");
  window.history.replaceState({}, "", window.location.pathname);
  if (!accessToken || !refreshToken) {
    status.textContent = params.get("error_description") || "The confirmation link is invalid or expired.";
    return;
  }
  try {
    const response = await fetch("/auth/session-callback", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CSRFToken": panel.dataset.csrfToken},
      body: JSON.stringify({access_token: accessToken, refresh_token: refreshToken}),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    window.location.replace(result.redirect);
  } catch (error) {
    status.textContent = error.message || "We could not confirm your email. Please try again.";
  }
});

document.querySelectorAll("[data-password-toggle]").forEach((button) => {
  button.addEventListener("click", () => {
    const input = button.form.querySelector("[data-password-input]");
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    button.textContent = show ? "Hide password" : "Show password";
  });
});

document.querySelectorAll("[data-pdf-upload]").forEach((box) => {
  const input = box.querySelector("[data-pdf-input]");
  const status = box.querySelector("[data-pdf-status]");
  const fileRow = box.querySelector("[data-pdf-file]");
  const nameEl = box.querySelector("[data-pdf-name]");
  const sizeEl = box.querySelector("[data-pdf-size]");
  const errorEl = box.querySelector("[data-pdf-error]");
  const replace = box.querySelector("[data-pdf-replace]");
  const remove = box.querySelector("[data-pdf-remove]");
  const dropzone = box.querySelector(".upload-dropzone");
  const form = box.closest("form");
  const submit = form.querySelector("[data-submit-label]");
  const maxBytes = Number(form.dataset.maxBytes || 10 * 1024 * 1024);

  function showFile(file) {
    errorEl.textContent = "";
    if (!file) {
      fileRow.hidden = true;
      status.querySelector("strong").textContent = "No PDF selected";
      status.querySelector("span").textContent = "Choose one text-based PDF resume.";
      submit.disabled = true;
      return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf") || !["application/pdf", "application/octet-stream", ""].includes(file.type)) {
      input.value = "";
      fileRow.hidden = true;
      errorEl.textContent = "Select a valid PDF file. Other document types are not accepted.";
      submit.disabled = true;
      return;
    }
    if (file.size === 0 || file.size > maxBytes) {
      input.value = "";
      fileRow.hidden = true;
      errorEl.textContent = file.size === 0 ? "The selected PDF is empty." : `PDF size must be ${Math.floor(maxBytes / 1024 / 1024)} MB or less.`;
      submit.disabled = true;
      return;
    }
    nameEl.textContent = file.name;
    sizeEl.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
    fileRow.hidden = false;
    status.querySelector("strong").textContent = "Selected locally. Click Analyze Resume to upload and scan.";
    status.querySelector("span").textContent = "The file will be uploaded only when you analyze it.";
    submit.disabled = false;
  }

  input.addEventListener("change", () => showFile(input.files[0]));
  replace.addEventListener("click", () => input.click());
  remove.addEventListener("click", () => {
    input.value = "";
    showFile(null);
  });
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("is-dragging");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.remove("is-dragging");
    });
  });
  dropzone.addEventListener("drop", (event) => {
    if (event.dataTransfer.files.length !== 1) {
      errorEl.textContent = "Select exactly one PDF resume.";
      return;
    }
    const file = event.dataTransfer.files[0];
    if (!file) return;
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    showFile(file);
  });
});

document.querySelectorAll("[data-hyperspeed]").forEach((section) => {
  const canvas = section.querySelector("[data-hyperspeed-canvas]");
  if (!canvas || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }

  const ctx = canvas.getContext("2d");
  const state = {
    width: 0,
    height: 0,
    speed: 1,
    targetSpeed: 1,
    lines: [],
    pointerDown: false,
  };
  const palette = ["#58d8ff", "#7c5cff", "#e95bd4", "#ffffff", "#64ffd2"];

  function resize() {
    const rect = section.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    state.width = rect.width;
    state.height = rect.height;
    canvas.width = Math.floor(rect.width * ratio);
    canvas.height = Math.floor(rect.height * ratio);
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    seedLines();
  }

  function seedLines() {
    const count = Math.max(120, Math.floor(state.width / 7));
    state.lines = Array.from({ length: count }, () => createLine(true));
  }

  function createLine(randomDepth) {
    const angle = Math.random() * Math.PI * 2;
    const depth = randomDepth ? Math.random() : 1;
    return {
      angle,
      depth,
      length: 0.08 + Math.random() * 0.22,
      width: 0.7 + Math.random() * 1.8,
      color: palette[Math.floor(Math.random() * palette.length)],
    };
  }

  function draw() {
    const cx = state.width / 2;
    const cy = state.height * 0.52;
    const maxRadius = Math.hypot(cx, cy);
    state.speed += (state.targetSpeed - state.speed) * 0.06;
    ctx.clearRect(0, 0, state.width, state.height);
    const gradient = ctx.createRadialGradient(cx, cy, 10, cx, cy, maxRadius);
    gradient.addColorStop(0, "rgba(20, 28, 64, 0.35)");
    gradient.addColorStop(1, "rgba(2, 6, 23, 0.96)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, state.width, state.height);

    for (const line of state.lines) {
      line.depth += 0.006 * state.speed;
      if (line.depth > 1.15) {
        Object.assign(line, createLine(false));
        line.depth = 0.02;
      }
      const eased = line.depth * line.depth;
      const radius = eased * maxRadius;
      const tailRadius = Math.max(0, radius - line.length * maxRadius * state.speed);
      const wobble = Math.sin(performance.now() * 0.0006 + line.angle * 3) * 0.035;
      const angle = line.angle + wobble;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(angle) * tailRadius, cy + Math.sin(angle) * tailRadius);
      ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius);
      ctx.strokeStyle = line.color;
      ctx.globalAlpha = Math.min(0.95, line.depth + 0.15);
      ctx.lineWidth = line.width * (0.4 + line.depth);
      ctx.shadowBlur = 12;
      ctx.shadowColor = line.color;
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
    ctx.shadowBlur = 0;
    requestAnimationFrame(draw);
  }

  function speedUp() {
    state.targetSpeed = 3.2;
    section.classList.add("is-speeding");
  }

  function slowDown() {
    state.targetSpeed = 1;
    section.classList.remove("is-speeding");
  }

  section.addEventListener("pointerdown", speedUp);
  window.addEventListener("pointerup", slowDown);
  window.addEventListener("resize", resize);
  resize();
  draw();
});

document.querySelectorAll("[data-light-rays-canvas]").forEach((canvas) => {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }
  const ctx = canvas.getContext("2d");
  const section = canvas.closest(".landing-hero") || canvas.parentElement;
  const mouse = { x: 0.5, y: 0.2 };
  const rays = Array.from({ length: 34 }, (_, index) => ({
    offset: index / 34,
    width: 0.025 + Math.random() * 0.05,
    alpha: 0.04 + Math.random() * 0.12,
    speed: 0.35 + Math.random() * 0.9,
  }));

  function resize() {
    const rect = section.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(rect.width * ratio);
    canvas.height = Math.floor(rect.height * ratio);
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  }

  function draw(time) {
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    ctx.clearRect(0, 0, width, height);
    const originX = width * (0.5 + (mouse.x - 0.5) * 0.18);
    const originY = -height * 0.12;
    rays.forEach((ray) => {
      const drift = Math.sin(time * 0.0004 * ray.speed + ray.offset * 8) * 0.12;
      const center = (ray.offset - 0.5 + drift) * width * 1.5 + width / 2;
      const gradient = ctx.createLinearGradient(originX, originY, center, height);
      gradient.addColorStop(0, `rgba(0,255,255,${ray.alpha * 1.8})`);
      gradient.addColorStop(0.48, `rgba(52,211,153,${ray.alpha})`);
      gradient.addColorStop(1, "rgba(0,255,255,0)");
      ctx.beginPath();
      ctx.moveTo(originX, originY);
      ctx.lineTo(center - width * ray.width, height);
      ctx.lineTo(center + width * ray.width, height);
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();
    });
    requestAnimationFrame(draw);
  }

  section.addEventListener("pointermove", (event) => {
    const rect = section.getBoundingClientRect();
    mouse.x = (event.clientX - rect.left) / rect.width;
    mouse.y = (event.clientY - rect.top) / rect.height;
  });
  window.addEventListener("resize", resize);
  resize();
  requestAnimationFrame(draw);
});

document.querySelectorAll("[data-interview-timer]").forEach((timer) => {
  const target = timer.querySelector("strong");
  const started = Date.now();
  setInterval(() => {
    const seconds = Math.floor((Date.now() - started) / 1000);
    const mins = String(Math.floor(seconds / 60)).padStart(2, "0");
    const secs = String(seconds % 60).padStart(2, "0");
    target.textContent = `${mins}:${secs}`;
  }, 1000);
});
