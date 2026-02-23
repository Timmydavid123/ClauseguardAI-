import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Contract, Risk
from .services import extract_text_from_file, extract_text_from_pdf, analyze_contract
from .tasks import analyze_contract_task
from celery.result import AsyncResult
from analyzer.models import Risk

logger = logging.getLogger(__name__)
def _json_error(message, status=400):
    return JsonResponse({"success": False, "error": message}, status=status)
# Public views (no login required)
def landing(request):
    """Public landing page"""
    return render(request, 'analyzer/landing.html')

# Protected views (login required)
@login_required
def index(request):
    recent = Contract.objects.filter(user=request.user)[:5]
    return render(request, 'analyzer/index.html', {'recent': recent})

@login_required
def history(request):
    contracts = Contract.objects.filter(user=request.user)
    return render(request, 'analyzer/history.html', {'contracts': contracts})

@login_required
def results(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id, user=request.user)
    analysis = contract.analysis_json
    return render(request, 'analyzer/results.html', {
        'contract': contract,
        'risks': contract.risks.all(),
        'missing_protections': analysis.get('missing_protections', []),
        'positive_clauses': analysis.get('positive_clauses', []),
        'quick_stats': analysis.get('quick_stats', {}),
        'party_info': analysis.get('party_info', {}),
    })

@login_required
@require_POST
def analyze_document(request):
    uploaded = request.FILES.get("contract_pdf") or request.FILES.get("contract_document")
    if not uploaded:
        return _json_error("No file uploaded. Field must be contract_pdf.", 400)
    
    if uploaded.size > 10 * 1024 * 1024:
        return JsonResponse({'error': 'File too large. Max 10MB.'}, status=400)

    try:
        # Use your extract_text_from_file function that handles multiple types
        text = extract_text_from_file(uploaded, uploaded.name)
    except ValueError as e:
        # Handle unsupported file types
        logger.error(f"Unsupported file type: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Text extraction failed: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Could not read file: {e}'}, status=422)

    if len(text.strip()) < 100:
        return JsonResponse({'error': 'File has no readable text.'}, status=422)

    return _run_analysis(request, text, uploaded.name)

@login_required
@require_POST
def analyze_text(request):
    if request.content_type != "application/json":
        return _json_error("Content-Type must be application/json", 415)

    try:
        body = json.loads(request.body.decode("utf-8"))
        text = (body.get("text") or "").strip()
    except Exception:
        logger.exception("Invalid JSON")
        return _json_error("Invalid JSON body", 400)

    if len(text) < 100:
        return _json_error("Text too short. Please paste more content.", 400)

    return _run_analysis(request, text, "Pasted Contract")

@login_required
@require_POST
def update_risk(request, risk_id):
    risk = get_object_or_404(Risk, id=risk_id, contract__user=request.user)
    try:
        body = json.loads(request.body)
        risk.status = body.get('status', risk.status)
        risk.user_note = body.get('note', risk.user_note)
        risk.save()
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Failed to update risk {risk_id}: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def delete_contract(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id, user=request.user)
    contract.delete()
    return JsonResponse({'success': True})

@login_required
def task_status(request, task_id):
    """Check the status of a Celery task"""
    task = AsyncResult(task_id)
    
    if task.ready():
        result = task.result
        if result and result.get('success'):
            return JsonResponse({
                'status': 'SUCCESS',
                'redirect': result.get('redirect')
            })
        else:
            return JsonResponse({
                'status': 'FAILURE',
                'error': result.get('error') if result else 'Unknown error'
            })
    else:
        meta = task.info or {}
        return JsonResponse({
            'status': 'PROGRESS',
            'progress': meta.get('progress', 0),
            'message': meta.get('message', 'Processing...')
        })
    
def _run_analysis(request, text, filename):
    """Helper function to handle both file and text analysis"""
    try:
        # Create contract record with correct field names
        contract = Contract.objects.create(
            user=request.user,
            filename=filename,  # Changed from 'title' to 'filename'
            raw_text=text,      # Changed from 'original_text' to 'raw_text'
            # No status field for Contract - remove it
            # You might want to set initial values for these:
            summary='',  # Will be filled by analysis
            overall_risk_score=0,
            overall_risk_level='Low',
            analysis_json={}
        )
        
        # Start Celery task for analysis
        task = analyze_contract_task.delay(contract.id)
        
        # Return task ID for polling
        return JsonResponse({
            'success': True,
            'task_id': task.id,
            'message': 'Analysis started'
        })
        
    except Exception as e:
        logger.error(f"Failed to start analysis: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Failed to start analysis: {str(e)}'
        }, status=500)