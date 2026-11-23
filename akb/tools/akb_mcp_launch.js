#!/usr/bin/env node
/**
 * Cross-platform launcher for tools/akb_mcp_server.py.
 *
 * Windows: prefer tools/akb_mcp_launch.cmd via cmd.exe so the Python
 * app-execution alias keeps working stdio pipes for Cursor.
 * Linux/macOS: spawn python3/python directly.
 *
 * mcp.json on this repo targets Windows Cursor with cmd.exe + .cmd.
 * This Node entry remains for offline tests and non-Windows hosts.
 */
"use strict";

const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const script = path.join(__dirname, "akb_mcp_server.py");
const winCmd = path.join(__dirname, "akb_mcp_launch.cmd");

function exists(file) {
  try {
    return fs.existsSync(file) && fs.statSync(file).isFile();
  } catch (_) {
    return false;
  }
}

function run(command, args) {
  console.error(`akb-mcp-launch: ${command} ${args.join(" ")}`);
  const child = spawn(command, args, {
    stdio: "inherit",
    env: process.env,
    windowsHide: true,
    shell: false,
  });
  child.on("exit", (code, signal) => {
    if (signal) process.exit(1);
    process.exit(code == null ? 1 : code);
  });
  child.on("error", (err) => {
    console.error(`akb-mcp-launch: failed: ${err.message}`);
    process.exit(1);
  });
}

function main() {
  if (!exists(script)) {
    console.error(`akb-mcp-launch: missing server script: ${script}`);
    process.exit(2);
  }
  if (process.env.AKB_PYTHON) {
    run(process.env.AKB_PYTHON, ["-u", script, ...process.argv.slice(2)]);
    return;
  }
  if (process.platform === "win32") {
    if (!exists(winCmd)) {
      console.error(`akb-mcp-launch: missing ${winCmd}`);
      process.exit(2);
    }
    run("cmd.exe", ["/d", "/s", "/c", winCmd, ...process.argv.slice(2)]);
    return;
  }
  run("python3", ["-u", script, ...process.argv.slice(2)]);
}

main();
