import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.test import RequestFactory, SimpleTestCase, TestCase

from pyensemble.experiments.finders import ExperimentFinder
from pyensemble.experiments.plugins import PluginConfigurationError, resolve_plugins
from pyensemble.models import Experiment, ExperimentXForm, Form, Session, Ticket
from pyensemble.views import serve_form


class StaticFixture:
    def setUp(self):
        super().setUp()
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.experiments = self.root / 'experiments'
        self.experiments.mkdir()
        self.shared = self.root / 'shared'
        self.shared.mkdir()
        self.settings_override = self.settings(
            EXPERIMENT_DIR=self.experiments,
            STATICFILES_DIRS=[self.shared],
            STATIC_ROOT=self.root / 'collected',
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        # Django caches finder instances for the lifetime of a settings context.
        finders.get_finder.cache_clear()
        self.addCleanup(finders.get_finder.cache_clear)
        self.write(self.shared / 'jsPsych/plugins/jspsych-standard.js')
        for package in ('alpha', 'beta'):
            self.write(self.experiments / package / '__init__.py')
            self.write(
                self.experiments / package / 'static/jspsych/plugins/jspsych-custom.js'
            )
        self.write(self.experiments / 'alpha/private.txt')

    def write(self, path, content=''):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path


class PluginDiscoveryTests(StaticFixture, SimpleTestCase):
    def test_find_and_list_are_namespaced(self):
        finder = ExperimentFinder()
        for package in ('alpha', 'beta'):
            path = f'experiments/{package}/jspsych/plugins/jspsych-custom.js'
            self.assertEqual(
                finder.find(path),
                str(self.experiments / package / 'static/jspsych/plugins/jspsych-custom.js'),
            )
        self.assertFalse(finder.find('jspsych/plugins/jspsych-custom.js'))
        self.assertFalse(finder.find('experiments/alpha/private.txt'))
        self.assertEqual(
            [(path, storage.prefix) for path, storage in finder.list([])],
            [
                ('jspsych/plugins/jspsych-custom.js', 'experiments/alpha'),
                ('jspsych/plugins/jspsych-custom.js', 'experiments/beta'),
            ],
        )
        self.assertEqual(finder.check(), [])

    def test_ignores_nonpackages_and_hidden_directories(self):
        for package in ('__pycache__', '.hidden', 'not-a-package', 'no_init'):
            self.write(self.experiments / package / 'static/leaked.js')
        self.assertEqual(len(ExperimentFinder().locations), 2)

    def test_collectstatic_and_findstatic(self):
        output = StringIO()
        path = 'experiments/alpha/jspsych/plugins/jspsych-custom.js'
        call_command('findstatic', path, stdout=output, verbosity=0)
        self.assertIn(str(self.experiments / 'alpha/static'), output.getvalue())
        call_command('collectstatic', interactive=False, verbosity=0)
        for package in ('alpha', 'beta'):
            self.assertTrue(
                (self.root / f'collected/experiments/{package}/jspsych/plugins/jspsych-custom.js').is_file()
            )
        self.assertFalse((self.root / 'collected/experiments/alpha/private.txt').exists())

    def test_resolves_nested_inherited_and_mixed_types_once(self):
        self.assertEqual(resolve_plugins([
            {'type': 'standard'},
            {'type': 'alpha/custom', 'timeline': [
                {'stimulus': 'Inherited'},
                {'timeline': [{'stimulus': 'Nested'}]},
                {'type': 'beta/custom'},
            ]},
            {'type': 'standard'},
        ]), [
            'jsPsych/plugins/jspsych-standard.js',
            'experiments/alpha/jspsych/plugins/jspsych-custom.js',
            'experiments/beta/jspsych/plugins/jspsych-custom.js',
        ])

    def test_overridden_container_type_is_not_loaded(self):
        self.assertEqual(resolve_plugins([
            {'type': 'absent', 'timeline': [{'type': 'standard'}]},
        ]), ['jsPsych/plugins/jspsych-standard.js'])

    def test_rejects_invalid_types_and_timeline_shapes(self):
        for timeline in (
            {}, [None], [{}], [{'type': None}], [{'type': 42}],
            [{'timeline': {}}], [{'type': '../custom'}],
            [{'type': 'alpha/../custom'}], [{'type': 'alpha/custom.js'}],
            [{'type': 'https://example.com/plugin'}], [{'type': 'alpha\\custom'}],
            [{'type': 'alpha/custom?x'}], [{'type': '/custom'}],
        ):
            with self.subTest(timeline=timeline):
                with self.assertRaises(PluginConfigurationError):
                    resolve_plugins(timeline)

    def test_missing_plugins_do_not_fall_back(self):
        for plugin_type in ('missing', 'alpha/standard', 'unknown/custom'):
            with self.subTest(plugin_type=plugin_type):
                with self.assertRaisesRegex(PluginConfigurationError, 'was not found'):
                    resolve_plugins([{'type': plugin_type}])


class PluginViewTests(StaticFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.experiment = Experiment.objects.create(title='Plugin test')
        self.form = Form.objects.create(name='Plugin form')
        ExperimentXForm.objects.create(
            experiment=self.experiment, form=self.form, form_order=1,
            form_handler='form_stimulus_s', stimulus_script='alpha.trials.select(request)',
        )
        ticket = Ticket.objects.create(experiment=self.experiment, ticket_code='plugin-test')
        self.session = Session.objects.create(experiment=self.experiment, ticket=ticket)

    def request(self, method='get'):
        request = getattr(RequestFactory(), method)('/')

        class SessionDict(dict):
            modified = False

        request.session = SessionDict({
            self.experiment.cache_key: {
                'session_id': self.session.pk, 'curr_form_idx': 0,
                'first_form': False, 'stimulus_id': None,
            },
        })
        return request

    def test_view_renders_plugins_before_starting_trial(self):
        timeline = [{'type': 'standard'}, {'type': 'alpha/custom'}]
        with patch('pyensemble.views.fetch_experiment_method') as fetch:
            fetch.return_value.return_value = (timeline, None)
            response = serve_form(self.request(), self.experiment.pk)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        core = html.index('src="/static/jsPsych/jspsych.js"')
        shared = html.index('src="/static/jsPsych/plugins/jspsych-standard.js"')
        custom = html.index('src="/static/experiments/alpha/jspsych/plugins/jspsych-custom.js"')
        self.assertLess(core, shared)
        self.assertLess(shared, custom)
        self.assertLess(custom, html.index('start_trial(timeline_json)'))
        self.assertIn(json.dumps(timeline), html)

    def test_missing_plugin_logs_and_shows_error(self):
        with patch('pyensemble.views.fetch_experiment_method') as fetch:
            fetch.return_value.return_value = ([{'type': 'alpha/missing'}], None)
            with self.assertLogs(level='ERROR') as logs:
                response = serve_form(self.request(), self.experiment.pk)
        self.assertEqual(response.status_code, 500)
        self.assertIn('alpha/missing', '\n'.join(logs.output))
        self.assertIn(b'contact the experiment administrator', response.content)

    def test_invalid_post_skips_trial_without_resolving_plugins(self):
        with patch('pyensemble.views.resolve_plugins') as resolve:
            response = serve_form(self.request('post'), self.experiment.pk)
        self.assertEqual(response.status_code, 200)
        resolve.assert_not_called()
        self.assertIn(b"$('#questions').removeClass('d-none')", response.content)
        self.assertNotIn(b'src="/static/experiments/', response.content)
