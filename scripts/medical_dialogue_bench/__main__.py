import argparse
import json
from pathlib import Path
from scripts.patient_eval.import_batch import write_new_json
from scripts.patient_eval import app_pilot
from .assets import load_assets
from .runtime import batch
from .verifier import verify


def main(argv=None):
    parser=argparse.ArgumentParser(description='12-card synthetic medical dialogue benchmark')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('validate')
    run=sub.add_parser('run');run.add_argument('--backend',choices=['oracle','noop','naive','stale','openai'],default='oracle')
    run.add_argument('--model');run.add_argument('--out',required=True);run.add_argument('--repeats',type=int,default=1)
    run.add_argument('--probe',action='store_true');run.add_argument('--max-calls',type=int,default=72)
    run.add_argument('--max-output-tokens',type=int,default=2048);run.add_argument('--resume',action='store_true')
    run.add_argument('--key-env',default='OPENAI_API_KEY')
    check=sub.add_parser('verify');check.add_argument('--reviews',nargs='*');check.add_argument('--out')
    review=sub.add_parser('review');review.add_argument('--reviewer',required=True);review.add_argument('--out',required=True)
    judge=sub.add_parser('judge');judge.add_argument('--reviewer',required=True);judge.add_argument('--model',required=True)
    judge.add_argument('--key-env',default='OPENAI_API_KEY');judge.add_argument('--max-calls',type=int,default=200);judge.add_argument('--out',required=True)
    for command in [check,review,judge]:command.add_argument('--run',required=True)
    args=parser.parse_args(argv)
    try:
        suite,sha,patients,asset_sha=load_assets()
        if args.command=='validate':result=dict(cases=len(suite['scenarios']),families=6,asset_sha256=asset_sha,clinical_approval=False)
        elif args.command=='run':
            if args.backend=='openai':
                from .client import ResponsesClient
                client=ResponsesClient(args.model,args.key_env,args.max_output_tokens)
            else:
                from .oracle import Oracle
                client=Oracle(args.backend)
            batch(suite,sha,patients,asset_sha,client,args.out,backend=args.backend,model=args.model if args.backend=='openai' else 'authored-'+args.backend,repeats=args.repeats,probe=args.probe,max_calls=args.max_calls,max_output_tokens=args.max_output_tokens,resume=args.resume)
            _,result=verify(args.out,suite,sha,patients,asset_sha)
        else:
            sessions,result=verify(args.run,suite,sha,patients,asset_sha)
            if args.command=='verify':
                packets=[json.loads(Path(p).read_text()) for p in (args.reviews or [])]
                _,result=verify(args.run,suite,sha,patients,asset_sha,packets)
                if args.out:write_new_json(args.out,result)
            elif args.command=='review':
                packet=app_pilot.make_review(sessions,suite,sha,args.reviewer);write_new_json(args.out,packet)
                html=Path(args.out).with_suffix('.html')
                with html.open('x',encoding='utf-8') as stream:stream.write(app_pilot.render_page('review.html',dict(packet=packet,sessions=sessions,suite=suite)))
                result=dict(review_rows=len(packet['rows']),scored=0,clinical_approval=False)
            else:
                from .client import ResponsesClient
                from .judge import draft
                if Path(args.out).exists():raise ValueError('refusing to overwrite judge output')
                packet,result=draft(sessions,suite,sha,ResponsesClient(args.model,args.key_env),args.reviewer,args.max_calls)
                write_new_json(args.out,packet);write_new_json(str(args.out)+'.audit.json',result)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,KeyError,TypeError,OSError) as exc:parser.exit(2,'benchmark failed: '+str(exc)+'\n')

if __name__=='__main__':main()
