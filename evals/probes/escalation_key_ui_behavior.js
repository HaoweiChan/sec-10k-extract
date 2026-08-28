"use strict";

const fs = require("node:fs");
const vm = require("node:vm");

function functionSource(source, signature) {
  const start = source.indexOf(signature);
  if (start < 0) throw new Error(`missing ${signature}`);
  const open = source.indexOf("{", start + signature.length);
  let depth = 0;
  for (let i = open; i < source.length; i++) {
    if (source[i] === "{") depth++;
    if (source[i] === "}" && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`unbalanced ${signature}`);
}

function assert(ok, message) {
  if (!ok) throw new Error(message);
}

function response(ok, valid = false, status = ok ? 200 : 403) {
  return {ok, status, json: async () => ({valid, doc_status: "success", items: [], counts: {}, warnings: [], meta: {}, trace: []})};
}

function deferred() {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  return {promise, resolve};
}

function harness(source, saved = "") {
  const storage = new Map(saved ? [["sec10k.escalation-key", saved]] : []);
  const elements = new Map();
  const element = id => {
    const listeners = {};
    const classes = new Set();
    const value = {
      id, value: "", textContent: "", innerHTML: "", hidden: true, disabled: false,
      addEventListener(type, fn) { listeners[type] = fn; },
      dispatch(type, event = {}) { return listeners[type]?.(event); },
      classList: {
        toggle(name, on) { on ? classes.add(name) : classes.delete(name); },
        contains(name) { return classes.has(name); },
      },
    };
    elements.set(id, value);
    return value;
  };
  for (const id of ["esc-key-row", "esc-key", "verify-key", "key-status", "fx", "sha"])
    element(id);

  let verify = async () => response(false);
  const extract = [];
  const context = vm.createContext({
    document: {querySelector: selector => elements.get(selector.slice(1)) || null},
    localStorage: {
      getItem: key => storage.get(key) || null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: key => storage.delete(key),
    },
    fetch: async (url, opts = {}) => {
      if (url === "/api/meta") return {json: async () => ({git_sha: "test", escalation_token_required: true, fixtures: []})};
      if (url === "/api/extract/verify-key") return verify(url, opts);
      extract.push({url, opts});
      return response(true, false);
    },
    deepLink() {}, loadCapabilities() {}, busy() {}, render() {},
  });
  const keyBlock = source.slice(source.indexOf('const KEY_STORE = "sec10k.escalation-key"'),
                                source.indexOf("// D7 (postmortem", source.indexOf('const KEY_STORE')));
  const program = [
    "const $ = s => document.querySelector(s);",
    functionSource(source, "async function boot()"),
    keyBlock,
  ].join("\n");
  vm.runInContext(program, context);
  return {
    context, storage, elements, extract,
    setVerify(fn) { verify = fn; },
    run(expression) { return vm.runInContext(expression, context); },
  };
}

async function boot(h) {
  await h.run("boot()");
  return h.elements.get("esc-key");
}

async function main() {
  const source = fs.readFileSync(process.argv[2], "utf8");
  const keyName = "sec10k.escalation-key";

  const h = harness(source);
  const field = await boot(h);
  const status = h.elements.get("key-status");
  h.setVerify(async () => response(true, false));
  field.value = "wrong-key";
  await h.run("verifyKey()");
  assert(status.textContent === "Key not valid", "wrong key did not stay invalid");
  assert(!status.classList.contains("verified"), "wrong key enabled green state");
  assert(!h.storage.has(keyName), "wrong key was remembered");
  await h.run('call("/api/extract/fixture", {method:"POST"})');
  assert(!h.extract.at(-1).opts.headers?.["X-Escalation-Token"], "wrong/raw field was sent to extraction");

  h.setVerify(async () => response(true, true));
  field.value = "valid-key-A";
  await h.run("verifyKey()");
  assert(status.textContent === "✓ Enabled" && status.classList.contains("verified"), "valid key was not enabled");
  assert(h.storage.get(keyName) === "valid-key-A", "valid key was not remembered");
  await h.run('call("/api/extract/url", {method:"POST", headers:{"Content-Type":"application/json"}})');
  assert(h.extract.at(-1).opts.headers["X-Escalation-Token"] === "valid-key-A", "verified key was not the extraction header");

  field.value = "edited-key-B";
  field.dispatch("input");
  assert(status.textContent === "Not verified" && !status.classList.contains("verified"), "editing did not clear enabled state");
  assert(!h.storage.has(keyName), "editing did not clear remembered key");
  await h.run('call("/api/extract/upload", {method:"POST"})');
  assert(!h.extract.at(-1).opts.headers?.["X-Escalation-Token"], "edited unverified key was sent to extraction");

  const reload = harness(source, "valid-key-A");
  reload.setVerify(async () => response(true, true));
  await boot(reload);
  assert(reload.elements.get("key-status").textContent === "✓ Enabled", "remembered key was not reverified on reload");
  await reload.run('call("/api/extract/fixture", {method:"POST"})');
  assert(reload.extract.at(-1).opts.headers["X-Escalation-Token"] === "valid-key-A", "reverified reload key was not sent");

  const stale = harness(source);
  const staleField = await boot(stale);
  const late = deferred();
  stale.setVerify(async () => late.promise);
  staleField.value = "valid-key-A";
  const pending = stale.run("verifyKey()");
  staleField.value = "edited-key-B";
  staleField.dispatch("input");
  late.resolve(response(true, true));
  await pending;
  assert(stale.elements.get("key-status").textContent === "Not verified", "stale response re-enabled edited input");
  assert(!stale.storage.has(keyName), "stale response remembered the old key");
  await stale.run('call("/api/extract/url", {method:"POST"})');
  assert(!stale.extract.at(-1).opts.headers?.["X-Escalation-Token"], "stale key was sent to extraction");

  const superseded = harness(source);
  const sameField = await boot(superseded);
  const first = deferred();
  superseded.setVerify(async () => first.promise);
  sameField.value = "valid-key-A";
  const oldRequest = superseded.run("verifyKey()");
  superseded.setVerify(async () => response(false));
  await superseded.run("verifyKey()");
  first.resolve(response(true, true));
  await oldRequest;
  assert(superseded.elements.get("key-status").textContent === "Key not valid", "superseded request re-enabled the same field value");
  assert(!superseded.storage.has(keyName), "superseded request remembered its key");
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
