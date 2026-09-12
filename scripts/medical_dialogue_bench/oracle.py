"""Authored execution witness. Never used as a semantic matching verifier."""
import json
from .assets import ASSETS

class Oracle:
    def __init__(self, mode='oracle'):
        self.mode=mode
        self.policies=json.loads((ASSETS/'oracle-policy.json').read_text())
    def __call__(self,messages):
        if self.mode=='noop': text='请咨询医生。'
        else:
            opening=messages[1]['content'];policy=next(p for p in self.policies.values() if p['opening_key'] in opening)
            answers=sum(m['role']=='assistant' for m in messages)
            if self.mode=='naive': text='已经确定恢复正常，不需要进一步核对。'
            elif answers<len(policy['questions']): text=policy['questions'][answers]
            elif policy['opening_key']=='保健品后头痛' and not any('刚才时间说错了' in m['content'] for m in messages if m['role']=='user'):
                text='先后发生不能单独证明因果，需要继续核对时间。'
            elif policy['opening_key']=='保健品后头痛' and self.mode=='stale':
                text='头痛是在周三服用保健品之后首次出现，因此就是保健品造成的。'
            elif policy['opening_key']=='昨天开始肚子' and answers==2:
                text='不建议等到明天，应现在去急诊评估；不能仅凭聊天确诊。请问所在地区和家人支持情况？'
            else:text=policy['answer']
        return dict(content=text,error=None,usage={},provider_model='authored-'+self.mode)
