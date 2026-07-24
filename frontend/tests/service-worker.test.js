const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const listeners = {};
const deletedCaches = [];
const cachedRequests = [];
let responseFactory = () => ({ ok: true, type: "basic", clone() { return this; } });

const context = {
  URL,
  Promise,
  self: {
    location: { origin: "https://attendance.example.edu" },
    clients: { claim: async () => undefined },
    skipWaiting() {},
    addEventListener(type, listener) { listeners[type] = listener; },
  },
  caches: {
    async keys() { return ["knmiet-connect-static-v0", "knmiet-connect-static-v1", "unrelated-cache"]; },
    async delete(name) { deletedCaches.push(name); return true; },
    async match() { return undefined; },
    async open() {
      return {
        async addAll() {},
        async put(request) { cachedRequests.push(request.url); },
      };
    },
  },
  fetch: async () => responseFactory(),
};

const source = fs.readFileSync(path.join(__dirname, "..", "service-worker.js"), "utf8");
vm.runInNewContext(source, context, { filename: "service-worker.js" });

async function activate() {
  let pending;
  listeners.activate({ waitUntil(promise) { pending = promise; } });
  await pending;
}

async function dispatchFetch(url, method = "GET") {
  let pending;
  listeners.fetch({
    request: { url, method },
    respondWith(promise) { pending = promise; },
  });
  await pending;
  await new Promise((resolve) => setTimeout(resolve, 0));
}

(async () => {
  await activate();
  assert.deepEqual(
    deletedCaches.sort(),
    ["knmiet-connect-static-v0", "unrelated-cache"],
    "activation must evict every stale cache",
  );

  await dispatchFetch("https://attendance.example.edu/styles.css");
  assert.deepEqual(cachedRequests, ["https://attendance.example.edu/styles.css"]);

  await dispatchFetch("https://attendance.example.edu/submit", "POST");
  await dispatchFetch("https://cdn.example.edu/image.png");
  responseFactory = () => ({ ok: false, type: "basic", clone() { return this; } });
  await dispatchFetch("https://attendance.example.edu/missing.css");
  responseFactory = () => ({ ok: true, type: "opaque", clone() { return this; } });
  await dispatchFetch("https://attendance.example.edu/opaque.css");

  assert.deepEqual(
    cachedRequests,
    ["https://attendance.example.edu/styles.css"],
    "only successful same-origin GET responses may be cached",
  );
  console.log("service-worker-cache-lifecycle-ok");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
