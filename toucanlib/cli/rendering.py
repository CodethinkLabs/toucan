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

"""Render objects to the command line."""

import consonant
import textwrap

import toucanlib


class ObjectClassListRenderer(object):

    """Render the objects of a class to a text stream."""

    def __init__(self, service):
        """Initialise an ObjectClassListRenderer."""
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
            rows.append(('info', info['name'], info['description'].strip()))
        self.render_rows(stream, rows)


class ViewListRenderer(ObjectClassListRenderer):

    """Render lists of view objects to a text stream."""

    def render(self, stream, views):
        """Render a list of views to a text stream."""
        rows = []
        for view in sorted(views, key=lambda view: view['name']):
            if 'lanes' in view:
                num_lanes = len(view['lanes'])
            else:
                num_lanes = 0
            rows.append(('view', view['name'], view['description'].strip(),
                         '%d lanes' % num_lanes))
        self.render_rows(stream, rows)


class LaneListRenderer(ObjectClassListRenderer):

    """Render lists of lane objects to a text stream."""

    def render(self, stream, lanes):
        """Render a list of lanes to a text stream."""
        rows = []
        for lane in sorted(lanes, key=lambda lane: lane['name']):
            if 'cards' in lane:
                num_cards = len(lane['cards'])
            else:
                num_cards = 0
            rows.append(('lane', lane['name'], lane['description'].strip(),
                         '%d cards' % num_cards))
        self.render_rows(stream, rows)


class UserListRenderer(ObjectClassListRenderer):

    """Render lists of user objects to a text stream."""

    def render(self, stream, users):
        """Render a list of users to a text stream."""
        rows = []
        for user in sorted(users, key=lambda user: user['name']):
            roles = [role.value for role in user['roles']]
            rows.append(('user', user['name'], user['email'], ','.join(roles)))
        self.render_rows(stream, rows)


class UserConfigListRenderer(ObjectClassListRenderer):

    """Render lists of user config objects to a text stream."""

    def render(self, stream, configs):
        """Render a list of user configs to a text stream."""
        rows = []
        for config in sorted(configs, key=self._sort_key):
            user = self.service.resolve_reference(config['user'])
            if 'default-view' in config:
                default_view = config['default-view']
            else:
                default_view = ''
            rows.append(('user-config', user['name'], default_view))
        self.render_rows(stream, rows)

    def _sort_key(self, config):
        user = self.service.resolve_reference(config['user'])
        return user['name']


class ListRenderer(object):

    """Render lists of objects to a text stream."""

    def __init__(self, service):
        """Initialise a ListRenderer."""
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
        """Initialise an ObjectClassShowRenderer."""
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
            # format card name
            card_name = self.name_generator.presentable_name(card).ljust(12)

            # wrap the card title
            indent = 17
            wrapper = textwrap.TextWrapper(
                initial_indent='  - %s # ' % card_name,
                subsequent_indent=(' ' * indent) + '# ',
                width=80)
            lines += wrapper.wrap(card['title'])

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
            number = self.name_generator.presentable_name(comment).ljust(13)
            user = self.service.resolve_reference(comment['author'])

            # format first line
            format_string = '  - %s # %s <%s>'
            lines.append(format_string % (number, user['name'], user['email']))

            # wrap the comment
            indent = 20
            wrapper = textwrap.TextWrapper(
                initial_indent=(' ' * indent) + '# ',
                subsequent_indent=(' ' * indent) + '# ',
                width=80)
            lines += wrapper.wrap(comment['comment'])

    def _list_assignees(self, assignees, lines, name_length):
        """Add a formatted list of assignees to a given list of lines."""
        for user in assignees:
            lines.append('  - ' + self._get_user(user, name_length))

    def _get_user(self, user, name_length=None):
        """Get formatted string of user information.

        Return a string of the format:
                user/[firstname] # [name] <email>

        """
        user_id = self.name_generator.presentable_name(user)
        if name_length:
            user_id = user_id.ljust(name_length + 5)
        return '%s # %s <%s>' % (user_id, user['name'], user['email'])

    def _get_lane(self, lane, name_length=None):
        """Get formatted string of lane information.

        Returns a string of the format:
                lane/[name] # [name], [number of cards]

        """
        lane_id = self.name_generator.presentable_name(lane)
        lane_name = ('%s,' % lane['name'])
        if name_length:
            lane_name = lane['name'].ljust(name_length + 1)
            lane_id = lane_id.ljust(name_length + 5)
        if 'cards' in lane:
            cards = '%d cards' % len(lane['cards'])
        else:
            cards = '0 cards'
        return '%s # %s %s' % (lane_id, lane_name, cards)

    def _get_view(self, view, name_length=None):
        """Get formatted string of view information.

        Return a string of the format:
                view/[name] # [name]

        """
        short_name = self.name_generator.presentable_name(view)
        if name_length:
            short_name = short_name.ljust(name_length + 5)
        return '%s # %s' % (short_name, view['name'])

    def _get_milestone(self, milestone):
        """Get formatted string of milestone information.

        Return a string of the format:
                milestone/[name] # [name] [deadline]

        """
        short_name = self.name_generator.presentable_name(milestone)
        date = milestone['deadline'].value.date().isoformat()
        return '%s # %s, %s' % (short_name, milestone['name'], date)

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
        """Initialise an InfoShowRenderer."""
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
            view_class = self.service.klass(self.commit, 'view')
            views = self.service.objects(self.commit, view_class)
            length = max(len(v['name']) for v in views)

            lines.append('views:')
            self._list_views(views, lines, length)

            # add separator
            lines.append('---')

        self.render_lines(stream, lines)


class AttachmentShowRenderer(ObjectClassShowRenderer):

    """Render information about an attachment."""

    def __init__(self, service, commit):
        """Initialise an AttachmentShowRenderer."""
        self.service = service
        self.commit = commit
        self.name_generator = toucanlib.cli.names.NameGenerator()

    def render(self, stream, objects):
        """Render information about attachments to a text stream."""
        lines = []

        for obj in objects:
            # first, render the name of the attachment (usually a filename)
            lines.append('name: %s' % (obj['name']))

            # get required information
            comment = self.service.resolve_reference(obj['comment'])
            number = self.name_generator.presentable_name(comment).ljust(13)
            user = self.service.resolve_reference(comment['author'])

            # format comment
            format_string = 'comment: %s # %s <%s>'
            lines.append(format_string % (number, user['name'], user['email']))
            # wrap the comment
            indent = 20
            wrapper = textwrap.TextWrapper(
                initial_indent=(' ' * indent) + '# ',
                subsequent_indent=(' ' * indent) + '# ',
                width=80)
            lines += wrapper.wrap(comment['comment'])

            # add separator
            lines.append('---')

        self.render_lines(stream, lines)


class ViewShowRenderer(ObjectClassShowRenderer):

    """Render information about a view."""

    def __init__(self, service, commit):
        """Initialise a ViewShowRenderer."""
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
        """Initialise a LaneShowRenderer."""
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
        """Initialise a CardShowRenderer."""
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
            _, comments = self._resolve_references(obj['comments'])

            # add the comments list
            self._list_comments(comments, lines)


class MilestoneShowRenderer(ObjectClassShowRenderer):

    """Render information about a milestone."""

    def __init__(self, service, commit):
        """Initialise a MilestoneShowRenderer."""
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
            date = obj['deadline'].value.date().isoformat()
            lines.append('deadline: %s' % date)

            # finally the cards
            card_class = self.service.klass(self.commit, 'card')
            all_cards = self.service.objects(self.commit, card_class)
            cards = []
            for card in all_cards:
                if card.get('milestone', ''):
                    ref_obj = self.service.resolve_reference(card['milestone'])
                    if ref_obj['short-name'] == obj['short-name']:
                        cards.append(card)
            if cards:
                lines.append('cards:')
                self._list_cards(cards, lines)

            # add separator
            lines.append('---')

        self.render_lines(stream, lines)


class ReasonShowRenderer(ObjectClassShowRenderer):

    """Render information about a reason."""

    def __init__(self, service, commit):
        """Initialise a ReasonShowRenderer."""
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
            card_class = self.service.klass(self.commit, 'card')
            all_cards = self.service.objects(self.commit, card_class)
            cards = []
            for card in all_cards:
                card_reason = self.service.resolve_reference(card['reason'])
                if card_reason['short-name'] == obj['short-name']:
                    cards.append(card)
            if cards:
                lines.append('cards:')
                self._list_cards(cards, lines)

            # add separator
            lines.append('---')

        self.render_lines(stream, lines)


class UserShowRenderer(ObjectClassShowRenderer):

    """Render information about users."""

    def __init__(self, service, commit):
        """Initialise a UserShowRenderer."""
        self.service = service
        self.commit = commit
        self.name_generator = toucanlib.cli.names.NameGenerator()

    def render(self, stream, objects):
        """Render inormation about users to a text stream."""
        lines = []
        for obj in objects:
            # first render the name
            lines.append('name: %s' % obj['name'])

            # next, the email address
            lines.append('email: %s' % obj['email'])

            # next, the roles
            lines.append('roles:')
            for role in obj['roles']:
                lines.append('  - %s' % role.value)

            # next the avatar url
            if 'avatar' in obj:
                lines.append('avatar: %s' % obj['avatar'])

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
        """Initialise a CommentShowRenderer."""
        self.service = service
        self.commit = commit
        self.name_generator = toucanlib.cli.names.NameGenerator()

    def render(self, stream, objects):
        """Render comments to a text stream."""
        lines = []
        for obj in objects:
            # first, render the number
            comment_number = self.name_generator.comment_id(obj)
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
        """Initialise a ShowRenderer."""
        self.service = service
        self.commit = commit

    def render(self, stream, objects):
        """Render a list of objects to a text stream."""
        groups = self._group_objects(objects)
        for name in sorted(groups.iterkeys()):
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


class TemplateRenderer(object):

    """Render an object template to a text stream."""

    def __init__(self, service):
        """Initialise a TemplateRenderer."""
        self.service = service

    def render(self, stream, klass, data={}):
        """Render a template to a stream."""
        templates = {
            'attachment': self._attachment_template,
            'card': self._card_template,
            'comment': self._comment_template,
            'lane': self._lane_template,
            'milestone': self._milestone_template,
            'reason': self._reason_template,
            'user': self._user_template,
            'view': self._view_template
        }

        template = templates[klass]
        lines = template(data)
        lines.append(
            '# To cancel this action, remove all content from this file')
        for line in lines:
            stream.write(line + '\n')

    def _attachment_template(self):
        raise NotImplementedError

    def _card_template(self, data):
        lines = []
        lines.append('title: %s # required' % data.get('title', ''))
        lines.append('description: >\n  %s' % data.get('description', ''))
        lines.append('creator: %s # required' % data.get('creator', ''))
        lines.append('lane: %s # required' % data.get('lane', ''))
        lines.append('reason: %s # required' % data.get('reason', ''))
        lines.append('milestone: %s' % data.get('milestone', ''))
        if not len(data.get('assignees', [])):
            lines.append('assignees:\n  - ')
        else:
            lines.append('assignees:')
        for assignee in data.get('assignees', []):
            lines.append('  - %s' % assignee)
        return lines

    def _comment_template(self, data):
        lines = []
        lines.append('card: %s # required - the short uuid of the card '
                     'that you are commenting on' % data.get('card', ''))
        lines.append('author: %s # required' % data.get('author', ''))
        lines.append('comment: >\n  %s # required' % data.get('comment', ''))
        return lines

    def _lane_template(self, data):
        lines = []
        lines.append('name: %s # required' % data.get('name', ''))
        lines.append('description: >\n  %s' % data.get('description', ''))
        if not len(data.get('views', [])):
            lines.append('views:\n  -  # required')
        else:
            lines.append('views:')
        for view in data.get('views', []):
            lines.append('  - %s # required' % view)
        if not len(data.get('cards', [])):
            lines.append('cards:\n  - ')
        else:
            lines.append('cards:')
        for card in data.get('cards', []):
            lines.append('  - %s' % card)
        return lines

    def _milestone_template(self, data):
        lines = []
        lines.append('short-name: %s # required' % data.get('short-name', ''))
        lines.append('name: %s # required' % data.get('name', ''))
        lines.append('description: >\n  %s' % data.get('description', ''))
        lines.append(
            'deadline: %s # required - YYYY-MM-DD' % data.get('deadline', ''))
        return lines

    def _reason_template(self, data):
        lines = []
        lines.append('short-name: %s # required' % data.get('short-name', ''))
        lines.append('name: %s # required' % data.get('name', ''))
        lines.append('description: >\n  %s' % data.get('description', ''))
        return lines

    def _user_template(self, data):
        lines = []
        lines.append('name: %s # required' % data.get('name', ''))
        lines.append('email: %s # required' % data.get('email', ''))
        if not len(data.get('roles', [])):
            lines.append('roles:\n  -  # required')
        else:
            lines.append('roles:')
        for role in data.get('roles', []):
            lines.append('  - %s # required' % role)
        lines.append('default-view: %s' % data.get('default-view', ''))
        lines.append('avatar: %s' % data.get('avatar', ''))
        return lines

    def _view_template(self, data):
        lines = []
        lines.append('name: %s # required' % data.get('name', ''))
        lines.append('description: >\n  %s' % data.get('name', ''))
        if not len(data.get('lanes', [])):
            lines.append('lanes:\n  -  # required')
        else:
            lines.append('lanes:')
        for lane in data.get('lanes', []):
            lines.append('  - %s # required' % lane)
        return lines
