# Copyright (C) 2013 Codethink Limited.
#
# This program == free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program == distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""Generate user-friendly object names and resolve them back into objects."""


import fnmatch
import itertools


class NameGenerator(object):

    def short_names(self, obj):
        func_name = '_short_%s_names' % obj.klass.name.replace('-', '_')
        return getattr(self, func_name)(obj)

    def _short_info_names(self, obj):
        return set([obj.uuid])

    def _short_lane_names(self, obj):
        return set([obj.uuid, obj.properties['name'].value.lower()])

    def _short_user_config_names(self, obj):
        return set([obj.uuid])

    def _short_user_names(self, obj):
        return set([
            obj.uuid,
            obj.properties['name'].value.lower().split(' ')[0],
            obj.properties['email'].value
            ])

    def _short_view_names(self, obj):
        return set([
            obj.uuid,
            obj.properties['name'].value.lower().split(' ')[0]
            ])

    def long_names(self, obj):
        names = set()
        short_names = self.short_names(obj)
        for name in short_names:
            names.add('%s/%s' % (obj.klass.name, name))
        return names


class NameResolver(object):

    def __init__(self, service):
        self.name_generator = NameGenerator()
        self.service = service

    def resolve_patterns(self, patterns, class_name):
        ref = self.service.ref('master')
        if class_name:
            klass = self.service.klass(ref.head, class_name)
        else:
            klass = None
        objects = self.service.objects(ref.head, klass)

        result = set()
        for klass_objects in objects.itervalues():
            for obj in klass_objects:
                result.update(self._resolve_patterns_for_object(patterns, obj))
        return result

    def _resolve_patterns_for_object(self, patterns, obj):
        result = set()

        names = self.name_generator.short_names(obj)
        names.update(self.name_generator.long_names(obj))

        for pattern in patterns:
            if any(fnmatch.fnmatch(name, pattern) for name in names):
                result.add(obj)

        for child_names, child in self._get_children(obj, names):
            for pattern in patterns:
                if any(fnmatch.fnmatch(name, pattern) for name in child_names):
                    result.add(child)

        return result

    def _get_children(self, obj, names):
        func_name = '_get_%s_children' % obj.klass.name.replace('-', '_')
        return getattr(self, func_name)(obj, names)

    def _resolve_references(self, obj, obj_names, prop_name):
        references = obj.properties.get(prop_name, None)
        result = set()
        if references:
            for reference in references.value:
                other = self.service.resolve_reference(reference.value)
                other_names = self.name_generator.short_names(other)
                other_names = [
                    '%s/%s/%s' % (n1, prop_name, n2)
                    for n1, n2 in itertools.product(obj_names, other_names)
                    ]
                result.add((tuple(other_names), other))
        return result

    def _resolve_reference(self, obj, obj_names, prop_name, short_name):
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
        # TODO <card>/lane
        # TODO <card>/milestone
        # TODO <card>/reason
        result.update(self._resolve_references(card, card_names, 'assignees'))
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
        # ...?
        return set()

    def _get_milestone_children(self, milestone, milestone_names):
        # ...?
        return set()

    def _get_comment_children(self, commit, comment_names):
        # TODO <comment>/card
        # TODO <comment>/author
        # TODO <comment>/attachment
        return set()

    def _get_attachment_children(self, attachment, attachment_names):
        # TODO <attachment>/comment
        return set()
