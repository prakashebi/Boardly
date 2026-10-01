from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if "detail" not in response.data:
            if isinstance(response.data, dict):
                response.data = {"detail": str(response.data)}
            else:
                response.data = {"detail": response.data}
        return response

    return response
