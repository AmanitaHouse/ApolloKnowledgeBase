#!/usr/bin/env python3
"""Classify a non-uploading ApolloCrossDev build command.

This is the only build-command policy used by find-acd.sh and
write_project_files.py. It does not run make, a shell, or a recipe.

A command is returned only when the selected target is one of:

  make
  make compile
  make cleanbefore build

and every recipe that target would run has been recognized as a local
compile, link, echo, or cleanup step. Anything else fails closed.

The recognized makefile shape is the documented ApolloCrossDev template:
assignments, explicit rules, pattern rules, includes, and the functions
$(shell pwd), $(or), $(if), $(wildcard), $(patsubst) and $(notdir).
$(wildcard) is not turned into a directory listing. Object recipes are
taken from pattern rules and from explicit rules whose names fit those
patterns. Unknown constructs are unverified.

Usage:
  python tools/classify_build.py --makefile PATH
"""
import argparse
import os
import re
import sys

STATUS_VERIFIED = "verified-non-uploading"
STATUS_UNVERIFIED = "unverified"
STATUS_UPLOAD = "upload-capable"
STATUS_MISSING = "missing"

COMMAND_MAKE = "make"
COMMAND_COMPILE = "make compile"
COMMAND_CLEANBEFORE = "make cleanbefore build"

# Private-use markers. str.split() treats U+001F as whitespace, so these
# sentinels have to be characters that make and Python both keep intact.
PWD = "\ue000"
WILD = "\ue001"
MAKE = "\ue002"
AUTO = "\ue003"
DOLLAR = "\ue004"
MATCH_MARK = "\ue005"
MATCH_END = "\ue006"
MARKERS = (PWD, WILD, MAKE, AUTO, DOLLAR, MATCH_MARK, MATCH_END)

ALLOWED_FUNCTIONS = {"shell", "or", "if", "wildcard", "patsubst", "notdir"}
CONDITIONALS = {"ifeq", "ifneq", "ifdef", "ifndef", "else", "endif", "define", "endef"}
UPLOAD_BASES = {
    "acp", "acp.exe",
    "scp", "scp.exe",
    "sftp", "sftp.exe",
    "rsync", "rsync.exe",
    "ftp", "ftp.exe",
    "tftp", "tftp.exe",
    "curl", "curl.exe",
    "wget", "wget.exe",
    "ssh", "ssh.exe",
}
COMPILE_BASES = {
    "m68k-amigaos-gcc", "m68k-amigaos-gcc.exe",
    "m68k-amigaos-g++", "m68k-amigaos-g++.exe",
    "vasmm68k_mot", "vasmm68k_mot.exe",
}
LOCAL_COMMANDS = {"echo", "rm", "mkdir", "clear", "true", "cp", "mv"}
AUTOMATIC = {
    "@", "<", "^", "?", "*", "+", "|", "%",
    "@D", "@F", "<D", "<F", "^D", "^F", "?D", "?F",
    "*D", "*F", "+D", "+F", "|D", "|F", "%D", "%F",
}
FUNC_RE = re.compile(r"\$\(([A-Za-z][A-Za-z0-9_.-]*)(?:\s|,)")
ASSIGN_RE = re.compile(
    r"^(?:(?:override|export)\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(\?=|\+=|:=|!=|=)\s*(.*)$"
)
TARGET_VAR_RE = re.compile(
    r"^([^:#=]+):\s*([A-Za-z_][A-Za-z0-9_]*)\s*(:\+?=|\?=|\+=|:=|=)\s*"
)
INCLUDE_RE = re.compile(r"^(-?include|sinclude)\s+(.+)$")
REDIR_OP = re.compile(r"^[0-9]*(?:>>?|<|&>|&>>|<&)$")
REDIR_GLUED = re.compile(r"^[0-9]*>>?\S+$|^[0-9]*<&\S+$|^[0-9]*<>\S+$")


class ExpandError(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status
        self.reason = reason


class Verdict:
    def __init__(self, status, command, reason, built=False):
        self.status = status
        self.command = command
        self.reason = reason
        self.built = built

    def lines(self):
        rows = [f"STATUS={self.status}"]
        if self.command:
            rows.append(f"COMMAND={self.command}")
        rows.append("REASON=" + one_line(self.reason))
        return rows


class Var:
    def __init__(self, flavor, value):
        self.flavor = flavor
        self.value = value


class Rule:
    def __init__(self, raw_targets, raw_prereqs, recipe):
        self.raw_targets = raw_targets
        self.raw_prereqs = raw_prereqs
        self.recipe = recipe


class Makefile:
    def __init__(self):
        self.variables = {}
        self.rules = []
        self.explicit = {}
        self.patterns = []
        self.default_goal = None
        self.problem = None
        self.directory = None


def one_line(text):
    return " ".join((text or "").split())


def classify_makefile(path):
    """Classify the makefile at path. Does not run make."""
    if not os.path.isfile(path):
        return Verdict(STATUS_UNVERIFIED, None, f"makefile cannot be read: {path}")
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    return classify_text(text, path)


def classify_text(text, path=None):
    """Classify makefile text. path is the directory base for includes."""
    if any(marker in text for marker in MARKERS):
        return refuse("the makefile contains a marker this classifier reserves")
    try:
        mf = Makefile()
        if path:
            mf.directory = os.path.dirname(os.path.abspath(path))
        parse_text(text, mf, [])
        if mf.problem:
            return refuse(mf.problem[1], mf.problem[0])
        index_rules(mf)
        if mf.problem:
            return refuse(mf.problem[1], mf.problem[0])
    except ExpandError as exc:
        return refuse(exc.reason, exc.status)
    compile_verdict = inspect_named(mf, ["compile"])
    if compile_verdict.status == STATUS_VERIFIED:
        return Verdict(
            STATUS_VERIFIED,
            COMMAND_COMPILE,
            "compile and every target it builds were inspected; "
            "their recipes are local compile, link, echo, or cleanup steps",
        )
    if mf.default_goal == "all":
        all_verdict = inspect_named(mf, ["all"])
    else:
        all_verdict = Verdict(STATUS_MISSING, None, "all is not the default goal")
    if all_verdict.status == STATUS_VERIFIED and all_verdict.built:
        return Verdict(
            STATUS_VERIFIED,
            COMMAND_MAKE,
            "default target all and every target it builds were inspected; "
            "their recipes are local compile, link, echo, or cleanup steps",
        )
    fallback = inspect_named(mf, ["cleanbefore", "build"])
    if fallback.status == STATUS_VERIFIED:
        detail = (
            "cleanbefore and build, including the targets they build, were inspected; "
            "their recipes are local compile, link, echo, or cleanup steps"
        )
        if compile_verdict.status == STATUS_UPLOAD:
            detail += "; compile was not selected because it can upload"
        elif compile_verdict.status == STATUS_UNVERIFIED:
            detail += "; compile was not selected because it could not be verified"
        elif all_verdict.status == STATUS_UPLOAD:
            detail += "; default target all was not selected because it can upload"
        elif all_verdict.status == STATUS_UNVERIFIED:
            detail += "; default target all was not selected because it could not be verified"
        return Verdict(STATUS_VERIFIED, COMMAND_CLEANBEFORE, detail)
    return combine(compile_verdict, all_verdict, fallback)


def refuse(reason, status=STATUS_UNVERIFIED):
    return Verdict(
        status,
        None,
        "no Make command can be recommended automatically: " + one_line(reason),
    )


def combine(compile_verdict, all_verdict, fallback):
    parts = []
    statuses = []
    for label, verdict in (
        ("compile", compile_verdict),
        ("all", all_verdict),
        ("cleanbefore build", fallback),
    ):
        if verdict.status == STATUS_MISSING:
            parts.append(f"{label} is not present")
        elif label == "all" and verdict.status == STATUS_VERIFIED and not verdict.built:
            parts.append("all does not invoke a build target or compiler")
            statuses.append(STATUS_UNVERIFIED)
        else:
            parts.append(f"{label} is {verdict.status}: {verdict.reason}")
            statuses.append(verdict.status)
    status = STATUS_UPLOAD if STATUS_UPLOAD in statuses else STATUS_UNVERIFIED
    return refuse("; ".join(parts), status)


def inspect_named(mf, goals):
    """Inspect goals that exist. A partial pair is not a verified command."""
    existing = [goal for goal in goals if goal_exists(mf, goal)]
    missing = [goal for goal in goals if goal not in existing]
    if not existing:
        return Verdict(STATUS_MISSING, None, ", ".join(goals) + " is not present")
    verdict = inspect(mf, existing)
    if not missing:
        return verdict
    if verdict.status in {STATUS_UPLOAD, STATUS_UNVERIFIED}:
        return verdict
    return Verdict(STATUS_MISSING, None, ", ".join(missing) + " is not present")


def inspect(mf, goals, visiting=None):
    visiting = set() if visiting is None else set(visiting)
    missing = [goal for goal in goals if goal not in visiting and not goal_exists(mf, goal)]
    if missing:
        listed = ", ".join(missing)
        return Verdict(STATUS_MISSING, None, f"{listed} is not present")
    state = {"status": STATUS_VERIFIED, "reason": "inspected", "built": False}
    seen = set()
    pending = [goal for goal in goals if goal not in visiting]
    while pending:
        item = pending.pop()
        key = ("match", item) if item.startswith(MATCH_MARK) else ("goal", item)
        if key in seen:
            continue
        seen.add(key)
        if not item.startswith(MATCH_MARK):
            if item in visiting:
                continue
            visiting.add(item)
        if item.startswith(MATCH_MARK):
            pattern = item[len(MATCH_MARK):-len(MATCH_END)]
            consider_pattern(mf, pattern, pending, state, visiting)
            if state["status"] == STATUS_UPLOAD:
                break
            continue
        rule = mf.explicit.get(item, False)
        if rule is False:
            continue
        if rule is None:
            return Verdict(STATUS_UNVERIFIED, None, f"duplicate rule for {item}")
        if item == "build":
            state["built"] = True
        note = classify_recipe(mf, rule, pending, visiting, state)
        merge(state, note)
        if state["status"] == STATUS_UPLOAD:
            break
        queue_prereqs(mf, rule, pending, state)
        if state["status"] == STATUS_UPLOAD:
            break
    return Verdict(state["status"], None, state["reason"], built=state["built"])


def goal_exists(mf, goal):
    if goal in mf.explicit:
        return True
    return any(pattern_matches(pattern, goal) for pattern, _rule in mf.patterns)


def consider_pattern(mf, pattern, pending, state, visiting):
    if not pattern or "%" not in pattern:
        return
    for rule_pattern, rule in mf.patterns:
        if could_supply(rule_pattern, pattern):
            note = classify_recipe(mf, rule, pending, visiting, state)
            merge(state, note)
            queue_prereqs(mf, rule, pending, state)
    for target, rule in mf.explicit.items():
        if rule is None:
            merge(state, (STATUS_UNVERIFIED, f"duplicate rule for {target}"))
            continue
        if pattern_matches(pattern, target):
            pending.append(target)


def could_supply(rule_pattern, needed_pattern):
    if "%" not in rule_pattern or "%" not in needed_pattern:
        return False
    rule_prefix, rule_suffix = rule_pattern.split("%", 1)
    need_prefix, need_suffix = needed_pattern.split("%", 1)
    if need_prefix.startswith(rule_prefix) and need_suffix.endswith(rule_suffix):
        return True
    if rule_prefix.startswith(need_prefix) and rule_suffix.endswith(need_suffix):
        return True
    return False


def pattern_matches(pattern, name):
    if "%" not in pattern:
        return False
    prefix, suffix = pattern.split("%", 1)
    if not (name.startswith(prefix) and name.endswith(suffix)):
        return False
    return len(name) >= len(prefix) + len(suffix)


def queue_prereqs(mf, rule, pending, state):
    try:
        text = expand(rule.raw_prereqs, mf, [])
    except ExpandError as exc:
        merge(state, (exc.status, exc.reason))
        return
    if "$" in text:
        merge(state, (STATUS_UNVERIFIED, "a prerequisite did not finish expanding"))
        return
    for token in text.split():
        if token == "|":
            continue
        if token == WILD:
            merge(state, (STATUS_UNVERIFIED, "a wildcard prerequisite has no known rule"))
            continue
        if token.startswith(MATCH_MARK):
            pending.append(token)
            continue
        if "%" in token:
            if any(could_supply(pattern, token) for pattern, _rule in mf.patterns):
                pending.append(MATCH_MARK + token + MATCH_END)
            continue
        if goal_exists(mf, token) or token in mf.explicit:
            pending.append(token)


def classify_recipe(mf, rule, pending, visiting, state=None):
    worst = STATUS_VERIFIED
    reason = "inspected"
    for raw in rule.recipe:
        stripped = strip_prefixes(raw)
        if not stripped.strip():
            continue
        try:
            expanded = expand(stripped, mf, [])
        except ExpandError as exc:
            return exc.status, exc.reason
        if "$" in expanded or "`" in expanded:
            return STATUS_UNVERIFIED, "a recipe still contains an unexpanded command"
        if stripped_has_unset_command(stripped, expanded, mf):
            return STATUS_UNVERIFIED, "a recipe command comes from an unset variable"
        for segment in split_shell(expanded):
            tokens = without_redirections(tokenize(segment))
            if not tokens:
                if "$(" in raw or "${" in raw:
                    return STATUS_UNVERIFIED, "a recipe command comes from an unset variable"
                continue
            status, detail, built_here = classify_command(tokens, mf, visiting)
            if state is not None and built_here:
                state["built"] = True
            if rank(status) > rank(worst):
                worst = status
                reason = detail
            if worst == STATUS_UPLOAD:
                return worst, reason
    return worst, reason


def stripped_has_unset_command(raw, expanded, mf):
    """An unset variable may be supplied by the environment."""
    if expanded.strip():
        return False
    return "$(" in raw or "${" in raw or re.search(r"\$[A-Za-z@%<?^*+|]", raw) is not None


def classify_command(tokens, mf, visiting):
    command = tokens[0]
    if command == MAKE:
        return classify_recursive(tokens[1:], mf, visiting)
    base = basename(command)
    if base in UPLOAD_BASES or command.rstrip("/").endswith("/acp"):
        return STATUS_UPLOAD, f"a recipe runs the upload command {base or 'acp'}", False
    if any(marker in command for marker in (WILD, MATCH_MARK, AUTO)):
        return STATUS_UNVERIFIED, "a recipe command is not a fixed local program", False
    if base in COMPILE_BASES:
        return STATUS_VERIFIED, "compiler", True
    if base in LOCAL_COMMANDS:
        status, detail = classify_local(base, tokens[1:])
        return status, detail, False
    return STATUS_UNVERIFIED, f"a recipe command cannot be classified: {base or command}", False


def classify_local(base, args):
    if base in {"cp", "mv"}:
        for arg in args:
            if "AMIGAHOST" in arg or _remote_destination(arg):
                return STATUS_UPLOAD, f"a recipe copies a file to a remote destination with {base}"
            if basename(arg) in UPLOAD_BASES:
                return STATUS_UNVERIFIED, f"a {base} argument names an upload command"
    if base == "rm":
        for arg in args:
            if arg.startswith("-") and arg not in {"-f", "-r", "-R", "-rf", "-fr", "-Rf", "-fR"}:
                return STATUS_UNVERIFIED, "rm uses a flag this classifier does not recognize"
    if base == "mkdir" and any(arg.startswith("-") and arg != "-p" for arg in args):
        return STATUS_UNVERIFIED, "mkdir uses a flag this classifier does not recognize"
    if base == "clear" and args:
        return STATUS_UNVERIFIED, "clear has arguments"
    if base == "true" and args:
        return STATUS_UNVERIFIED, "true has arguments"
    return STATUS_VERIFIED, base


def _remote_destination(arg):
    if ":" not in arg:
        return False
    head = arg.split(":", 1)[0]
    return bool(head) and "/" not in head and "\\" not in head


def classify_recursive(args, mf, visiting):
    targets = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"-C", "--directory", "-f", "--file", "--makefile", "-I", "--include-dir"}:
            return STATUS_UNVERIFIED, "recursive make changes directory, makefile, or include path", False
        if arg.startswith(("-C", "--directory=", "-f", "--file=", "--makefile=", "-I", "--include-dir=")):
            return STATUS_UNVERIFIED, "recursive make changes directory, makefile, or include path", False
        if arg.startswith("-"):
            return STATUS_UNVERIFIED, "recursive make uses a flag this classifier does not inspect", False
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", arg):
            return STATUS_UNVERIFIED, "recursive make overrides a variable", False
        targets.append(arg)
        index += 1
    if not targets:
        if not mf.default_goal:
            return STATUS_UNVERIFIED, "recursive make names no target", False
        targets = [mf.default_goal]
    verdict = inspect(mf, targets, visiting)
    if verdict.status == STATUS_VERIFIED:
        return STATUS_VERIFIED, "recursive make stays on inspected targets", verdict.built
    if verdict.status == STATUS_MISSING:
        return STATUS_UNVERIFIED, "recursive make names a target that is not present", False
    if verdict.status == STATUS_UPLOAD:
        return STATUS_UPLOAD, "recursive make builds a target that uploads", False
    return STATUS_UNVERIFIED, "recursive make cannot be inspected: " + verdict.reason, False


def merge(state, note):
    status, reason = note
    if rank(status) > rank(state["status"]):
        state["status"] = status
        state["reason"] = reason


def rank(status):
    return {
        STATUS_VERIFIED: 0,
        STATUS_MISSING: 1,
        STATUS_UNVERIFIED: 2,
        STATUS_UPLOAD: 3,
    }[status]


def basename(token):
    token = token.strip("\"'")
    token = token.replace("\\", "/")
    if "/" in token:
        token = token.rsplit("/", 1)[-1]
    return token


def strip_prefixes(line):
    index = 0
    while index < len(line) and line[index] in "@+-":
        index += 1
    return line[index:]


def tokenize(text):
    tokens = []
    index = 0
    length = len(text)
    while index < length:
        while index < length and text[index] in " \t":
            index += 1
        if index >= length:
            break
        if text[index] in "\"'":
            quote = text[index]
            index += 1
            start = index
            while index < length and text[index] != quote:
                index += 1
            tokens.append(text[start:index])
            if index < length:
                index += 1
            continue
        start = index
        while index < length and text[index] not in " \t":
            index += 1
        tokens.append(text[start:index])
    return tokens


def split_shell(text):
    parts = []
    buf = []
    index = 0
    quote = None
    while index < len(text):
        ch = text[index]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            index += 1
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
            index += 1
            continue
        if text.startswith("&&", index) or text.startswith("||", index):
            parts.append("".join(buf))
            buf = []
            index += 2
            continue
        if ch == ";":
            parts.append("".join(buf))
            buf = []
            index += 1
            continue
        buf.append(ch)
        index += 1
    parts.append("".join(buf))
    return [part.strip() for part in parts if part.strip()]


def without_redirections(tokens):
    kept = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if REDIR_GLUED.match(token) and not token.startswith("-"):
            index += 1
            continue
        if REDIR_OP.match(token):
            index += 2 if index + 1 < len(tokens) else 1
            continue
        kept.append(token)
        index += 1
    return kept


def index_rules(mf):
    explicit = {}
    patterns = []
    default = None
    for rule in mf.rules:
        expanded = expand(rule.raw_targets, mf, [])
        if "$" in expanded:
            raise ExpandError(STATUS_UNVERIFIED, "a target did not finish expanding")
        targets = expanded.split()
        if not targets:
            continue
        if any("%" in target for target in targets):
            if len(targets) != 1 or targets[0].count("%") != 1:
                raise ExpandError(STATUS_UNVERIFIED, "a pattern rule is ambiguous")
            patterns.append((targets[0], rule))
            continue
        for target in targets:
            if target.startswith("."):
                continue
            if target in explicit:
                explicit[target] = None
            else:
                explicit[target] = rule
            if default is None:
                default = target
    mf.explicit = explicit
    mf.patterns = patterns
    mf.default_goal = default


def parse_text(text, mf, stack):
    problem = prescan(text)
    if problem:
        mf.problem = problem
        return
    lines = logical_lines(text)
    rule = None
    for line in lines:
        if not line.strip():
            continue
        if line.startswith("\t"):
            if rule is None:
                mf.problem = (STATUS_UNVERIFIED, "a recipe line has no target")
                return
            rule.recipe.append(line[1:])
            continue
        rule = None
        stripped = line.strip()
        include = INCLUDE_RE.match(stripped)
        if include:
            if not parse_include(include.group(1), include.group(2), mf, stack):
                return
            continue
        if TARGET_VAR_RE.match(stripped):
            mf.problem = (STATUS_UNVERIFIED, "a target-specific variable is not classified")
            return
        assignment = ASSIGN_RE.match(stripped)
        if assignment:
            if not store_assignment(mf, assignment.group(1), assignment.group(2), assignment.group(3)):
                return
            continue
        if "::" in stripped.split(";")[0]:
            mf.problem = (STATUS_UNVERIFIED, "a double-colon rule is not classified")
            return
        head, inline = split_inline_recipe(stripped)
        if head.count(":") != 1:
            mf.problem = (STATUS_UNVERIFIED, "a rule is not an explicit or single pattern rule")
            return
        targets, prereqs = head.split(":", 1)
        rule = Rule(targets.strip(), prereqs.strip(), [])
        if inline:
            rule.recipe.append(inline)
        mf.rules.append(rule)


def split_inline_recipe(line):
    quote = None
    for index, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            continue
        if ch == ";":
            return line[:index], line[index + 1:]
    return line, None


def store_assignment(mf, name, op, value):
    if op == "!=":
        status = shell_body_status(value) or (
            STATUS_UNVERIFIED,
            "a shell assignment was not executed",
        )
        mf.problem = status
        return False
    if op == "?=" and name in mf.variables:
        return True
    if op == "+=":
        current = mf.variables.get(name)
        value = (current.value + " " + value) if current else value
        op = "=" if current is None or current.flavor == "recursive" else ":="
    if op == ":=":
        try:
            value = expand(value, mf, [])
        except ExpandError as exc:
            mf.problem = (exc.status, exc.reason)
            return False
        mf.variables[name] = Var("immediate", value)
    else:
        mf.variables[name] = Var("recursive", value)
    return True


def parse_include(kind, names, mf, stack):
    optional = kind in {"-include", "sinclude"}
    for name in expand(names, mf, []).split():
        path = resolve_include(mf, name)
        if path is None:
            if optional:
                continue
            mf.problem = (STATUS_UNVERIFIED, f"an included makefile cannot be read: {name}")
            return False
        real = os.path.realpath(path)
        if real in stack:
            mf.problem = (STATUS_UNVERIFIED, "included makefiles form a cycle")
            return False
        with open(path, encoding="utf-8", errors="replace") as fh:
            included = fh.read()
        if any(marker in included for marker in MARKERS):
            mf.problem = (STATUS_UNVERIFIED, "an included makefile contains a reserved marker")
            return False
        previous = mf.directory
        mf.directory = os.path.dirname(real)
        parse_text(included, mf, stack + [real])
        mf.directory = previous
        if mf.problem:
            return False
    return True


def resolve_include(mf, name):
    if os.path.isabs(name) and os.path.isfile(name):
        return name
    candidates = []
    if mf.directory:
        candidates.append(os.path.join(mf.directory, name))
    candidates.append(os.path.join(os.getcwd(), name))
    found = []
    for candidate in candidates:
        if os.path.isfile(candidate):
            real = os.path.realpath(candidate)
            if real not in found:
                found.append(real)
    if len(found) == 1:
        return found[0]
    if len(found) > 1:
        return None
    return None


def prescan(text):
    cleaned = "\n".join(strip_comment(line) for line in text.splitlines())
    for match in FUNC_RE.finditer(cleaned):
        name = match.group(1)
        if name == "shell":
            body = call_body(cleaned, match.start())
            if body is None:
                return STATUS_UNVERIFIED, "a shell function could not be read"
            return_status = shell_body_status(body)
            if return_status:
                return return_status
            continue
        if name not in ALLOWED_FUNCTIONS:
            return STATUS_UNVERIFIED, f"an unsupported function was not classified: {name}"
    for line in cleaned.splitlines():
        word = line.strip().split(" ", 1)[0] if line.strip() else ""
        if word in CONDITIONALS:
            return STATUS_UNVERIFIED, f"an unsupported conditional was not classified: {word}"
        if word in {"undefine", "vpath", "unexport"}:
            return STATUS_UNVERIFIED, f"an unsupported directive was not classified: {word}"
    return None


def shell_body_status(body):
    if body.strip() == "pwd":
        return None
    words = body.strip().split()
    if words and basename(words[0]) in UPLOAD_BASES:
        return STATUS_UPLOAD, f"a shell function runs the upload command {basename(words[0])}"
    return STATUS_UNVERIFIED, "a shell function other than pwd was not executed"


def call_body(text, start):
    """Return the raw argument text of the $(...) call at start."""
    open_at = text.find("(", start)
    if open_at < 0:
        return None
    depth = 0
    for index in range(open_at, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                inner = text[open_at + 1:index]
                parts = inner.split(None, 1)
                return parts[1] if len(parts) == 2 else ""
    return None


def logical_lines(text):
    lines = []
    buf = None
    for raw in text.splitlines():
        line = strip_comment(raw)
        if buf is None:
            buf = line
        else:
            buf += " " + line.lstrip()
        if buf.endswith("\\") and not buf.endswith("\\\\"):
            buf = buf[:-1]
            continue
        lines.append(buf)
        buf = None
    if buf is not None:
        lines.append(buf)
    return lines


def strip_comment(line):
    out = []
    index = 0
    while index < len(line):
        if line[index] == "\\" and index + 1 < len(line):
            out.append(line[index:index + 2])
            index += 2
            continue
        if line[index] == "#":
            break
        out.append(line[index])
        index += 1
    return "".join(out).rstrip()


def expand(text, mf, stack):
    out = []
    index = 0
    while index < len(text):
        if text.startswith("$$", index):
            out.append(DOLLAR)
            index += 2
            continue
        if text[index] != "$":
            out.append(text[index])
            index += 1
            continue
        if index + 1 >= len(text):
            raise ExpandError(STATUS_UNVERIFIED, "a lone dollar sign was not classified")
        nxt = text[index + 1]
        if nxt in "({":
            close = ")" if nxt == "(" else "}"
            body, end = balanced(text, index + 2, close)
            if body is None:
                raise ExpandError(STATUS_UNVERIFIED, "an unclosed variable reference was not classified")
            out.append(expand_reference(body, mf, stack))
            index = end + 1
            continue
        out.append(expand_reference(nxt, mf, stack))
        index += 2
    return "".join(out)


def balanced(text, start, close):
    depth = 1
    index = start
    open_ch = "(" if close == ")" else "{"
    while index < len(text):
        if text[index] == open_ch:
            depth += 1
        elif text[index] == close:
            depth -= 1
            if depth == 0:
                return text[start:index], index
        index += 1
    return None, None


def expand_reference(body, mf, stack):
    body_stripped = body.strip()
    if body_stripped in AUTOMATIC:
        return AUTO
    name, args = split_function(body)
    if name is not None:
        return expand_function(name, args, mf, stack)
    if body_stripped == "MAKE" and "MAKE" not in mf.variables:
        return MAKE
    if body_stripped in AUTOMATIC:
        return AUTO
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", body_stripped):
        raise ExpandError(STATUS_UNVERIFIED, "a variable reference was not classified")
    if body_stripped in stack:
        raise ExpandError(STATUS_UNVERIFIED, f"variable {body_stripped} refers to itself")
    var = mf.variables.get(body_stripped)
    if var is None:
        return ""
    if var.flavor == "immediate":
        return var.value
    return expand(var.value, mf, stack + [body_stripped])


def split_function(body):
    match = re.match(r"^([A-Za-z][A-Za-z0-9_.-]*)(?:\s+(.*))?$", body, re.S)
    if not match:
        return None, None
    name = match.group(1)
    if name not in ALLOWED_FUNCTIONS and name != "shell":
        return None, None
    if match.group(2) is None and name not in ALLOWED_FUNCTIONS:
        return None, None
    # $(NAME) with no argument is a variable, except calls that use a space.
    if match.group(2) is None:
        return None, None
    return name, match.group(2)


def expand_function(name, args, mf, stack):
    if name not in ALLOWED_FUNCTIONS:
        raise ExpandError(STATUS_UNVERIFIED, f"an unsupported function was not classified: {name}")
    parts = split_args(args)
    if name == "shell":
        if args.strip() != "pwd":
            status = shell_body_status(args)
            raise ExpandError(status[0], status[1])
        return PWD
    if name == "notdir":
        value = expand(args, mf, stack)
        value = value.rstrip("/")
        if "/" in value:
            return value.rsplit("/", 1)[-1]
        return value
    if name == "or":
        for part in parts:
            value = expand(part.strip(), mf, stack)
            if value.strip():
                return value.strip()
        return ""
    if name == "if":
        if len(parts) not in {2, 3}:
            raise ExpandError(STATUS_UNVERIFIED, "an if function is ambiguous")
        condition = expand(parts[0], mf, stack)
        chosen = parts[1] if condition.strip() else (parts[2] if len(parts) == 3 else "")
        return expand(chosen, mf, stack)
    if name == "wildcard":
        value = expand(args, mf, stack).strip()
        if " " in value or "?" in value or "[" in value or value.count("*") != 1:
            raise ExpandError(STATUS_UNVERIFIED, "a wildcard is ambiguous")
        pattern = value.replace("*", "%", 1)
        if MATCH_MARK in pattern or MATCH_END in pattern:
            raise ExpandError(STATUS_UNVERIFIED, "a wildcard is ambiguous")
        return MATCH_MARK + pattern + MATCH_END
    if name == "patsubst":
        if len(parts) != 3:
            raise ExpandError(STATUS_UNVERIFIED, "patsubst does not have three arguments")
        pattern = expand(parts[0], mf, stack)
        replacement = expand(parts[1], mf, stack)
        text = expand(parts[2], mf, stack)
        return apply_patsubst(pattern, replacement, text)
    raise ExpandError(STATUS_UNVERIFIED, f"an unsupported function was not classified: {name}")


def split_args(body):
    args = []
    depth = 0
    start = 0
    for index, ch in enumerate(body):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            args.append(body[start:index])
            start = index + 1
    args.append(body[start:])
    return args


def apply_patsubst(pattern, replacement, text):
    words = []
    for word in text.split():
        if word.startswith(MATCH_MARK) and word.endswith(MATCH_END):
            inner = word[len(MATCH_MARK):-len(MATCH_END)]
            if inner != pattern or replacement.count("%") != 1 or " " in replacement:
                raise ExpandError(STATUS_UNVERIFIED, "patsubst does not match a wildcard")
            if MATCH_MARK in replacement or MATCH_END in replacement:
                raise ExpandError(STATUS_UNVERIFIED, "patsubst does not match a wildcard")
            words.append(MATCH_MARK + replacement + MATCH_END)
            continue
        if "%" not in pattern:
            words.append(word.replace(pattern, replacement) if pattern else word)
            continue
        prefix, suffix = pattern.split("%", 1)
        if word.startswith(prefix) and word.endswith(suffix) and len(word) >= len(prefix) + len(suffix):
            stem = word[len(prefix):len(word) - len(suffix) if suffix else len(word)]
            words.append(replacement.replace("%", stem, 1))
        else:
            words.append(word)
    return " ".join(words)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--makefile", required=True)
    args = parser.parse_args(argv)
    if not os.path.isfile(args.makefile):
        print(f"STATUS={STATUS_UNVERIFIED}")
        print("REASON=no Make command can be recommended automatically: the makefile cannot be read")
        return 1
    verdict = classify_makefile(args.makefile)
    for line in verdict.lines():
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
