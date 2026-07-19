import { existsSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const backend = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(backend);
const windows = process.platform === "win32";
const venvPython = (directory) => path.join(directory, windows ? "Scripts/python.exe" : "bin/python");
const managedVenv = path.join(backend, ".venv");
process.env.FLASK_ENV = "development";
process.env.SESSION_COOKIE_SECURE = "false";

function works(command, args = ["--version"]) {
  return spawnSync(command, args, { cwd: root, stdio: "ignore" }).status === 0;
}

function run(command, args, label) {
  console.log(`[dev] ${label}`);
  const result = spawnSync(command, args, { cwd: root, stdio: "inherit", env: process.env });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

function findPython() {
  const environments = [managedVenv, path.join(root, "Optional/.venv"), path.join(root, ".venv")];
  for (const environment of environments) {
    const python = venvPython(environment);
    if (existsSync(python) && works(python)) return python;
  }

  const systemPython = windows ? ["py", "python"] : ["python3", "python"];
  const command = systemPython.find((candidate) => works(candidate));
  if (!command) {
    console.error("Python 3.11+ is required. Install Python, then run npm run dev again.");
    process.exit(1);
  }
  run(command, ["-m", "venv", managedVenv], "Creating Backend/.venv");
  return venvPython(managedVenv);
}

const python = findPython();
if (!works(python, ["-c", "import flask, flask_sqlalchemy, fitz, sklearn, reportlab"])) {
  run(python, ["-m", "pip", "install", "-r", "Backend/requirements.txt"], "Installing Python dependencies");
}

run(
  python,
  ["-m", "flask", "--app", "Backend/wsgi.py", "db", "upgrade", "-d", "Backend/migrations"],
  "Applying database migrations",
);

const port = process.env.PORT || "5000";
console.log(`[dev] CareerPath ATS: http://127.0.0.1:${port}`);
const debugArgs = process.env.FLASK_DEBUG?.toLowerCase() === "true" ? ["--debug"] : [];
const server = spawn(
  python,
  ["-m", "flask", "--app", "Backend/wsgi.py", "run", ...debugArgs, "--host=127.0.0.1", `--port=${port}`],
  { cwd: root, stdio: "inherit", env: process.env },
);

server.on("exit", (code) => process.exit(code ?? 0));
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.kill(signal));
}
