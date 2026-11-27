// Offline browser regression for replay import/Forget races.
// Usage: PW_CORE=/path/to/playwright-core CHROME=/path/to/chrome node tests/browser/replay-forget.cjs [_site]
const { chromium } = require(process.env.PW_CORE || "playwright-core");
const assert = require("node:assert/strict");
const { createServer } = require("node:http");
const { readFile, writeFile } = require("node:fs/promises");
const { resolve, extname, sep } = require("node:path");
const { createHash } = require("node:crypto");

const root = resolve(process.argv[2] || "_site");
const marker = "synthetic-replay-probe-z41";
const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Synthetic offline replay fixture" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><name>Fake fixture, not a real route</name><trkseg>
    <trkpt lat="0.000000" lon="0.000000"><time>2000-01-01T00:00:00Z</time><hdop>1.0</hdop></trkpt>
    <trkpt lat="0.000010" lon="0.000000"><time>2000-01-01T00:00:01Z</time><hdop>1.0</hdop></trkpt>
    <trkpt lat="0.000020" lon="0.000000"><time>2000-01-01T00:00:02Z</time><hdop>1.0</hdop></trkpt>
  </trkseg></trk>
</gpx>`;
const types = {
  ".html": "text/html", ".js": "application/javascript", ".mjs": "application/javascript",
  ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml",
  ".wasm": "application/wasm", ".zip": "application/zip", ".py": "text/plain",
  ".txt": "text/plain", ".onnx": "application/octet-stream", ".stl": "model/stl",
};
const bad = [], requests = [], pageErrors = [], workerEvents = [];
const hashes = {};

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, "http://127.0.0.1");
    const relative = decodeURIComponent(url.pathname).replace(/^\/+/, "") || "replay.html";
    const file = resolve(root, relative);
    if (req.method !== "GET" || url.search || relative.includes("..") || !file.startsWith(root + sep)) {
      bad.push([req.method, req.url]);
      res.writeHead(404);
      return res.end();
    }
    let body = await readFile(file);
    hashes[relative] = createHash("sha256").update(body).digest("hex");
    // Hold the real Python worker at its parsing boundary so Forget deterministically
    // races the parsing job rather than depending on a fast machine's timing.
    if (relative === "assets/replay-worker.js") {
      const source = body.toString("utf8");
      const needle = 'self.postMessage({ id, status: "running" });';
      assert.ok(source.includes(needle));
      body = Buffer.from(source.replace(needle, needle + '\n    await new Promise((resolve) => setTimeout(resolve, 1000));'));
    }
    res.writeHead(200, { "content-type": types[extname(file)] || "application/octet-stream", "cache-control": "no-store" });
    res.end(body);
  } catch (error) {
    res.writeHead(404);
    res.end();
  }
});

(async () => {
  await new Promise((resolveListen) => server.listen(0, "127.0.0.1", resolveListen));
  const base = `http://127.0.0.1:${server.address().port}`;
  let browser;
  try {
    browser = await chromium.launch({ executablePath: process.env.CHROME || chromium.executablePath() });
    const context = await browser.newContext({ serviceWorkers: "block" });
    await context.route("**/*", (route) => {
      const req = route.request();
      const url = new URL(req.url());
      requests.push([req.method(), url.pathname]);
      if (url.origin !== base || req.method() !== "GET" || url.search || req.postData()) {
        bad.push([req.method(), req.url()]);
        return route.abort();
      }
      return route.continue();
    });
    await context.addInitScript(() => {
      const NativeWorker = window.Worker;
      window.Worker = class {
        constructor(...args) {
          const worker = new NativeWorker(...args);
          if (String(args[0]).includes("replay-worker")) {
            worker.addEventListener("message", (event) => {
              const data = event.data || {};
              if (data.status === "running" && window.__recordReplayWorker) window.__recordReplayWorker("running");
              if (data.trace && window.__recordReplayWorker) {
                const parsed = JSON.parse(data.trace);
                window.__recordReplayWorker(parsed.ticks?.length ? "finished" : "error:empty worker trace");
              }
              if (data.error && window.__recordReplayWorker) window.__recordReplayWorker(`error:${data.error}`);
            });
          }
          return worker;
        }
      };
    });
    const page = await context.newPage();
    await page.exposeFunction("__recordReplayWorker", (event) => workerEvents.push(event));
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("websocket", (socket) => bad.push(["WebSocket", socket.url()]));
    const options = page.locator("#log-select option");
    const builtIns = ["example", "sim-example", "sim-camera", "sim-before"];
    const ready = () => page.waitForFunction(() =>
      document.querySelectorAll("#log-select option").length === 4 &&
      document.querySelector("#tick-count").textContent.startsWith("Tick 1 of"));
    const assertForgotten = async () => {
      await ready();
      assert.deepEqual(await options.evaluateAll((nodes) => nodes.map((node) => node.value)), builtIns);
      assert.equal(await page.locator("#log-select").inputValue(), "example");
      assert.equal(await page.locator("#forget-files").isHidden(), true);
      assert.equal(await page.evaluate((text) => document.body.innerText.includes(text), marker), false);
    };
    const forget = async () => {
      await page.locator("#forget-files").click();
      await assertForgotten();
    };
    const upload = async (selector, name, data, mimeType) => page.locator(selector).setInputFiles({
      name, mimeType, buffer: Buffer.from(data),
    });

    await page.goto(`${base}/replay.html`);
    await ready();
    const trace = JSON.parse(await readFile(resolve(root, "data/replay-example.json"), "utf8"));
    trace.note = marker;
    trace.ticks = trace.ticks.slice(0, 2);
    await upload("#file-input", `${marker}.json`, JSON.stringify(trace), "application/json");
    await page.waitForFunction((text) =>
      document.querySelector("#tick-count").textContent === "Tick 1 of 2" &&
      document.querySelector("#log-note").textContent.includes(text), marker);
    assert.equal(await options.count(), 5);
    await page.locator("#btn-next").click();
    assert.equal(await page.locator("#tick-count").textContent(), "Tick 2 of 2");
    await forget();

    await upload("#file-input", `${marker}-broken.json`, "{", "application/json");
    await page.waitForFunction(() => document.querySelector("#log-note").classList.contains("error"));
    assert.equal(await options.count(), 4);
    assert.match(await page.locator("#log-note").textContent(), /Could not read/);
    await forget();

    const build = JSON.parse(await readFile(resolve(root, "data/build.json"), "utf8"));
    assert.equal(build.python, true, "The offline fixture build must include Pyodide");
    await upload("#gpx-input", `${marker}.gpx`, gpx, "application/gpx+xml");
    await page.waitForFunction(() => document.querySelector("#log-note").textContent.includes("Starting Python"));
    // The binding, rather than page globals, survives any accidental reload.
    await page.waitForFunction(() => document.querySelector("#log-note").textContent.includes("Simulating"), null, { timeout: 120000 });
    assert.ok(workerEvents.includes("running"), "The real Python GPX worker must be active before Forget");
    assert.equal(await options.count(), 4);
    assert.equal(workerEvents.includes("finished"), false, "Forget must happen before parsing completes");
    await page.locator("#forget-files").click();
    await assertForgotten();
    const deadline = Date.now() + 120000;
    while (!workerEvents.includes("finished") && !workerEvents.some((event) => event.startsWith("error:"))) {
      if (Date.now() > deadline) throw new Error("GPX worker did not finish after Forget");
      await new Promise((resolveWait) => setTimeout(resolveWait, 25));
    }
    assert.deepEqual(workerEvents.filter((event) => event.startsWith("error:")), []);
    assert.ok(workerEvents.includes("finished"), "Forget must not reload and terminate the parsing worker");
    await assertForgotten();
    assert.deepEqual(bad, []);
    assert.deepEqual(pageErrors, []);
    const receipt = {
      browser: browser.version(),
      fixtures: "Static synthetic two-tick JSON, malformed JSON, and three-fix fake GPX at 0,0",
      validLoadedAndStepped: true,
      malformedRejected: true,
      forgetRestoredFourBuiltIns: 3,
      pythonWorkerRunningBeforeForget: true,
      pythonWorkerFinishedAfterForget: true,
      importedTraceRemainedAbsent: true,
      observedRequests: requests.length,
      methods: [...new Set(requests.map((entry) => entry[0]))],
      observedStaticPaths: [...new Set(requests.map((entry) => entry[1]))].sort(),
      unexpectedRequestsOrSockets: bad,
      pageErrors,
      inputSha256: hashes,
      limitations: "Offline synthetic browser simulation only; worker start is delayed at the parsing boundary for a deterministic race. No hardware, real route, external request, SITL, or flight validation.",
    };
    const serialized = JSON.stringify(receipt, null, 2) + "\n";
    if (process.argv[3]) await writeFile(process.argv[3], serialized);
    console.log(serialized, end="");
  } finally {
    if (browser) await browser.close();
    server.closeAllConnections();
    await new Promise((resolveClose) => server.close(resolveClose));
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
