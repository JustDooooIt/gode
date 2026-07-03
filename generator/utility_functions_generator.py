import json
import os
from .base_generator import CodeGenerator
from .utils.api_path import find_extension_api_json
from .utils.type_mappings import get_cpp_type

# Utility functions that Godot exposes in extension_api.json but godot-cpp
# deliberately omits from UtilityFunctions. Gode still exposes them through the
# GDExtension utility-function table because JavaScript needs a runtime-safe way
# to validate wrapped Object and singleton values.
GODOT_CPP_OMITTED_UTILITY_FUNCTIONS = {
    'is_instance_valid': (
        'godot-cpp omits this wrapper; call the GDExtension utility table directly'
    ),
}

UTILITY_FUNCTION_CPP_RENAMES = {
    'typeof': 'type_of',
}


class UtilityFunctionsGenerator(CodeGenerator):
    def run(self):
        api_path = find_extension_api_json()
        
        try:
            with open(api_path, 'r', encoding='utf-8') as f:
                api_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: extension_api.json not found at {api_path}")
            return

        utility_funcs = []
        if 'utility_functions' in api_data:
            for func in api_data['utility_functions']:
                name = func['name']
                is_vararg = func.get('is_vararg', False)
                return_type = func.get('return_type', 'void')
                has_ret = return_type != 'void'
                uses_low_level = is_vararg or name in GODOT_CPP_OMITTED_UTILITY_FUNCTIONS
                return_type_cpp = get_cpp_type(return_type, '', set(), False) if has_ret else 'void'

                utility_funcs.append({
                    'name': name,
                    'cpp_name': UTILITY_FUNCTION_CPP_RENAMES.get(name, name),
                    'is_vararg': is_vararg,
                    'uses_low_level': uses_low_level,
                    'has_return_value': has_ret,
                    'return_type': return_type_cpp,
                    'hash': func['hash'],
                    'low_level_reason': GODOT_CPP_OMITTED_UTILITY_FUNCTIONS.get(name, '') if uses_low_level else '',
                })
        
        context = {
            'utility_functions': utility_funcs
        }

        # Generate Header
        self.render('utility_functions.h.jinja2', context, 'utility_functions/utility_functions.h', 'include_dir')
        
        # Generate Source
        self.render('utility_functions.cpp.jinja2', context, 'utility_functions/utility_functions.cpp', 'src_dir')
        
        # Generate Vararg Header
        self.render('utility_functions_vararg.h.jinja2', context, 'utility_functions/utility_functions_vararg_method.h', 'include_dir')
