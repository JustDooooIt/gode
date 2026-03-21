import os
import json
from core.base_generator import CodeGenerator

# Godot primitive → TypeScript type
PRIMITIVE_MAP = {
    'void':       'void',
    'bool':       'boolean',
    'int':        'number',
    'float':      'number',
    'Nil':        'null',
    'Variant':    'Variant',
    'Object':     'GodotObject',
    'String':     'string',
    'StringName': 'string',
    'NodePath':   'string',
}

# Builtin classes that map directly to JS primitives — skip class generation
SKIP_BUILTINS = frozenset(['Nil', 'void', 'bool', 'int', 'float', 'Variant'])

# Global enums to skip — already represented in the hand-crafted Variant class
SKIP_GLOBAL_ENUMS = frozenset(['Variant.Type', 'Variant.Operator'])

# Rename map: Godot name → TS name (avoids conflicts with JS built-ins)
RENAME_MAP = {
    'Object':     'GodotObject',
    'String':     'GDString',
    'Dictionary': 'GDDictionary',
    'Array':      'GDArray',
}

# Method/param names that are reserved in TypeScript/JS
TS_RESERVED = frozenset([
    'constructor', 'delete', 'class', 'new', 'return', 'typeof',
    'void', 'function', 'var', 'let', 'const', 'if', 'else',
    'for', 'while', 'break', 'continue', 'switch', 'case',
    'default', 'import', 'export', 'from', 'extends', 'super',
    'this', 'static', 'get', 'set', 'in', 'of', 'instanceof',
    'throw', 'try', 'catch', 'finally', 'async', 'await',
    'yield', 'debugger', 'with', 'enum',
])


def sanitize_name(name: str) -> str:
    name = name.replace('-', '_')
    if name in TS_RESERVED:
        return name + '_gd'
    return name


def godot_type_to_ts(type_str: str, is_input: bool = False) -> str:
    if not type_str:
        return 'void'

    # Comma-separated multi-type → TypeScript union
    # Strip leading '-' (Godot exclusion syntax, e.g. "-AnimatedTexture")
    if ',' in type_str:
        return ' | '.join(godot_type_to_ts(t.strip().lstrip('-'), is_input) for t in type_str.split(','))

    if type_str == 'Variant':
        return 'VariantArgument' if is_input else 'Variant'

    if type_str in PRIMITIVE_MAP:
        return PRIMITIVE_MAP[type_str]

    if type_str.startswith('enum::'):
        inner = type_str[6:]
        if '.' in inner:
            cls, enum = inner.split('.', 1)
            return f'{RENAME_MAP.get(cls, cls)}.{enum}'
        return inner  # global enum name

    if type_str.startswith('bitfield::'):
        inner = type_str[10:]
        if '.' in inner:
            cls, enum = inner.split('.', 1)
            return f'{RENAME_MAP.get(cls, cls)}.{enum}'
        return 'number'

    if type_str.startswith('typedarray::'):
        return 'GDArray'

    if type_str.startswith('typeddictionary::'):
        return 'GDDictionary'

    if type_str.endswith('*'):
        return godot_type_to_ts(type_str[:-1], is_input)

    return RENAME_MAP.get(type_str, type_str)


class DtsGenerator(CodeGenerator):

    def run(self):
        dts_pkg_dir  = os.path.dirname(os.path.abspath(__file__))
        generator_dir = os.path.dirname(dts_pkg_dir)
        project_root  = os.path.dirname(generator_dir)

        api_path   = os.path.join(project_root, 'godot-cpp', 'gdextension', 'extension_api.json')
        output_dir = os.path.join(project_root, 'example', 'addons', 'gode', 'core')
        output_path = os.path.join(output_dir, 'godot.d.ts')

        with open(api_path, 'r', encoding='utf-8') as f:
            api = json.load(f)

        os.makedirs(output_dir, exist_ok=True)

        lines = self._generate(api)

        with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines))
            f.write('\n')

        print(f'Generated: {output_path}')

    def _has_raw_pointer(self, method: dict) -> bool:
        """Return True if any argument or the return value contains a raw pointer type."""
        for arg in method.get('arguments', []):
            if '*' in arg.get('type', ''):
                return True
        ret = method.get('return_value') or method.get('return_type')
        if ret:
            t = ret if isinstance(ret, str) else ret.get('type', '')
            if '*' in t:
                return True
        return False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _ind(self, n: int) -> str:
        return '    ' * n

    def _format_params(self, arguments: list) -> str:
        parts = []
        for arg in arguments:
            name = sanitize_name(arg['name'])
            ts_type = godot_type_to_ts(arg['type'], is_input=True)
            parts.append(f'{name}: {ts_type}')
        return ', '.join(parts)

    # ── Enum ──────────────────────────────────────────────────────────────────

    def _gen_enum(self, enum_data: dict, indent: int) -> list:
        ind  = self._ind(indent)
        ind2 = self._ind(indent + 1)
        lines = [f'{ind}const enum {enum_data["name"]} {{']
        for val in enum_data.get('values', []):
            lines.append(f'{ind2}{val["name"]} = {val["value"]},')
        lines.append(f'{ind}}}')
        return lines

    # ── Builtin class ─────────────────────────────────────────────────────────

    def _gen_builtin(self, cls_data: dict, ts_name: str, indent: int) -> list:
        ind  = self._ind(indent)
        ind2 = self._ind(indent + 1)
        lines = [f'{ind}class {ts_name} {{']

        # Constructors
        for ctor in cls_data.get('constructors', []):
            args = ctor.get('arguments', [])
            params = self._format_params(args) if args else ''
            lines.append(f'{ind2}constructor({params});')

        # Members (instance properties)
        for member in cls_data.get('members', []):
            ts_type = godot_type_to_ts(member['type'])
            lines.append(f'{ind2}{member["name"]}: {ts_type};')

        # Constants
        for const in cls_data.get('constants', []):
            ts_type = godot_type_to_ts(const['type'])
            lines.append(f'{ind2}static readonly {const["name"]}: {ts_type};')

        # Methods
        for method in cls_data.get('methods', []):
            if self._has_raw_pointer(method):
                continue
            name   = sanitize_name(method['name'])
            ret    = godot_type_to_ts(method.get('return_type', 'void'))
            params = self._format_params(method.get('arguments', []))
            static = 'static ' if method.get('is_static') else ''
            if method.get('is_vararg'):
                params = (params + ', ...args: any[]') if params else '...args: any[]'
            lines.append(f'{ind2}{static}{name}({params}): {ret};')

        # Index signature
        idx_type = cls_data.get('indexing_return_type')
        if idx_type:
            lines.append(f'{ind2}[index: number]: {godot_type_to_ts(idx_type)};')

        lines.append(f'{ind}}}')

        # Declaration merging: namespace for nested enums
        enums = cls_data.get('enums', [])
        if enums:
            lines.append(f'{ind}namespace {ts_name} {{')
            for enum in enums:
                lines += self._gen_enum(enum, indent + 1)
            lines.append(f'{ind}}}')

        return lines

    # ── Object-derived class ──────────────────────────────────────────────────

    def _gen_class(self, cls_data: dict, indent: int) -> list:
        ind  = self._ind(indent)
        ind2 = self._ind(indent + 1)
        lines = []

        name     = godot_type_to_ts(cls_data['name'])
        inherits = cls_data.get('inherits', '')
        extends  = f' extends {inherits}' if inherits else ' extends _GodotObject'
        lines.append(f'{ind}class {name}{extends} {{')

        # Constants
        for const in cls_data.get('constants', []):
            lines.append(f'{ind2}static readonly {const["name"]}: number;')

        # Properties
        # Track which method names the methods loop will declare (to avoid duplicates)
        declared_methods: set = set()
        for method in cls_data.get('methods', []):
            if not self._has_raw_pointer(method):
                declared_methods.add(method['name'])

        for prop in cls_data.get('properties', []):
            if '/' in prop['name']:  # skip grouped sub-properties
                continue
            ts_type = godot_type_to_ts(prop['type'])
            ts_type_input = godot_type_to_ts(prop['type'], is_input=True)
            getter  = prop.get('getter', '')
            setter  = prop.get('setter', '')
            lines.append(f'{ind2}get {prop["name"]}(): {ts_type};')
            if setter:
                lines.append(f'{ind2}set {prop["name"]}(value: {ts_type_input});')
            # Emit getter/setter as explicit methods when not already in the methods section
            if getter and getter not in declared_methods:
                lines.append(f'{ind2}{sanitize_name(getter)}(): {ts_type};')
            if setter and setter not in declared_methods:
                lines.append(f'{ind2}{sanitize_name(setter)}(value: {ts_type_input}): void;')

        # Signals (as comments — no runtime type)
        for sig in cls_data.get('signals', []):
            params = self._format_params(sig.get('arguments', []))
            lines.append(f'{ind2}{sig["name"]}: Signal')

        # Methods
        for method in cls_data.get('methods', []):
            if self._has_raw_pointer(method):
                continue
            mname  = sanitize_name(method['name'])
            ret_v  = method.get('return_value') or {}
            ret    = godot_type_to_ts(ret_v.get('type', 'void'))
            params = self._format_params(method.get('arguments', []))
            static = 'static ' if method.get('is_static') else ''
            if method.get('is_vararg'):
                params = (params + ', ...args: any[]') if params else '...args: any[]'
            lines.append(f'{ind2}{static}{mname}({params}): {ret};')

        lines.append(f'{ind}}}')

        # Namespace for nested enums
        enums = cls_data.get('enums', [])
        if enums:
            lines.append(f'{ind}namespace {name} {{')
            for enum in enums:
                lines += self._gen_enum(enum, indent + 1)
            lines.append(f'{ind}}}')

        return lines

    # ── Variant class (hand-crafted to match variant_binding.gen.cpp) ────────────

    def _gen_variant_class(self) -> list:
        i = '    '   # 1-level indent (inside declare module)
        ii = '        '  # 2-level
        lines = [
            f'{i}class Variant {{',
            f'{ii}constructor(value?: any);',
            '',
            f'{ii}// Core',
            f'{ii}get_type(): number;',
            f'{ii}booleanize(): boolean;',
            f'{ii}stringify(): string;',
            f'{ii}toString(): string;',
            f'{ii}/** Unwrap to the underlying JS-native value */',
            f'{ii}value(): any;',
            '',
            f'{ii}// Primitive casts',
            f'{ii}as_bool(): boolean;',
            f'{ii}as_int(): number;',
            f'{ii}as_float(): number;',
            f'{ii}as_string(): string;',
            '',
            f'{ii}// Builtin type casts',
            f'{ii}as_vector2(): Vector2;',
            f'{ii}as_vector2i(): Vector2i;',
            f'{ii}as_vector3(): Vector3;',
            f'{ii}as_vector3i(): Vector3i;',
            f'{ii}as_vector4(): Vector4;',
            f'{ii}as_vector4i(): Vector4i;',
            f'{ii}as_rect2(): Rect2;',
            f'{ii}as_rect2i(): Rect2i;',
            f'{ii}as_plane(): Plane;',
            f'{ii}as_quaternion(): Quaternion;',
            f'{ii}as_aabb(): AABB;',
            f'{ii}as_basis(): Basis;',
            f'{ii}as_transform2d(): Transform2D;',
            f'{ii}as_transform3d(): Transform3D;',
            f'{ii}as_projection(): Projection;',
            f'{ii}as_color(): Color;',
            f'{ii}as_string_name(): string;',
            f'{ii}as_node_path(): string;',
            f'{ii}as_rid(): RID;',
            f'{ii}as_callable(): Callable;',
            f'{ii}as_signal(): Signal;',
            f'{ii}as_dictionary(): GDDictionary;',
            f'{ii}as_array(): GDArray;',
            '',
            f'{ii}// Generic operator evaluation',
            f'{ii}evaluate(op: number, right?: VariantArgument): any;',
            '',
            f'{ii}// Binary operators',
            f'{ii}add(right: VariantArgument): any;',
            f'{ii}subtract(right: VariantArgument): any;',
            f'{ii}multiply(right: VariantArgument): any;',
            f'{ii}divide(right: VariantArgument): any;',
            f'{ii}module(right: VariantArgument): any;',
            f'{ii}power(right: VariantArgument): any;',
            f'{ii}shift_left(right: VariantArgument): any;',
            f'{ii}shift_right(right: VariantArgument): any;',
            f'{ii}bit_and(right: VariantArgument): any;',
            f'{ii}bit_or(right: VariantArgument): any;',
            f'{ii}bit_xor(right: VariantArgument): any;',
            f'{ii}equal(right: VariantArgument): any;',
            f'{ii}not_equal(right: VariantArgument): any;',
            f'{ii}less(right: VariantArgument): any;',
            f'{ii}less_equal(right: VariantArgument): any;',
            f'{ii}greater(right: VariantArgument): any;',
            f'{ii}greater_equal(right: VariantArgument): any;',
            f'{ii}and(right: VariantArgument): any;',
            f'{ii}or(right: VariantArgument): any;',
            f'{ii}xor(right: VariantArgument): any;',
            f'{ii}in(right: VariantArgument): any;',
            '',
            f'{ii}// Unary operators',
            f'{ii}negate(): any;',
            f'{ii}positive(): any;',
            f'{ii}bit_negate(): any;',
            f'{ii}not(): any;',
            '',
            f'{ii}// Static',
            f'{ii}static get_type_name(type: number): string;',
            '',
            f'{ii}// Variant.Type constants',
            f'{ii}static readonly TYPE_NIL: number;',
            f'{ii}static readonly TYPE_BOOL: number;',
            f'{ii}static readonly TYPE_INT: number;',
            f'{ii}static readonly TYPE_FLOAT: number;',
            f'{ii}static readonly TYPE_STRING: number;',
            f'{ii}static readonly TYPE_VECTOR2: number;',
            f'{ii}static readonly TYPE_VECTOR2I: number;',
            f'{ii}static readonly TYPE_RECT2: number;',
            f'{ii}static readonly TYPE_RECT2I: number;',
            f'{ii}static readonly TYPE_VECTOR3: number;',
            f'{ii}static readonly TYPE_VECTOR3I: number;',
            f'{ii}static readonly TYPE_TRANSFORM2D: number;',
            f'{ii}static readonly TYPE_VECTOR4: number;',
            f'{ii}static readonly TYPE_VECTOR4I: number;',
            f'{ii}static readonly TYPE_PLANE: number;',
            f'{ii}static readonly TYPE_QUATERNION: number;',
            f'{ii}static readonly TYPE_AABB: number;',
            f'{ii}static readonly TYPE_BASIS: number;',
            f'{ii}static readonly TYPE_TRANSFORM3D: number;',
            f'{ii}static readonly TYPE_PROJECTION: number;',
            f'{ii}static readonly TYPE_COLOR: number;',
            f'{ii}static readonly TYPE_STRING_NAME: number;',
            f'{ii}static readonly TYPE_NODE_PATH: number;',
            f'{ii}static readonly TYPE_RID: number;',
            f'{ii}static readonly TYPE_OBJECT: number;',
            f'{ii}static readonly TYPE_CALLABLE: number;',
            f'{ii}static readonly TYPE_SIGNAL: number;',
            f'{ii}static readonly TYPE_DICTIONARY: number;',
            f'{ii}static readonly TYPE_ARRAY: number;',
            f'{ii}static readonly TYPE_PACKED_BYTE_ARRAY: number;',
            f'{ii}static readonly TYPE_PACKED_INT32_ARRAY: number;',
            f'{ii}static readonly TYPE_PACKED_INT64_ARRAY: number;',
            f'{ii}static readonly TYPE_PACKED_FLOAT32_ARRAY: number;',
            f'{ii}static readonly TYPE_PACKED_FLOAT64_ARRAY: number;',
            f'{ii}static readonly TYPE_PACKED_STRING_ARRAY: number;',
            f'{ii}static readonly TYPE_PACKED_VECTOR2_ARRAY: number;',
            f'{ii}static readonly TYPE_PACKED_VECTOR3_ARRAY: number;',
            f'{ii}static readonly TYPE_PACKED_COLOR_ARRAY: number;',
            f'{ii}static readonly TYPE_PACKED_VECTOR4_ARRAY: number;',
            f'{ii}static readonly TYPE_MAX: number;',
            '',
            f'{ii}// Variant.Operator constants',
            f'{ii}static readonly OP_EQUAL: number;',
            f'{ii}static readonly OP_NOT_EQUAL: number;',
            f'{ii}static readonly OP_LESS: number;',
            f'{ii}static readonly OP_LESS_EQUAL: number;',
            f'{ii}static readonly OP_GREATER: number;',
            f'{ii}static readonly OP_GREATER_EQUAL: number;',
            f'{ii}static readonly OP_ADD: number;',
            f'{ii}static readonly OP_SUBTRACT: number;',
            f'{ii}static readonly OP_MULTIPLY: number;',
            f'{ii}static readonly OP_DIVIDE: number;',
            f'{ii}static readonly OP_NEGATE: number;',
            f'{ii}static readonly OP_POSITIVE: number;',
            f'{ii}static readonly OP_MODULE: number;',
            f'{ii}static readonly OP_POWER: number;',
            f'{ii}static readonly OP_SHIFT_LEFT: number;',
            f'{ii}static readonly OP_SHIFT_RIGHT: number;',
            f'{ii}static readonly OP_BIT_AND: number;',
            f'{ii}static readonly OP_BIT_OR: number;',
            f'{ii}static readonly OP_BIT_XOR: number;',
            f'{ii}static readonly OP_BIT_NEGATE: number;',
            f'{ii}static readonly OP_AND: number;',
            f'{ii}static readonly OP_OR: number;',
            f'{ii}static readonly OP_XOR: number;',
            f'{ii}static readonly OP_NOT: number;',
            f'{ii}static readonly OP_IN: number;',
            f'{ii}static readonly OP_MAX: number;',
            f'{i}}}',
            f'{i}namespace Variant {{',
            f'{ii}type Type = number;',
            f'{ii}type Operator = number;',
            f'{i}}}',
        ]
        return lines
    
    def _gen_utility_functions(self, api: dict, indent: int) -> list:
        ind = self._ind(indent)
        lines = []
        for func in api.get('utility_functions', []):
            name = sanitize_name(func['name'])
            ret = godot_type_to_ts(func.get('return_type', 'void'))
            params = self._format_params(func.get('arguments', []))
            if func.get('is_vararg'):
                params = (params + ', ...args: any[]') if params else '...args: any[]'
            lines.append(f'{ind}{ind}{name}({params}): {ret};')
        return lines

    # ── Top-level ─────────────────────────────────────────────────────────────

    def _generate(self, api: dict) -> list:
        # Collect all builtin classes that are generated
        builtin_types = []
        for cls in api.get('builtin_classes', []):
            name = cls['name']
            if name in SKIP_BUILTINS:
                continue
            builtin_types.append(RENAME_MAP.get(name, name))
        
        variant_arg_types = ['Variant', 'boolean', 'number', 'string', 'GodotObject'] + builtin_types + ['any']
        variant_arg_str = ' | '.join(variant_arg_types)

        lines = []
        lines.append('// Auto-generated by code_generator/dts — do not edit manually.')
        lines.append('')
        lines.append('declare module "godot" {')
        lines.append('')
        lines.append(f'    type VariantArgument = {variant_arg_str};')
        lines.append('')

        # GodotObject base (every Object without an explicit parent inherits this)
        lines += [
            '    class _GodotObject {',
            '        get_instance_id(): number;',
            '        connect(signal: string, callable: (...args: any[]) => void): void;',
            '        disconnect(signal: string, callable: (...args: any[]) => void): void;',
            '        emit_signal(signal: string, ...args: any[]): void;',
            '        to_signal(signal: string, options?: { timeoutMs?: number; abortSignal?: AbortSignal }): Promise<any>;',
            '    }',
            '',
        ]

        # Variant class (hand-crafted — matches variant_binding.gen.cpp)
        lines += self._gen_variant_class()
        lines.append('')

        # Global enums
        for enum in api.get('global_enums', []):
            if enum['name'] in SKIP_GLOBAL_ENUMS:
                continue
            lines += self._gen_enum(enum, indent=1)
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
        for cls in api.get('classes', []):
            lines += self._gen_class(cls, indent=1)
            lines.append('')

        lines.append('    class GD {')
        # Utility functions (sin, cos, print, ...)
        lines += self._gen_utility_functions(api, indent=1)
        lines.append('    }')

        # GodotNamespace — what `import godot from "godot"` returns
        singletons = {s['name']: s['type'] for s in api.get('singletons', [])}

        lines.append('')
        lines.append('    export const Variant: typeof Variant;')
        for cls in api.get('builtin_classes', []):
            name = cls['name']
            if name in SKIP_BUILTINS:
                continue
            ts_name = RENAME_MAP.get(name, name)
            lines.append(f'    export const {ts_name}: typeof {ts_name};')

        for cls in api.get('classes', []):
            name = cls['name']
            lines.append(f'    export const {name}: typeof {name};')

        for s_name, s_type in singletons.items():
            lines.append(f'    export const {s_name}: {s_type};')
        lines.append('    export const GD: GD;')
        lines.append('')
        

        lines.append('    interface GodotNamespace {')
        
        for cls in api.get('builtin_classes', []):
            name = cls['name']
            if name in SKIP_BUILTINS:
                continue
            ts_name = RENAME_MAP.get(name, name)
            lines.append(f'        {ts_name}: typeof {ts_name};')

        for cls in api.get('classes', []):
            name = cls['name']
            lines.append(f'        {name}: typeof {name};')

        for s_name, s_type in singletons.items():
            lines.append(f'        {s_name}: {s_type};')
        lines.append('        GD: GDObjectSingleton;')

        lines.append('    }')
        lines.append('')
        lines.append('    const _godot: GodotNamespace;')
        lines.append('    export default _godot;')
        lines.append('}')

        lines.append('')
        lines.append('declare const Variant: typeof import("godot").Variant;')
        for cls in api.get('builtin_classes', []):
            name = cls['name']
            if name in SKIP_BUILTINS:
                continue
            ts_name = RENAME_MAP.get(name, name)
            lines.append(f'declare const {ts_name}: typeof import("godot").{ts_name};')

        for s_name, s_type in singletons.items():
            lines.append(f'declare const {s_name}: import("godot").{s_type};')
        lines.append('declare const GD: import("godot").GDObjectSingleton;')

        return lines
