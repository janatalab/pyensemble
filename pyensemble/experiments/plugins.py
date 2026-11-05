"""Resolve jsPsych timeline types to discoverable static paths."""

import re
from pathlib import Path

from django.contrib.staticfiles import finders


class PluginConfigurationError(ValueError):
    pass


def resolve_plugins(timeline):
    """Return unique plugin paths in first-use order, including nested trials."""
    paths = []
    seen = set()

    def visit(nodes, inherited_type=None):
        if not isinstance(nodes, list):
            raise PluginConfigurationError('A jsPsych timeline must be a list.')
        for node in nodes:
            if not isinstance(node, dict):
                raise PluginConfigurationError('Each jsPsych timeline node must be an object.')
            plugin_type = node.get('type', inherited_type)
            if 'timeline' in node:
                visit(node['timeline'], plugin_type)
                continue
            if not isinstance(plugin_type, str):
                raise PluginConfigurationError('Each jsPsych trial must have a string plugin type.')
            parts = plugin_type.split('/')
            if len(parts) == 1 and re.fullmatch(r'[A-Za-z0-9_-]+', parts[0]):
                path = f'jsPsych/plugins/jspsych-{plugin_type}.js'
            elif (
                len(parts) == 2
                and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', parts[0])
                and re.fullmatch(r'[A-Za-z0-9_-]+', parts[1])
            ):
                path = f'experiments/{parts[0]}/jspsych/plugins/jspsych-{parts[1]}.js'
            else:
                raise PluginConfigurationError(f'Invalid jsPsych plugin type: {plugin_type!r}.')
            if path not in seen:
                source = finders.find(path)
                if not source or not Path(source).is_file():
                    raise PluginConfigurationError(
                        f'jsPsych plugin {plugin_type!r} was not found at {path!r}.'
                    )
                seen.add(path)
                paths.append(path)

    visit(timeline)
    return paths
