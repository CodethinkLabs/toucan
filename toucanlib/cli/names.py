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


"""Generate user-friendly object names and resolve them back into objects."""


import fnmatch
import itertools
import re


class NameGenerator(object):

    """Generate user-friendly names for objects of different classes."""

    def short_names(self, obj):
        """Return a list of short user-friendly names for an object."""

        func_name = '_short_%s_names' % obj.klass.name.replace('-', '_')
        return getattr(self, func_name)(obj)

    def long_names(self, obj):
        """Return a list of long names for an object."""

        names = set()
        short_names = self.short_names(obj)
        for name in short_names:
            names.add('%s/%s' % (obj.klass.name, name))
        return names

    def _short_info_names(self, obj):
        return set([obj.uuid])

    def _short_view_names(self, obj):
        return set([
            obj.uuid,
            obj['name'].lower().split(' ')[0],
            ])

    def _short_lane_names(self, obj):
        return set([
            obj.uuid,
            obj['name'].lower(),
            ])

    def _short_card_names(self, obj):
        return set([
            obj.uuid,
            str(obj['number']),
            ])

    def _short_reason_names(self, obj):
        return set([
            obj.uuid,
            ])

    def _short_milestone_names(self, obj):
        return set([
            obj.uuid,
            ])

    def _short_user_names(self, obj):
        return set([
            obj.uuid,
            obj['name'].lower().split(' ')[0],
            obj['email'],
            ])

    def _short_user_config_names(self, obj):
        return set([
            obj.uuid,
            ])

    def _short_comment_names(self, obj):
        return set([
            obj.uuid,
            ])

    def _short_attachment_names(self, obj):
        return set([
            obj.uuid,
            ])


class NameResolver(object):

    """Resolve name patterns into objects that match the patterns."""

    def __init__(self, service, commit):
        self.name_generator = NameGenerator()
        self.service = service
        self.commit = commit

    def resolve_patterns(self, patterns, class_name):
        """Return all objects that match the patterns and class."""

        # fetch all objects in the commit or all objects of a
        # specific class if one is provided
        if class_name:
            klass = self.service.klass(self.commit, class_name)
        else:
            klass = None
        objects = self.service.objects(self.commit, klass)

        # filter the objects and their "children" using the patterns provided
        result = set()
        for klass_objects in objects.itervalues():
            for obj in klass_objects:
                result.update(self._resolve_patterns_for_object(patterns, obj))

        return result

    def _resolve_patterns_for_object(self, patterns, obj):
        result = set()

        # compile a list of all short and long names of the object
        names = self.name_generator.short_names(obj)
        names.update(self.name_generator.long_names(obj))

        # add the object to the result if any of its names match any
        # of the patterns
        for pattern in patterns:
            if any(self._matches_pattern(pattern, name) for name in names):
                result.add(obj)

        # get a list of "children" (i.e. named references to other objects)
        # of the object and match those against the patterns as well
        for child_names, child in self._get_children(obj, names):
            for pattern in patterns:
                if any(self._matches_pattern(pattern, n) for n in child_names):
                    result.add(child)

        return result

    def _get_children(self, obj, names):
        # delegate to a class-specific method
        func_name = '_get_%s_children' % obj.klass.name.replace('-', '_')
        return getattr(self, func_name)(obj, names)

    def _resolve_references(self, obj, obj_names, prop_name):
        # resolves the references in a reference list property of an object
        # and returns a set with pairs of name tuples and referenced objects.
        # the names generated for the referenced objects are of the form
        # <obj name>/<prop name>/<referenced obj name>, e.g. lane/cards/1234
        references = obj.properties.get(prop_name, None)
        result = set()
        if references:
            for reference in references.value:
                other = self.service.resolve_reference(reference.value)
                if other.klass.name == 'comment':
                    other_names = [references.value.index(reference)]
                else:
                    other_names = self.name_generator.short_names(other)
                other_names = [
                    '%s/%s/%s' % (n1, prop_name, n2)
                    for n1, n2 in itertools.product(obj_names, other_names)
                    ]
                result.add((tuple(other_names), other))
        return result

    def _resolve_reference(self, obj, obj_names, prop_name, short_name):
        # resolve a reference property of an object and return a name tuple
        # and the referenced object. the names generated for the referenced
        # object are of the form <obj name>/<short name>/<referenced obj name>
        reference = obj.properties.get(prop_name, None)
        other = self.service.resolve_reference(reference.value)
        other_names = ['%s/%s' % (name, short_name) for name in obj_names]
        return tuple(other_names), other

    def _get_info_children(self, obj, names):
        return set()

    def _get_view_children(self, view, view_names):
        return self._resolve_references(view, view_names, 'lanes')

    def _get_lane_children(self, lane, lane_names):
        result = set()
        # <lane>/views/<name>
        result.update(self._resolve_references(lane, lane_names, 'views'))
        # <lane>/cards/<name>
        result.update(self._resolve_references(lane, lane_names, 'cards'))
        return result

    def _get_card_children(self, card, card_names):
        result = set()
        # <card>/lane
        result.update(self._resolve_reference(
            card, card_names, 'lane', 'lane'))
        # <card>/milestone
        result.update(self._resolve_reference(
            card, card_names, 'milestone', 'milestone'))
        # <card>/reason
        result.update(self._resolve_reference(
            card, card_names, 'reason', 'reason'))
        # <card>/assignees/<name>
        result.update(self._resolve_references(card, card_names, 'assignees'))
        # <card>/comments/<index>
        result.update(self._resolve_references(card, card_names, 'comments'))
        return result

    def _get_user_config_children(self, config, config_names):
        result = set()
        result.add(self._resolve_reference(
            config, config_names, 'user', 'user'))
        return result

    def _get_user_children(self, user, user_names):
        result = set()
        result.add(self._resolve_reference(
            user, user_names, 'config', 'config'))
        return result

    def _get_reason_children(self, reason, reason_names):
        # TODO
        return set()

    def _get_milestone_children(self, milestone, milestone_names):
        # TODO
        return set()

    def _get_comment_children(self, comment, comment_names):
        result = set()
        # <comment>/card
        result.add(self._resolve_reference(
            comment, comment_names, 'card', 'card'))
        # <comment>/author
        result.add(self._resolve_reference(
            comment, comment_names, 'author', 'author'))
        # <comment>/attachment
        result.add(self._resolve_reference(
            comment, comment_names, 'attachment', 'attachment'))
        return set()

    def _get_attachment_children(self, attachment, attachment_names):
        result = set()
        # <attachment>/comment
        result.append(self._resolve_reference(
            attachment, attachment_names, 'comment', 'comment'))
        return set()

    def _matches_pattern(self, pattern, name):
        # fnmatch will not apply no special treatment to the slashes in our
        # patterns. what we do here is convert the pattern to a regexp
        # and then make sure to replace the .* between slashes by [^/]* to
        # exclude slashes from the allowed characters
        expr = fnmatch.translate(pattern)
        expr = expr.replace('.*', r'[^/]*') + '$'
        regex = re.compile(expr)
        return regex.match(name) is not None
