const assert = require("node:assert/strict");
const Module = require("node:module");
const path = require("node:path");
const test = require("node:test");

const FunASRManager = require("../src/helpers/funasrManager");

function restoreEnvironment(name, value) {
  if (value === undefined) {
    delete process.env[name];
  } else {
    process.env[name] = value;
  }
}

test("system Python environment drops inherited embedded paths", () => {
  const originalPythonHome = process.env.PYTHONHOME;
  const originalPythonPath = process.env.PYTHONPATH;
  const originalLdLibraryPath = process.env.LD_LIBRARY_PATH;
  const originalDyldLibraryPath = process.env.DYLD_LIBRARY_PATH;
  const originalLoad = Module._load;

  process.env.PYTHONHOME = "/missing/ququ/python";
  process.env.PYTHONPATH = "/missing/ququ/python/lib/python3.11/site-packages";
  process.env.LD_LIBRARY_PATH = "/missing/ququ/python/lib";
  process.env.DYLD_LIBRARY_PATH = "/missing/ququ/python/lib";
  Module._load = function (request) {
    if (request === "electron") {
      return { app: { getPath: () => "/tmp/ququ-test" } };
    }
    return originalLoad.apply(this, arguments);
  };

  try {
    const manager = new FunASRManager();
    manager.getEmbeddedPythonPath = () =>
      path.join("/missing", "ququ", "python", "bin", "python3.11");

    const env = manager.buildPythonEnvironment();

    assert.equal(Object.hasOwn(env, "PYTHONHOME"), false);
    assert.equal(Object.hasOwn(env, "PYTHONPATH"), false);
    assert.equal(Object.hasOwn(env, "LD_LIBRARY_PATH"), false);
    assert.equal(Object.hasOwn(env, "DYLD_LIBRARY_PATH"), false);
  } finally {
    Module._load = originalLoad;
    restoreEnvironment("PYTHONHOME", originalPythonHome);
    restoreEnvironment("PYTHONPATH", originalPythonPath);
    restoreEnvironment("LD_LIBRARY_PATH", originalLdLibraryPath);
    restoreEnvironment("DYLD_LIBRARY_PATH", originalDyldLibraryPath);
  }
});
