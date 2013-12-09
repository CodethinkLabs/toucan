#!/usr/bin/env python
#
# Copyright (C) 2013 Codethink Limited.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""Script to test, build and install toucan."""


import glob
import itertools
import os
import subprocess
import sys

from distutils.core import setup
from distutils.cmd import Command


class Check(Command):

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def _test_repo_base_url(self):
        script_dir = os.path.dirname(__file__)
        default_url = os.path.abspath(os.path.join(script_dir, '..'))
        return os.environ.get('TEST_REPO_BASE_URL', default_url)

    def _check_coding_style(self):
        sys.stdout.write('Checking coding style against PEP 8\n')
        subprocess.check_call(['pep8', '--statistics', '.'])

    def _check_docstrings(self):
        sys.stdout.write('Checking coding style against PEP 257\n')
        subprocess.check_call(['pep257', '.'])

    def _run_unit_tests(self):
        sys.stdout.write('Running unit tests\n')
        subprocess.check_call(
            ['python', '-m', 'CoverageTestRunner',
             '--ignore-missing-from=modules-without-tests',
             'toucanlib'])
        if os.path.exists('.coverage'):
            os.remove('.coverage')

    def _run_scenario_tests(self):
        sys.stdout.write('Running scenario tests\n')

        suites = {
            'cli': ('local',),
        }

        for suite, locations in suites.iteritems():
            self._run_scenario_test_suite(suite, locations)

    def _run_scenario_test_suite(self, suite, locations):
        sys.stdout.write('Running scenario tests for %s\n' % suite)

        yarn_dir = os.path.join('tests', 'yarn')
        if not locations:
            patterns = [
                os.path.join(yarn_dir, suite.replace('.', '-'), '*.yarn'),
                os.path.join(yarn_dir, 'implementations', '*.yarn')
            ]
        else:
            patterns = [
                os.path.join(yarn_dir, '*.yarn'),
                os.path.join(yarn_dir, suite.replace('.', '-'), '*.yarn'),
                os.path.join(yarn_dir, 'implementations', '*.yarn')
            ]

        globs = [glob.glob(x) for x in patterns]
        filenames = list(itertools.chain.from_iterable(globs))

        locations = locations if locations else ('',)

        for location in locations:
            if location:
                sys.stdout.write(
                    'Running scenario tests for %s against a %s store\n' %
                    (suite, location))
            subprocess.check_call(
                ['yarn',
                 '--env=TEST_REPO_BASE_URL=%s' % self._test_repo_base_url(),
                 '--env=LOCATION=%s' % location,
                 '--env=API=%s' % suite,
                 '--env=PYTHONPATH=%s' % os.environ.get('PYTHONPATH', ''),
                 '-s', os.path.join(yarn_dir, 'implementations', 'helpers.sh')]
                + filenames)

    def _check_copyright_years_and_license_headers(self):
        if os.path.isdir('.git'):
            sys.stdout.write('Collecting versioned files\n')
            files = subprocess.check_output(['git', 'ls-files']).splitlines()
            files.remove('COPYING')

            sys.stdout.write('Check copyright years\n')
            for filename in files:
                subprocess.check_call(
                    [os.path.join('scripts', 'check-copyright-year'),
                     '-v', filename])

            sys.stdout.write('Check license headers\n')
            for filename in files:
                subprocess.check_call(
                    [os.path.join('scripts', 'check-license-header'),
                     '-v', filename])

    def run(self):
        self._check_coding_style()
        self._check_docstrings()
        self._run_unit_tests()
        self._run_scenario_tests()
        self._check_copyright_years_and_license_headers()


class Clean(Command):

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        pass


setup(
    name='toucan',
    long_description='''\
        toucan is a kanban solution based on Consonant. \
        It is written mostly in Python provides a command line and \
        web interface to manage kanban boards.''',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Framework :: Twisted',
        'Intended Audience :: Customer Service',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: '
        'GNU Affero General Public License v3 or later (AGPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: JavaScript',
        'Programming Language :: Python',
        'Programming Language :: Unix Shell',
        'Topic :: Database :: Database Engines/Servers',
        'Topic :: Database :: Front-Ends',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: Site Management',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Server',
        'Topic :: Office/Business',
        'Topic :: Office/Business :: Scheduling',
        'Topic :: Scientific/Engineering :: Information Analysis'
        'Topic :: Software Development :: Version Control',
        'Topic :: Utilities',
    ],
    author='Codethink Limited',
    author_email='toucan@consonant-project.org',
    url='http://consonant-project.org',
    scripts=['toucan'],
    packages=['toucanlib'],
    package_data={},
    data_files=[],
    cmdclass={
        'check': Check,
        'clean': Clean,
    })
