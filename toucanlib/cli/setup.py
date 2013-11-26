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


"""Representation, parsing and execution of Toucan board setup files."""


import yaml

from consonant.util import expressions
from consonant.util.phase import Phase


class SetupFile(object):

    """A Toucan board setup file."""

    pass


class SetupParserError(Exception):

    """Errors occuring while parsing Toucan board setup files."""

    pass


class SetupParser(object):

    """A parser for Toucan board setup files."""

    def parse(self, stream):
        """Parse a file stream and return a SetupFile on success."""

        # phase 1: load the input YAML
        with Phase() as phase:
            try:
                data = yaml.load(stream)
            except Exception, e:
                phase.error(e)

        # phase 2: validate the setup data
        with Phase() as phase:
            if not isinstance(data, dict):
                phase.error(SetupParserError(
                    'Setup file is not a YAML dictionary.'))
            else:
                self._validate_meta_data(phase, data)
                self._validate_board_info(phase, data)
                self._validate_views(phase, data)
                #self._validate_lanes(phase, data)
                #self._validate_users(phase, data)

        setup_file = SetupFile()
        return setup_file

    def _validate_meta_data(self, phase, data):
        # validate the service name
        if not 'name' in data:
            phase.error(SetupParserError(
                'Setup file defines no service name'))
        elif not isinstance(data['name'], basestring):
            phase.error(SetupParserError(
                'Setup file defines a non-string service name: %s' %
                data['name']))
        elif not expressions.service_name.match(data['name']):
            phase.error(SetupParserError(
                'Setup file defines an invalid service name: %s' %
                data['name']))

        # validate the schema name
        if not 'schema' in data:
            phase.error(SetupParserError(
                'Setup file defines no schema name'))
        elif not isinstance(data['schema'], basestring):
            phase.error(SetupParserError(
                'Setup file defines a non-string schema name: %s' %
                data['schema']))
        elif not expressions.schema_name.match(data['schema']):
            phase.error(SetupParserError(
                'Setup file defines an invalid schema name: %s' %
                data['schema']))

    def _validate_board_info(self, phase, data):
        if not 'info' in data:
            phase.error(SetupParserError(
                'Setup file defines no board info'))
        elif not isinstance(data['info'], dict):
            phase.error(SetupParserError(
                'Setup file defines non-dict board info: %s' %
                data['info']))
        else:
            # validate the board name
            if not 'name' in data['info']:
                phase.error(SetupParserError(
                    'Setup file defines no board name'))
            elif not isinstance(data['info']['name'], basestring):
                phase.error(SetupParserError(
                    'Setup file defines a non-string board name: %s' %
                    data['info']['name']))

            # validate the board description
            if 'info' in data and \
                    not isinstance(data['info']['description'], basestring):
                phase.error(SetupParserError(
                    'Setup file defines a non-string board description: %s' %
                    data['info']['description']))

    def _validate_views(self, phase, data):
        if not 'views' in data:
            return

        if not isinstance(data['views'], list):
            phase.error(SetupParserError(
                'Setup file defines a non-list views entry'))
        else:
            for view in data['views']:
                if not 'name' in view:
                    phase.error(SetupParserError(
                        'Setup file defines a view without a name: %s' %
                        view))
                elif not isinstance(view['name'], basestring):
                    phase.error(SetupParserError(
                        'Setup file defines a non-string view name: %s' %
                        view['name']))

                if 'description' in view \
                        and not isinstance(view['description'], basestring):
                    phase.error(SetupParserError(
                        'Setup file defines a non-string view '
                        'description: %s' % view['description']))

                if not 'lanes' in view:
                    phase.error(SetupParserError(
                        'Setup file defines a view with no lanes: %s' %
                        view))
                elif not isinstance(view['lanes'], list):
                    phase.error(SetupParserError(
                        'Setup file defines a view with a non-list '
                        'lanes entry: %s' % view))
                else:
                    for lane in view['lanes']:
                        if not isinstance(lane, basestring):
                            phase.error(SetupParserError(
                                'Setup file defines a view with a non-string '
                                'lane name reference: %s' % lane))
                        else:
                            lanes = [x for x in data.get('lanes', [])
                                     if isinstance(x, dict) and 'name' in x]
                            matches = [x for x in lanes if x['name'] == lane]
                            if not matches:
                                phase.error(SetupParserError(
                                    'Setup file defines a view that refers '
                                    'to a non-existent lane: %s' % lane))


class SetupRunner(object):

    """A class that performs a setup against a repository and setup file."""

    def run(self, repo, setup_file):
        """Perform the board setup against a repository and setup file."""

        pass
