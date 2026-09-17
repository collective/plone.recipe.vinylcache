Changelog
=========

9.0.3.0.dev0 (unreleased)
-------------------------

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
