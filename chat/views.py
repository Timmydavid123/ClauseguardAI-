import json
import anthropic
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings
from analyzer.models import Contract
from .models import ChatMessage


@login_required
@require_POST
def send_message(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id, user=request.user)

    try:
        body = json.loads(request.body)
        user_message = body.get('message', '').strip()
    except Exception:
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    if not user_message:
        return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

    # Save user message
    ChatMessage.objects.create(
        contract=contract,
        user=request.user,
        role='user',
        content=user_message,
    )

    # Build conversation history for AI
    history = contract.messages.all()
    messages = [
        {'role': m.role, 'content': m.content}
        for m in history
    ]

    # System prompt with contract context
    system = f"""You are ClauseGuard's AI legal assistant. You help users understand their contracts.

You have already analyzed this contract and here is the context:

CONTRACT SUMMARY: {contract.summary}
RISK LEVEL: {contract.overall_risk_level} ({contract.overall_risk_score}/100)
DOCUMENT TYPE: {contract.analysis_json.get('party_info', {}).get('document_type', 'Unknown')}

CONTRACT TEXT (first 4000 chars):
{contract.raw_text[:4000]}

IDENTIFIED RISKS:
{json.dumps(contract.analysis_json.get('risks', []), indent=2)[:2000]}

Answer the user's questions about this specific contract in plain English.
Be helpful, clear, and practical. If asked about legal advice, remind them to consult a lawyer.
Keep responses concise and focused."""

    try:
        client = anthropic.Anthropic(api_key=settings.AI_API_KEY)
        response = client.messages.create(
            model='claude-opus-4-6',
            max_tokens=1000,
            system=system,
            messages=messages,
        )
        ai_reply = response.content[0].text
    except Exception as e:
        return JsonResponse({'error': f'AI error: {str(e)}'}, status=500)

    # Save AI reply
    ChatMessage.objects.create(
        contract=contract,
        user=request.user,
        role='assistant',
        content=ai_reply,
    )

    return JsonResponse({'success': True, 'reply': ai_reply})


@login_required
def get_messages(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id, user=request.user)
    messages = contract.messages.values('role', 'content', 'created_at')
    return JsonResponse({'messages': list(messages)})
