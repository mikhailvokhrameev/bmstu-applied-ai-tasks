"""Explicit model wiring; no default model or acceptance attestation."""
from dataclasses import asdict
from .proposals import OllamaModels, SemanticDeduplicator, ModelResponse, ProposalError, parse_proposal, render_prompt
from .search import ControlGenerator
from .bridge import evaluate, CORE
from .metrics import compute_metrics, fitness, BASELINE

class ModelGenerator:
    def __init__(self,propose,context):self.propose,self.context,self.attempts=propose,context,[]
    def __call__(self,parent,rng):
        self.attempts=[];context=self.context(parent);error=None
        for _ in range(3):
            attempt=dict(request=render_prompt(context,error),context=context,previous_error=error)
            owner=getattr(self.propose,'__self__',None)
            if isinstance(owner,OllamaModels):
                attempt['http_request']=dict(url=owner.endpoint+'/api/generate',payload=dict(model=owner.model,prompt=attempt['request'],stream=False,format='json',options=dict(temperature=.7,top_p=.95,num_predict=2000,num_ctx=32768,seed=owner.seed)))
            self.attempts.append(attempt)
            try:
                response=self.propose(context,error)
                attempt['response']=asdict(response) if isinstance(response,ModelResponse) else response
            except Exception as exc:
                if isinstance(getattr(exc,'response',None),ModelResponse):
                    attempt['response']=asdict(exc.response)
                attempt['service_error']=str(exc);raise
            try:
                p=parse_proposal(response.text if isinstance(response,ModelResponse) else response)
                # Mutation operates on the parent, unlike crossover's set union.
                # Removing a previously introduced axiom cancels that addition.
                added=set(parent['add']);removed=set(parent['remove'])
                return dict(add=sorted((added-set(p.remove)) | set(p.add)),
                            remove=sorted((removed-set(p.add)) | (set(p.remove)-added)))
            except ValueError as exc:
                error=str(exc);attempt['parse_error']=error
        raise ProposalError('Three unsuccessful attempts: '+error)

def build_runtime(manifest,seed):
    required=('model','embedding_model','model_sha256','embedding_sha256','server_version','acceptance_approved','inventory','entities')
    if any(k not in manifest for k in required) or manifest['acceptance_approved'] is not True:
        raise ValueError('Explicit pinned model manifest and acceptance_approved required; T04 is not inferred')
    models=OllamaModels(manifest['model'],manifest['embedding_model'],manifest.get('endpoint','http://127.0.0.1:11434'),seed)
    def context(delta):
        result=evaluate(CORE,delta['add'],delta['remove']);m=compute_metrics(result['counts'])
        return dict(ontology_manchester=result['manchester'],metrics=asdict(m),relative=fitness(m,BASELINE).relative)
    return dict(model_generator=ModelGenerator(models.propose,context),control_generator=ControlGenerator(manifest['inventory']),
                duplicate_checker=SemanticDeduplicator(models.embed,manifest['entities']))
