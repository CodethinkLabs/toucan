Toucan
======


What is Toucan?
---------------

Toucan is an implementation of the kanban concept written in Python and
based on Consonant. It provides a command line interface and a web
application to manage kanban boards in local or remote Consonant store
repositories or Consonant web services.


Dependencies
------------

Toucan depends on the following software components:

  * Python >= 2.7.0
  * python-consonant >= ?

For running the Toucan test suite, the following additional components
are required:

  * python-coverage-test-runner >= 1.9
  * pep8 >= 1.4.8
  * pep257 >= 0.2.4
  * cmdtest >= 0.9
  * git >= 1.8.0


Testing
-------

Toucan comes with an elaborate test suite with the following features:

  * License checking of all source files
  * Unit tests
  * Scenario tests
  * Coding style checks (PEP 8, PEP 257)

These tests can be executed with

    python setup.py check

from the root directory of the source tree.


Building & Installing
---------------------

Like most Python projects, Toucan can be built and installed using the
standard commands

    python setup.py build
    sudo python setup.py install

from the root directory of the source tree.


Contributing
------------

The development of Toucan takes place within the Codethink Labs project
on GitHub:

  https://github.com/CodethinkLabs/toucan

Anyone interested in improving Toucan is welcome to clone the project
repository and send pull requests.

We don't currently have a mailing list set up for discussions.


License
-------

Copyright (C) 2013-2014 Codethink Limited.

Toucan is licensed under the GNU Affero General Public License version
3 or later (AGPLv3+). The full text of the license can be found in the
COPYING file distributed along with this README.
