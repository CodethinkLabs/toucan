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

import textwrap

import toucanlib
import consonant


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

    def __init__(self, service, commit):
        self.service = service
        self.commit = commit
        self.name_generator = toucanlib.cli.names.NameGenerator()

    def render(self, stream, objects):
        """Render a list of objects to a text stream."""

        raise NotImplementedError

    def render_lines(self, stream, lines):
        """Render the formatted lines generated about the object."""

        for line in lines:
            stream.write('%s\n' % line)

    def _list_cards(self, cards, lines):
        """Add a formatted list of cards to a given list of lines."""

        for card in cards:
            # format some strings
            card_name = self.name_generator.presentable_name(card)
            card_name = card_name.ljust(12)
            card_title = card['title']

            # wrap the card title
            indent = 17
            wrapper = textwrap.TextWrapper(
                    initial_indent='  - %s # ' % card_name,
                    subsequent_indent=(' ' * indent) + '# ',
                    width=80)
            lines += wrapper.wrap(card_title)

    def _list_views(self, views, lines, name_length):
        """Add a formatted list of views to a given list of lines."""

        for view in views:
            lines.append('  - ' + self._get_view(view, name_length))

    def _list_lanes(self, lanes, lines, name_length):
        """Add a formatted list of lanes to a given list of lines."""

        for lane in lanes:
            lines.append('  - ' + self._get_lane(lane, name_length))

    def _list_comments(self, comments, lines):
        """Add a formatted list of comments to a given list of lines."""

        for comment in comments:
            # get required information
            comment_id = self.name_generator.presentable_name(comment)
            comment_id = comment_id.ljust(13)
            comment_content = comment['comment']
            user_ref = comment['author']
            user = self.service.resolve_reference(user_ref)
            user_name = user['name']
            user_email = user['email']

            # format first line
            format_string = '  - %s # %s <%s>'
            lines.append(format_string % (comment_id, user_name, user_email))

            # wrap the comment
            indent = 20
            wrapper = textwrap.TextWrapper(
                    initial_indent=(' ' * indent) + '# ',
                    subsequent_indent=(' ' * indent) + '# ',
                    width=80)
            lines += wrapper.wrap(comment_content)

    def _list_assignees(self, assignees, lines, name_length):
        """Add a formatted list of assignees to a given list of lines."""

        for user in assignees:
            # add the line
            lines.append('  - ' + self._get_user(user, name_length))

    def _get_user(self, user, name_length=None):
        """Get formatted string of user information.

        Return a string of the format:
                user/[firstname] # [name] <email>

        """

        # get required information
        user_name = user['name']
        user_email = user['email']
        user_id = self.name_generator.presentable_name(user)
        if name_length:
            user_id = user_id.ljust(name_length + 5)

        # return the formatted string
        return '%s # %s <%s>' % (user_id, user_name, user_email)

    def _get_lane(self, lane, name_length=None):
        """Get formatted string of lane information.

        Returns a string of the format:
                lane/[name] # [name], [number of cards]

        """

        # get the required information
        lane_name = lane['name']
        lane_name = ('%s,' % lane_name)
        lane_id = self.name_generator.presentable_name(lane)
        if name_length:
            lane_name = lane_name.ljust(name_length + 1)
            lane_id = lane_id.ljust(name_length + 5)
        if 'cards' in lane:
            cards = '%d cards' % len(lane['cards'])
        else:
            cards = '0 cards'

        # return the formatted string
        return '%s # %s %s' % (lane_id, lane_name, cards)

    def _get_view(self, view, name_length=None):
        """Get formatted string of view information.

        Return a string of the format:
                view/[name] # [name]

        """

        view_name = view['name']
        view_short_name = self.name_generator.presentable_name(view)
        if name_length:
            view_short_name = view_short_name.ljust(name_length + 5)

        # return the formatted string
        return '%s # %s' % (view_short_name, view_name)

    def _get_milestone(self, milestone):
        """Get formatted string of milestone information.

        Return a string of the format:
                milestone/[name] # [name] [deadline]

        """

        # get required info
        m_short_name = self.name_generator.presentable_name(milestone)
        m_name = milestone['name']
        m_date = milestone['deadline'].value.date().isoformat()
        return '%s # %s, %s' % (m_short_name, m_name, m_date)

    def _get_reason(self, reason):
        """ Get formatted string of reason information.

        Return a string of the format:
                reason/[name] # [description]

        """

        # get required information
        reason_name = self.name_generator.presentable_name(reason)
        if 'description' in reason:
            return '%s # %s' % (reason_name, reason['description'])
        else:
            return '%s' % reason_name

    def _get_attachment(self, attachment):
        """Get formatted string of attachment information.

        Return a string of the format:
                attachment/[name] # [content-type]

        """

        # get required information
        attachment_name = self.name_generator.presentable_name(attachment)

        # return the formatted string
        return '%s' % attachment_name.lower()

    def _resolve_references(self, refs, prop=''):
        """Resolve multiple reference objects.

        Return a list of objects resolved from items in `refs`. Also
        return the length of the longest property of a certain type.

        Params:
             refs: A list of reference objects.
             prop: The property to get the length of.

        """

        objects = [self.service.resolve_reference(r.value) for r in refs]
        if prop:
            lengths = [len(str(o[prop])) for o in objects]
            return max(lengths), objects
        else:
            return None, objects

    def _render_description(self, obj, lines):
        if 'description' in obj:
            lines.append('description: >')
            wrapper = textwrap.TextWrapper(
                    initial_indent='  ',
                    subsequent_indent='  ',
                    width=80)
            lines += wrapper.wrap(obj['description'])


class InfoShowRenderer(ObjectClassShowRenderer):

    """Render information about the board in general."""

    def __init__(self, service, commit):
        self.service = service
        self.commit = commit
        self.name_generator = toucanlib.cli.names.NameGenerator()

    def render(self, stream, objects):
        """Render information about the board to a text stream."""

        lines = []

        for obj in objects:
            # first, render the name of the board
            lines.append('name: %s' % obj['name'])

            # next, render the description
            lines.append('description: >')
            wrapper = textwrap.TextWrapper(
                    initial_indent='  ',
                    subsequent_indent='  ',
                    width=80)
            lines += wrapper.wrap(obj['description'])

            # finally, render the views
            length = 0
            view_class = consonant.store.objects.ObjectClass('view', [])
            views = self.service.objects(self.commit, view_class)
            for view in views:
                length = max(len(view['name']), length)

            self._list_views(views, lines, length)

            # add separator
            lines.append('---')

        self.render_lines(stream, lines)


class AttachmentShowRenderer(ObjectClassShowRenderer):

    """Render information about an attachment."""

    def __init__(self, service, commit):
        self.service = service
        self.commit = commit
        self.name_generator = toucanlib.cli.names.NameGenerator()

    def render(self, stream, objects):
        """Render information about attachments to a text stream."""

        lines = []

        for obj in objects:
            # first, render the name of the attachment (usually a filename)
            lines.append('name: %s' % (obj['name']))

            # finally, render the comment that has the attachment
            lines.append('comment:')
            n, comments = self._resolve_references([obj['comment']])
            self._list_comments(comments, lines)

            # add separator
            lines.append('---')

        self.render_lines(stream, lines)


class ViewShowRenderer(ObjectClassShowRenderer):

    """Render information about a view."""

    def __init__(self, service, commit):
        self.service = service
        self.commit = commit
        self.name_generator = toucanlib.cli.names.NameGenerator()

    def render(self, stream, objects):
        """Render information about view objects to a text stream."""

        lines = []

        for obj in objects:
            # first, render the name of the view
            lines.append('name: %s' % (obj['name']))

            # next, render the description
            lines.append('description: >')
            wrapper = textwrap.TextWrapper(
                    initial_indent='  ',
                    subsequent_indent='  ',
                    width=80)
            lines += wrapper.wrap(obj['description'])

            # next, render the lanes
            lines.append('lanes:')

            # resolve the lane references
            name_length, lanes = self._resolve_references(obj['lanes'], 'name')

            # add the lanes
            self._list_lanes(lanes, lines, name_length)

            # add separator
            lines.append('---')

        self.render_lines(stream, lines)


class LaneShowRenderer(ObjectClassShowRenderer):

    """Render information about a lane."""

    def __init__(self, service, commit):
        self.service = service
        self.commit = commit
        self.name_generator = toucanlib.cli.names.NameGenerator()

    def render(self, stream, objects):
        """Render information about lane objects to a text stream."""

        lines = []

        for obj in objects:
            # first, render the name
            lines.append('name: %s' % (obj['name']))

            # next, render the description
            lines.append('description: >')
            wrapper = textwrap.TextWrapper(
                    initial_indent='  ',
                    subsequent_indent='  ',
                    width=80)
            lines += wrapper.wrap(obj['description'])

            # now render the views
            lines.append('views:')

            # resolve the references into view objects
            name_length, views = self._resolve_references(obj['views'], 'name')

            # add lines representing the views
            self._list_views(views, lines, name_length)

            # finally, render the cards
            if 'cards' in obj:
                lines.append('cards:')

                # resolve card references
                n, cards = self._resolve_references(obj['cards'])

                self._list_cards(cards, lines)

            # add separator
            lines.append('---')

        self.render_lines(stream, lines)


class CardShowRenderer(ObjectClassShowRenderer):

    """Render information about a card."""

    def __init__(self, service, commit):
        self.service = service
        self.commit = commit
        self.name_generator = toucanlib.cli.names.NameGenerator()

    def render(self, stream, objects):
        """Render information about cards to a text stream."""

        lines = []

        for obj in objects:
            # first, render the number
            lines.append('number: %s' % self.name_generator.card_id(obj))

            # next, render the title
            lines.append('title: %s' % obj['title'])

            # next, render the description
            self._render_description(obj, lines)

            # now the lane which contains the card
            lane = self.service.resolve_reference(obj['lane'])
            lines.append('lane: %s' % self._get_lane(lane))

            # now the milestone
            if 'milestone' in obj:
                milestone = self.service.resolve_reference(obj['milestone'])
                lines.append('milestone: ' + self._get_milestone(milestone))

            # now the reason
            r = self.service.resolve_reference(obj['reason'])
            lines.append('reason: ' + self._get_reason(r))

            # now the creator
            user = self.service.resolve_reference(obj['creator'])
            lines.append('creator: ' + self._get_user(user))

            # penultimately, the assignees
            self._render_assignees(obj, lines)

            # finally, render the comments
            self._render_comments(obj, lines)

            # add separator
            lines.append('---')

        self.render_lines(stream, lines)

    def _render_assignees(self, obj, lines):
        if 'assignees' in obj:
            lines.append('assignees:')
            name_length, assignees = self._resolve_references(obj['assignees'])
            for user in assignees:
                name_length = max(len(user['name'].split()[0]), name_length)

            # add the assignees list
            self._list_assignees(assignees, lines, name_length)

    def _render_comments(self, obj, lines):
        if 'comments' in obj:
            lines.append('comments:')
            n, comments = self._resolve_references(obj['comments'])

            # add the comments list
            self._list_comments(comments, lines)


class MilestoneShowRenderer(ObjectClassShowRenderer):

    """Render information about a milestone."""

    def __init__(self, service, commit):
        self.service = service
        self.commit = commit
        self.name_generator = toucanlib.cli.names.NameGenerator()

    def render(self, stream, objects):
        """Render information about milestones to a text stream."""

        lines = []

        for obj in objects:
            # first, render the name
            lines.append('name: %s' % obj['name'])

            # next, render the description
            self._render_description(obj, lines)

            # next, the deadline (yyyy-mm-dd)
            d = obj['deadline'].value.date().isoformat()
            lines.append('deadline: %s' % (d))

            # finally the cards
            if 'cards' in obj:
                lines.append('cards:')
                all_cards = self.service.objects(self.commit, 'card')
                cards = [x for x in all_cards
                        if x.get('milestone', '') == obj['short-name']]
                self._list_cards(cards, lines)

            # add separator
            lines.append('---')

        self.render_lines(stream, lines)


class ReasonShowRenderer(ObjectClassShowRenderer):

    """Render information about a reason."""

    def __init__(self, service, commit):
        self.service = service
        self.commit = commit
        self.name_generator = toucanlib.cli.names.NameGenerator()

    def render(self, stream, objects):
        """Render information about reasons to a text stream."""

        lines = []

        for obj in objects:
            # first, render the name
            lines.append('name: %s' % obj['name'])

            # next, render the description
            self._render_description(obj, lines)

            # next, the work items
            if 'work-items' in obj:
                # the method of displaying these is not yet decided upon,
                # as they are references to a remote store (NYI)
                pass

            # finally, the cards associated with the reason
            if 'cards' in obj:
                lines.append('cards:')
                all_cards = self.service.objects(self.commit, 'card')
                cards = [x for x in all_cards
                        if x['reason'] == obj['short-name']]
                self._list_cards(cards, lines)

            # add separator
            lines.append('---')

        self.render_lines(stream, lines)


class UserShowRenderer(ObjectClassShowRenderer):

    """Render information about users."""

    def __init__(self, service, commit):
        self.service = service
        self.commit = commit
        self.name_generator = toucanlib.cli.names.NameGenerator()

    def render(self, stream, objects):
        """Render inormation about users to a text stream."""

        lines = []
        for obj in objects:
            # first render the name
            lines.append('name: %s' % (obj['name']))

            # next, the email address
            lines.append('email: %s' % (obj['email']))

            # next, the roles
            lines.append('roles:')
            roles = obj['roles']
            for role in roles:
                lines.append('  - %s' % (role.value))

            # next the avatar url
            if 'avatar' in obj:
                lines.append('avatar: %s' % (obj['avatar']))

            # finally, the default-view
            if 'default-view' in obj:
                view = self.service.resolve_reference(obj['default-view'])
                lines.append('default-view: ' + self._get_view(view))

            # add separator
            lines.append('---')

        self.render_lines(stream, lines)


class CommentShowRenderer(ObjectClassShowRenderer):

    """Render information about comments to a text stream."""

    def __init__(self, service, commit):
        self.service = service
        self.commit = commit
        self.name_generator = toucanlib.cli.names.NameGenerator()

    def render(self, stream, objects):
        """Render comments to a text stream."""

        lines = []
        for obj in objects:
            # first, render the number
            comment_number = self.name_generator.presentable_name(obj)
            lines.append('number: %s' % comment_number)

            # next, the author
            author = self.service.resolve_reference(obj['author'])
            lines.append('author: %s' % self._get_user(author))

            # next, the card that the comment is on
            card = self.service.resolve_reference(obj['card'])
            card_number = self.name_generator.presentable_name(card)
            lines.append('card: %s' % card_number)

            # next, the comment itself
            lines.append('comment: >')
            self._render_comment(obj, lines)

            # finally, the attachment (if any)
            if 'attachment' in obj:
                a = self.service.resolve_reference(obj['attachment'])
                lines.append('attachment: %s' % self._get_attachment(a))
            lines.append('---')

        self.render_lines(stream, lines)

    def _render_comment(self, obj, lines):
        """Render the content of a comment, nicely wrapped."""

        wrapper = textwrap.TextWrapper(initial_indent='  ', width=78)
        lines += wrapper.wrap(obj['comment'])


class ShowRenderer(object):

    """Render lists of objects to a text stream."""

    def __init__(self, service, commit):
        self.service = service
        self.commit = commit

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
        renderer_classes = {
            'attachment': AttachmentShowRenderer,
            'card': CardShowRenderer,
            'comment': CommentShowRenderer,
            'info': InfoShowRenderer,
            'lane': LaneShowRenderer,
            'milestone': MilestoneShowRenderer,
            'reason': ReasonShowRenderer,
            'user': UserShowRenderer,
            'view': ViewShowRenderer
        }

        renderer_class = renderer_classes[name]
        renderer = renderer_class(self.service, self.commit)
        renderer.render(stream, objects)
