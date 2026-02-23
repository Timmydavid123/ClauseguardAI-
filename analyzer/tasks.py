# analyzer/tasks.py
import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from .models import Contract, Risk
from .services import analyze_contract

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def analyze_contract_task(self, contract_id):
    """
    Celery task to analyze contract asynchronously
    Takes a contract_id and updates the existing contract with analysis results
    """
    try:
        # Get the contract
        contract = Contract.objects.get(id=contract_id)
        
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={
                'step': 'analyzing',
                'message': 'AI is analyzing your contract...',
                'progress': 50
            }
        )
        
        logger.info(f"Starting analysis for contract {contract_id}, file: {contract.filename}")
        
        # Run the actual analysis (this makes the Anthropic API call)
        analysis = analyze_contract(contract.raw_text)
        
        self.update_state(
            state='PROGRESS',
            meta={
                'step': 'saving',
                'message': 'Saving analysis results...',
                'progress': 90
            }
        )
        
        # Update contract with analysis results
        contract.summary = analysis.get('summary', '')
        contract.overall_risk_score = analysis.get('overall_risk_score', 0)
        contract.overall_risk_level = analysis.get('overall_risk_level', 'Low')
        contract.analysis_json = analysis
        contract.save()
        
        # Save individual risks
        for r in analysis.get('risks', []):
            Risk.objects.create(
                contract=contract,
                risk_id=r.get('id', ''),
                title=r.get('title', ''),
                severity=r.get('severity', 'Low'),
                category=r.get('category', 'Other'),
                clause=r.get('clause', ''),
                explanation=r.get('explanation', ''),
                recommendation=r.get('recommendation', ''),
            )
        
        logger.info(f"Analysis complete for contract {contract.id}")
        
        return {
            'success': True,
            'contract_id': contract.id,
            'redirect': f'/results/{contract.id}/'
        }
        
    except Contract.DoesNotExist:
        logger.error(f"Contract {contract_id} not found")
        return {
            'success': False,
            'error': f'Contract {contract_id} not found'
        }
    except Exception as e:
        logger.error(f"Task failed: {str(e)}", exc_info=True)
        
        # Update contract to show failure if needed
        try:
            contract = Contract.objects.get(id=contract_id)
            contract.analysis_json = {'error': str(e)}
            contract.save()
        except:
            pass
            
        return {
            'success': False,
            'error': str(e)
        }