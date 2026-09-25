# -*- coding: utf-8 -*-
from . import jinja2env
from zc.recipe.cmmi import Recipe as CMMIRecipe
from zc.recipe.cmmi import system

import logging
import os
import re
import zc.buildout

# Vinyl Cache (the project/company formerly known as Varnish Cache/Varnish
# Software) 9.0.x is the current stable line this recipe targets. NOTE:
# despite the project rename, the actual 9.0.x *source release* is still
# published as a "varnish-X.Y.Z.tar.gz" tarball (PACKAGE_TARNAME is still
# "varnish", confirmed by inspecting the real 9.0.3 configure.ac), and it
# still builds/installs a binary literally called `varnishd` (confirmed via
# the upstream Makefile.am: `sbin_PROGRAMS = varnishd`) -- only internal
# source directories (e.g. bin/vinyld/) and branding/docs have been renamed
# so far. Re-verify both facts against a future release before assuming
# otherwise.
DOWNLOAD_URL = (
    "https://github.com/varnish/varnish/releases/download/"
    "varnish-9.0.4/varnish-9.0.4.tar.gz"
)
# varnish-modules (vmods like header/xkey) dropped support for Varnish 6.0
# LTS as of the releases targeting 7.0+; this tag targets the 9.0 line.
# The project itself is still hosted/named "varnish-modules" (not renamed).
VMODS_DOWNLOAD_URL = "https://github.com/varnish/varnish-modules/archive/0.28.0.tar.gz"

COOKIE_WHITELIST_DEFAULT = """\
statusmessages
__ac
_ZopeId
__cp
auth_token
"""

DEFAULT_VCL_HASH = """\
hash_data(req.url);
if (req.http.host) {
    hash_data(req.http.host);
} else {
    hash_data(server.ip);
}
return(lookup);
"""

COOKIE_PASS_DEFAULT = """\
"auth_token|__ac(|_(name|password|persistent))=":"\.(js|css|woff|woff2)$"
"""  # noqa: W605
COOKIE_PASS_RE = re.compile('"(.*)":"(.*)"')
COOKIE_PASS_NOT_EXCLUDE_DEFAULT = "/\\+\\+resource\\+\\+zmi/"


class BaseRecipe(object):
    def __init__(self, buildout, name, options):
        self.name = name
        self.options = options
        self.buildout = buildout
        self.logger = logging.getLogger(self.name)

    def _log_and_raise(self, message):
        """log error first and then raise buildout Exception"""
        self.logger.error(message)
        raise zc.buildout.UserError(message)

    def _process_bind(self):
        self.options["bind"] = self.options.get("bind").lstrip(":")
        bind = self.options["bind"].split(":")
        if len(bind) == 1 and bind[0].isdigit():
            self.options["bind-host"] = ""
            self.options["bind-port"] = bind[0]
            self.options["bind"] = ":" + bind[0]
        elif len(bind) == 2 and bind[1].isdigit():
            self.options["bind-host"] = bind[0]
            self.options["bind-port"] = bind[1]
        else:
            self._log_and_raise("Invalid syntax for bind")

    def get_from_section(self, part, key, default):
        if part not in self.buildout:
            return default
        if key not in self.buildout[part]:
            return default
        return self.buildout[part][key]

    def install(self):
        pass

    def update(self):
        pass


class BuildRecipe(CMMIRecipe, BaseRecipe):
    def __init__(self, buildout, name, options):
        # An inherited/extended buildout.cfg may declare "url =" with no
        # value as a placeholder meant to be overridden downstream.
        # setdefault() below leaves that empty string in place (the key
        # already exists), which zc.recipe.cmmi then hands to
        # zc.buildout.download.Download() as if it were a local path,
        # failing with "FileNotFoundError: [Errno 2] No such file or
        # directory: ''" instead of falling back to our default. Drop it
        # first so setdefault() actually applies.
        if "url" in options and not options["url"]:
            del options["url"]
        BaseRecipe.__init__(self, buildout, name, options)
        self.options.setdefault("url", DOWNLOAD_URL)
        self.options.setdefault("jobs", "4")
        CMMIRecipe.__init__(self, buildout, name, self.options)

    def build(self):
        # build varnish (Vinyl Cache)
        super(BuildRecipe, self).build()
        if zc.buildout.buildout.bool_option(self.options, "compile-vmods", False):
            if "PKG_CONFIG_PATH" not in self.environ:
                self.environ["PKG_CONFIG_PATH"] = os.path.join(
                    self.options["location"], "lib", "pkgconfig"
                )
                os.environ.update(self.environ)
            vmods_options = {
                k[6:]: v for k, v in self.options.items() if k.startswith("vmods_")
            }
            # Same empty-placeholder issue as the main "url" option above.
            if "url" in vmods_options and not vmods_options["url"]:
                del vmods_options["url"]
            vmods_options.setdefault("url", VMODS_DOWNLOAD_URL)
            vmods_options.setdefault("source-directory-contains", "bootstrap")
            vmods_options.setdefault("configure-command", "./bootstrap; ./configure")
            vmods_recipe = CMMIRecipe(self.buildout, self.name, vmods_options)
            vmods_recipe.build()

    def cmmi(self, dest):
        """Do the 'configure; make; make install' command sequence.

        When this is called, the current working directory is the
        source directory.  The 'dest' parameter specifies the
        installation prefix.

        This is overidden in order to enable parallel jobs in make.
        """
        options = self.configure_options

        if options is None:
            options = '--prefix="%s"' % dest
        if self.extra_options:
            options += " %s" % self.extra_options
        options += " --with-sphinx-build=false"
        # C
        system("%s %s" % (self.configure_cmd, options))

        # M
        base_make = "make"
        if int(self.options.get("jobs")) > 1:
            base_make += " -j {0}".format(self.options.get("jobs"))
        system(base_make)

        # MI
        system("make install")

        # set daemon location. Despite the Varnish Cache -> Vinyl Cache
        # project rename, the installed binary is still called `varnishd`
        # as of Vinyl Cache 9.0.x (confirmed against the upstream source:
        # `sbin_PROGRAMS = varnishd` in bin/vinyld/Makefile.am).
        self.options["daemon"] = os.path.join(
            self.options["location"], "sbin", "varnishd"
        )


class ConfigureRecipe(BaseRecipe):
    def __init__(self, buildout, name, options):
        super(ConfigureRecipe, self).__init__(buildout, name, options)

        self.options.setdefault("build-part", "varnish-build")

        self.options.setdefault(
            "location", os.path.join(buildout["buildout"]["parts-directory"], self.name)
        )
        # `saint-mode` was removed from Varnish itself years ago and was
        # already a no-op in the code this recipe was forked from; rather
        # than silently accept it, fail loudly if it's set to anything but
        # the (also removed) default so upgraders get clear feedback.
        if self.options.get("saint-mode", "off") != "off":
            self._log_and_raise(
                "The 'saint-mode' option has been removed (saint mode no "
                "longer exists in Varnish/Vinyl Cache); remove it from your "
                "buildout configuration."
            )
        self.options.setdefault("verbose-headers", "off")
        # collective.purgebyid compatibility. Two modes:
        # - "ban" (also "on"): ban()-based, no vmod needed, works
        #   everywhere. Matches collective.purgebyid's own non-xkey
        #   fallback.
        # - "xkey": uses the `xkey` vmod's secondary-key purge instead of
        #   a ban scan; more efficient, but requires
        #   `[varnish-build] compile-vmods = true` (the `xkey` import is
        #   only emitted in this mode, so "off"/"ban" never break
        #   compilation for setups that haven't built vmods).
        self.options.setdefault("purge-by-id", "off")
        purgebyid = self.options["purge-by-id"].strip().lower()
        if purgebyid == "on":
            purgebyid = "ban"
        if purgebyid not in ("off", "ban", "xkey"):
            self._log_and_raise(
                "Invalid value for 'purge-by-id': {0!r}. Must be one of "
                "'off', 'ban'/'on' or 'xkey'.".format(self.options["purge-by-id"])
            )
        self.options["purge-by-id"] = purgebyid
        self.options.setdefault("balancer", "none")
        self.options.setdefault("backends", "127.0.0.1:8080")
        self.options.setdefault(
            "config-file", os.path.join(self.options["location"], "varnish.vcl")
        )
        self.options.setdefault("connect-timeout", "0.4s")
        self.options.setdefault("first-byte-timeout", "300s")
        self.options.setdefault("between-bytes-timeout", "60s")
        self.options.setdefault("purge-hosts", "")
        self.options.setdefault("cookie-pass", COOKIE_PASS_DEFAULT)
        self.options.setdefault(
            "cookie-pass-not-exclude", COOKIE_PASS_NOT_EXCLUDE_DEFAULT
        )
        self.options.setdefault("cookie-whitelist", COOKIE_WHITELIST_DEFAULT)
        # Set default vcl_hash function so it doesn't use the default.vcl hostname
        self.options.setdefault("vcl_hash", DEFAULT_VCL_HASH)
        # set and test for valid bind value
        self.options.setdefault("bind", "127.0.0.1:8000")
        self._process_bind()

    def _process_backends(self):
        result = []
        raw_backends = [
            _.rsplit(":", 2) for _ in self.options["backends"].strip().split()
        ]
        # consistency checks
        if len(raw_backends) > 1:
            lengths = set([len(x) for x in raw_backends])
            if lengths != set([3]):
                self._log_and_raise(
                    "When using multiple backends a hostname "
                    "must be given for each client"
                )
        for idx, raw_backend in enumerate(raw_backends):
            backend = {"name": "backend_{0:03d}".format(idx)}
            try:
                if len(raw_backend) == 3:
                    url, host, port = raw_backend
                else:
                    host, port = raw_backend
                    url = None
            except ValueError:
                self._log_and_raise(
                    "Invalid syntax for backend: {0}".format(":".join(raw_backend))
                )
                raise zc.buildout.UserError("Invalid syntax for backends")
            backend["url"] = url
            backend["host"] = host
            backend["port"] = port
            backend["connect_timeout"] = self.options["connect-timeout"]
            backend["first_byte_timeout"] = self.options["first-byte-timeout"]
            backend["between_bytes_timeout"] = self.options["between-bytes-timeout"]

            result.append(backend)

        return result

    def _process_zope_vhm_map(self, backends):
        result = {}

        vhm_external_port = self.options.get(
            "zope2_vhm_port", self.options["bind-port"]
        )
        vhm_proto = "http"
        if self.options.get("zope2_vhm_ssl", False) == "on":
            vhm_external_port = self.options.get("zope2_vhm_ssl_port", "443")
            vhm_proto = "https"

        for line in self.options.get("zope2_vhm_map", "").split():
            domain, location = line.split(":")
            result[domain.strip()] = {
                "location": location.strip(),
                "proto": vhm_proto,
                "external_port": vhm_external_port,
            }
        return result

    def _process_balancers(self, balancer, backends):
        """if theres is a balancer configured, all backends are assigned.

        this could be refactored in future to support multiple balancers.
        """
        result = []
        if balancer != "none":
            record = {
                "type": balancer,
                "name": "balancer_0",
                "backends": [_["name"] for _ in backends],
            }
            result.append(record)
        return result

    def install(self):
        if "configuration-file" not in self.options:
            if not os.path.exists(self.options["location"]):
                os.mkdir(self.options["location"])
                self.options.created(self.options["location"])
            self.options["configuration-file"] = os.path.join(
                self.options["location"], "varnish.vcl"
            )
        self.create_varnish_configuration()
        return self.options.created()

    def update(self):
        self.install()

    def create_varnish_configuration(self):
        from plone.recipe.vinylcache.vclgen import VclGenerator

        config = {}

        # enable verbose (diagnostic) response headers: X-Cache, X-Cacheable,
        # grace. Off by default to avoid leaking cache internals to clients.
        config["verbose"] = self.options["verbose-headers"] == "on"
        config["purgebyid"] = self.options["purge-by-id"]
        # Objects larger than this (by Content-Length) are never cached.
        # Without a limit, a single very large object can nuke a large
        # fraction of the cache under LRU pressure to make room for
        # itself; unset (the default) means no size limit is applied.
        # Value must be a valid VCL BYTES literal, e.g. "50MB", "1GB".
        config["maxcacheablesize"] = self.options.get("max-cacheable-size", None)
        config["gracehealthy"] = self.options.get("grace-healthy", None)
        config["gracesick"] = self.options.get("grace-sick", "600s")
        config["healthprobeurl"] = self.options.get("health-probe-url", None)
        config["healthprobetimeout"] = self.options.get("health-probe-timeout", None)
        config["healthprobeinterval"] = self.options.get("health-probe-interval", None)
        config["healthprobewindow"] = self.options.get("health-probe-window", None)
        config["healthprobethreshold"] = self.options.get(
            "health-probe-threshold", None
        )
        config["healthprobeinitial"] = self.options.get("health-probe-initial", None)

        # fixup cookies for better plone caching
        config["cookiewhitelist"] = [
            _.strip() for _ in self.options["cookie-whitelist"].split()
        ]
        config["cookiepass"] = []
        for line in self.options["cookie-pass"].split():
            line = line.strip()
            if not line:
                continue
            match = COOKIE_PASS_RE.match(line)
            mg = match.groups()
            if not mg and len(mg) != 2:
                continue
            config["cookiepass"].append(dict(zip(("match", "exclude"), mg)))
        config["cookiepassnotexclude"] = self.options["cookie-pass-not-exclude"]
        # inject custom vcl
        config["custom"] = {}
        for name in (
            "vcl_import",
            "vcl_recv",
            "vcl_hit",
            "vcl_miss",
            "vcl_backend_fetch",
            "vcl_purge",
            "vcl_deliver",
            "vcl_pipe",
            "vcl_backend_response",
            "vcl_hash",
            "vcl_init",
            "vcl_pass",
            "vcl_synth",
        ):
            config["custom"][name] = self.options.get(name, "")

        config["backends"] = self._process_backends()
        config["directors"] = self._process_balancers(
            self.options["balancer"].strip(), config["backends"]
        )
        config["zope2_vhm_map"] = self._process_zope_vhm_map(config["backends"])
        config["code404page"] = True

        # build the purge host string
        config["purgehosts"] = set([])
        for segment in self.options["purge-hosts"].split():
            segment = segment.strip()
            if segment:
                config["purgehosts"].add(segment)

        vclgenerator = VclGenerator(config)
        filedata = vclgenerator()
        with open(self.options["configuration-file"], "wt") as fio:
            fio.write(filedata)
        self.options.created(self.options["configuration-file"])


class ScriptRecipe(BaseRecipe):
    def __init__(self, buildout, name, options):
        super(ScriptRecipe, self).__init__(buildout, name, options)

        self.options.setdefault("build-part", "varnish-build")
        self.options.setdefault("configuration-part", "varnish-configuration")

        self.options.setdefault(
            "daemon",
            self.get_from_section(self.options["build-part"], "location", "/usr")
            + "/sbin/varnishd",
        )

        self.options.setdefault(
            "bind",
            self.get_from_section(
                self.options["configuration-part"], "bind", "127.0.0.1:8000"
            ),
        )
        self.options.setdefault(
            "configuration-file",
            self.get_from_section(
                self.options["configuration-part"], "config-file", ""
            ),
        )
        if not self.options["configuration-file"]:
            self._log_and_raise("No configuration file found")
        self._process_bind()

        self.options.setdefault(
            "location", os.path.join(buildout["buildout"]["parts-directory"], self.name)
        )
        # Default varnishd's working directory (-n) to somewhere inside the
        # buildout's `var` directory, not whatever system default varnishd
        # itself picks (e.g. /var/run/varnishd, which typically requires
        # root -- the single most common "Permission denied" trap when
        # running varnishd unprivileged from a buildout). Deliberately
        # *not* under `parts` (that tree is meant to be disposable/
        # regenerated, e.g. on a varnish-build recompile, which would lose
        # this runtime state) and keyed by this part's own name so multiple
        # varnish instances in the same buildout don't collide. A `name`
        # starting with "/" is used by varnishd as an absolute
        # working-directory path directly (see the `name` option docs in
        # README.rst).
        self.options.setdefault(
            "name",
            os.path.join(buildout["buildout"]["directory"], "var", self.name),
        )
        self.options.setdefault("cache-type", "file")
        self.options.setdefault("cache-size", "256M")
        self.options.setdefault("runtime-parameters", "")
        self.options.setdefault("secret-file", "nosecret")
        self.options.setdefault(
            "script-filename",
            os.path.join(self.buildout["buildout"]["bin-directory"], self.name),
        )

    def install(self):
        if not os.path.exists(self.options["location"]):
            os.mkdir(self.options["location"])
            self.options.created(self.options["location"])
        if "cache-location" not in self.options:
            # Like `name` above: under `var`, not `parts`, and keyed by this
            # part's name. A sibling of the default working directory rather
            # than inside it, so it doesn't mix with varnishd's own files.
            self.options["cache-location"] = os.path.join(
                self.buildout["buildout"]["directory"], "var", self.name + "-storage"
            )
            if not os.path.exists(self.options["cache-location"]):
                os.makedirs(self.options["cache-location"])
                self.options.created(self.options["cache-location"])

        # If `name` is an absolute path, it's used by varnishd as its
        # working directory (-n) -- create it (and any missing parent,
        # e.g. `var/`) ourselves, since varnishd itself only creates the
        # leaf directory, not the full path, and fails outright
        # ("Cannot create working directory ...: No such file or
        # directory") when an intermediate parent is missing.
        name = self.options.get("name")
        if name and name.startswith("/") and not os.path.exists(name):
            os.makedirs(name)
            self.options.created(name)

        script = self.create_varnish_script()
        with open(self.options["script-filename"], "wt") as fio:
            fio.write(script)
        os.chmod(self.options["script-filename"], 0o755)
        self.options.created(self.options["script-filename"])
        return self.options.created()

    def create_varnish_script(self):
        # render script file
        data = {}

        data["daemon"] = self.options["daemon"]
        data["user"] = self.options.get("user")
        data["group"] = self.options.get("group")
        data["cfg_file"] = self.options["configuration-file"]
        data["pid_file"] = os.path.join(self.options["location"], "varnish.pid")
        data["bind"] = self.options["bind"]
        data["cache_type"] = self.options["cache-type"].lower()
        data["cache_location"] = self.options["cache-location"]
        data["cache_size"] = self.options["cache-size"]
        data["mode"] = self.options.get("mode", "daemon")
        data["name"] = self.options.get("name")
        data["secret"] = self.options.get("secret-file", "nosecret")
        data["telnet"] = self.options.get("telnet")
        # `-A` (a hitch-like TLS config file) is a Vinyl Cache 9.0 addition,
        # letting varnishd terminate TLS itself instead of needing a
        # separate terminator in front of it.
        data["tls_config"] = self.options.get("tls-config")
        data["parameters"] = self.options["runtime-parameters"].strip().split()

        template = jinja2env.get_template("start_script.jinja2")
        return template.render(data)


class SelfSignedCertRecipe(BaseRecipe):
    """Generate a self-signed TLS certificate plus a hitch-style config
    file suitable for `varnishd -A` (see `ScriptRecipe`'s `tls-config`
    option). Meant for internal/dev/testing use where a real CA-issued
    certificate isn't warranted -- clients will need to explicitly trust
    this certificate (or ignore validation errors) since it is
    self-signed.
    """

    def __init__(self, buildout, name, options):
        super(SelfSignedCertRecipe, self).__init__(buildout, name, options)

        self.options.setdefault(
            "location", os.path.join(buildout["buildout"]["parts-directory"], self.name)
        )
        self.options.setdefault("common-name", "localhost")
        self.options.setdefault("bind", "*:8443")
        self.options.setdefault("key-size", "2048")
        self.options.setdefault("days", "3650")
        self.options.setdefault(
            "key-file", os.path.join(self.options["location"], "key.pem")
        )
        self.options.setdefault(
            "cert-file", os.path.join(self.options["location"], "cert.pem")
        )
        self.options.setdefault(
            "combined-file", os.path.join(self.options["location"], "combined.pem")
        )
        self.options.setdefault(
            "config-file", os.path.join(self.options["location"], "tls.conf")
        )
        self._process_bind()

    def install(self):
        if not os.path.exists(self.options["location"]):
            # 0o700: this directory holds private key material.
            os.mkdir(self.options["location"], 0o700)
            self.options.created(self.options["location"])

        # Idempotent: don't regenerate (and so don't rotate/invalidate) an
        # already-present key/cert on every buildout run.
        if not os.path.exists(self.options["key-file"]) or not os.path.exists(
            self.options["cert-file"]
        ):
            cmd = (
                "openssl req -x509 -nodes "
                "-newkey rsa:{key_size} "
                '-keyout "{key_file}" -out "{cert_file}" '
                "-days {days} "
                '-subj "/CN={common_name}"'
            ).format(
                key_size=self.options["key-size"],
                key_file=self.options["key-file"],
                cert_file=self.options["cert-file"],
                days=self.options["days"],
                common_name=self.options["common-name"],
            )
            self.logger.info(
                "Generating self-signed certificate for CN=%s",
                self.options["common-name"],
            )
            system(cmd)
            # openssl writes the key with the process' default umask (often
            # world/group-readable); it's private key material, restrict it.
            os.chmod(self.options["key-file"], 0o600)
            self.options.created(self.options["key-file"])
            self.options.created(self.options["cert-file"])

        # hitch/varnishd's -A pem-file directive expects cert and key
        # concatenated into a single file. It also contains the private
        # key, so write it with restricted permissions from the start
        # rather than creating it world-readable and fixing it up after.
        with open(self.options["cert-file"]) as fio:
            cert_data = fio.read()
        with open(self.options["key-file"]) as fio:
            key_data = fio.read()
        fd = os.open(
            self.options["combined-file"], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
        )
        with os.fdopen(fd, "wt") as fio:
            fio.write(cert_data)
            fio.write(key_data)
        self.options.created(self.options["combined-file"])

        config = (
            "frontend = {{\n"
            '    host = "{host}"\n'
            '    port = "{port}"\n'
            "}}\n"
            'pem-file = "{combined_file}"\n'
        ).format(
            host=self.options["bind-host"] or "*",
            port=self.options["bind-port"],
            combined_file=self.options["combined-file"],
        )
        with open(self.options["config-file"], "wt") as fio:
            fio.write(config)
        self.options.created(self.options["config-file"])

        return self.options.created()

    def update(self):
        self.install()
