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

function assert(ok, message) { if (!ok) throw new Error(message); }

function main() {
  const source = fs.readFileSync(process.argv[2], "utf8");
  const attrs = new Map();
  const status = {textContent: ""};
  const pane = {innerHTML: ""};
  const cover = {setAttribute(k, v) { attrs.set(k, v); }};
  const item = {setAttribute() {}};
  const scroller = {scrollTop: 77};
  const frame = {contentDocument: {scrollingElement: scroller, documentElement: scroller}};
  const context = vm.createContext({
    VIEW: {front_matter: {text: "FORM 10-K\nACME", chars: 14, truncated: false},
           markdown: false, items: [{item: "1", status: "extracted", start: 20, heading_text: "Item 1"}]},
    SEL: 8, SYNC_GUARD: false, region: {start: 200, end: 400},
    document: {
      getElementById(id) { return id === "src-frame" ? frame : id === "anchor-status" ? status : null; },
      querySelector(s) { return s === "#pane" ? pane : s === "#cover" ? cover : s.startsWith("#pane ") ? {} : null; },
      querySelectorAll(s) { return s === ".it" ? [item] : []; },
    },
    esc: String, mdToHtml: String, bindPaneScroll() {},
    itemRegion() { return context.region; },
  });
  vm.runInContext([
    "const $ = s => document.querySelector(s);",
    functionSource(source, "function anchorStatus("),
    functionSource(source, "function scrollSourceToItem("),
    functionSource(source, "function showCover("),
  ].join("\n"), context);

  vm.runInContext("showCover()", context);
  assert(context.SEL === -1, "cover did not become the default selection");
  assert(pane.innerHTML.includes("FORM 10-K"), "cover did not render front matter");
  assert(scroller.scrollTop === 0, "cover did not return the source to its opening");
  assert(status.textContent === "Cover", "cover location was not reported");
  assert(attrs.get("aria-current") === "true", "cover row was not marked current");

  scroller.scrollTop = 0;
  vm.runInContext("scrollSourceToItem(0)", context);
  assert(scroller.scrollTop === 180, "anchored item did not move the source scroller");
  assert(status.textContent === "Item 1", "successful item jump was silent");

  context.VIEW.items[0] = {item: "1C", status: "omitted", start: null, heading_text: null};
  context.region = null;
  scroller.scrollTop = 33;
  vm.runInContext("scrollSourceToItem(0)", context);
  assert(scroller.scrollTop === 33, "span-less item guessed a source position");
  assert(status.textContent === "No span · Item 1C",
         "span-less item did not explain why it cannot jump");

  context.VIEW.items[0] = {item: "1", status: "extracted", start: 20, heading_text: "Item 1"};
  context.region = null;
  vm.runInContext("scrollSourceToItem(0)", context);
  assert(status.textContent === "Heading not found",
         "a missing heading did not use the compact source status");
}

try { main(); } catch (error) { console.error(error.message); process.exitCode = 1; }
