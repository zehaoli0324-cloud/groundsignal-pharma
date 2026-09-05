#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
from urllib.parse import urlparse


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def host_matches(host, registered):
    return any(host == h or host.endswith('.' + h) for h in registered)


def validate_backbone(path, registry_ids, errors, warnings):
    modules = claims_n = 0
    p = Path(path)
    if not p.exists():
        warnings.append(f'backbone not found: {p}')
        return modules, claims_n
    backbone = load_json(p)
    seen_modules = set()
    for module in backbone.get('modules', []):
        modules += 1
        mid = module.get('module_id')
        if not mid:
            errors.append(f'{p}: module missing module_id')
        elif mid in seen_modules:
            errors.append(f'{p}: duplicate module_id {mid}')
        else:
            seen_modules.add(mid)
        sid = module.get('source_id')
        if sid not in registry_ids:
            errors.append(f'{p}: {mid} references unregistered source_id {sid}')
        if not module.get('evidence_scope'):
            errors.append(f'{p}: {mid} missing evidence_scope')
        if not module.get('forbidden_inference'):
            warnings.append(f'{p}: {mid} missing forbidden_inference')
        claims = module.get('claims', [])
        if not claims:
            errors.append(f'{p}: {mid} has no claims')
        for claim in claims:
            claims_n += 1
            for key in ('subject', 'predicate', 'object', 'locator', 'review_status'):
                if not claim.get(key):
                    errors.append(f'{p}: {mid} claim missing {key}')
    return modules, claims_n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--registry', default='medical/knowledge-base/SOURCE_REGISTRY.json')
    ap.add_argument('--registry-supplement', default='medical/knowledge-base/SOURCE_REGISTRY_SUPPLEMENT.json')
    ap.add_argument('--case-root', default='medical/case-families')
    ap.add_argument('--backbone', action='append', default=[])
    ap.add_argument('--strict-hosts', action='store_true')
    args = ap.parse_args()

    errors, warnings = [], []
    reg = load_json(args.registry)
    registered_sources = list(reg['sources'])
    supplement_path = Path(args.registry_supplement)
    if supplement_path.exists():
        supplement = load_json(supplement_path)
        registered_sources.extend(supplement.get('sources', []))

    ids = [s['source_id'] for s in registered_sources]
    if len(ids) != len(set(ids)):
        errors.append('duplicate source_id across source registries')
    registry_ids = set(ids)

    hosts = set()
    for s in registered_sources:
        if s.get('host'):
            hosts.add(s['host'])
        hosts.update(s.get('hosts', []))

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

    backbones = args.backbone or [
        'medical/knowledge-base/PHARMACOLOGY_BACKBONE_V0.1.json',
        'medical/knowledge-base/ORGAN_SPECIAL_POP_SAFETY_BACKBONE_V0.1.json',
    ]
    backbone_modules = backbone_claims = 0
    backbone_breakdown = {}
    for path in backbones:
        m, c = validate_backbone(path, registry_ids, errors, warnings)
        backbone_modules += m
        backbone_claims += c
        backbone_breakdown[path] = {'modules': m, 'claims': c}

    print(json.dumps({
        'registry_sources': len(registered_sources),
        'evidence_manifests': len(manifests),
        'local_sources': source_count,
        'case_claims': claim_count,
        'backbone_modules': backbone_modules,
        'backbone_claims': backbone_claims,
        'backbone_breakdown': backbone_breakdown,
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
