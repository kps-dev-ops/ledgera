from django.db import connection


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            with connection.cursor() as c:
                c.execute(
                    "SET LOCAL app.user_id = %s; "
                    "SET LOCAL app.user_email = %s; "
                    "SET LOCAL app.ip = %s;",
                    [str(request.user.id), request.user.email, get_client_ip(request)],
                )
        return self.get_response(request)
