const authStatus = document.querySelector("#authStatus");
const scanStatus = document.querySelector("#scanStatus");
const userTitle = document.querySelector("#userTitle");
const attendanceRows = document.querySelector("#attendanceRows");
const qrBox = document.querySelector("#qrBox");

let currentUser = null;

function readCookie(name) {
  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie.split("; ").find((item) => item.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

async function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrfToken = readCookie("csrf_token");
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken;
    }
  }
  const response = await fetch(`/api${path}`, {
    credentials: "include",
    ...options,
    headers,
  });
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(data.detail || data.message || "Request failed");
  }
  return data;
}

document.querySelector("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  authStatus.textContent = "Signing in...";
  try {
    currentUser = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: document.querySelector("#email").value,
        password: document.querySelector("#password").value,
      }),
    });
    userTitle.textContent = `${currentUser.name} (${currentUser.role})`;
    authStatus.textContent = "Signed in";
    await loadAttendance();
  } catch (error) {
    authStatus.textContent = error.message;
  }
});

document.querySelector("#logoutBtn").addEventListener("click", async () => {
  await api("/auth/logout", { method: "POST" });
  currentUser = null;
  userTitle.textContent = "Not signed in";
  attendanceRows.replaceChildren();
});

document.querySelector("#registerDeviceBtn").addEventListener("click", async () => {
  scanStatus.textContent = "Registering device...";
  try {
    const result = await api("/attendance/devices/register", { method: "POST" });
    scanStatus.textContent = result.message;
  } catch (error) {
    scanStatus.textContent = error.message;
  }
});

document.querySelector("#scanForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  scanStatus.textContent = "Submitting scan...";
  try {
    const result = await api("/attendance/scan", {
      method: "POST",
      body: JSON.stringify({
        session_id: document.querySelector("#sessionId").value,
        token: document.querySelector("#totpToken").value,
      }),
    });
    scanStatus.textContent = result.message;
    await loadAttendance();
  } catch (error) {
    scanStatus.textContent = error.message;
  }
});

document.querySelector("#sessionForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  qrBox.textContent = "Starting session...";
  try {
    const result = await api("/attendance/sessions", {
      method: "POST",
      body: JSON.stringify({ course_id: document.querySelector("#courseId").value }),
    });
    qrBox.textContent = `${result.session_id}\n${result.qr_payload}`;
  } catch (error) {
    qrBox.textContent = error.message;
  }
});

document.querySelector("#refreshAttendanceBtn").addEventListener("click", loadAttendance);

async function loadAttendance() {
  try {
    const rows = await api("/attendance/me");
    const tableRows = rows.map((row) => {
      const tableRow = document.createElement("tr");
      const values = [
        `${row.course_code} - ${row.course_name}`,
        row.attended,
        row.total_sessions,
        row.percentage,
      ];
      values.forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = String(value);
        tableRow.appendChild(cell);
      });
      return tableRow;
    });
    attendanceRows.replaceChildren(...tableRows);
  } catch {
    attendanceRows.replaceChildren();
  }
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/service-worker.js");
}
