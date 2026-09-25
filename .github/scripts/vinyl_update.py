"""Bump the default Vinyl Cache version to the latest upstream release.

Usage: vinyl_update.py {patch,minor}

``patch`` looks for a newer release in the current X.Y line, ``minor`` for
a release in a newer X.Y line. If one exists, the working tree is updated
(download URL, package version, changelog) and ``version``, ``branch`` and
``title`` are written to ``$GITHUB_OUTPUT``, plus the PR body to
``pr-body.md``. If none exists, nothing is changed or written.
"""

from pathlib import Path

import json
import os
import re
import sys
import urllib.request

RELEASES_API = "https://api.github.com/repos/varnish/varnish/releases?per_page=100"
RELEASE_PAGE = "https://github.com/varnish/varnish/releases/tag/varnish-{0}"
TAG_RE = re.compile(r"^varnish-(\d+)\.(\d+)\.(\d+)$")
URL_PATH = "varnish-{0}/varnish-{0}.tar.gz"

ROOT = Path(__file__).resolve().parents[2]
RECIPE = ROOT / "src/plone/recipe/vinylcache/recipe.py"
DOCTEST = ROOT / "src/plone/recipe/vinylcache/tests/recipe.rst"
BUILDOUT = ROOT / "buildout.cfg"
PYPROJECT = ROOT / "pyproject.toml"
CHANGES = ROOT / "CHANGES.rst"


def parse(version):
    return tuple(int(part) for part in version.split("."))


def fmt(version):
    return ".".join(str(part) for part in version)


def current_version():
    match = re.search(
        r"varnish-(\d+\.\d+\.\d+)/varnish-\1\.tar\.gz", RECIPE.read_text()
    )
    if not match:
        sys.exit(f"Cannot find DOWNLOAD_URL version in {RECIPE}")
    return parse(match.group(1))


def upstream_versions():
    request = urllib.request.Request(RELEASES_API)
    request.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        releases = json.load(response)
    versions = []
    for release in releases:
        match = TAG_RE.match(release["tag_name"])
        if release["draft"] or release["prerelease"] or not match:
            continue
        tarball = f"{release['tag_name']}.tar.gz"
        # Only releases that publish the source tarball the recipe downloads.
        if any(asset["name"] == tarball for asset in release["assets"]):
            versions.append(tuple(int(part) for part in match.groups()))
    return versions


def pick_target(kind, current, versions):
    if kind == "patch":
        candidates = [v for v in versions if v[:2] == current[:2] and v > current]
    else:
        candidates = [v for v in versions if v[:2] > current[:2]]
    return max(candidates, default=None)


def replace(path, old, new):
    text = path.read_text()
    if old not in text:
        sys.exit(f"{old!r} not found in {path}")
    path.write_text(text.replace(old, new))


def update_changelog(new):
    text = CHANGES.read_text()
    match = re.search(r"^\S+ \(unreleased\)\n-+\n\n", text, re.M)
    if not match:
        sys.exit(f"Cannot find the unreleased section in {CHANGES}")
    header = f"{new}.0 (unreleased)"
    entry = (
        f"- Update the default download URL to Vinyl Cache {new}\n"
        f"  (`release notes <{RELEASE_PAGE.format(new)}>`_).\n"
        "  [github-actions]\n\n"
    )
    rest = text[match.end() :]
    if rest.startswith("- Nothing changed yet.\n"):
        rest = rest[len("- Nothing changed yet.\n") :].lstrip("\n")
        entry += "\n"
    CHANGES.write_text(
        text[: match.start()] + f"{header}\n{'-' * len(header)}\n\n" + entry + rest
    )


def apply(kind, current, target):
    old, new = fmt(current), fmt(target)
    replace(RECIPE, URL_PATH.format(old), URL_PATH.format(new))
    replace(BUILDOUT, URL_PATH.format(old), URL_PATH.format(new))
    text = PYPROJECT.read_text()
    text = re.sub(
        r'^version = ".*"$', f'version = "{new}.0.dev0"', text, count=1, flags=re.M
    )
    text = text.replace(f"currently {old}.", f"currently {new}.")
    PYPROJECT.write_text(text)
    update_changelog(new)
    if kind == "minor":
        old_line, new_line = fmt(current[:2]), fmt(target[:2])
        replace(
            DOCTEST,
            f"'varnishd (varnish-{old_line}.",
            f"'varnishd (varnish-{new_line}.",
        )


def pr_body(kind, current, target):
    old, new = fmt(current), fmt(target)
    body = [
        f"Vinyl Cache [{new}]({RELEASE_PAGE.format(new)}) is available "
        f"(current default: {old}).",
        "",
        "This PR updates:",
        "",
        "- `DOWNLOAD_URL` in `recipe.py` and the sample URL in `buildout.cfg`",
        f"- the package version to `{new}.0.dev0` (positions 1-3 track the Vinyl Cache release)",
        "- `CHANGES.rst`",
    ]
    if kind == "minor":
        old_line, new_line = fmt(current[:2]), fmt(target[:2])
        body[-1:-1] = [f"- the `varnishd -V` doctest check to `{new_line}.x`"]
        body += [
            "",
            f"**New release line ({old_line}.x → {new_line}.x): this PR is a draft "
            "and needs manual work before merging.**",
            "",
            f"- [ ] Read the upstream changes between {old} and {new} "
            "(VCL syntax, `varnishd` options, renamed binaries or tarball)",
            f"- [ ] Update the `{old_line}.x` mentions in `README.rst`, "
            "`recipe.py` comments and the doctests",
            "- [ ] Check that `VMODS_DOWNLOAD_URL` (varnish-modules) supports the new line",
            "- [ ] Rewrite the changelog entry to describe the change in support",
        ]
    body += ["", "Opened automatically by the `vinyl-update` workflow."]
    return "\n".join(body) + "\n"


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("patch", "minor"):
        sys.exit(__doc__)
    kind = sys.argv[1]
    current = current_version()
    target = pick_target(kind, current, upstream_versions())
    if target is None:
        print(f"No {kind} update for Vinyl Cache {fmt(current)}.")
        return
    new = fmt(target)
    print(f"Vinyl Cache {fmt(current)} -> {new} ({kind}).")
    apply(kind, current, target)
    (ROOT / "pr-body.md").write_text(pr_body(kind, current, target))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a") as fh:
            fh.write(f"version={new}\n")
            fh.write(f"branch=vinyl-update/{kind}-{new}\n")
            fh.write(f"title=Update Vinyl Cache to {new}\n")


if __name__ == "__main__":
    main()
