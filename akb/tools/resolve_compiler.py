#!/usr/bin/env python3
"""Resolve the effective project compiler PREFIX from an ApolloCrossDev Makefile.

Recognises the documented shapes only:

- v1.2: PREFIX = $(ACD_ROOT)/Compilers/GCC-6.50-Dev|Stable|Base
  ACD_ROOT resolves when APOLLOCROSSDEV points at the ApolloCrossDev root,
  or when the project sits two levels under that root.
- v1.0: PREFIX = $(PWD)/../../Compilers/GCC-6.50-Dev|Stable|Base
  Effective only when the project sits two levels under the ApolloCrossDev
  root. Setting APOLLOCROSSDEV does not change a v1.0 PREFIX.

Never invents a path from the Dev/Stable/Base label alone. Never treats
m68k-amigaos/ndk-include as a documented NDK. This module does not run make.

Usage:
  python tools/resolve_compiler.py --makefile FILE --project DIR [--acd-root DIR]
  python tools/resolve_compiler.py --text-file FILE --project DIR [--acd-root DIR]
"""
from __future__ import annotations

import argparse
import os
import re
import sys

VARIANTS = ("GCC-6.50-Dev", "GCC-6.50-Stable", "GCC-6.50-Base")
GCC_NAME = "m68k-amigaos-gcc"
GPP_NAME = "m68k-amigaos-g++"
NDK_PATHS = {
    "3.9": ("m68k-amigaos", "ndk39-include"),
    "3.2": ("m68k-amigaos", "ndk32-include", "Include_H"),
}


def _abspath(path):
    return os.path.abspath(os.path.expanduser(path))


def find_acd_root(project, env=None, home=None):
    """Locate ApolloCrossDev the same way find-acd.sh does."""
    env = os.environ if env is None else env
    home = os.path.expanduser("~") if home is None else home
    candidates = []
    ap = env.get("APOLLOCROSSDEV") or ""
    if ap:
        candidates.append(ap)
    candidates.append(os.path.join(project, "..", ".."))
    candidates.append(os.path.join(home, "ApolloCrossDev"))
    for candidate in candidates:
        if not candidate:
            continue
        path = _abspath(candidate)
        if os.path.isdir(os.path.join(path, "Compilers")):
            return path
    return None


def acd_root_resolves(project, acd_root, env=None):
    """True when a v1.2 Makefile may take ACD_ROOT as acd_root."""
    if not acd_root:
        return False
    env = os.environ if env is None else env
    want = _abspath(acd_root)
    ap = env.get("APOLLOCROSSDEV") or ""
    if ap:
        try:
            if _abspath(ap) == want:
                return True
        except OSError:
            pass
    try:
        parent = _abspath(os.path.join(project, "..", ".."))
    except OSError:
        return False
    return parent == want


def project_under_acd(project, acd_root):
    if not acd_root:
        return False
    try:
        return _abspath(os.path.join(project, "..", "..")) == _abspath(acd_root)
    except OSError:
        return False


def last_assignment(text, name):
    """Return the last uncommented NAME= value, or None."""
    pattern = re.compile(rf"^[ \t]*{re.escape(name)}[ \t]*=[ \t]*(.*)$")
    found = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = pattern.match(raw.rstrip("\r\n"))
        if match:
            found = match.group(1).strip()
    return found


def prefix_line(text):
    pattern = re.compile(r"^[ \t]*PREFIX[ \t]*=[ \t]*(.*)$")
    found = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = pattern.match(raw.rstrip("\r\n"))
        if match:
            found = match.group(0).rstrip("\r\n")
    return found


def variant_from_prefix_line(line):
    if not line:
        return None
    for variant in VARIANTS:
        if f"Compilers/{variant}" in line:
            return variant
    return None


def prefix_shape(line):
    if not line:
        return None
    if "$(ACD_ROOT)/Compilers/" in line:
        return "v12_acd_root"
    if "$(PWD)/../../Compilers/" in line:
        return "v10_relative"
    return "unknown"


def required_ndk_version(text):
    """Last uncommented C_INCL_NDK that names a documented fragment, or None."""
    value = last_assignment(text, "C_INCL_NDK")
    if not value:
        return None
    if "ndk39-include" in value:
        return "3.9"
    if "ndk32-include" in value:
        return "3.2"
    return None


def ndk_feeds_flags(text):
    """Documented template wiring: C_INCL_NDK reaches C_FLAGS."""
    active = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        active.append(stripped)
    joined = "\n".join(active)
    if re.search(r"(?m)^C_FLAGS\s*=.*\$\(C_INCL_NDK\)", joined):
        return True
    if not re.search(r"(?m)^C_INCL_ALL\s*=.*\$\(C_INCL_NDK\)", joined):
        return False
    return bool(re.search(r"(?m)^C_FLAGS\s*=.*\$\(C_INCL_ALL\)", joined))


def ndk_directory(prefix, version):
    parts = NDK_PATHS.get(version)
    if not parts or not prefix:
        return None
    return os.path.join(prefix, *parts)


def gcc_path(prefix):
    if not prefix:
        return None
    return os.path.join(prefix, "bin", GCC_NAME)


def gpp_path(prefix):
    if not prefix:
        return None
    return os.path.join(prefix, "bin", GPP_NAME)


def requires_gpp(text):
    """True when the Makefile configures project C++ compilation with g++.

    An active CXX_COMPILER or C_COMPILER that names m68k-amigaos-g++ counts.
    A commented g++ line alone does not: C-only projects keep that comment on
    the stock ApolloCrossDev templates. This checks toolchain presence only;
    it does not verify C++ compilation, linkage, or runtime libraries.
    """
    for name in ("CXX_COMPILER", "C_COMPILER"):
        value = last_assignment(text, name)
        if value and GPP_NAME in value:
            return True
    return False


def resolve_prefix(text, project, acd_root=None, env=None, home=None):
    """Return a dict describing the effective project compiler PREFIX."""
    env = os.environ if env is None else env
    project = _abspath(project)
    if acd_root is None:
        acd_root = find_acd_root(project, env=env, home=home)
    elif acd_root:
        acd_root = _abspath(acd_root)

    line = prefix_line(text)
    shape = prefix_shape(line)
    variant = variant_from_prefix_line(line)
    gpp_needed = requires_gpp(text)
    result = {
        "acd_root": acd_root,
        "prefix_line": line,
        "shape": shape,
        "variant": variant,
        "prefix": None,
        "status": "unresolved",
        "reason": "",
        "supports_apollocrossdev": shape == "v12_acd_root",
        "gcc": None,
        "gcc_present": False,
        "gpp_required": gpp_needed,
        "gpp": None,
        "gpp_present": False,
    }

    if line is None:
        result["status"] = "no_prefix"
        result["reason"] = "the Makefile has no uncommented PREFIX assignment"
        return result

    if shape == "unknown" or variant is None:
        result["reason"] = (
            "PREFIX uses an unrecognised shape. Documented forms are "
            "$(ACD_ROOT)/Compilers/GCC-6.50-Dev|Stable|Base (v1.2) and "
            "$(PWD)/../../Compilers/GCC-6.50-Dev|Stable|Base (v1.0)."
        )
        return result

    if shape == "v12_acd_root":
        if not acd_root:
            result["reason"] = (
                "v1.2 PREFIX=$(ACD_ROOT)/Compilers/... needs ApolloCrossDev, "
                "but no ApolloCrossDev root was found. Set APOLLOCROSSDEV or "
                "place the project under ApolloCrossDev/Projects/."
            )
            return result
        if not acd_root_resolves(project, acd_root, env=env):
            result["reason"] = (
                f"v1.2 PREFIX=$(ACD_ROOT)/Compilers/{variant} needs ACD_ROOT to "
                f"resolve to {acd_root}. Set APOLLOCROSSDEV={acd_root}, or place "
                "the project two levels under that ApolloCrossDev root."
            )
            return result
        result["prefix"] = os.path.join(acd_root, "Compilers", variant)
    elif shape == "v10_relative":
        if not acd_root or not project_under_acd(project, acd_root):
            resolved = _abspath(os.path.join(project, "..", "..", "Compilers", variant))
            result["reason"] = (
                f"v1.0 PREFIX=$(PWD)/../../Compilers/{variant} resolves to "
                f"{resolved} for this project location, which is not the "
                "ApolloCrossDev Compilers tree. Setting APOLLOCROSSDEV does not "
                "fix a v1.0 Makefile. Place the project under "
                "ApolloCrossDev/Projects/<name>, or update ApolloCrossDev for a "
                "v1.2+ template that uses ACD_ROOT."
            )
            return result
        result["prefix"] = os.path.join(acd_root, "Compilers", variant)
    else:
        result["reason"] = "PREFIX shape was not recognised"
        return result

    result["gcc"] = gcc_path(result["prefix"])
    result["gpp"] = gpp_path(result["prefix"]) if gpp_needed else None
    if not os.path.isdir(result["prefix"]):
        result["status"] = "missing"
        result["reason"] = (
            f"project Makefile PREFIX resolves to {result['prefix']}, "
            "but that directory does not exist"
        )
        return result
    if not os.path.exists(result["gcc"]):
        result["status"] = "missing"
        result["reason"] = (
            f"project Makefile PREFIX resolves to {result['prefix']}, "
            f"but {GCC_NAME} is missing at {result['gcc']}"
        )
        return result
    result["gcc_present"] = True
    if gpp_needed:
        if not os.path.exists(result["gpp"]):
            result["status"] = "missing"
            result["reason"] = (
                f"project Makefile configures {GPP_NAME} under "
                f"{result['prefix']}, but {GPP_NAME} is missing at {result['gpp']}. "
                "C++ compilation remains unverified even when the binary is present."
            )
            return result
        result["gpp_present"] = True

    result["status"] = "ready"
    result["reason"] = f"project Makefile PREFIX resolves to {result['prefix']}"
    return result


def resolve_ndk(text, prefix):
    """Return NDK readiness for an active wired C_INCL_NDK requirement."""
    version = required_ndk_version(text)
    info = {
        "required": None,
        "path": None,
        "status": "none",
        "reason": "",
        "wired": False,
    }
    if version is None:
        info["reason"] = "no documented C_INCL_NDK requirement is active"
        return info
    if not ndk_feeds_flags(text):
        info["required"] = version
        info["status"] = "unwired"
        info["reason"] = (
            f"C_INCL_NDK names documented NDK {version}, but it is not shown to "
            "feed compilation flags through C_INCL_ALL and C_FLAGS"
        )
        return info
    info["required"] = version
    info["wired"] = True
    path = ndk_directory(prefix, version)
    info["path"] = path
    if not prefix:
        info["status"] = "unresolved"
        info["reason"] = (
            f"documented NDK {version} is required, but the compiler PREFIX "
            "was not established"
        )
        return info
    if path and os.path.isdir(path):
        info["status"] = "present"
        info["reason"] = f"documented NDK {version} is present at {path}"
        return info
    info["status"] = "absent"
    info["reason"] = (
        f"documented NDK {version} directory is absent at {path}"
    )
    return info


def assess_build_readiness(text, project, acd_root=None, env=None, home=None):
    """Combine PREFIX and NDK readiness. Does not classify upload safety."""
    compiler = resolve_prefix(text, project, acd_root=acd_root, env=env, home=home)
    ndk = resolve_ndk(text, compiler.get("prefix"))
    ready = compiler["status"] == "ready" and ndk["status"] in {"none", "present", "unwired"}
    # unwired C_INCL_NDK is not an established requirement: do not block.
    if ndk["status"] == "absent":
        ready = False
    if compiler["status"] != "ready":
        ready = False
    return {
        "compiler": compiler,
        "ndk": ndk,
        "ready": ready,
    }


def agents_ready_command(verdict_command, assessment):
    """Return the Make command to document, or None when blocked."""
    if verdict_command not in ("make compile", "make cleanbefore build"):
        return None
    if not assessment["ready"]:
        return None
    return verdict_command


def blocked_build_body(verdict, assessment):
    """AGENTS.md Build section when upload-safe but not compiler-ready."""
    command = verdict.command if hasattr(verdict, "command") else verdict
    compiler = assessment["compiler"]
    ndk = assessment["ndk"]
    lines = [
        "# Compilation is blocked until the compiler path and required headers are ready.",
    ]
    if compiler["status"] != "ready":
        lines.append("# " + " ".join(compiler["reason"].replace("<", "").replace(">", "").split()))
        if compiler["shape"] == "v10_relative":
            lines.append(
                "# A v1.0 Makefile does not use APOLLOCROSSDEV; only the relative "
                "$(PWD)/../../Compilers/... path applies."
            )
        elif compiler["shape"] == "v12_acd_root" and compiler["supports_apollocrossdev"]:
            lines.append(
                "# For this v1.2 Makefile, set APOLLOCROSSDEV to the ApolloCrossDev "
                "root, or place the project under ApolloCrossDev/Projects/."
            )
    if ndk["status"] == "absent":
        lines.append("# " + " ".join(ndk["reason"].replace("<", "").replace(">", "").split()))
        lines.append(
            "# Do not substitute m68k-amigaos/ndk-include for the documented NDK path."
        )
    if command in ("make compile", "make cleanbefore build"):
        lines.append(
            f"# A non-uploading Make target was classified ({command}); "
            "that is upload safety only, not build readiness."
        )
    lines.append("# This file names no build command.")
    return "\n".join(lines)


def emit_find_acd(assessment, file_handle=None):
    """Print KEY=value / PROBLEM= lines for find-acd.sh."""
    out = file_handle or sys.stdout
    compiler = assessment["compiler"]

    if compiler["prefix"]:
        out.write(f"PROJECT_PREFIX={compiler['prefix']}\n")
    out.write(f"COMPILER_STATUS={compiler['status']}\n")

    if compiler["status"] == "ready":
        out.write(f"NOTE=project Makefile compiler PREFIX is ready at {compiler['prefix']}\n")
    elif compiler["status"] == "no_prefix":
        out.write(f"NOTE={compiler['reason']}\n")
    else:
        out.write(f"PROBLEM=project Makefile compiler path: {compiler['reason']}\n")
        if compiler["shape"] == "v10_relative":
            out.write(
                "NOTE=setting APOLLOCROSSDEV does not fix a v1.0 "
                "$(PWD)/../../Compilers/... PREFIX\n"
            )
    # NDK absence is reported by find-acd.sh report_ndk when PREFIX resolves.


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--makefile", help="path to a Makefile")
    src.add_argument("--text-file", help="path to Makefile text to assess")
    parser.add_argument("--project", required=True)
    parser.add_argument("--acd-root", default="")
    parser.add_argument(
        "--emit",
        action="store_true",
        help="print find-acd style PROJECT_PREFIX / COMPILER_STATUS / PROBLEM lines",
    )
    args = parser.parse_args(argv)

    path = args.makefile or args.text_file
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    acd = args.acd_root or None
    assessment = assess_build_readiness(text, args.project, acd_root=acd)
    if args.emit:
        emit_find_acd(assessment)
        return 0 if assessment["compiler"]["status"] in {"ready", "no_prefix"} else 1

    compiler = assessment["compiler"]
    print(f"STATUS={compiler['status']}")
    if compiler["prefix"]:
        print(f"PREFIX={compiler['prefix']}")
    if compiler["shape"]:
        print(f"SHAPE={compiler['shape']}")
    if compiler["variant"]:
        print(f"VARIANT={compiler['variant']}")
    print(f"READY={'yes' if assessment['ready'] else 'no'}")
    print(f"REASON={compiler['reason']}")
    if assessment["ndk"]["required"]:
        print(f"NDK={assessment['ndk']['required']}")
        print(f"NDK_STATUS={assessment['ndk']['status']}")
        if assessment["ndk"]["path"]:
            print(f"NDK_PATH={assessment['ndk']['path']}")
    return 0 if assessment["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
