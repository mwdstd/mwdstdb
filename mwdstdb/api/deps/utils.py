from fastapi import Request

async def get_resource_id(request: Request):
    for k, v in request.path_params.items():
        if k.endswith('_id'):
            return v
    return None
