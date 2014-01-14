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


"""Render objects to the command line."""


class ObjectClassListRenderer(object):

    """Render the objects of a class to a text stream."""

    def __init__(self, service):
        self.service = service

    def render(self, stream, objects):
        """Render a list of objects to a text stream."""

        raise NotImplementedError

    def render_rows(self, stream, rows):
        """Render a list of rows with cells to a text stream."""

        if len(rows) > 0:
            # compute the maximum width for all columns
            column_widths = [0 for column in rows[0]]
            for row in rows:
                for column in range(0, len(row)):
                    column_widths[column] = \
                        max(column_widths[column], len(row[column]))

            # generate a format string to the columns of all rows
            column_formats = ['%%-%ds' % width for width in column_widths]
            format_string = ' | '.join(column_formats)

            # write the rows to the stream using the row format
            for row in rows:
                stream.write('%s\n' % (format_string % row))


class InfoListRenderer(ObjectClassListRenderer):

    """Render lists of info objects to a text stream."""

    def render(self, stream, infos):
        """Render a list of infos to a text stream."""

        rows = []
        for info in infos:
            rows.append(('info',
                         info.properties['name'].value,
                         info.properties['description'].value.strip()))
        self.render_rows(stream, rows)


class ViewListRenderer(ObjectClassListRenderer):

    """Render lists of view objects to a text stream."""

    def render(self, stream, views):
        """Render a list of views to a text stream."""

        rows = []
        for view in sorted(views, key=lambda l: l.properties['name'].value):
            if 'lanes' in view.properties:
                num_lanes = len(view.properties['lanes'].value)
            else:
                num_lanes = 0
            rows.append(('view',
                         view.properties['name'].value,
                         view.properties['description'].value.strip(),
                         '%d lanes' % num_lanes))
        self.render_rows(stream, rows)


class LaneListRenderer(ObjectClassListRenderer):

    """Render lists of lane objects to a text stream."""

    def render(self, stream, lanes):
        """Render a list of lanes to a text stream."""

        rows = []
        for lane in sorted(lanes, key=lambda l: l.properties['name'].value):
            if 'cards' in lane.properties:
                num_cards = len(lane.properties['cards'].value)
            else:
                num_cards = 0
            rows.append(('lane',
                         lane.properties['name'].value,
                         lane.properties['description'].value.strip(),
                         '%d cards' % num_cards))
        self.render_rows(stream, rows)


class UserListRenderer(ObjectClassListRenderer):

    """Render lists of user objects to a text stream."""

    def render(self, stream, users):
        """Render a list of users to a text stream."""

        rows = []
        for user in sorted(users, key=lambda u: u.properties['name'].value):
            roles = [role.value for role in user.properties['roles'].value]
            rows.append(('user',
                         user.properties['name'].value,
                         user.properties['email'].value,
                         ','.join(roles)))
        self.render_rows(stream, rows)


class UserConfigListRenderer(ObjectClassListRenderer):

    """Render lists of user config objects to a text stream."""

    def render(self, stream, configs):
        """Render a list of user configs to a text stream."""

        rows = []
        for config in sorted(configs, key=self._sort_key):
            user = self.service.resolve_reference(
                config.properties['user'].value)
            if 'default-view' in config.properties:
                default_view = config.properties['default-view'].value
            else:
                default_view = ''
            rows.append(('user-config',
                         user.properties['name'].value,
                         default_view))
        self.render_rows(stream, rows)

    def _sort_key(self, config):
        user = self.service.resolve_reference(config.properties['user'].value)
        return user.properties['name'].value


class ListRenderer(object):

    """Render lists of objects to a text stream."""

    def __init__(self, service):
        self.service = service

    def render(self, stream, objects):
        """Render a list of objects to a text stream."""

        groups = self._group_objects(objects)
        names = sorted(groups.iterkeys())
        for name in names:
            self._render_group(stream, name, groups[name])

    def _group_objects(self, objects):
        groups = {}
        for obj in objects:
            if not obj.klass.name in groups:
                groups[obj.klass.name] = []
            groups[obj.klass.name].append(obj)
        return groups

    def _render_group(self, stream, name, objects):
        render_group_func = '_render_%s_group' % name.replace('-', '_')
        getattr(self, render_group_func)(stream, objects)

    def _render_info_group(self, stream, objects):
        return InfoListRenderer(self.service).render(stream, objects)

    def _render_lane_group(self, stream, objects):
        return LaneListRenderer(self.service).render(stream, objects)

    def _render_view_group(self, stream, objects):
        return ViewListRenderer(self.service).render(stream, objects)

    def _render_user_group(self, stream, objects):
        return UserListRenderer(self.service).render(stream, objects)

    def _render_user_config_group(self, stream, objects):
        return UserConfigListRenderer(self.service).render(stream, objects)

class ObjectClassShowRenderer(object):

    """Render the objects of a class to a text stream."""

    def __init__(self, service):
        self.service = service

    def render(self, stream, objects):
        """Render a list of objects to a text stream."""

        raise NotImplementedError
