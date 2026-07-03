# Gode Code Generator

This directory contains the Python + Jinja2 code generation framework for Gode.

## Structure

- `builtin/`: Generates built-in Variant bindings.
- `class/`: Generates Godot class bindings.
- `register/`: Generates binding registration and utility-function wrappers.
- `dts/`: Generates TypeScript declaration files.
- `core/`: Contains the base generator class.
- `utils/`: Contains shared generator policy, path, naming, and type-mapping helpers.
- `templates/`: Jinja2 templates for code generation.
- `generator.py`: Main entry point to run all generators.

## Usage

1. Install dependencies:
   ```bash
   python -m pip install -r generator/requirements.txt
   ```

2. Create a new generator:
   - Create a Python file in `builtin/`, `class/`, `register/`, or `dts/`.
   - Define a class inheriting from `core.base_generator.CodeGenerator`.
   - Implement the `run(self)` method.
   - Use `self.render(template_name, context, output_filename, output_key)` to generate files.

3. Run the generator:
   ```bash
   python generator/generator.py
   ```

By default, the generator reads `third/godot-cpp/gdextension/extension_api.json`.
Set `GODOT_EXTENSION_API_JSON` or `GODOT_CPP_DIR` when generating against a
different Godot API checkout.

## Example Generator

```python
from core.base_generator import CodeGenerator

class MyGenerator(CodeGenerator):
    def run(self):
        context = {"name": "World"}
        self.render("my_template.jinja2", context, "my_output.cpp", "src_dir")
```
