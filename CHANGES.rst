Changelog
=========

9.0.3.0 (2026-09-25)
--------------------

- Moved the package source to a ``src`` layout and migrated packaging
  metadata from ``setup.py`` to ``pyproject.toml`` (``setup.py`` now only
  carries the legacy ``namespace_packages``/``packages``/``package_dir``
  arguments that PEP 621's ``[project]`` table cannot express). Dropped
  Python 3.9 support, added 3.12 and 3.13.
  [mamico]

- BUGFIX: ``plone.recipe.vinylcache:build``'s ``url`` (and
  ``vmods_url``) option now falls back to the built-in default download
  URL when set to an *empty* string, not just when entirely absent. An
  inherited/extended ``buildout.cfg`` declaring ``url =`` with no value
  as a placeholder for a downstream override previously made
  ``setdefault()`` a no-op (the key already existed), which
  ``zc.recipe.cmmi`` then handed to ``zc.buildout.download.Download()``
  as if it were a local path, failing with ``FileNotFoundError: [Errno
  2] No such file or directory: ''`` instead of using the default.
  [mamico]

- BUGFIX: the new default ``name`` (``${buildout:directory}/var/<part
  name>``, see above) broke ``varnishd`` startup and even ``varnishd -C``
  syntax checks with "Error: Cannot create working directory ...: No
  such file or directory": ``varnishd`` only creates the leaf directory
  of its ``-n`` working directory, not missing parents (e.g. ``var/``
  itself). ``plone.recipe.vinylcache:script`` now creates that directory
  (and any missing parents) itself during install. Caught by actually
  running the compiled binary against the generated script in CI/locally,
  not just by inspecting the VCL. [mamico]

- New features, beyond parity with ``plone.recipe.varnish``:

  - ``vcl_hash`` default now includes ``req.http.host`` (falling back to
    ``server.ip``), matching Varnish's own built-in default. The previous
    default hashed on ``req.url`` alone, which can cross-contaminate the
    cache between two different vhosts/backends serving overlapping URL
    paths on the same Vinyl Cache instance.
  - ``PATCH`` added to the method whitelist in ``vcl_recv`` (alongside
    ``PUT``/``POST``/``DELETE``), for REST APIs (e.g. ``plone.restapi``).
  - WebSocket upgrade requests (``Upgrade: websocket``) are now piped
    straight through in ``vcl_recv`` instead of falling into normal
    GET/HEAD caching logic.
  - ``Accept-Encoding`` is normalized in ``vcl_recv`` (to ``gzip`` or
    unset) to avoid fragmenting the cache per client-specific
    ``Accept-Encoding`` strings.
  - Large files (by extension) are now streamed (``beresp.do_stream``)
    instead of piped in ``vcl_backend_response`` -- streaming keeps the
    response cacheable and visible to logging, unlike pipe.
  - ``balancer`` accepts a new value, ``shard``, using Varnish's
    consistent-hashing director: the same request lands on the same
    backend every time, which is better for cache hit ratio than
    ``round_robin``/``random`` when several backends could each
    independently cache the same content. Emits the documented
    ``.reconfigure()`` call after adding backends.
  - The purge ACL (``acl list_purge``) now sets ``+fold(-report)``,
    keeping Vinyl Cache 9.0's default ACL-folding optimization but
    silencing the (harmless but noisy) compiler warning it emits for
    common setups, e.g. a backend on 127.0.0.1 overlapping with the
    "localhost" entry.
  - ``verbose-headers`` is a real, working option again (it was removed
    earlier in this fork's history because it was dead code in the
    version it was forked from). When ``off`` (the default), the
    diagnostic ``X-Cache``, ``X-Cacheable`` and ``grace`` response
    headers are stripped before delivery; set to ``on`` to keep them
    for debugging.
  - New ``purge-by-id`` option (default ``off``) for
    ``plone.recipe.vinylcache:configuration``, compatible with
    `collective.purgebyid <https://github.com/collective/collective.purgebyid>`_:
    ``GET /@@purgebyid/<id>`` purges every cached object tagged with
    that id (via the backend's ``X-Ids-Involved`` header) without
    needing to enumerate every cached URL variant of that content. Two
    modes: ``ban`` (also ``on``, the default when enabled) purges via
    ``ban()`` and needs no vmod, matching a real-world production
    pattern found in the wild that avoids the vmod-compile step
    entirely; ``xkey`` purges via the ``xkey`` vmod's secondary-key
    support instead (more efficient, requires
    ``[varnish-build] compile-vmods = true`` -- the ``xkey`` import is
    only emitted in this mode).
  - New ``tls-config`` option for ``plone.recipe.vinylcache:script``,
    mapping to ``varnishd -A`` (a Vinyl Cache 9.0 addition letting
    ``varnishd`` terminate TLS itself via a hitch-like config file,
    instead of needing a separate TLS terminator in front of it).
  - New ``max-cacheable-size`` option for
    ``plone.recipe.vinylcache:configuration`` (default: unset, no limit).
    Objects whose backend response ``Content-Length`` exceeds this value
    (a VCL BYTES literal, e.g. ``50MB``) are marked uncacheable in
    ``vcl_backend_response``. Without a limit, a single very large
    object can nuke a large fraction of the cache under LRU pressure
    just to make room for itself, evicting many still-useful smaller
    objects along the way.
  - New ``plone.recipe.vinylcache:selfsigned`` recipe: generates a
    self-signed certificate/key (via ``openssl``, idempotently -- it
    won't regenerate an already-present certificate on later buildout
    runs) plus a ready-to-use ``-A``-style config file, for pairing with
    ``tls-config`` in internal/dev/testing setups where a CA-issued
    certificate isn't warranted. The key file, the combined cert+key
    file, and the directory holding them are all written with
    restricted permissions (0600/0600/0700) since they contain private
    key material.

  [mamico]

- Default ``plone.recipe.vinylcache:script``'s ``name`` option (which maps
  to ``varnishd -n``, controlling its working directory) to
  ``${buildout:directory}/var/<part name>`` instead of leaving it unset.
  Without it, ``varnishd`` picks its own system default working directory
  (typically under ``/var/run``), which requires root and is the most
  common "Permission denied: Cannot create working directory" trap when
  running ``varnishd`` unprivileged from a buildout. Deliberately placed
  under ``var``, not ``parts`` (which is disposable/regenerated e.g. on a
  ``varnish-build`` recompile), and keyed by the part's own name so
  multiple instances in one buildout don't collide. Set ``name``
  explicitly to override. [mamico]

- BUGFIX: revert to legacy (``pkg_resources``-declared) ``plone``/
  ``plone.recipe`` namespace packages (restoring ``plone/__init__.py``
  and ``plone/recipe/__init__.py``, and ``namespace_packages=`` in
  ``setup.py``) instead of pure PEP 420 native namespaces. Real-world
  Plone buildouts still mix in many ``plone.*`` eggs that declare the
  namespace the legacy way; when this package was native-only, its
  develop egg became invisible to ``zc.buildout``'s ``pkg_resources``-
  based dependency/recipe resolution as soon as it was combined with
  those other eggs in the same buildout (reproduced with a real
  Plone-buildout-shaped setup: worked in isolation, failed with
  "Couldn't find index page for 'plone.recipe.vinylcache'" once other
  legacy-``plone``-namespace eggs were also present -- the exact same
  root cause as the ``zc.recipe.testrunner`` CI fix above, this time
  hitting real users). [mamico]

- CI: py39 is only tested against Plone 6.0 -- Plone's floating
  ``6.1-latest``/``6.2-latest`` requirements.txt now pin a ``pip``
  release requiring Python>=3.10. [mamico]

- Fork of `plone.recipe.varnish <https://pypi.org/project/plone.recipe.varnish/>`_,
  created to track the Varnish Cache -> Vinyl Cache project rename (early
  2026) and the new 9.0.x stable release line. All credit for the original
  recipe design and years of maintenance goes to the
  ``plone.recipe.varnish`` authors and contributors. If you don't need
  Vinyl Cache 9.0.x, please keep using ``plone.recipe.varnish`` -- it is
  unaffected by this fork and continues to target Varnish 6.0 LTS.
  [mamico]

- BREAKING: only support Vinyl Cache (formerly Varnish Cache) version
  9.0.x and generate config (VCL) for this version only. [mamico]

- BUGFIX: ``vcl_hit``'s grace-handling code used ``return(miss)``, which
  is no longer a valid VCL return action from ``vcl_hit`` as of VCL
  syntax 4.1 (confirmed against the real Vinyl Cache 9.0.3 VCC returns
  table -- discovered by actually compiling the generated VCL in CI, not
  just by reading docs). Replaced with ``return(restart)``, which
  re-enters VCL processing at ``vcl_recv`` and naturally resolves to a
  fresh fetch once an object's grace window has genuinely expired.
  [mamico]

- Drop Python 3.8 from the test matrix and ``python_requires`` (matches
  upstream ``plone.recipe.varnish``, which dropped it for the same
  reason: Plone's floating "-latest" requirements.txt files now pin
  setuptools/packaging releases with no Python 3.8 wheels). [mamico]

- Pin ``zc.recipe.egg`` to ``3.0.0`` in ``versions.cfg``: the current
  ``zc.recipe.egg`` (4.0.0, pulled in transitively by
  ``zc.recipe.testrunner``) requires ``zc.buildout>=5.0.0``, which
  conflicts with Plone 6.1's pinned ``zc.buildout==4.2.0``. [mamico]

- Pin ``zc.recipe.testrunner`` to ``3.2``: releases from 4.0 onwards
  dropped the ``namespace_packages.txt`` metadata shim that
  ``pkg_resources`` (still used internally by ``zc.buildout``) needs to
  merge a purely-PEP-420 package into a ``zc`` namespace that is
  otherwise legacy-declared -- which it is here, because of the
  ``zc.recipe.egg`` pin above. Without this, buildout's own entry-point
  loader fails with ``ModuleNotFoundError: No module named
  'zc.recipe.testrunner'`` even though the same package installs and
  imports fine via plain ``pip install``. Reproduced locally against both
  a Plone-6.0/6.1-like (``zc.buildout`` 4.x) and Plone-6.2-like
  (``zc.buildout`` 5.x) environment; 3.2 works in both. [mamico]

- Update the default download URL to Vinyl Cache 9.0.3 and the default
  ``varnish-modules`` URL to release 0.28.0 (the release targeting the
  9.0 line; ``varnish-modules`` dropped support for Varnish 6.0 LTS
  starting with the releases that target 7.0+). Note: despite the
  project's rename from Varnish Cache to Vinyl Cache, the installed
  daemon binary is still called ``varnishd`` as of 9.0.x (confirmed
  against the upstream source), so this recipe does *not* rename it;
  only the download defaults and the recipe's own package name track
  the new branding/release line. [mamico]

- BUGFIX: ``vcl_init`` and ``vcl_pass`` custom VCL snippet options were
  silently dropped by the recipe (present in the template and documented
  in the README, but missing from the option-collection list); they are
  now correctly included in the generated VCL. [mamico]

- BUGFIX: ``user``/``group`` options for ``plone.recipe.vinylcache:script``
  were silently ignored because of a dead, version-gated template branch
  left over from supporting older Varnish releases; they now correctly
  emit ``-j unix,user=...[,ccgroup=...]``. [mamico]

- Fix the internal VCL syntax version marker to be the string ``"4.1"``
  instead of the float ``4.0`` -- this recipe always generates VCL syntax
  version 4.1. [mamico]

- Remove the ``verbose-headers`` option: it computed a value that was
  never actually forwarded to the VCL template and so never had any
  effect. [mamico]

- Remove the ``saint-mode`` option: saint mode was removed from Varnish
  itself years ago, and this recipe's own implementation of it was
  already disabled. Setting ``saint-mode`` to anything other than
  ``off`` now raises a clear error instead of being silently ignored.
  [mamico]

- Remove the undocumented-in-code, docs-only ``vcl-version`` option; no
  code ever read it. This recipe always targets VCL syntax version 4.1.
  [mamico]

- Drop Python 2.7 support. Modernize packaging: native PEP 420 namespace
  packages (no more ``plone/__init__.py``/``plone/recipe/__init__.py``
  ``declare_namespace`` calls), remove the broken ``setup.py`` test
  command (``setuptools.command.test`` was removed in setuptools>=72),
  update classifiers/``python_requires`` to Python 3.8+. [mamico]

- Test against Plone 6.0, 6.1 and 6.2 (and their respective zc.buildout
  versions) in CI; drop the Plone 5.2 / Python 2.7 test variant.
  [mamico]

- Carried over from ``plone.recipe.varnish``'s own history (already fixed
  there, not novel to this fork): the ``cookie-pass-not-exclude`` config
  option and ``vcl_synth`` custom VCL insertion point (6.0.13); the
  hostname-matching regex character-class bug for ``hostname:path``
  backends, fixed the same way independently while porting (6.0.18); and
  the ``cookie-pass`` default extension list dropping ``kss`` in favour of
  ``woff``/``woff2`` (6.0.13.1, [erral]). [mamico]
