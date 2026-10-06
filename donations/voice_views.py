import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User

from .voice_parser import DonationVoiceParser, VoiceParseError, VoiceParserUnavailable, VoiceProviderError


@login_required(login_url="login")
@role_required(User.Role.DONOR)
@require_POST
def voice_parse(request):
    """Parse a spoken donation description into form field suggestions. Nothing is saved."""
    try:
        payload = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"detail": "Invalid request body."}, status=400)
    transcript = payload.get("transcript") if isinstance(payload, dict) else None
    if not isinstance(transcript, str):
        return JsonResponse({"detail": "A transcript is required."}, status=400)
    try:
        result = DonationVoiceParser().parse(transcript)
    except VoiceParserUnavailable as error:
        return JsonResponse({"detail": str(error)}, status=503)
    except VoiceProviderError as error:
        return JsonResponse({"detail": str(error)}, status=502)
    except VoiceParseError as error:
        return JsonResponse({"detail": str(error)}, status=400)
    return JsonResponse(result)
