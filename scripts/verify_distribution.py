#!/usr/bin/env python3
"""Install the wheel offline in a fresh venv and test it outside the checkout."""

import argparse
from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import venv
import zipfile

from hook_doctor import __version__

ROOT = Path(__file__).resolve().parents[1]


def verify(wheel, result):
    checks = result["checks"]

    def require(name, condition):
        if not condition:
            raise RuntimeError(name)
        checks.append({"name": name, "passed": True})

    with zipfile.ZipFile(wheel) as archive:
        metadata_names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        require("one package metadata file", len(metadata_names) == 1)
        metadata = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8"))
        require("distribution version matches source", metadata["Version"] == __version__)
        require("no third-party runtime dependencies", not metadata.get_all("Requires-Dist"))
        packaged_profile = archive.read("hook_doctor/profiles/dsh-claude-ce7073d.json")
        source_profile = ROOT / "scripts/hook_doctor/profiles/dsh-claude-ce7073d.json"
        require("pinned profile shipped without changes", packaged_profile == source_profile.read_bytes())
        require("only runtime package and metadata in wheel", all(
            name.startswith(("hook_doctor/", "hook_portability_doctor-")) for name in archive.namelist()
        ))

    with tempfile.TemporaryDirectory(prefix="hpd-wheel-") as temporary:
        base = Path(temporary)
        environment = base / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        bin_dir = environment / ("Scripts" if os.name == "nt" else "bin")
        python = bin_dir / ("python.exe" if os.name == "nt" else "python")
        cli = bin_dir / ("hook-portability-doctor.exe" if os.name == "nt" else "hook-portability-doctor")
        consumer = base / "consumer 中文 space"
        consumer.mkdir()
        env = {key: value for key, value in os.environ.items()
               if key not in ("PYTHONPATH", "PYTHONHOME")}
        env.update(PYTHONNOUSERSITE="1", PYTHONUTF8="1", PIP_DISABLE_PIP_VERSION_CHECK="1")

        def run(arguments):
            return subprocess.run(list(map(str, arguments)), cwd=consumer, env=env,
                                  capture_output=True, text=True, encoding="utf-8", timeout=60)

        installation = run([python, "-m", "pip", "install", "--no-index", "--no-deps", wheel])
        if installation.returncode:
            raise RuntimeError(f"Offline installation failed: {installation.stderr}")
        require("wheel installs offline in fresh environment", True)
        imported = run([python, "-c", "import hook_doctor; print(hook_doctor.__file__)"])
        require("imports resolve to installed package",
                imported.returncode == 0 and Path(imported.stdout.strip()).is_relative_to(environment))

        command = 'echo must-not-run > "hook-executed.txt"'

        def config(event="Stop", **fields):
            return {"hooks": {event: [{"hooks": [{"command": command, **fields}]}]}}

        scenarios = [
            ("supported", config(), ["--strict"], 0, "no_static_differences_found"),
            ("incompatible", config("PreCompact"), ["--strict"], 1, "incompatibilities_found"),
            ("report-only", config("PreCompact"), [], 0, "incompatibilities_found"),
            ("behavior-change", config(args=["ignored"]), ["--strict"], 0, "behavior_changes_found"),
            ("no-hooks", {"hooks": {}}, ["--strict"], 0, "no_hooks"),
            ("invalid-json", "{", [], 2, None),
            ("context-unknown", config(command="node " + "$" + "{CLAUDE_PLUGIN_ROOT}/x.js"),
             ["--strict"], 0, "review_required"),
            ("context-provided", config(command="node " + "$" + "{CLAUDE_PLUGIN_ROOT}/x.js"),
             ["--strict", "--plugin-root", consumer], 0, "no_static_differences_found"),
        ]
        for entry_name, entry in (("console", [cli]), ("module", [python, "-m", "hook_doctor"])):
            version = run([*entry, "--version"])
            require(f"{entry_name} version", version.returncode == 0 and version.stdout.strip() == __version__)
            for name, value, extra, expected_exit, expected_status in scenarios:
                source = consumer / f"{entry_name}-{name}.json"
                source.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
                before = source.read_bytes()
                destination = consumer / f"{entry_name}-{name}"
                process = run([*entry, source, "--out", destination, *extra])
                require(f"{entry_name}/{name} exit code", process.returncode == expected_exit)
                require(f"{entry_name}/{name} preserves input", source.read_bytes() == before)
                report_path = destination / "report.json"
                if expected_status is None:
                    require(f"{entry_name}/{name} produces no success report", not report_path.exists())
                else:
                    report = json.loads(report_path.read_text(encoding="utf-8"))
                    require(f"{entry_name}/{name} report",
                            report["summary"]["status"] == expected_status
                            and report["analyzer_version"] == __version__
                            and not report["execution_verified"]
                            and not report["target_runtime_verified"]
                            and (destination / "report.md").is_file())
            collision = consumer / f"{entry_name}-collision"
            collision.mkdir()
            source = collision / "report.json"
            source.write_text(json.dumps(config()), encoding="utf-8")
            before = source.read_bytes()
            process = run([*entry, source, "--out", collision])
            require(f"{entry_name} protects input from report overwrite",
                    process.returncode == 2 and source.read_bytes() == before)
        require("no configured Hook command executed", not (consumer / "hook-executed.txt").exists())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--out", type=Path, default=ROOT / "reports/package-verification.json")
    args = parser.parse_args()
    result = {"passed": False, "version": __version__, "python": platform.python_version(),
              "platform": platform.platform(), "checks": [], "network_used_for_install": False}
    try:
        wheels = list(args.dist.resolve().glob(f"hook_portability_doctor-{__version__}-*.whl"))
        if len(wheels) != 1:
            raise ValueError("Expected exactly one wheel for the current version; run python -m build first.")
        result["wheel"] = wheels[0].name
        result["sha256"] = hashlib.sha256(wheels[0].read_bytes()).hexdigest()
        verify(wheels[0], result)
        result["passed"] = True
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        print(result["error"], file=sys.stderr)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{'PASS' if result['passed'] else 'FAIL'}: {len(result['checks'])} distribution checks")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
