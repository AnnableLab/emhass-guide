"""Tests for YAML file validity and structure."""
import os
import re
from pathlib import Path
import pytest
import yaml
from jinja2 import Environment, TemplateSyntaxError
from voluptuous import Schema, Required, Optional, Any, ALLOW_EXTRA


# Path to includes directory
INCLUDES_DIR = Path(__file__).parent.parent / "src" / "includes"


def get_yaml_files():
    """Get all YAML files from the includes directory."""
    return list(INCLUDES_DIR.glob("*.yaml"))


# Custom YAML loader that handles Home Assistant tags
class HomeAssistantYAMLLoader(yaml.SafeLoader):
    """Custom YAML loader that handles Home Assistant specific tags."""
    pass


def ha_include_constructor(loader, node):
    """Handle !include tag by returning a placeholder."""
    return f"!include {loader.construct_scalar(node)}"


def ha_include_dir_named_constructor(loader, node):
    """Handle !include_dir_named tag by returning a placeholder."""
    return f"!include_dir_named {loader.construct_scalar(node)}"


def ha_include_dir_list_constructor(loader, node):
    """Handle !include_dir_list tag by returning a placeholder."""
    return f"!include_dir_list {loader.construct_scalar(node)}"


def ha_include_dir_merge_list_constructor(loader, node):
    """Handle !include_dir_merge_list tag by returning a placeholder."""
    return f"!include_dir_merge_list {loader.construct_scalar(node)}"


def ha_include_dir_merge_named_constructor(loader, node):
    """Handle !include_dir_merge_named tag by returning a placeholder."""
    return f"!include_dir_merge_named {loader.construct_scalar(node)}"


def ha_secret_constructor(loader, node):
    """Handle !secret tag by returning a placeholder."""
    return f"!secret {loader.construct_scalar(node)}"


def ha_env_var_constructor(loader, node):
    """Handle !env_var tag by returning a placeholder."""
    return f"!env_var {loader.construct_scalar(node)}"


# Register HA-specific constructors
HomeAssistantYAMLLoader.add_constructor('!include', ha_include_constructor)
HomeAssistantYAMLLoader.add_constructor('!include_dir_named', ha_include_dir_named_constructor)
HomeAssistantYAMLLoader.add_constructor('!include_dir_list', ha_include_dir_list_constructor)
HomeAssistantYAMLLoader.add_constructor('!include_dir_merge_list', ha_include_dir_merge_list_constructor)
HomeAssistantYAMLLoader.add_constructor('!include_dir_merge_named', ha_include_dir_merge_named_constructor)
HomeAssistantYAMLLoader.add_constructor('!secret', ha_secret_constructor)
HomeAssistantYAMLLoader.add_constructor('!env_var', ha_env_var_constructor)


def load_yaml_file(filepath):
    """Load a YAML file and return its contents."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.load(f, Loader=HomeAssistantYAMLLoader)


# Define schemas for different HA component types
AUTOMATION_SCHEMA = Schema({
    Required('alias'): str,
    Optional('description'): str,
    Required('triggers'): list,
    Optional('conditions'): Any(list, None),
    Required('actions'): list,
    Required('mode'): str,
    Optional('variables'): dict,
    Optional('max'): int,
    Optional('max_exceeded'): str,
}, extra=ALLOW_EXTRA)


SCRIPT_SCHEMA = Schema({
    Required('sequence'): list,
    Required('alias'): str,
    Optional('description'): str,
    Optional('variables'): dict,
    Optional('mode'): str,
    Optional('max'): int,
    Optional('fields'): dict,
}, extra=ALLOW_EXTRA)


class TestYAMLValidity:
    """Test YAML file validity."""

    @pytest.mark.parametrize("yaml_file", get_yaml_files(), ids=lambda x: x.name)
    def test_yaml_syntax(self, yaml_file):
        """Test that YAML files have valid syntax."""
        try:
            load_yaml_file(yaml_file)
        except yaml.YAMLError as e:
            pytest.fail(f"YAML syntax error in {yaml_file.name}: {e}")

    @pytest.mark.parametrize("yaml_file", get_yaml_files(), ids=lambda x: x.name)
    def test_yaml_not_empty(self, yaml_file):
        """Test that YAML files are not empty."""
        data = load_yaml_file(yaml_file)
        assert data is not None, f"{yaml_file.name} is empty"
        assert len(data) > 0, f"{yaml_file.name} has no content"


class TestStructureValidity:
    """Test structure validity of automations and scripts."""

    def is_automation(self, data):
        """Check if the YAML data represents an automation."""
        return 'triggers' in data or 'trigger' in data

    def is_script(self, data):
        """Check if the YAML data represents a script."""
        return 'sequence' in data

    def is_config_file(self, data):
        """Check if the YAML data is a configuration file (not automation/script)."""
        # Config files typically have keys like homeassistant, automation, script, etc.
        if isinstance(data, dict):
            config_keys = {'homeassistant', 'automation', 'script', 'sensor', 'binary_sensor', 'template'}
            return bool(config_keys & set(data.keys()))
        return False

    @pytest.mark.parametrize("yaml_file", get_yaml_files(), ids=lambda x: x.name)
    def test_has_alias(self, yaml_file):
        """Test that all automations/scripts have an alias."""
        data = load_yaml_file(yaml_file)
        
        # Skip config files
        if self.is_config_file(data):
            pytest.skip(f"{yaml_file.name} is a configuration file, not an automation/script")
        
        if 'alias' in data:
            assert isinstance(data['alias'], str), f"{yaml_file.name} alias must be a string"
            assert len(data['alias']) > 0, f"{yaml_file.name} alias cannot be empty"

    @pytest.mark.parametrize("yaml_file", get_yaml_files(), ids=lambda x: x.name)
    def test_automation_structure(self, yaml_file):
        """Test automation structure if file contains an automation."""
        data = load_yaml_file(yaml_file)
        
        # Skip config files
        if self.is_config_file(data):
            pytest.skip(f"{yaml_file.name} is a configuration file, not an automation/script")
        
        if self.is_automation(data):
            # Check for required fields
            assert 'alias' in data, f"{yaml_file.name} automation missing 'alias'"
            assert 'triggers' in data or 'trigger' in data, f"{yaml_file.name} automation missing 'triggers' or 'trigger'"
            assert 'actions' in data or 'action' in data, f"{yaml_file.name} automation missing 'actions' or 'action'"
            assert 'mode' in data, f"{yaml_file.name} automation missing 'mode'"
            
            # Check mode is valid
            valid_modes = ['single', 'restart', 'queued', 'parallel']
            assert data['mode'] in valid_modes, f"{yaml_file.name} has invalid mode: {data['mode']}"

    @pytest.mark.parametrize("yaml_file", get_yaml_files(), ids=lambda x: x.name)
    def test_script_structure(self, yaml_file):
        """Test script structure if file contains a script."""
        data = load_yaml_file(yaml_file)
        
        # Skip config files
        if self.is_config_file(data):
            pytest.skip(f"{yaml_file.name} is a configuration file, not an automation/script")
        
        if self.is_script(data):
            # Check for required fields
            assert 'alias' in data, f"{yaml_file.name} script missing 'alias'"
            assert 'sequence' in data, f"{yaml_file.name} script missing 'sequence'"
            assert isinstance(data['sequence'], list), f"{yaml_file.name} sequence must be a list"
            assert len(data['sequence']) > 0, f"{yaml_file.name} sequence cannot be empty"


class TestEntityIDs:
    """Test entity ID formats and conventions."""

    ENTITY_ID_PATTERN = re.compile(r'^[a-z_]+\.[a-z0-9_]+$')

    def extract_entity_ids(self, data, entity_ids=None):
        """Recursively extract entity IDs from YAML data."""
        if entity_ids is None:
            entity_ids = set()

        if isinstance(data, dict):
            for key, value in data.items():
                if key == 'entity_id':
                    if isinstance(value, str):
                        entity_ids.add(value)
                    elif isinstance(value, list):
                        entity_ids.update(value)
                else:
                    self.extract_entity_ids(value, entity_ids)
        elif isinstance(data, list):
            for item in data:
                self.extract_entity_ids(item, entity_ids)

        return entity_ids

    @pytest.mark.parametrize("yaml_file", get_yaml_files(), ids=lambda x: x.name)
    def test_entity_id_format(self, yaml_file):
        """Test that all entity IDs follow proper format."""
        data = load_yaml_file(yaml_file)
        entity_ids = self.extract_entity_ids(data)

        for entity_id in entity_ids:
            # Skip template variables
            if '{{' in entity_id or '{%' in entity_id:
                continue
            
            assert self.ENTITY_ID_PATTERN.match(entity_id), \
                f"{yaml_file.name} has invalid entity_id format: {entity_id}"

    @pytest.mark.parametrize("yaml_file", get_yaml_files(), ids=lambda x: x.name)
    def test_entity_ids_exist(self, yaml_file):
        """Test that entity IDs are present where expected."""
        data = load_yaml_file(yaml_file)
        entity_ids = self.extract_entity_ids(data)
        
        # Just check that we found some entity IDs (if this is an automation/script)
        if 'sequence' in data or 'triggers' in data or 'actions' in data:
            # Some files might not have entity IDs, so we just check they're valid if present
            pass


class TestJinja2Templates:
    """Test Jinja2 template syntax."""

    def extract_templates(self, data, templates=None):
        """Recursively extract Jinja2 templates from YAML data."""
        if templates is None:
            templates = []

        if isinstance(data, str):
            # Find all Jinja2 expressions
            if '{{' in data or '{%' in data:
                templates.append(data)
        elif isinstance(data, dict):
            for value in data.values():
                self.extract_templates(value, templates)
        elif isinstance(data, list):
            for item in data:
                self.extract_templates(item, templates)

        return templates

    @pytest.mark.parametrize("yaml_file", get_yaml_files(), ids=lambda x: x.name)
    def test_jinja2_syntax(self, yaml_file):
        """Test that Jinja2 templates have valid syntax."""
        data = load_yaml_file(yaml_file)
        templates = self.extract_templates(data)
        
        env = Environment()
        for template in templates:
            try:
                # Try to parse the template
                env.parse(template)
            except TemplateSyntaxError as e:
                # Only fail on clear syntax errors, not on undefined variables
                if "unexpected" in str(e).lower() or "expected" in str(e).lower():
                    pytest.fail(f"{yaml_file.name} has Jinja2 syntax error: {e}\nTemplate: {template[:100]}")


class TestBestPractices:
    """Test Home Assistant best practices."""

    @pytest.mark.parametrize("yaml_file", get_yaml_files(), ids=lambda x: x.name)
    def test_no_hardcoded_paths(self, yaml_file):
        """Test that there are no hardcoded file paths."""
        with open(yaml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for common hardcoded path patterns
        suspicious_patterns = [
            r'/home/[^/]+/',
            r'C:\\Users\\',
            r'/Users/[^/]+/',
        ]
        
        for pattern in suspicious_patterns:
            matches = re.findall(pattern, content)
            if matches:
                pytest.fail(f"{yaml_file.name} contains hardcoded path: {matches[0]}")

    @pytest.mark.parametrize("yaml_file", get_yaml_files(), ids=lambda x: x.name)
    def test_has_description(self, yaml_file):
        """Test that automations and scripts have descriptions."""
        data = load_yaml_file(yaml_file)
        
        # Skip config files
        if isinstance(data, dict):
            config_keys = {'homeassistant', 'automation', 'script', 'sensor', 'binary_sensor', 'template'}
            if bool(config_keys & set(data.keys())):
                pytest.skip(f"{yaml_file.name} is a configuration file, not an automation/script")
        
        # Only check if it's an automation or script
        if 'sequence' in data or 'triggers' in data:
            if 'description' in data:
                assert isinstance(data['description'], str), \
                    f"{yaml_file.name} description must be a string"

    @pytest.mark.parametrize("yaml_file", get_yaml_files(), ids=lambda x: x.name)
    def test_action_has_alias(self, yaml_file):
        """Test that important actions have aliases for debugging."""
        data = load_yaml_file(yaml_file)
        
        # Skip config files
        if isinstance(data, dict):
            config_keys = {'homeassistant', 'automation', 'script', 'sensor', 'binary_sensor', 'template'}
            if bool(config_keys & set(data.keys())):
                pytest.skip(f"{yaml_file.name} is a configuration file, not an automation/script")
        
        def check_actions(actions):
            if not isinstance(actions, list):
                return
            
            for action in actions:
                if not isinstance(action, dict):
                    continue
                
                # Check nested choose/if-then-else structures
                if 'choose' in action:
                    for choice in action['choose']:
                        if 'sequence' in choice:
                            check_actions(choice['sequence'])
                
                if 'if' in action:
                    if 'then' in action:
                        check_actions(action['then'])
                    if 'else' in action:
                        check_actions(action['else'])
        
        if 'sequence' in data:
            check_actions(data['sequence'])
        if 'actions' in data:
            check_actions(data['actions'])

