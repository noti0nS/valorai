import json

from django.http import HttpResponse
from django.urls import path

from valorai.runtime import current_api


def dispatch(request, unused=None):
    import traceback
    try:
        api = current_api()
        body = request.body if request.method == "POST" else b""
        result = api.handle(request.method, request.build_absolute_uri(), dict(request.headers), body)
    except Exception:
        traceback.print_exc()
        payload = json.dumps({"error": "Não foi possível concluir agora. Tente novamente em instantes."}, ensure_ascii=False)
        return HttpResponse(payload, status=500, content_type="application/json")
    response = HttpResponse(json.dumps(result.body, ensure_ascii=False), status=result.status, content_type="application/json")
    for key, value in result.headers.items():
        response[key] = value
    return response


urlpatterns = [path("<path:unused>", dispatch), path("", dispatch)]
