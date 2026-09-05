#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
from urllib.parse import urlparse


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def host_matches(host, registered):
    return any(host == h or host.endswith('.' + h) for h in registered)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--registry', default='medical/knowledge-base/SOURCE_REGISTRY.json')
    ap.add_argument('--case-root', default='medical/case-families')
    ap.add_argument('--strict-hosts', action='store_true')
    args = ap.parse_args()

    errors, warnings = [], []
    reg = load_json(args.registry)
    ids = [s['source_id'] for s in reg['sources']]
    if len(ids) != len(set(ids)):
        errors.append('duplicate source_id in registry')
    hosts = {s['host'] for s in reg['sources']}

    manifests = sorted(Path(args.case_root).glob('*/evidence.json'))
    source_count = claim_count = 0

    for path in manifests:
        data = load_json(path)
        local_sources = {}
        for src in data.get('sources', []):
            source_count += 1
            sid = src.get('source_id')
            if not sid:
                errors.append(f'{path}: source missing source_id')
                continue
            if sid in local_sources:
                errors.append(f'{path}: duplicate local source_id {sid}')
            local_sources[sid] = src
            url = src.get('url', '')
            if url.startswith('groundsignal://'):
                continue
            if not url:
                errors.append(f'{path}: {sid} missing URL')
                continue
            host = (urlparse(url).hostname or '').lower()
            if not host_matches(host, hosts):
                msg = f'{path}: unregistered source host {host} ({sid})'
                (errors if args.strict_hosts else warnings).append(msg)

        seen_passages = set()
        for claim in data.get('claims', []):
            claim_count += 1
            cid = claim.get('claim_id', '<missing>')
            sid = claim.get('source_id')
            if sid not in local_sources:
                errors.append(f'{path}: {cid} references missing source_id {sid}')
            pid = claim.get('passage_id')
            if not pid:
                errors.append(f'{path}: {cid} missing passage_id')
            elif pid in seen_passages:
                warnings.append(f'{path}: repeated passage_id {pid}')
            else:
                seen_passages.add(pid)
            if not claim.get('locator'):
                errors.append(f'{path}: {cid} missing locator')
            if not claim.get('claim_scope'):
                errors.append(f'{path}: {cid} missing claim_scope')
            if not claim.get('evidence_role'):
                errors.append(f'{path}: {cid} missing evidence_role')
            if claim.get('review_status') == 'source_verified':
                src = local_sources.get(sid, {})
                if not src.get('document_date'):
                    warnings.append(f'{path}: source-verified {cid} source has no document_date')

    print(json.dumps({
        'registry_sources': len(reg['sources']),
        'evidence_manifests': len(manifests),
        'local_sources': source_count,
        'claims': claim_count,
        'warnings': len(warnings),
        'errors': len(errors)
    }, ensure_ascii=False, indent=2))
    for w in warnings:
        print('WARN', w)
    for e in errors:
        print('ERROR', e, file=sys.stderr)
    return 1 if errors else 0

if __name__ == '__main__':
    raise SystemExit(main())
