Todo
====

Area's this recipe could further be improved.

* Explore the use of varnishtest. Varnishtest is the testing framework
  Varnish/Vinyl Cache uses internally to validate cache functionalite. I
  have seen regressions in for example purging functionality because of
  minor version updates or small tweaks in Plone. We are already building
  Vinyl Cache in the receipe test setup, so we could prevent these from
  happening unnoticed by adding a few varnishtest scenario's. See
  https://github.com/varnishcache/varnish-cache/tree/master/bin/varnishtest/tests

* Improve purging. There are more clever purging schemes possible than the
  current purge setup. One possible setup is by using secondary cache key
  functionality as is done by https://pypi.org/project/collective.purgebyid/ .
  Another option is to start using

* The backends/redirector functions in the recipe and VCL generator are
  interdependent, complex and at the moment still miss the use case where you can
  have 4 backends for 2 sites. The backends should first be sorted on the
  domain/vhm/hostname part and then 2 directors should be created with each 2
  backends.

* Sticky sessions support in the directores when Vinyl Cache does load
  balancing to the backends. There is some discussion in the github issues
  for the ``plone.recipe.varnish`` repo this package was forked from. Also
  see this blog post on the Varnish Software website:
  https://info.varnish-software.com/blog/proper-sticky-session-load-balancing-varnish

* Expose unix-domain-socket backends (the VCL template already renders a
  ``.path`` backend when a backend dict has a ``path`` key, see
  ``vclgen.py``/the VCL template) through the ``backends =`` option
  syntax, which today only supports ``host:port``.

* Migrate ``setup.py`` to a ``pyproject.toml``-based build backend. Not
  done as part of the 9.0.3.0 fork to keep that rewrite's surface area
  focused on the Varnish -> Vinyl Cache version bump.
