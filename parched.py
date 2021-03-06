# Copyright (c) 2009 Sebastian Nowicki
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
.. moduleauthor:: Sebastian Nowicki <sebnow@gmail.com>

This module defines two classes which provide information about Pacman
packages and PKGBUILDs, :class:`PacmanPackage` and :class:`PKGBUILD`. These
classes iniherit from the :class:`Package` class, which provides the basic
metadata about package.
"""

import tarfile
from datetime import datetime
import re
import shlex

__all__ = ['Package', 'PacmanPackage', 'PKGBUILD']

class Package(object):
    """An abstract package class
    This class provides no functionality whatsoever. Use either
    :class:`PacmanPackage`, :class:`PKGBUILD`, or another subclass instead.
    
    The class provides attributes common to all packages. All attributes are
    supposed to be read-only.
    
    .. attribute:: name

        The name of the package.

    .. attribute:: version

        The version of the package, as a string.

    .. attribute:: release

        Release version of the package, i.e., version of the package itself,
        as an integer.

    .. attribute:: description

        Description of the package.

    .. attribute:: url

        Package's website.

    .. attribute:: licenses

        A list of licenses.

    .. attribute:: groups

        A list of groups the package belongs to.

    .. attribute:: provides

        A list of "virtual provisions" that the package provides.

    .. attribute:: depends

        A list of the names of packages the package depends on.

    .. attribute:: optdepends

        A list of optional dependencies which are not required during runtime.

    .. attribute:: conflicts

        A list of packages the package conflicts with.

    .. attribute:: replaces

        A list of packages this package replaces.

    .. attribute:: architectures

        A list of architectures the package can be installed on.

    .. attribute:: backup

        A list of files which should be backed up on upgrades

    .. attribute:: options

        Options used when building the package, represented as a list. This
        list is equivalent to that of `options` in a PKGBUILD. See
        :manpage:`PKGBUILD(5)` for more information.

    For more information about these attributes see :manpage:`PKGBUILD(5)`.

    """
    def __init__(self, pkgfile):
        super(Package, self).__init__()
        self.name = ""
        self.version = ""
        self.release = ""
        self.description = ""
        self.url = ""
        self.licenses = []
        self.groups = []
        self.provides = []
        self.depends = []
        self.optdepends = []
        self.conflicts = []
        self.replaces = []
        self.architectures = []
        self.options = []
        self.backup = []


class PacmanPackage(Package):
    """

    The :class:`PacmanPackage` class provides information about a package, by
    parsing a tarball in `pacman <http://www.archlinux.org/pacman>`_ package
    format. This tarball must have a `.PKGINFO` member. This member provides
    all metadata about the package.

    To instantiate a :class:`PacmanPackage` object, pass the package's file
    path in the constructor::

        >>> import parched
        >>> package = PacmanPackage("foo-1.0-1-any.tar.gz")

    If *tarfileobj* is specified, it is used as an alternative to a
    :class:`TarFile` like object opened for *name*. It is supposed to be
    at position 0. *tarfileobj* may be any object that has an
    :meth:`extractfile` method, which returns a file like object::

        >>> import tarfile
        >>> f = tarfile.open("foo-1.0-1-any.tar.gz", "r|gz")
        >>> package = PacmanPackage(tarfileobj=f)
        >>> f.close()

    .. note::

        *tarfileobj* is not closed.

    The packages metadata can then be accessed directly::
    
        >>> print package
        "foo 1.0-1"
        >>> print package.description
        "Example package"
    
    In addition to the attributes provided by :class:`Package`,
    :class:`PacmanPackage` provides the following attributes:
    
    .. attribute:: builddate

        A :class:`datetime` object indicating time at which the package was
        built.

    .. attribute:: packager

        The person who made the package, represented as a string in the format::
        
            First_name Last_name <email@domain.com>

    .. attribute:: is_force

        Indicates whether an upgrade is forced
    
    .. attribute:: files
    
        An array of files contained in the package

    """
    def __init__(self, name=None, tarfileobj=None):
        super(PacmanPackage, self).__init__(tarfileobj)
        self.builddate = ""
        self.packager = ""
        self.is_forced = ""
        self.size = 0
        self.files = []
        self._symbol_map = {
            'pkgname': 'name',
            'pkgver': 'version',
            'pkgdesc': 'description',
            'license': 'licenses',
            'arch': 'architectures',
            'force': 'is_forced',
            'conflict': 'conflicts',
            'group': 'groups',
            'optdepend': 'optdepends',
            'makepkgopt': 'options',
            'depend': 'depends',
        }
        self._arrays = (
            'arch',
            'license',
            'replaces',
            'group',
            'depend',
            'optdepend',
            'conflict',
            'provides',
            'backup',
            'makepkgopt',
        )
        if not name and not tarfileobj:
            raise ValueError("nothing to open")
        should_close = False
        if not tarfileobj:
            tarfileobj = tarfile.open(str(name), "r|*")
            should_close = True
        pkginfo = tarfileobj.extractfile(".PKGINFO")
        self.files = tarfileobj.getnames()
        self._parse(pkginfo)
        if should_close:
            tarfileobj.close()

    def __str__(self):
        return '%s %s-%s' % (self.name, self.version, self.release)

    def _parse(self, pkginfo):
        """Parse the .PKGINFO file"""
        if hasattr(pkginfo, "seek"):
            pkginfo.seek(0)
        for line in pkginfo:
            if line[0] == '#' or line.strip() == '':
                continue
            var, _, value = line.strip().rpartition(' = ')
            real_name = var
            if var in self._symbol_map:
                real_name = self._symbol_map[var]
            if var in self._arrays:
                array = getattr(self, real_name)
                array.append(value)
            else:
                setattr(self, real_name, value)
        if self.size:
            self.size = int(self.size)
        if not self.is_forced == False:
            self.is_forced = self.is_forced == "True"
        if self.builddate:
            self.builddate = datetime.utcfromtimestamp(int(self.builddate))
        if self.version:
            self.version, _, self.release = self.version.rpartition('-')
            self.release = int(self.release)
        if self.packager == 'Uknown Packager':
            self.packager = None


class PKGBUILD(Package):
    """A :manpage:`PKGBUILD(5)` parser

    The :class:`PKGBUILD` class provides information about a
    package by parsing a :manpage:`PKGBUILD(5)` file.

    To instantiate a :class:`PacmanPackage` object, pass the package's file
    path in the constructor::

        >>> import parched
        >>> package = PKGBUILD("PKGBUILD")

    If *fileobj* is specified, it is used as an alternative to a
    :class:`file` like object opened for *name*. It is supposed to be
    at position 0. For example::

        >>> f = open("PKGBUILD", "r")
        >>> package = PKGBUILD(fileobj=f)
        >>> f.close()

    .. note::

        *fileobj* is not closed.

    The packages metadata can then be accessed directly::

        >>> print package
        "foo 1.0-1"
        >>> print package.description
        "Example package"

    In addition to the attributes provided by :class:`Package`,
    :class:`PKGBUILD` provides the following attributes:

    .. attribute:: install

        The filename of the install scriptlet.

    .. attribute:: checksums

        A dictionary containing the checksums of files in the
        :attr:`sources` list. The dictionary's keys are the algorithms
        used, and can be any of 'md5', 'sha1', 'sha256', 'sha384', and
        'sha512'. The value is a list of checksums. The elements
        correspond to files in the :attr:`sources` list, in relation to
        their position.

    .. attribute:: sources

        A list containing the URIs of filenames. Local file paths can be
        relative and do not require a protocol prefix.

    .. attribute:: makedepends

        A list of compile-time dependencies.

    .. attribute:: noextract

        A list of files not to be extracted. These files correspond to
        the basenames of the URIs in :attr:`sources`

    """
    _symbol_regex = re.compile(r"\$(?P<name>{[\w\d_]+}|[\w\d]+)")

    def __init__(self, name=None, fileobj=None):
        super(PKGBUILD, self).__init__(fileobj)
        self.install = ""
        self.checksums = {
            'md5': [],
            'sha1': [],
            'sha256': [],
            'sha384': [],
            'sha512': [],
        }
        self.noextract = []
        self.sources = []
        self.makedepends = []

        # Symbol lookup table
        self._var_map = {
            'pkgname': 'name',
            'pkgver': 'version',
            'pkgdesc': 'description',
            'pkgrel': 'release',
            'source': 'sources',
            'arch': 'architectures',
            'license': 'licenses',
        }
        self._checksum_fields = (
            'md5sums',
            'sha1sums',
            'sha256sums',
            'sha384sums',
            'sha512sums',
        )
        # Symbol table
        self._symbols = {}

        if not name and not fileobj:
            raise ValueError("nothing to open")
        should_close = False
        if not fileobj:
            fileobj = open(name, "r")
            should_close = True
        self._parse(fileobj)
        if should_close:
            fileobj.close()

    def _handle_assign(self, token):
        var, equals, value = token.strip().partition('=')
        # Is it an array?
        if value[0] == '(' and value[-1] == ')':
            self._symbols[var] = self._clean_array(value)
        else:
            self._symbols[var] = self._clean(value)

    def _parse(self, fileobj):
        """Parse PKGBUILD"""
        if hasattr(fileobj, "seek"):
            fileobj.seek(0)
        parser = shlex.shlex(fileobj, posix=True)
        parser.whitespace_split = True
        in_function = False
        while 1:
            token = parser.get_token()
            if token is None or token == '':
                break
            # Skip escaped newlines and functions
            if token == '\n' or in_function:
                continue
            # Special case:
            # Array elements are dispersed among tokens, we have to join
            # them first
            if token.find("=(") >= 0 and not token.rfind(")") >= 0:
                in_array = True
                elements = []
                while in_array:
                    _token = parser.get_token()
                    if _token == '\n':
                        continue
                    if _token[-1] == ')':
                        _token = '"%s")' % _token.strip(')')
                        token = token.replace('=(', '=("', 1) + '"'
                        token = " ".join((token, " ".join(elements), _token))
                        in_array = False
                    else:
                        elements.append('"%s"' % _token.strip())
            # Assignment
            if re.match(r"^[\w\d_]+=", token):
                self._handle_assign(token)
            # Function definitions
            elif token == '{':
                in_function = True
            elif token == '}' and in_function:
                in_function = False
        self._substitute()
        self._assign_local()
        if self.release:
            self.release = float(self.release)

    def _clean(self, value):
        """Pythonize a bash string.

        shlex strips enclosing double quotes from right-hand side of
        assignment, but not enclosing single quotes.

        """
        if value.startswith("'") and value.endswith("'"):
            return value.strip("'")
        else:
            return value

    def _clean_array(self, value):
        """Pythonize a bash array"""
        return shlex.split(value.strip('()'))

    def _replace_symbol(self, matchobj):
        """Replace a regex-matched variable with its value"""
        symbol = matchobj.group('name').strip("{}")
        # If the symbol isn't found fallback to an empty string, like bash
        try:
            value = self._symbols[symbol]
        except KeyError:
            value = ''
        # BUG: Might result in an infinite loop, oops!
        return self._symbol_regex.sub(self._replace_symbol, value)

    def _substitute(self):
        """Substitute all bash variables within values with their values"""
        for symbol in self._symbols:
            value = self._symbols[symbol]
            # FIXME: This is icky
            if isinstance(value, str):
                result = self._symbol_regex.sub(self._replace_symbol, value)
            else:
                result = [self._symbol_regex.sub(self._replace_symbol, x)
                    for x in value]
            self._symbols[symbol] = result

    def _assign_local(self):
        """Assign values from _symbols to PKGBUILD variables"""
        for var in self._symbols:
            value = self._symbols[var]
            if var in self._checksum_fields:
                key = var.replace('sums', '')
                self.checksums[key] = value
            else:
                if var in self._var_map:
                    var = self._var_map[var]
                setattr(self, var, value)

