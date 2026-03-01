import json
import os
from core.base_generator import CodeGenerator

class UtilityFunctionsGenerator(CodeGenerator):
    def run(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        api_path = os.path.join(root_dir, 'godot-cpp', 'gdextension', 'extension_api.json')
        
        try:
            with open(api_path, 'r', encoding='utf-8') as f:
                api_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: extension_api.json not found at {api_path}")
            return

        utility_funcs = []
        if 'utility_functions' in api_data:
            for func in api_data['utility_functions']:
                # Filter logic if needed, currently taking all or specific ones as per manual example
                # The manual example only had a few functions: print, print_rich, printerr, printt, prints, printraw, print_verbose, push_error, push_warning, max, min, str
                # We should probably generate all of them or a specific subset. 
                # Let's generate all that are vararg for now as the template supports vararg primarily.
                
                name = func['name']
                is_vararg = func.get('is_vararg', False)
                return_type = func.get('return_type')
                
                # Check if it's one of the functions we want to support specifically or all?
                # The prompt implies generating code based on the file, likely meaning automating what was manual.
                # Let's try to support all vararg functions as they fit the pattern.
                
                # Check for return type void explicitly to determine has_return_value
                has_ret = True
                if return_type == 'void' or return_type is None:
                    has_ret = False
                
                if is_vararg:
                    utility_funcs.append({
                        'name': name,
                        'is_vararg': True,
                        'has_return_value': has_ret,
                        'hash': func['hash']
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
