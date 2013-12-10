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
        print 'resolve patterns for object %s (%s)' % (obj, obj.klass.name)

        result = set()

        names = self.name_generator.short_names(obj)
        names.update(self.name_generator.long_names(obj))

        print '    names: %s' % ', '.join(sorted(names, key=len))

        for pattern in patterns:
            if any(fnmatch.fnmatch(name, pattern) for name in names):
                print '    OK'
                result.add(obj)

        for child_names, child in self._get_children(obj, names):
            print '    child %s (%s)' % (child, child.klass.name)
            print '        names: %s' % \
                ', '.join(sorted(child_names, key=len))
            for pattern in patterns:
                if any(fnmatch.fnmatch(name, pattern) for name in child_names):
                    result.add(child)

        print

        return result

    def _get_children(self, obj, names):
        func_name = '_get_%s_children' % obj.klass.name.replace('-', '_')
        return getattr(self, func_name)(obj, names)

    def _get_info_children(self, obj, names):
        return []

    def _get_view_children(self, view, view_names):
        # add lanes in the view
        references = view.properties.get('lanes', None)
        if references:
            for reference in references.value:
                 lane = self.service.resolve_reference(reference.value)
                 lane_names = self.name_generator.short_names(lane)
                 child_names = [
                    '%s/lanes/%s' % (v, l)
                    for v, l in itertools.product(view_names, lane_names)
                    ]
                 yield child_names, lane

    def _get_lane_children(self, lane, lane_names):
        # add views for the lane
        references = lane.properties.get('views', None)
        if references:
            for reference in references.value:
                view = self.service.resolve_reference(reference.value)
                view_names = self.name_generator.short_names(view)
                child_names = [
                    '%s/views/%s' % (l, v)
                    for l, v in itertools.product(lane_names, view_names)
                    ]
                yield child_names, view

        # add cards in the lane
        references = lane.properties.get('cards', None)
        if references:
            for reference in references.value:
                card = self.service.resolve_reference(reference.value)
                card_names = self.name_generator.short_names(card)
                child_names = [
                    '%s/cards/%s' % (l, c)
                    for l, c in itertools.product(lane_names, card_names)
                    ]
                yield child_names, card

    def _get_card_children(self, card, card_names):
        # <card>/lane
        # <card>/milestone
        # <card>/reason
        # <card>/assignees/<name>
        # <card>/comments/<index>
        pass

    def _get_user_config_children(self, config, config_names):
        # <config>/user
        return []

    def _get_user_children(self, user, user_names):
        # <user>/config
        return []

    def _get_reason_children(self, reason, reason_names):
        # ...?
        return []

    def _get_milestone_children(self, milestone, milestone_names):
        # ...?
        return []

    def _get_comment_children(self, commit, comment_names):
        # <comment>/card
        # <comment>/author
        # <comment>/attachment
        return []

    def _get_attachment_children(self, attachment, attachment_names):
        # <attachment>/comment
        return []
