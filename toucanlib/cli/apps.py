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

        if len(args) < 1:
            raise cliapp.AppException(
                'Usage: toucan list BOARD [PATTERN ...]')

        if len(args) == 1:
            args.append('*')

        cmd = toucanlib.cli.commands.ListCommand(self, args[0], args[1:])
        cmd.run()

    def cmd_show(self, args):
        """Show detailed information about objects in a Toucan board."""

        # If there is no board defined then raise an exception
        if len(args) < 1:
            raise cliapp.AppException(
                'Usage: toucan show BOARD [PATTERN ...]')

        board = args[0]

        # If no pattern is specified then show the board details
        if len(args) == 1:
            patterns = ['info/*']
        else:
            patterns = args[1:]

        # Run show command
        cmd = toucanlib.cli.commands.ShowCommand(self, board, patterns)
        cmd.run()

    def cmd_add(self, args):
        """Add an object to a Toucan board."""

        # If there are not enough arquments then raise an exception
        if len(args) < 2:
            raise cliapp.AppException(
                'Usage: toucan add BOARD CLASS')

        board = args[0]
        klass = args[1]

        # Run add command
        cmd = toucanlib.cli.commands.AddCommand(self, board, klass)
        cmd.run()

    def cmd_move(self, args):
        """Move a card to a lane in a Toucan board."""

        # If there are not enough arguments then raise an exception
        if len(args) < 3:
            raise cliapp.AppException(
                'Usage: toucan move BOARD CARD LANE')

        board = args[0]
        card = args[1]
        lane = args[2]

        cmd = toucanlib.cli.commands.MoveCommand(self, board, card, lane)
        cmd.run()
