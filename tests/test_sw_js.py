"""Unit tests for the web push service worker (``app/static/sw.js``).

The service worker is plain browser JavaScript, so these tests execute it in
Node with a stubbed ``ServiceWorkerGlobalScope`` (``self``) and assert the
notification/click contract the backend depends on.

Requires ``node`` on PATH; skipped otherwise.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which("node")
SW_PATH = Path(__file__).resolve().parent.parent / "app" / "static" / "sw.js"

HARNESS = r"""
const fs = require("fs");
const assert = require("assert");

const swSource = fs.readFileSync(process.argv[1], "utf8");

const calls = {
  skipWaiting: 0,
  claim: 0,
  shown: [],
  closed: 0,
  focused: 0,
  navigated: [],
  opened: [],
  matchAllArgs: [],
};

const listeners = {};

const clients = {
  claim: async () => { calls.claim += 1; },
  matchAll: async (opts) => {
    calls.matchAllArgs.push(opts);
    return clients._windows;
  },
  openWindow: async (url) => { calls.opened.push(url); return {}; },
  _windows: [],
};

globalThis.self = {
  skipWaiting: () => { calls.skipWaiting += 1; },
  clients,
  registration: {
    showNotification: (title, options) => {
      calls.shown.push({ title, options });
      return Promise.resolve();
    },
  },
  addEventListener: (type, fn) => { listeners[type] = fn; },
};

eval(swSource);

function waitUntil(arg) {
  // handlers call event.waitUntil(promise); the test fire() helper passes a fn.
  const result = typeof arg === "function" ? arg() : arg;
  if (result && typeof result.then === "function") {
    return result.then(() => {});
  }
  return Promise.resolve();
}

function fire(type, event) {
  return waitUntil(() => listeners[type]({ ...event, waitUntil }));
}

(async () => {
  // --- install -> skipWaiting -------------------------------------------------
  await fire("install", {});
  assert.strictEqual(calls.skipWaiting, 1, "skipWaiting called on install");

  // --- activate -> clients.claim ----------------------------------------------
  await fire("activate", {});
  assert.strictEqual(calls.claim, 1, "clients.claim called on activate");

  // --- push with full payload --------------------------------------------------
  await fire("push", {
    data: {
      json: () => ({
        title: "Hello",
        body: "Body text",
        data: { icon: "/i.png", url: "/orders", type: "order", tag: "t1" },
      }),
    },
  });
  assert.strictEqual(calls.shown.length, 1, "showNotification called once");
  const n1 = calls.shown[0];
  assert.strictEqual(n1.title, "Hello", "title from payload");
  assert.strictEqual(n1.options.body, "Body text", "body from payload");
  assert.strictEqual(n1.options.icon, "/i.png", "icon from payload data");
  assert.strictEqual(n1.options.tag, "t1", "tag from payload data");
  assert.strictEqual(n1.options.renotify, true, "renotify set");
  assert.deepStrictEqual(n1.options.data, { url: "/orders", type: "order" });

  // --- push with invalid JSON -> safe fallback ---------------------------------
  await fire("push", {
    data: { json: () => { throw new Error("bad json"); } },
  });
  const n2 = calls.shown[1];
  assert.strictEqual(n2.title, "Bouwnce", "fallback title on bad JSON");
  assert.strictEqual(n2.options.body, "", "fallback body on bad JSON");

  // --- push with no data -> defaults -------------------------------------------
  await fire("push", { data: null });
  const n3 = calls.shown[2];
  assert.strictEqual(n3.title, "Bouwnce", "default title");
  assert.strictEqual(n3.options.icon, "/static/icon-192.png", "default icon");
  assert.strictEqual(n3.options.tag, "bouwnce-push", "default tag");
  assert.deepStrictEqual(n3.options.data, { url: "/", type: "" }, "default data");

  // --- notificationclick with an open window client -----------------------------
  const win = {
    focus: async () => { calls.focused += 1; },
    navigate: async (url) => { calls.navigated.push(url); },
  };
  clients._windows = [win];
  await fire("notificationclick", {
    notification: { close: () => { calls.closed += 1; }, data: { url: "/profile" } },
  });
  assert.strictEqual(calls.closed, 1, "notification closed on click");
  assert.strictEqual(calls.focused, 1, "existing client focused");
  assert.deepStrictEqual(calls.navigated, ["/profile"], "existing client navigated");
  assert.strictEqual(calls.opened.length, 0, "no openWindow when a client exists");
  assert.deepStrictEqual(
    calls.matchAllArgs[0],
    { type: "window", includeUncontrolled: true },
    "matchAll window+uncontrolled"
  );

  // --- notificationclick with a window client that lacks navigate() ------------
  const winNoNav = { focus: async () => { calls.focused += 1; } };
  clients._windows = [winNoNav];
  const openedBefore = calls.opened.length;
  await fire("notificationclick", {
    notification: { close: () => {}, data: { url: "/older-client" } },
  });
  assert.strictEqual(
    calls.opened.length,
    openedBefore,
    "no openWindow when an existing client focuses"
  );

  // --- notificationclick with no clients -> openWindow --------------------------
  clients._windows = [];
  await fire("notificationclick", {
    notification: { close: () => {}, data: { url: "/settings" } },
  });
  assert.deepStrictEqual(calls.opened, ["/settings"], "openWindow with target url");

  // --- notificationclick default target ------------------------------------------
  await fire("notificationclick", {
    notification: { close: () => {}, data: null },
  });
  assert.strictEqual(
    calls.opened[calls.opened.length - 1],
    "/",
    "openWindow defaults to /"
  );

  console.log("SW_ALL_PASS");
})().catch((err) => {
  console.error("SW_FAIL:", err && err.message ? err.message : err);
  process.exit(1);
});
"""


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_service_worker_contract():
    assert SW_PATH.exists(), f"missing {SW_PATH}"
    proc = subprocess.run(
        [NODE, "-e", HARNESS, str(SW_PATH)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert (
        proc.returncode == 0
    ), f"sw.js contract test failed:\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    assert "SW_ALL_PASS" in proc.stdout
