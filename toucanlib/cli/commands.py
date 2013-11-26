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


"""Command implementations for the Toucan command line interface."""


import cliapp
import os
import pygit2

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

        setup = toucanlib.cli.setup.SetupRunner()
        setup.run(repo, setup_file)
