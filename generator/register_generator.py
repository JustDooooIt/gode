from .base_generator import CodeGenerator
from .utils.api_data import load_extension_api_json
from .utils.binding_policy import global_enum_export_name, singleton_enum_export_name
from .utils.string_utils import to_snake_case
from .utils.type_mappings import JS_CLASS_RENAME_MAP

def enum_variable_name(name):
    variable_name = to_snake_case(name)
    while "__" in variable_name:
        variable_name = variable_name.replace("__", "_")
    return variable_name


class RegisterGenerator(CodeGenerator):
    def run(self):
        api_data = load_extension_api_json(required_keys=("builtin_classes", "classes", "global_enums"))

        builtins = []
        classes = []

        # Process Builtin Classes
        for builtin_class in api_data['builtin_classes']:
            class_name = builtin_class['name']
            # Skip POD types and void/Nil
            if class_name in ['bool', 'int', 'float', 'void', 'Nil']:
                continue

            snake_name = to_snake_case(class_name)

            builtins.append({
                'class_name': class_name,
                'snake_name': snake_name,
                'include': f"builtin/{snake_name}_binding.gen.h"
            })

        # Process Classes
        for class_def in api_data['classes']:
            class_name = class_def['name']
            snake_name = to_snake_case(class_name)

            classes.append({
                'class_name': class_name,
                'snake_name': snake_name,
                'include': f"classes/{snake_name}_binding.gen.h"
            })

        global_enums = []
        for enum_def in api_data['global_enums']:
            export_name = global_enum_export_name(enum_def['name'])
            if not export_name:
                continue
            global_enums.append({
                'name': export_name,
                'variable_name': enum_variable_name(export_name),
                'values': enum_def.get('values', []),
            })

        singleton_names = {s['name'] for s in api_data.get('singletons', [])}
        singleton_enum_aliases = []
        for class_def in api_data['classes']:
            class_name = class_def['name']
            if class_name not in singleton_names:
                continue
            owner_name = JS_CLASS_RENAME_MAP.get(class_name, class_name)
            for enum_def in class_def.get('enums', []):
                export_name = singleton_enum_export_name(owner_name, enum_def['name'])
                singleton_enum_aliases.append({
                    'name': export_name,
                    'variable_name': enum_variable_name(export_name),
                    'values': enum_def.get('values', []),
                })

        context = {
            'builtins': builtins,
            'classes': [], # We don't want to register classes globally anymore
            'global_enums': global_enums,
        }

        # Generate Header
        self.render('register_builtin.h.jinja2', context, 'register_builtin.gen.h', 'include_dir')
        
        # Generate Source
        self.render('register_builtin.cpp.jinja2', context, 'register_builtin.gen.cpp', 'src_dir')

        # Process Singletons
        singletons = []
        for s in api_data.get('singletons', []):
            singleton_name = s['name']
            singleton_type = s['type']
            binding_type = singleton_type
            if singleton_name == 'ClassDB':
                singleton_type = 'ClassDBSingleton'
                binding_type = 'ClassDB'
            singletons.append({
                'name': singleton_name,
                'type': singleton_type,
                'binding_type': binding_type
            })

        context = {
            'classes': classes,
            'singletons': singletons,
            'singleton_enum_aliases': singleton_enum_aliases,
        }
        self.render('register_classes.h.jinja2', context, 'register_classes.gen.h', 'include_dir')
        self.render('register_classes.cpp.jinja2', context, 'register_classes.gen.cpp', 'src_dir')
