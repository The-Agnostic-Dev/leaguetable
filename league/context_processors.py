from . import permissions


def roles(request):
    user = request.user
    return {
        "is_secretary": permissions.is_secretary(user),
        "can_enter_results": permissions.can_enter_results(user),
    }
