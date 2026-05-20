import torch


def has_cuda():
    return torch.cuda.is_available()


def gpu_name():
    if torch.cuda.is_available():
        return torch.cuda.get_device_name(0)
    return "CPU"


def device_info():
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        return {
            "name": props.name,
            "memory": round(props.total_memory / 1024**3, 1),
            "cores": props.multi_processor_count,
            "cuda_version": torch.version.cuda,
        }
    return {"name": "CPU", "memory": 0, "cores": 0, "cuda_version": None}
