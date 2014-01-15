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
    
    def renderlines(self, stream, lines):
        """Render the formatted lines generated about the object."""
        
        for line in lines:
            stream.write('%s\n' % line)

    def _list_cards(self, cards, lines):
        """Add a formatted list of cards to a given list of lines."""
        
        for card in cards:
            # format some strings
            card_number = str(card.properties['number'].value)
            card_number.ljust(n_length)
            card_title = card.properties['title'].value
            
            # calculate the amount that each line of the card title
            # will need to be indented, and use that to decide how
            # many characters should be on each line
            offset = 80 - (11 + n_length)
            startchar = 0
            endchar = offset
            
            lines.append(' - card/%s # %s' % (card_number,
                                    card_title[startchar:endchar]))
            
            # move character pointers
            startchar += offset
            endchar += offset
            
            # while the end of the string hasn't been reached
            while endchar < len(card_title):
                # format string
                line = '# %s' % (card_title[startchar:endchar])
                # append line with indentation
                lines.append(line.rjust(80))
                # move the character pointers
                startchar += offset
                endchar += offset

    def _list_views(self, views, lines, name_length):
        """Add a formatted list of views to a given list of lines."""
        
        for view in views:
            # add the line
            lines.append('  - ' + self._get_view(view, name_length))

    def _list_lanes(self, lanes, lines, name_length):
        """Add a formatted list of lanes to a given list of lines."""

        for lane in lanes:
            # add the line
            lines.append('  - ' + self._get_lane(lane, name_length))

    def _list_comments(self, comments, lines, n_length):
        for comment in comments:
            format_string = '  - comment/%s # %s <%s>'
            
            # get required information
            comment_ID = str(comment.properties['number'].value).ljust(n_length)
            comment_content = comment.properties['comment'].value
            user_ref = comment.properties['user'].value
            user = self.service.resolve_reference(user_ref)
            user_name = user.properties['name'].value
            user_email = user.properties['email'].value
            
            # format first line
            lines.append(format_string % comment_ID, user_name, user_email)
            
            # calculate the amount that each line of the comment
            # will need to be indented, and use that to decide how
            # many characters should be on each line
            offset = 80 - (15 + n_length)
            startchar = 0
            endchar = offset
            
            # while the end of the string hasn't been reached
            while endchar < len(comment_content):
                # format string
                line = '# %s' % (comment_content[startchar:endchar])
                # append line with indentation
                lines.append(line.rjust(80))
                # move the character pointers
                startchar += offset
                endchar += offset
    
    def _list_assignees(self, assignees, lines, name_length):
        """Add a formatted list of assignees to a given list of lines."""
        
        for user in assignees:
            # add the line
            lines.append('  - ' + self._get_user(user, name_length))
    
    def _get_user(self, user, name_length=None):
        """Return a string of the format:
                user/[firstname] # [name] <email>
           
           Params:
                user: A user object."""
        
        # get required information
        user_name = user.properties['name'].value
        user_email = user.properties['email'].value
        if name_length:
            user_ID = user_name.split()[0].lower().ljust(name_length)
        else:
            user_ID = user_name.split()[0].lower()
        
        # return the formatted string
        return 'user/%s # %s <%s>' % (user_ID, user_name, user_email)
    
    def _get_lane(self, lane, name_length):
        """Return a string of the format:
                lane/[name] # [name], [number of cards]
           
           Params:
                lane: A lane object."""
        
        # get the required information
        lane_ID = lane.properties['name'].value
        lane_name = (lane_ID + ',').ljust(name_length + 1)
        lane_ID = lane_ID.ljust(name_length)
        if 'cards' in lane.properties:
            cards = str(len(lane.properties['cards'])) + ' cards'
        else:
            cards = '0 cards'
        
        # return the formatted string
        return 'lane/%s # %s %s' % (lane_ID.lower(), lane_name, cards)
    
    def _get_view(self, view, name_length=None):
        """Return a string of the format:
                view/[name] # [name]
           
           Params:
                view: A view object.
                name_length: The length to make [name]."""
        
        if name_length:
            # Standardise the name length by adding whitespace to the
            # end of each name shorter than the longest one.
            view_name = view.properties['name'].value.ljust(name_length)
        else:
            view_name = view.properties['name'].value
        
        # return the formatted string
        return 'view/%s # %s' % (view_name.lower(), view_name)
    
    def _get_milestone(self, milestone):
        
        # initial output
        line = 'milestone/%s # %s, %s'
        
        # get required info
        m_name = milestone.properties['name'].value
        m_date = milestone.properties['deadline'].value
        return line % (m_name.lower(), m_name, m_date)
    
    def _get_reason(self, reason):
        """Return a string of the format:
                reason/[name] # [description]"""
                
        # get required information
        reason_name = reason.properties['name'].value
        if 'description' in reason.properties:
            reason_descr = reason.properties['description'].value
        else:
            reason_descr = ''

        # return the formatted string
        return 'reason/%s # %s' % (reason_name.lower(), reason_descr)
    
    def _resolve_references(self, refs, objects, prop=''):
        """Populate `objects` with objects resolved from items in `refs`.
           Return the length of the longest property of a certain type. This
           function does the length checks to avoid needing an extra loop
           through the objects.
           
           Params:
                refs: A list of reference objects.
                objects: A list in which to store the objects resolved from
                         refs.
                prop: The property to get the length of."""
        
        length = 0
        for ref in refs:
            obj = self.service.resolve_reference(ref.value)
            objects.append(obj)
            if (prop != ''):
                length = max(len(objects[-1].properties[prop].value), length)
    
        return length

class InfoShowRenderer(ObjectClassShowRenderer):

    """Render information about the board in general."""
    
    def __init__(self, service):
        self.service = service
    
    def render(self, stream, objects):
        """Render information about the board to a text stream."""
        
        lines = []
        
        for obj in objects:
            # first, render the name of the board
            lines.append('name: %s' % obj.properties['name'].value)
            
            # next, render the description
            lines.append('description: >')
            lines.append('  %s' % (obj.properties['description'].value))
            
            # finally, render the views
            if 'views' in obj.properties:
                lines.append('views:')
                views = []
                name_length = self._resolve_references(
                                obj.properties['views'].value, views, 'name')
                self._list_views(views, lines, name_length)
            
            # add separator
            lines.append('---')
        
        self.renderlines(stream, lines)

class AttachmentShowRenderer(ObjectClassShowRenderer):

    """Render information about an attachment."""
    
    def __init__(self, service):
        self.service = service

    def render(self, stream, objects):
        """Render information about one or more attachments to a text
           stream."""
        
        lines = []
        
        for obj in objects:
            # first, render the name of the attachment (usually a filename)
            lines.append('name: %s' % (obj.properties['name'].value))
            
            # next, render the data content type
            lines.append('data: %s' % (obj.properties['content-type']))
            
            # finally, render the comment that has the attachment
            lines.append('comment:')
            comments = []
            n_length = self._resolve_references(
                            obj.properties['comments'].value, comments, 'number')
            self._list_comments(comments, lines, n_length)
            
            # add separator
            lines.append('---')

        self.renderlines(stream, lines)

class ViewShowRenderer(ObjectClassShowRenderer):
    
    """Render information about a view."""
    
    def __init__(self, service):
        self.service = service

    def render(self, stream, objects):
        """Render information about view objects to a text stream."""
        
        lines = []
        
        for obj in objects:
            # first, render the name of the view
            lines.append('name: %s' % (obj.properties['name'].value))
            
            # next, render the description
            lines.append('description: >')
            lines.append('  %s' % (obj.properties['description'].value))
            
            # next, render the lanes
            lines.append('lanes:')
            
            # resolve the lane references
            lanes = []
            name_length = self._resolve_references(
                            obj.properties['lanes'].value, lanes, 'name')
            
            # add the lanes
            self._list_lanes(lanes, lines, name_length)
            
            # add separator
            lines.append('---')

        self.renderlines(stream, lines)

class LaneShowRenderer(ObjectClassShowRenderer):

    """Render information about a lane."""
    
    def __init__(self, service):
        self.service = service

    def render(self, stream, objects):
        """Render information about lane objects to a text stream."""
        
        lines = []
        
        for obj in objects:
            # first, render the name
            lines.append('name: %s' % (obj.properties['name'].value))
            
            # next, render the description
            lines.append('description: >')
            lines.append('  %s' % (obj.properties['description'].value))
            
            # now render the views
            lines.append('views:')
            
            # resolve the references into view objects
            views = []
            name_length = self._resolve_references(
                            obj.properties['views'].value, views, 'name')
            
            # add lines representing the views
            self._list_views(views, lines, name_length)

            # finally, render the cards
            if 'cards' in obj.properties:
                lines.append('cards:')
                
                # resolve card references
                cards = []
                n_length = self._resolve_references(
                            obj.properties['cards'].value, cards, 'number')
                
                self._list_cards(cards, lines, n_length)
            
            # add separator
            lines.append('---')

        self.renderlines(stream, lines)

class CardShowRenderer(ObjectClassShowRenderer):

    """Render information about a card."""
    
    def __init__(self, service):
        self.service = service

    def render(self, stream, objects):
        """Render information about cards to a text stream."""
        
        lines = []
        
        for obj in objects:
            # first, render the number
            lines.append('number: %s' % (obj.properties['number'].value))
            
            # next, render the name
            lines.append('name: %s' % (obj.properties['name'].value))
            
            # next, render the description
            lines.append('description: >')
            lines.append('  %s' % (obj.properties['description'].value))
            
            # now the lane which contains the card
            lane = []
            length = self._resolve_references(obj.properties['lane'].value, lane)
            lines.append('lane: ' + _get_lane(lane[0], length))
            
            # now the milestone
            if 'milestone' in obj.properties:
                milestone = self.service.resolve_reference(
                                            obj.properties['milestone'].value)
                lines.append('milestone: ' + self._get_milestone(milestone))
            
            # now the reason
            reason = self.service.resolve_reference(
                                            obj.properties['reason'].value)
            lines.append('reason: ' + self._get_reason(reason))
            
            # now the creator
            user = self.service.resolve_reference(
                             obj.properties['creator'].value)
            length = len(user.properties['name'].value)
            lines.append('creator: ' + self._get_user(user, length))
            
            # penultimately, the assignees
            assignees = []
            self._resolve_references(
                            obj.properties['assignees'].value, assignees)
            # get longest first name, functionality for this is not provided
            # by self._resolve_references, so take the inefficient road.
            name_length = 0
            for user in assignees:
                name_length = max(len(
                            user.properties['name'].value.split()[0]), length)
            
            # add the assignees list
            self._list_assignees(assignees, lines, name_length)
            
            # finally, render the comments
            comments = []
            n_length = self._resolve_references(
                            obj.properties['comments'].value, comments, 'number')
            
            # add the comments list
            self._list_comments(comments, lines, n_length)
            
            # add separator
            lines.append('---')

        self.renderlines(stream, lines)

class MilestoneShowRenderer(ObjectClassShowRenderer):
    
    """Render information about a milestone."""
    
    def __init__(self, service):
        self.service = service
    
    def render(self, stream, objects):
        """Render information about milestones to a text stream."""
        
        lines = []
        
        for obj in objects:
            # first, render the name
            lines.append('name: %s' % obj.properties['name'].value)
            
            # next, render the description
            lines.append('description: >')
            lines.append('  %s' % (obj.properties['description'].value))
            
            # next, the deadline (yyyy-mm-dd)
            d = obj.properties['deadline'].value.value.value.date().isoformat()
            lines.append('deadline: %s' % (d))
            
            # finally the cards
            if 'cards' in obj.properties:
                cards = []
                n_length = self._resolve_references(
                                obj.properties['cards'].value, cards, 'number')
                
                self._list_cards(cards, lines, n_length)
            
            # add separator
            lines.append('---')

        self.renderlines(stream, lines)

class ReasonShowRenderer(ObjectClassShowRenderer):

    """Render information about a reason."""
    
    def __init__(self, service):
        self.service = service
    
    def render(self, stream, objects):
        """Render information about reasons to a text stream."""
        
        lines = []
        
        for obj in objects:
            # first, render the name
            lines.append('name: %s' % obj.properties['name'].value)
            
            # next, render the description
            lines.append('description: >')
            lines.append('  %s' % (obj.properties['description'].value))
            
            # next, the work items
            if 'work-items' in obj.properties:
                # the method of displaying these is not yet decided upon,
                # as they are references to a remote store (NYI)
                pass
            
            # finally, the cards associated with the reason
            if 'cards' in obj.properties:
                cards = []
                n_length = self._resolve_references(
                                obj.properties['cards'].value, cards, 'number')
                
                self._list_cards(cards, lines, n_length)
            
            # add separator
            lines.append('---')

        self.renderlines(stream, lines)

class UserShowRenderer(ObjectClassShowRenderer):

    """Render information about users."""
    
    def __init__(self, service):
        self.service = service
    
    def render(self, stream, objects):
        """Render inormation about users to a text stream."""
        
        lines = []
        for obj in objects:
            # first render the name
            lines.append('name %s' % (obj.properties['name'].value))
            
            # next, the email address
            lines.append('email: %s' % (obj.properties['email'].value))
            
            # next, the roles
            lines.append('roles:')
            roles = obj.properties['roles'].value
            for role in roles:
                lines.append('  - %s' % (role.value))
            
            # next the avatar url
            if 'avatar' in obj.properties:
                lines.append('avatar: %s' % (obj.properties['avatar'].value))
            
            # finally, the default-view
            if 'default-view' in obj.properties:
                view = self.service.resolve_reference(
                                obj.properties['default-view'].value)
                lines.append('default-view: ' + self._get_view(view))
            
            # add separator
            lines.append('---')

        self.renderlines(stream, lines)

class ShowRenderer(object):

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
    
    def _render_attachment_group(self, stream, objects):
        return AttachmentShowRenderer(self.service).render(stream, objects)
    
    def _render_card_group(self, stream, objects):
        return CardShowRenderer(self.service).render(stream, objects)
    
    def _render_info_group(self, stream, objects):
        return InfoShowRenderer(self.service).render(stream, objects)

    def _render_lane_group(self, stream, objects):
        return LaneShowRenderer(self.service).render(stream, objects)
    
    def _render_milestone_group(self, stream, objects):
        return MilestoneShowRenderer(self.service).render(stream, objects)
    
    def _render_reason_group(self, stream, objects):
        return ReasonShowRenderer(self.service).render(stream, objects)
    
    def _render_view_group(self, stream, objects):
        return ViewShowRenderer(self.service).render(stream, objects)

    def _render_user_group(self, stream, objects):
        return UserShowRenderer(self.service).render(stream, objects)
