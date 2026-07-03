import os
import json

from .base_generator import CodeGenerator
from .utils.api_path import find_extension_api_json
from .utils.binding_policy import skipped_method_reason
from .utils.type_mappings import (
    JS_CLASS_RENAME_MAP,
    PACKED_ARRAY_ELEMENT_TYPES,
    parse_typedarray_element_type,
    parse_typeddictionary_types,
)

# Godot primitive → TypeScript type
PRIMITIVE_MAP = {
    'void':       'void',
    'bool':       'boolean',
    'int':        'number',
    'float':      'number',
    'Nil':        'null',
    'Object':     'GodotObject',
    'String':     'string',
    'StringName': 'string',
    'NodePath':   'string',
}

# JS-facing collection types used for return values.
JS_ARRAY_TYPE = 'VariantArgument[]'
JS_OBJECT_TYPE = '{ [key: string]: VariantArgument }'
JS_MAP_TYPE = 'Map<VariantArgument, VariantArgument>'
JS_DICTIONARY_TYPE = f'{JS_OBJECT_TYPE} | {JS_MAP_TYPE}'

# Builtin classes that map directly to JS primitives — skip class generation
SKIP_BUILTINS = frozenset(['Nil', 'void', 'bool', 'int', 'float'])

# Global enums to skip — already represented in the hand-crafted Variant class
SKIP_GLOBAL_ENUMS = frozenset(['Variant.Type', 'Variant.Operator'])

# Rename map: Godot name → JS/TS API name (avoids conflicts with JS built-ins)
RENAME_MAP = JS_CLASS_RENAME_MAP

# Method/param names that are reserved in TypeScript/JS
TS_RESERVED = frozenset([
    'constructor', 'delete', 'class', 'new', 'return', 'typeof',
    'void', 'function', 'var', 'let', 'const', 'if', 'else',
    'for', 'while', 'break', 'continue', 'switch', 'case',
    'default', 'import', 'export', 'from', 'extends', 'super',
    'this', 'static', 'in', 'of', 'instanceof',
    'throw', 'try', 'catch', 'finally', 'async', 'await',
    'yield', 'debugger', 'with', 'enum',
])

OPERATOR_METHOD_NAMES = {
    '==': 'equal',
    '!=': 'not_equal',
    '<': 'less',
    '<=': 'less_equal',
    '>': 'greater',
    '>=': 'greater_equal',
    '+': 'add',
    '-': 'subtract',
    'unary-': 'negate',
    'unary+': 'positive',
    '*': 'multiply',
    '/': 'divide',
    '%': 'module',
    '**': 'power',
    '~': 'bit_not',
    '&': 'bit_and',
    '|': 'bit_or',
    '^': 'bit_xor',
    '<<': 'bit_shift_left',
    '>>': 'bit_shift_right',
}


def sanitize_name(name: str) -> str:
    name = name.replace('-', '_')
    if name in TS_RESERVED:
        return name + '_gd'
    return name


def member_name(name: str) -> str:
    name = name.replace('-', '_')
    if name in TS_RESERVED:
        return json.dumps(name)
    return name


def godot_type_to_ts(type_str: str, is_input: bool = False, singleton_class_names: frozenset = frozenset()) -> str:
    if not type_str:
        return 'void'

    # Comma-separated multi-type → TypeScript union
    # Strip leading '-' (Godot exclusion syntax, e.g. "-AnimatedTexture")
    if ',' in type_str:
        return ' | '.join(
            godot_type_to_ts(t.strip().lstrip('-'), is_input, singleton_class_names)
            for t in type_str.split(',')
        )

    if type_str == 'Variant':
        return 'VariantArgument'  # Treat Variant as any type since we removed the binding

    # Handle Variant.Type enum specially
    if type_str == 'Variant.Type':
        return 'VariantType'

    # Handle Variant.Operator enum specially
    if type_str == 'Variant.Operator':
        return 'VariantOperator'

    if type_str == 'Callable' and is_input:
        return 'Callable | Function'

    if type_str == 'int' and is_input:
        return 'number | bigint'

    if is_input and type_str in ('String', 'GDString', 'StringName'):
        return 'GDString | StringName | string'

    if type_str in PRIMITIVE_MAP:
        return PRIMITIVE_MAP[type_str]

    if type_str.startswith('enum::'):
        inner = type_str[6:]
        if '.' in inner:
            cls, enum = inner.split('.', 1)
            # Handle special cases for Variant enums
            if cls == 'Variant' and enum == 'Type':
                return 'VariantType'
            if cls == 'Variant' and enum == 'Operator':
                return 'VariantOperator'
            if cls in singleton_class_names:
                return f'{RENAME_MAP.get(cls, cls)}_{enum}'
            return f'{RENAME_MAP.get(cls, cls)}.{enum}'
        return inner  # global enum name

    if type_str.startswith('bitfield::'):
        inner = type_str[10:]
        if '.' in inner:
            cls, enum = inner.split('.', 1)
            if cls in singleton_class_names:
                return f'{RENAME_MAP.get(cls, cls)}_{enum}'
            return f'{RENAME_MAP.get(cls, cls)}.{enum}'
        return 'number'

    if type_str.startswith('typedarray::'):
        element_type = parse_typedarray_element_type(type_str)
        # typedarray is always represented as a JS generic array on the TypeScript side.
        element_ts = godot_type_to_ts(element_type, is_input=False, singleton_class_names=singleton_class_names)
        typed_array = f'Array<{element_ts}>'
        return f'GDArray | {typed_array}' if is_input else typed_array

    if type_str.startswith('typeddictionary::'):
        key_type, value_type = parse_typeddictionary_types(type_str)
        key_ts = godot_type_to_ts(key_type, is_input=False, singleton_class_names=singleton_class_names)
        value_ts = godot_type_to_ts(value_type, is_input=False, singleton_class_names=singleton_class_names)

        # JS object literals preserve Godot dictionary keys only for string-like keys.
        if key_ts == 'string':
            typed_container = f'Record<{key_ts}, {value_ts}>'
        else:
            typed_container = f'Map<{godot_type_to_ts(key_type, is_input=True, singleton_class_names=singleton_class_names)}, {value_ts}>'

        if is_input and key_ts == 'string':
            return f'GDDictionary | {typed_container} | Map<{key_ts}, {value_ts}>'
        return f'GDDictionary | {typed_container}' if is_input else typed_container

    if type_str.endswith('*'):
        return godot_type_to_ts(type_str[:-1], is_input, singleton_class_names)

    if is_input and type_str in ('Dictionary', 'GDDictionary'):
        return f'GDDictionary | {JS_DICTIONARY_TYPE}'

    if is_input and type_str in ('Array', 'GDArray'):
        return f'GDArray | {JS_ARRAY_TYPE}'

    if is_input and type_str in PACKED_ARRAY_ELEMENT_TYPES:
        element_type = PACKED_ARRAY_ELEMENT_TYPES[type_str]
        element_ts = godot_type_to_ts(element_type, is_input=True, singleton_class_names=singleton_class_names)
        return f'{type_str} | Array<{element_ts}>'

    if not is_input and type_str == 'Array':
        return JS_ARRAY_TYPE

    if not is_input and type_str in ('Dictionary', 'GDDictionary'):
        return JS_DICTIONARY_TYPE

    return RENAME_MAP.get(type_str, type_str)


class DtsGenerator(CodeGenerator):

    def run(self):
        generator_dir = os.path.dirname(os.path.abspath(__file__))
        project_root  = os.path.dirname(generator_dir)

        api_path   = find_extension_api_json()
        output_dir = os.path.join(project_root, 'example', 'addons', 'gode', 'types')
        godot_output_path = os.path.join(output_dir, 'godot.d.ts')
        globals_output_path = os.path.join(output_dir, 'globals.d.ts')

        with open(api_path, 'r', encoding='utf-8') as f:
            api = json.load(f)

        os.makedirs(output_dir, exist_ok=True)

        godot_lines = self._generate(api)
        globals_lines = self._generate_globals(api)

        self.write_file_if_changed(godot_output_path, '\n'.join(godot_lines) + '\n')
        self.write_file_if_changed(globals_output_path, '\n'.join(globals_lines) + '\n')

    def _has_raw_pointer(self, method: dict) -> bool:
        return skipped_method_reason(method, getattr(self, '_object_class_names', set())) is not None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _ind(self, n: int) -> str:
        return '    ' * n

    def _type_to_ts(self, type_str: str, is_input: bool = False) -> str:
        return godot_type_to_ts(type_str, is_input, getattr(self, '_singleton_class_names', frozenset()))

    def _enum_type_ref(self, owner_name: str, enum_name: str) -> str:
        enum_name = sanitize_name(enum_name)
        if owner_name in getattr(self, '_singleton_ts_names', frozenset()):
            return f'{owner_name}_{enum_name}'
        return f'{owner_name}.{enum_name}'

    def _extends_type_to_ts(self, type_str: str) -> str:
        ts_type = self._type_to_ts(type_str)
        if type_str in getattr(self, '_singleton_class_names', frozenset()):
            return f'__GodotSingletonBases.{ts_type}'
        return ts_type

    def _format_params(self, arguments: list) -> str:
        parts = []
        optional_flags = [False] * len(arguments)

        # In extension_api.json, default arguments are usually trailing.
        # Mark only the trailing default arguments as optional in TypeScript.
        optional_tail = True
        for i in range(len(arguments) - 1, -1, -1):
            has_default = 'default_value' in arguments[i]
            if optional_tail and has_default:
                optional_flags[i] = True
            else:
                optional_tail = False

        for arg, is_optional in zip(arguments, optional_flags):
            name = sanitize_name(arg['name'])
            ts_type = self._type_to_ts(arg['type'], is_input=True)
            opt = '?' if is_optional else ''
            parts.append(f'{name}{opt}: {ts_type}')
        return ', '.join(parts)

    # ── Enum ──────────────────────────────────────────────────────────────────

    def _gen_enum(self, enum_data: dict, indent: int, export: bool = False, const: bool = False, name: str = None) -> list:
        ind  = self._ind(indent)
        ind2 = self._ind(indent + 1)
        prefix = ''
        if export:
            prefix += 'export '
        if const:
            prefix += 'const '
        enum_name = sanitize_name(name or enum_data['name'])
        lines = [f'{ind}{prefix}enum {enum_name} {{']
        for val in enum_data.get('values', []):
            lines.append(f'{ind2}{val["name"]} = {val["value"]},')
        lines.append(f'{ind}}}')
        return lines

    def _gen_enum_static_constants(self, enums: list, indent: int, owner_name: str, static: bool = True) -> list:
        """Godot exposes class enum values directly on constructors at runtime.

        The nested namespace enum keeps enum types available as `Viewport.MSAA`,
        while these static constants type expressions such as
        `Viewport.MSAA_DISABLED` and `Window.MODE_FULLSCREEN`.
        """
        ind = self._ind(indent)
        lines = []
        seen = set()
        modifier = 'static readonly' if static else 'readonly'
        for enum in enums:
            enum_name = sanitize_name(enum['name'])
            enum_type = self._enum_type_ref(owner_name, enum_name)
            if not static:
                lines.append(f'{ind}readonly {enum_name}: typeof {enum_type};')
            for val in enum.get('values', []):
                name = sanitize_name(val['name'])
                if name in seen:
                    continue
                seen.add(name)
                lines.append(f'{ind}{modifier} {name}: {enum_type};')
        return lines

    # ── Builtin class ─────────────────────────────────────────────────────────

    def _gen_builtin(self, cls_data: dict, ts_name: str, indent: int) -> list:
        ind  = self._ind(indent)
        ind2 = self._ind(indent + 1)
        lines = [f'{ind}export class {ts_name} {{']

        # Constructors
        for ctor in cls_data.get('constructors', []):
            args = ctor.get('arguments', [])
            params = self._format_params(args) if args else ''
            lines.append(f'{ind2}constructor({params});')

        # Members (instance properties)
        for member in cls_data.get('members', []):
            ts_type = self._type_to_ts(member['type'])
            lines.append(f'{ind2}{member["name"]}: {ts_type};')

        # Constants
        for const in cls_data.get('constants', []):
            ts_type = self._type_to_ts(const['type'])
            lines.append(f'{ind2}static readonly {const["name"]}: {ts_type};')

        lines += self._gen_enum_static_constants(cls_data.get('enums', []), indent + 1, ts_name, static=True)

        # Methods
        for method in cls_data.get('methods', []):
            if self._has_raw_pointer(method):
                continue
            name   = member_name(method['name'])
            ret    = self._type_to_ts(method.get('return_type', 'void'))
            params = self._format_params(method.get('arguments', []))
            static = 'static ' if method.get('is_static') else ''
            if method.get('is_vararg'):
                params = (params + ', ...args: VariantArgument[]') if params else '...args: VariantArgument[]'
            lines.append(f'{ind2}{static}{name}({params}): {ret};')

        for operator in cls_data.get('operators', []):
            op_name = OPERATOR_METHOD_NAMES.get(operator['name'])
            if not op_name:
                continue
            right_type = operator.get('right_type')
            params = f'right: {self._type_to_ts(right_type, is_input=True)}' if right_type else ''
            ret = self._type_to_ts(operator.get('return_type', 'void'))
            lines.append(f'{ind2}{member_name(op_name)}({params}): {ret};')

        # Index signature
        idx_type = cls_data.get('indexing_return_type')
        if idx_type:
            lines.append(f'{ind2}[index: number]: {self._type_to_ts(idx_type)};')

        lines.append(f'{ind}}}')

        # Declaration merging: namespace for nested enums
        enums = cls_data.get('enums', [])
        if enums:
            lines.append(f'{ind}export namespace {ts_name} {{')
            for enum in enums:
                lines += self._gen_enum(enum, indent + 1, export=True)
            lines.append(f'{ind}}}')

        return lines

    # ── Object-derived class ──────────────────────────────────────────────────

    def _gen_class(self, cls_data: dict, indent: int, is_singleton: bool = False) -> list:
        ind = self._ind(indent)
        class_indent = indent + 1 if is_singleton else indent
        body_indent = class_indent + 1
        class_ind = self._ind(class_indent)
        body_ind = self._ind(body_indent)
        lines = []

        name = self._type_to_ts(cls_data['name'])
        inherits = cls_data.get('inherits', '')
        extends = f' extends {self._extends_type_to_ts(inherits)}' if inherits else ' extends _GodotObject'

        singleton_enums = cls_data.get('enums', []) if is_singleton else []
        for enum in singleton_enums:
            lines += self._gen_enum(
                enum,
                indent,
                export=True,
                const=True,
                name=f'{name}_{sanitize_name(enum["name"])}',
            )
            lines.append('')

        if is_singleton:
            lines.append(f'{ind}namespace __GodotSingletonBases {{')
            lines.append(f'{class_ind}export class {name}{extends} {{')
        else:
            lines.append(f'{ind}export class {name}{extends} {{')

        # Constants
        for const in cls_data.get('constants', []):
            modifier = 'readonly' if is_singleton else 'static readonly'
            lines.append(f'{body_ind}{modifier} {const["name"]}: number;')

        lines += self._gen_enum_static_constants(cls_data.get('enums', []), body_indent, name, static=not is_singleton)

        # Properties
        # Track which method names the methods loop will declare (to avoid duplicates)
        declared_methods: set = set()
        for method in cls_data.get('methods', []):
            if not self._has_raw_pointer(method):
                declared_methods.add(method['name'])
        # Keep getter/setter method type overrides aligned with property declared types.
        property_method_overrides: dict = {}

        for prop in cls_data.get('properties', []):
            if '/' in prop['name']:  # skip grouped sub-properties
                continue
            ts_type = self._type_to_ts(prop['type'])
            ts_type_input = self._type_to_ts(prop['type'], is_input=True)
            getter = prop.get('getter', '')
            setter = prop.get('setter', '')
            lines.append(f'{body_ind}get {prop["name"]}(): {ts_type};')
            if setter:
                lines.append(f'{body_ind}set {prop["name"]}(value: {ts_type_input});')
                property_method_overrides[setter] = {'first_arg_type': ts_type_input}
            # Emit getter/setter as explicit methods when not already in the methods section
            if getter and getter not in declared_methods:
                lines.append(f'{body_ind}{sanitize_name(getter)}(): {ts_type};')
            if getter:
                property_method_overrides[getter] = {'return_type': ts_type}
            if setter and setter not in declared_methods:
                lines.append(f'{body_ind}{sanitize_name(setter)}(value: {ts_type_input}): void;')

        # Signals (as comments — no runtime type)
        for sig in cls_data.get('signals', []):
            lines.append(f'{body_ind}{sig["name"]}: Signal;')

        # Methods
        for method in cls_data.get('methods', []):
            if self._has_raw_pointer(method):
                continue
            mname = member_name(method['name'])
            ret_v = method.get('return_value') or {}
            ret = self._type_to_ts(ret_v.get('type', 'void'))
            params = self._format_params(method.get('arguments', []))
            override = property_method_overrides.get(method['name'])
            if override:
                if 'return_type' in override:
                    ret = override['return_type']
                if 'first_arg_type' in override:
                    args = method.get('arguments', [])
                    if args:
                        first_name = sanitize_name(args[0]['name'])
                        first_param = f'{first_name}: {override["first_arg_type"]}'
                        if len(args) > 1:
                            rest_params = self._format_params(args[1:])
                            params = f'{first_param}, {rest_params}' if rest_params else first_param
                        else:
                            params = first_param
            static = 'static ' if method.get('is_static') and not is_singleton else ''
            if method.get('is_vararg'):
                params = (params + ', ...args: VariantArgument[]') if params else '...args: VariantArgument[]'
            lines.append(f'{body_ind}{static}{mname}({params}): {ret};')

        lines.append(f'{class_ind}}}')

        if is_singleton:
            lines.append(f'{ind}}}')
            lines.append(f'{ind}export type {name} = __GodotSingletonBases.{name};')

        # Namespace for nested enums
        enums = cls_data.get('enums', [])
        if enums and not is_singleton:
            lines.append(f'{ind}export namespace {name} {{')
            for enum in enums:
                lines += self._gen_enum(enum, indent + 1, export=True)
            lines.append(f'{ind}}}')

        return lines

    def _gen_utility_functions(self, api: dict, indent: int) -> list:
        ind = self._ind(indent)
        lines = []
        for func in api.get('utility_functions', []):
            name = member_name(func['name'])
            ret = self._type_to_ts(func.get('return_type', 'void'))
            params = self._format_params(func.get('arguments', []))
            if func.get('is_vararg'):
                params = (params + ', ...args: VariantArgument[]') if params else '...args: VariantArgument[]'
            lines.append(f'{ind}{ind}{name}({params}): {ret};')
        return lines

    def _gen_variant_type_enum(self) -> list:
        """Generate Variant.Type enum definition"""
        lines = []
        lines.append('    export const enum VariantType {')
        lines.append('        TYPE_NIL = 0,')
        lines.append('        TYPE_BOOL = 1,')
        lines.append('        TYPE_INT = 2,')
        lines.append('        TYPE_FLOAT = 3,')
        lines.append('        TYPE_STRING = 4,')
        lines.append('        TYPE_VECTOR2 = 5,')
        lines.append('        TYPE_VECTOR2I = 6,')
        lines.append('        TYPE_RECT2 = 7,')
        lines.append('        TYPE_RECT2I = 8,')
        lines.append('        TYPE_VECTOR3 = 9,')
        lines.append('        TYPE_VECTOR3I = 10,')
        lines.append('        TYPE_TRANSFORM2D = 11,')
        lines.append('        TYPE_VECTOR4 = 12,')
        lines.append('        TYPE_VECTOR4I = 13,')
        lines.append('        TYPE_PLANE = 14,')
        lines.append('        TYPE_QUATERNION = 15,')
        lines.append('        TYPE_AABB = 16,')
        lines.append('        TYPE_BASIS = 17,')
        lines.append('        TYPE_TRANSFORM3D = 18,')
        lines.append('        TYPE_PROJECTION = 19,')
        lines.append('        TYPE_COLOR = 20,')
        lines.append('        TYPE_STRING_NAME = 21,')
        lines.append('        TYPE_NODE_PATH = 22,')
        lines.append('        TYPE_RID = 23,')
        lines.append('        TYPE_OBJECT = 24,')
        lines.append('        TYPE_CALLABLE = 25,')
        lines.append('        TYPE_SIGNAL = 26,')
        lines.append('        TYPE_DICTIONARY = 27,')
        lines.append('        TYPE_ARRAY = 28,')
        lines.append('        TYPE_PACKED_BYTE_ARRAY = 29,')
        lines.append('        TYPE_PACKED_INT32_ARRAY = 30,')
        lines.append('        TYPE_PACKED_INT64_ARRAY = 31,')
        lines.append('        TYPE_PACKED_FLOAT32_ARRAY = 32,')
        lines.append('        TYPE_PACKED_FLOAT64_ARRAY = 33,')
        lines.append('        TYPE_PACKED_STRING_ARRAY = 34,')
        lines.append('        TYPE_PACKED_VECTOR2_ARRAY = 35,')
        lines.append('        TYPE_PACKED_VECTOR3_ARRAY = 36,')
        lines.append('        TYPE_PACKED_COLOR_ARRAY = 37,')
        lines.append('        TYPE_PACKED_VECTOR4_ARRAY = 38,')
        lines.append('        TYPE_MAX = 39,')
        lines.append('    }')
        return lines

    def _gen_variant_operator_enum(self) -> list:
        """Generate Variant.Operator enum definition"""
        lines = []
        lines.append('    export const enum VariantOperator {')
        lines.append('        OP_EQUAL = 0,')
        lines.append('        OP_NOT_EQUAL = 1,')
        lines.append('        OP_LESS = 2,')
        lines.append('        OP_LESS_EQUAL = 3,')
        lines.append('        OP_GREATER = 4,')
        lines.append('        OP_GREATER_EQUAL = 5,')
        lines.append('        OP_ADD = 6,')
        lines.append('        OP_SUBTRACT = 7,')
        lines.append('        OP_MULTIPLY = 8,')
        lines.append('        OP_DIVIDE = 9,')
        lines.append('        OP_NEGATE = 10,')
        lines.append('        OP_POSITIVE = 11,')
        lines.append('        OP_MODULE = 12,')
        lines.append('        OP_POWER = 13,')
        lines.append('        OP_SHIFT_LEFT = 14,')
        lines.append('        OP_SHIFT_RIGHT = 15,')
        lines.append('        OP_BIT_AND = 16,')
        lines.append('        OP_BIT_OR = 17,')
        lines.append('        OP_BIT_XOR = 18,')
        lines.append('        OP_BIT_NEGATE = 19,')
        lines.append('        OP_AND = 20,')
        lines.append('        OP_OR = 21,')
        lines.append('        OP_XOR = 22,')
        lines.append('        OP_NOT = 23,')
        lines.append('        OP_IN = 24,')
        lines.append('        OP_MAX = 25,')
        lines.append('    }')
        return lines

    def _collect_global_singleton_symbols(self, api: dict) -> dict:
        singletons = {}

        for singleton in api.get('singletons', []):
            name = singleton['name']
            singletons[name] = RENAME_MAP.get(singleton['type'], singleton['type'])

        return singletons

    def _generate_globals(self, api: dict) -> list:
        lines = []
        lines.append('// Auto-generated by generator/dts_generator.py; do not edit manually.')
        lines.append('')
        lines.append('declare global {')
        lines.append('  interface ExportOptions {')
        lines.append('    hint?: number;')
        lines.append('    hintString?: string;')
        lines.append('  }')
        lines.append('')
        lines.append('  function Export(hint: number, hintString?: string): any;')
        lines.append('  function Export(options?: ExportOptions): any;')
        lines.append('')
        lines.append('  function Signal(...args: any[]): any;')
        lines.append('  function Tool(...args: any[]): any;')
        lines.append('')
        lines.append('  interface ExportEntry {')
        lines.append('    type: string;')
        lines.append('    hint?: number;')
        lines.append('    hint_string?: string;')
        lines.append('  }')
        lines.append('  type ExportMap = Record<string, ExportEntry>;')

        lines.append('}')
        lines.append('')
        lines.append('export {};')
        return lines

    # Top-level generation.

    def _generate(self, api: dict) -> list:
        self._object_class_names = {cls['name'] for cls in api.get('classes', [])}
        self._singleton_class_names = frozenset(
            name
            for singleton in api.get('singletons', [])
            for name in (singleton['name'], singleton['type'])
        )
        self._singleton_ts_names = frozenset(RENAME_MAP.get(name, name) for name in self._singleton_class_names)

        # Collect all builtin classes that are generated
        builtin_types = []
        for cls in api.get('builtin_classes', []):
            name = cls['name']
            if name in SKIP_BUILTINS:
                continue
            builtin_types.append(RENAME_MAP.get(name, name))
        
        variant_arg_types = ['null', 'undefined', 'boolean', 'number', 'bigint', 'string', 'Function', 'Object'] + builtin_types
        variant_arg_types.extend([JS_OBJECT_TYPE, JS_MAP_TYPE, JS_ARRAY_TYPE])
        variant_arg_types = list(dict.fromkeys(variant_arg_types))
        variant_arg_str = ' | '.join(variant_arg_types)

        lines = []
        lines.append('// Auto-generated by generator/dts_generator.py; do not edit manually.')
        lines.append('')
        lines.append('declare module "godot" {')
        lines.append('')
        lines.append(f'    export type VariantArgument = {variant_arg_str};')
        lines.append('')

        # GodotObject base (every Object without an explicit parent inherits this)
        lines += [
            '    class _GodotObject {',
            '        get_instance_id(): number;',
            '        connect(signal: string, callable: (...args: VariantArgument[]) => void): void;',
            '        disconnect(signal: string, callable: (...args: VariantArgument[]) => void): void;',
            '        emit_signal(signal: string, ...args: VariantArgument[]): void;',
            '        to_signal(signal: string, options?: { timeoutMs?: number; abortSignal?: AbortSignal }): Promise<VariantArgument>;',
            '    }',
            '',
        ]

        # Global enums
        for enum in api.get('global_enums', []):
            if enum['name'] in SKIP_GLOBAL_ENUMS:
                continue
            lines += self._gen_enum(enum, indent=1, export=True, const=True)
            lines.append('')

        # Variant.Type enum (manually added since we removed VariantBinding)
        lines += self._gen_variant_type_enum()
        lines.append('')

        # Variant.Operator enum (manually added since we removed VariantBinding)
        lines += self._gen_variant_operator_enum()
        lines.append('')

        # Builtin classes (Vector2, Color, …)
        for cls in api.get('builtin_classes', []):
            name = cls['name']
            if name in SKIP_BUILTINS:
                continue
            ts_name = RENAME_MAP.get(name, name)
            lines += self._gen_builtin(cls, ts_name, indent=1)
            lines.append('')

        # Object-derived classes (Node, Sprite2D, …)
        singletons = self._collect_global_singleton_symbols(api)
        for cls in api.get('classes', []):
            lines += self._gen_class(cls, indent=1, is_singleton=cls['name'] in singletons)
            lines.append('')

        lines.append('    export interface GD {')
        # Utility functions (sin, cos, print, ...)
        lines += self._gen_utility_functions(api, indent=1)
        lines.append('    }')

        for s_name, s_type in singletons.items():
            lines.append(f'    export const {s_name}: {s_type};')
        lines.append('    export const GD: GD;')
        lines.append('}')

        return lines
