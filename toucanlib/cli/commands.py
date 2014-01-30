# Copyright (C) 2013-2014 Codethink Limited.
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


"""Command implementations for the Toucan command line interface."""


import cliapp
import consonant
import os
import pygit2
import sys
import subprocess
import tempfile

import toucanlib


class SetupCommand(object):

    """Command to create a new Toucan board from a setup file."""

    def __init__(self, app, setup_file, target_dir):
        self.app = app
        self.setup_filename = setup_file
        self.target_dir = target_dir

    def run(self):
        """Perform the board setup."""

        # parse the setup file
        parser = toucanlib.cli.setup.SetupParser()
        setup_file = parser.parse(open(self.setup_filename, 'r'))

        # create the target directory
        try:
            os.makedirs(self.target_dir)
        except OSError, e:
            raise cliapp.AppException(
                'Failed to create the target directory: %s' % e.strerror)

        # initialise the Git repository
        repo = pygit2.init_repository(self.target_dir)

        # perform the actual board setup
        setup = toucanlib.cli.setup.SetupRunner()
        setup.run(repo, setup_file)


class ListCommand(object):

    """Command to list objects in a Toucan board."""

    def __init__(self, app, service_url, patterns):
        self.app = app
        self.service_url = service_url
        self.patterns = patterns

    def run(self):
        """List objects in the Toucan board."""

        # obtain a Consonant service for the service URL
        factory = consonant.service.factories.ServiceFactory()
        service = factory.service(self.service_url)

        # resolve master into its latest commit
        commit = service.ref('master').head

        # resolve input patterns into objects
        resolver = toucanlib.cli.names.NameResolver(service, commit)
        objects = resolver.resolve_patterns(self.patterns, None)

        # render objects to the standard output
        renderer = toucanlib.cli.rendering.ListRenderer(service)
        renderer.render(self.app.output, objects)


class ShowCommand(object):

    """Command to show information about objects in a Toucan board. """

    def __init__(self, app, service_url, patterns):
        self.app = app
        self.service_url = service_url
        self.patterns = patterns

    def run(self):
        """Show detailed information about objects."""

        # Get a consonant service for the provided URL
        factory = consonant.service.factories.ServiceFactory()
        service = factory.service(self.service_url)

        # Get the latest commit from this service
        commit = service.ref('master').head

        # resolve the input patterns into object
        resolver = toucanlib.cli.names.NameResolver(service, commit)
        objects = resolver.resolve_patterns(self.patterns, None)

        # render the objects to stdout
        renderer = toucanlib.cli.rendering.ShowRenderer(service, commit)
        renderer.render(self.app.output, objects)

        # if there were no objects, inform the user
        if not objects:
            self.app.output.write(
                    'No objects found matching %s.\n' % self.patterns)


class AddCommand(object):

    """Command to add an object to a toucan board."""

    def __init__(self, app, service_url, klass):
        self.app = app
        self.service_url = service_url
        self.klass = klass

    def run(self):
        """Add an object to a board."""

        # get a Consonant service
        factory = consonant.service.factories.ServiceFactory()
        service = factory.service(self.service_url)

        # get the latest commit
        commit = service.ref('master').head

        # create a temporary file
        with tempfile.NamedTemporaryFile() as f:
            renderer = toucanlib.cli.rendering.TemplateRenderer(service)
            renderer.render(f, self.klass)
            f.flush()

            # get initial input
            self._run_editor(f.name)

            # create an object loader to parse the input
            loader = toucanlib.cli.loaders.ObjectLoader(
                f.name, service, commit)

            with toucanlib.cli.loaders.Phase() as phase:
                if loader.load():
                    while not loader.validate(self.klass, phase):
                        self.app.output.write(
                            "Error adding %s, please revise input.\n" % self.klass)
                        # Re-open the temporary file.
                        # This will only work on UNIX systems, and a better solution
                        # should be found in future. Without doing this, some
                        # editors (gedit) cause no data to be written to the file
                        # and no exceptions to be raised.
                        with open(f.name, 'w+') as t:
                            for error in phase.errors:
                                t.write('# %s\n' % error)
                            phase.errors = []
                            t.write('#\n')
                            renderer.render(t, self.klass, loader.data)
                            t.flush()
                        self._run_editor(f.name)
                        if not loader.load():
                            self.app.output.write(
                                'Cancelled addition of %s.\n' % self.klass)
                            return False
                    loader.create(self.klass, phase)
                    self.app.output.write("Added a %s.\n" % self.klass)
                    return True
                else:
                    self.app.output.write(
                        'Cancelled addition of %s.\n' % self.klass)
                    return False

    def _run_editor(self, file_path):
        editor = os.environ.get('EDITOR')
        if editor:
            command = editor.split()
            command.append(file_path)
            subprocess.check_call(command)
        else:
            subprocess.check_call(['vi', file_path])
