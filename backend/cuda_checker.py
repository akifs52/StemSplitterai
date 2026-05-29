def _ensure_cuda_dll_path():
    import os
    import sys
    if os.name != 'nt':
        return
    try:
        if hasattr(sys, '_MEIPASS'):
            torch_lib = os.path.join(sys._MEIPASS, "torch", "lib")
        else:
            import torch
            torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
        if os.path.isdir(torch_lib):
            os.add_dll_directory(torch_lib)
    except Exception:
        pass


def has_cuda():
    _ensure_cuda_dll_path()
    import torch
    return torch.cuda.is_available()


def gpu_name():
    _ensure_cuda_dll_path()
    import torch
    if torch.cuda.is_available():
        return torch.cuda.get_device_name(0)
    return "CPU"


def device_info():
    _ensure_cuda_dll_path()
    import torch
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        return {
            "name": props.name,
            "memory": round(props.total_memory / 1024**3, 1),
            "cores": props.multi_processor_count,
            "cuda_version": torch.version.cuda,
        }
    return {"name": "CPU", "memory": 0, "cores": 0, "cuda_version": None}
