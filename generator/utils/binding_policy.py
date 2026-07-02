from typing import Optional, Sequence, Set


METHOD_BIND_OUT_ARGUMENTS = {
    ("ResourceLoader", "load_threaded_get_status"): (1,),
    ("OS", "execute"): (2,),
    ("EditorExportPlatform", "ssh_run_on_remote"): (4,),
    ("VideoStreamPlayback", "mix_audio"): (1,),
}


def _clean_pointer_type(type_name: str) -> str:
    clean_type = type_name.replace('*', '').strip()
    if clean_type.startswith('const '):
        clean_type = clean_type[6:].strip()
    return clean_type


def is_safe_pointer_argument(type_name: str, object_class_names: Optional[Set[str]] = None) -> bool:
    if '*' not in type_name:
        return True
    if object_class_names is None:
        return False
    return _clean_pointer_type(type_name) in object_class_names


def skipped_method_reason(method: dict, object_class_names: Optional[Set[str]] = None) -> Optional[str]:
    return_value = method.get('return_value')
    return_type = method.get('return_type')
    if return_value:
        return_type = return_value.get('type') if isinstance(return_value, dict) else return_value
    if return_type and '*' in return_type:
        return f"raw pointer return type {return_type}"

    for arg in method.get('arguments', []):
        arg_type = arg.get('type', '')
        if not is_safe_pointer_argument(arg_type, object_class_names):
            return f"raw pointer argument {arg.get('name', '<unnamed>')}: {arg_type}"

    return None


def is_method_bindable(method: dict, object_class_names: Optional[Set[str]] = None) -> bool:
    return skipped_method_reason(method, object_class_names) is None


def method_bind_out_argument_indices(class_name: str, method: dict) -> Sequence[int]:
    return METHOD_BIND_OUT_ARGUMENTS.get((class_name, method.get("name", "")), ())
