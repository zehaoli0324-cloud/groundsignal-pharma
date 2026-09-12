"""Official Responses transport: stateless visible messages, no hidden tools."""
import json
import os
import urllib.request
import urllib.error
from scripts.patient_eval.adapters import NoRedirect
from scripts.patient_eval.contracts import require

class ResponsesClient:
    def __init__(self,model,key_env='OPENAI_API_KEY',max_output_tokens=2048,timeout=60):
        require(isinstance(model,str) and bool(model.strip()),'explicit model ID required')
        require(type(max_output_tokens) is int and 128<=max_output_tokens<=32768,'invalid output cap')
        require(type(timeout) in {int,float} and 0<timeout<=120,'invalid timeout')
        key=os.environ.get(key_env)
        require(bool(key),'missing credential environment variable: '+key_env)
        self.model,self.key,self.cap,self.timeout=model,key,max_output_tokens,timeout
        self.opener=urllib.request.build_opener(NoRedirect())
    def __call__(self,messages):
        require(all(set(m)=={'role','content'} and m['role'] in {'system','user','assistant'} and isinstance(m['content'],str) for m in messages),'visible messages only')
        payload=dict(model=self.model,input=messages,max_output_tokens=self.cap,store=False)
        req=urllib.request.Request('https://api.openai.com/v1/responses',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
        try:
            with self.opener.open(req,timeout=self.timeout) as stream: raw=stream.read(2_000_001)
            require(len(raw)<=2_000_000,'oversized response')
            result=json.loads(raw)
            require(isinstance(result,dict),'response must be an object')
            usage={k:v for k,v in result.get('usage',{}).items() if k in {'input_tokens','output_tokens','total_tokens'} and type(v) is int and v>=0}
            text='\n'.join(part.get('text',part.get('refusal','')) for item in result.get('output',[]) if item.get('type')=='message' and item.get('role')=='assistant' for part in item.get('content',[]) if part.get('type') in {'output_text','refusal'})
            status=result.get('status')
            error=None if status=='completed' and text.strip() else ('output_incomplete' if status=='incomplete' else 'invalid_response_schema')
            return dict(content=text or None,error=error,usage=usage,provider_model=result.get('model',self.model))
        except urllib.error.HTTPError as exc:return dict(content=None,error='http_'+str(exc.code),usage={},provider_model=self.model)
        except (urllib.error.URLError,TimeoutError,OSError):return dict(content=None,error='transport_error',usage={},provider_model=self.model)
        except (ValueError,KeyError,TypeError,AttributeError,UnicodeError):return dict(content=None,error='invalid_response_schema',usage={},provider_model=self.model)
