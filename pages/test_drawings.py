import uuid
from unittest import mock

from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase

from workspaces.tests import make_workspace_with_roles

from .models import Drawing, Page, Stroke
from .tests import doc

PTS = [[10, 20, 50], [11, 22, 60]]


def block(drawing_id):
    return {'type': 'drawing', 'attrs': {'id': drawing_id}}


class DrawingApiTests(APITestCase):
    def setUp(self):
        self.ws, self.u = make_workspace_with_roles('Acme')
        self.other_ws, self.other_u = make_workspace_with_roles('Beta')
        self.page = Page.objects.create(workspace=self.ws, name='P')
        self.drawing = Drawing.objects.create(page=self.page)
        self.url = f'/api/drawings/{self.drawing.id}/'

    def as_(self, label):
        self.client.force_authenticate(self.u[label])

    def stroke(self, points=PTS, uid=None, url=None):
        return self.client.post((url or self.url) + 'strokes/', {'uid': str(uid or uuid.uuid4()), 'points': points}, format='json')

    def test_create_roles(self):
        for label, expected in [('owner', 201), ('admin', 201), ('editor', 201), ('viewer', 403), ('outsider', 400)]:
            self.as_(label)
            self.assertEqual(self.client.post('/api/drawings/', {'page': self.page.id}).status_code, expected, label)

    def test_cannot_create_on_another_workspaces_page(self):
        self.client.force_authenticate(self.other_u['owner'])
        self.assertEqual(self.client.post('/api/drawings/', {'page': self.page.id}).status_code, 400)

    def test_read_members_only_with_strokes_in_order(self):
        first, second = uuid.uuid4(), uuid.uuid4()
        self.drawing.strokes.create(uid=first, points=PTS)
        self.drawing.strokes.create(uid=second, points=PTS)
        for label in ('owner', 'admin', 'editor', 'viewer'):
            self.as_(label)
            r = self.client.get(self.url)
            self.assertEqual(r.status_code, 200, label)
            self.assertEqual([s['uid'] for s in r.data['strokes']], [str(first), str(second)])
        self.as_('outsider')
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_reading_does_not_query_per_stroke(self):
        self.as_('viewer')
        counts = []
        for _ in range(2):
            with CaptureQueriesContext(connection) as q:
                self.client.get(self.url)
            counts.append(len(q))
            Stroke.objects.bulk_create(Stroke(drawing=self.drawing, uid=uuid.uuid4(), points=PTS) for _ in range(20))
        self.assertEqual(counts[0], counts[1])

    def test_add_stroke_roles(self):
        for label, expected in [('owner', 201), ('admin', 201), ('editor', 201), ('viewer', 403), ('outsider', 404)]:
            self.as_(label)
            self.assertEqual(self.stroke().status_code, expected, label)
        self.assertEqual(self.drawing.strokes.count(), 3)

    def test_stroke_is_stored_with_its_author(self):
        self.as_('editor')
        self.stroke()
        self.assertEqual(self.drawing.strokes.get().created_by, self.u['editor'])
        self.assertEqual(self.drawing.strokes.get().points, PTS)

    def test_retried_save_does_not_draw_twice(self):
        self.as_('editor')
        uid = uuid.uuid4()
        self.assertEqual(self.stroke(uid=uid).status_code, 201)
        self.assertEqual(self.stroke([[1, 1, 1]], uid=uid).status_code, 200)
        self.assertEqual(list(self.drawing.strokes.values_list('points', flat=True)), [PTS])  # first write wins

    def test_rejects_bad_strokes(self):
        self.as_('editor')
        bad = {
            'no points': [], 'not a list': 'x', 'float': [[1.5, 2, 3]], 'bool': [[True, 2, 3]], 'string': [[1, 2, '3']],
            'negative': [[-1, 2, 3]], 'too far': [[10_001, 2, 3]], 'pressure over 100': [[1, 2, 101]],
            'two numbers': [[1, 2]], 'four numbers': [[1, 2, 3, 4]], 'point not a list': [5], 'too many': [[1, 2, 3]] * 2001,
        }
        for why, points in bad.items():
            self.assertEqual(self.stroke(points).status_code, 400, why)
        self.assertEqual(self.client.post(self.url + 'strokes/', {'uid': 'nope', 'points': PTS}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url + 'strokes/', {'points': PTS}, format='json').status_code, 400)
        self.assertEqual(self.drawing.strokes.count(), 0)

    def test_stroke_and_drawing_limits(self):
        self.as_('editor')
        with mock.patch('pages.views.MAX_STROKES', 2):
            self.assertEqual([self.stroke().status_code for _ in range(3)], [201, 201, 400])
        with mock.patch('pages.serializers.MAX_DRAWINGS', 1):
            self.assertEqual(self.client.post('/api/drawings/', {'page': self.page.id}).status_code, 400)

    def test_undo_roles_and_repeat(self):
        uid = uuid.uuid4()
        self.drawing.strokes.create(uid=uid, points=PTS)
        url = f'{self.url}strokes/{uid}/'
        for label, expected in [('viewer', 403), ('outsider', 404)]:
            self.as_(label)
            self.assertEqual(self.client.delete(url).status_code, expected, label)
        self.as_('editor')
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.delete(url).status_code, 404)

    def test_undo_only_touches_the_drawing_in_the_url(self):
        uid = uuid.uuid4()
        mine = Drawing.objects.create(page=self.page)
        mine.strokes.create(uid=uid, points=PTS)
        theirs_page = Page.objects.create(workspace=self.other_ws, name='T')
        theirs = Drawing.objects.create(page=theirs_page)
        theirs.strokes.create(uid=uid, points=PTS)  # same uid, other workspace
        self.as_('editor')
        self.assertEqual(self.client.delete(f'{self.url}strokes/{uid}/').status_code, 404)  # not in this drawing
        self.assertEqual(self.client.delete(f'/api/drawings/{theirs.id}/strokes/{uid}/').status_code, 404)  # not mine
        self.assertEqual((mine.strokes.count(), theirs.strokes.count()), (1, 1))

    def test_deleting_the_page_deletes_its_drawings(self):
        self.drawing.strokes.create(uid=uuid.uuid4(), points=PTS)
        self.page.delete()
        self.assertEqual((Drawing.objects.count(), Stroke.objects.count()), (0, 0))


class DrawingBlockTests(APITestCase):
    """The drawing node inside Page.content."""

    def setUp(self):
        self.ws, self.u = make_workspace_with_roles('Acme')
        self.page = Page.objects.create(workspace=self.ws, name='P')
        self.mine = Drawing.objects.create(page=self.page)
        self.url = f'/api/pages/{self.page.id}/'
        self.client.force_authenticate(self.u['editor'])

    def save(self, *blocks):
        return self.client.patch(self.url, {'content': doc('T', *blocks)}, format='json')

    def test_a_page_can_hold_several_drawing_blocks(self):
        second = Drawing.objects.create(page=self.page)
        r = self.save(block(self.mine.id), block(second.id))
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['text'].strip(), '')  # blocks add no text

    def test_rejects_a_drawing_from_another_page_or_workspace(self):
        same_ws = Drawing.objects.create(page=Page.objects.create(workspace=self.ws, name='Q'))
        other_ws, _ = make_workspace_with_roles('Beta')
        foreign = Drawing.objects.create(page=Page.objects.create(workspace=other_ws, name='R'))
        for why, drawing in [('same workspace', same_ws), ('other workspace', foreign)]:
            self.assertEqual(self.save(block(drawing.id)).status_code, 400, why)
        self.assertEqual(self.save(block(999_999)).status_code, 400)

    def test_the_same_drawing_cannot_appear_twice(self):
        self.assertEqual(self.save(block(self.mine.id), block(self.mine.id)).status_code, 400)

    def test_new_page_cannot_start_with_a_drawing(self):
        r = self.client.post('/api/pages/', {'workspace': self.ws.id, 'content': doc('T', block(self.mine.id))}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_rejects_malformed_blocks(self):
        for why, node in {
            'no attrs': {'type': 'drawing'}, 'no id': {'type': 'drawing', 'attrs': {}}, 'string id': block('1'),
            'bool id': block(True), 'zero id': block(0), 'extra attr': {'type': 'drawing', 'attrs': {'id': self.mine.id, 'x': 1}},
            'children': {**block(self.mine.id), 'content': [{'type': 'text', 'text': 'x'}]},
            'marks': {**block(self.mine.id), 'marks': [{'type': 'bold'}]},
        }.items():
            self.assertEqual(self.save(node).status_code, 400, why)

    def test_viewer_cannot_save_a_drawing_block(self):
        self.client.force_authenticate(self.u['viewer'])
        self.assertEqual(self.save(block(self.mine.id)).status_code, 403)
