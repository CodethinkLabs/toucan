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


"""Toucan applications."""


import cliapp

import toucanlib


class Toucan(cliapp.Application):

    """The Toucan command line interface."""

    def cmd_setup(self, args):
        """Set up a new Toucan board from a setup file."""

        if len(args) < 2:
            raise cliapp.AppException(
                'Usage: toucan setup SETUP_FILE TARGET_DIRECTORY')

        setup_file = args[0]
        target_dir = args[1]

        cmd = toucanlib.cli.commands.SetupCommand(self, setup_file, target_dir)
        cmd.run()

    def cmd_list(self, args):
        """List objects in a Toucan board."""

        if len(args) < 2:
            raise cliapp.AppException(
                'Usage: toucan list BOARD PATTERN [PATTERN ...]')

        cmd = toucanlib.cli.commands.ListCommand(self, args[0], args[1:])
        cmd.run()
