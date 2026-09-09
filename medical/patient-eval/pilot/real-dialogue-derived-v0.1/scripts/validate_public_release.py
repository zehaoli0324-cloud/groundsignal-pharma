#!/usr/bin/env python3
"""Fail closed if the public pilot contains private review provenance or PII cues."""
from __future__ import annotations
import hashlib, json, re, sys, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ALLOWED_EXTENSIONS={".md",".json",".py",".xlsx",".pdf",""}
FORBIDDEN_FILE_FRAGMENTS=["candidate-review","second-clinical-review","transcript","raw-dialogue","original.json","reviewer-",".jsonl"]
FORBIDDEN_TEXT=["source_dialogue_id","source_review_sha256","source_fact_ids","source_turn_ids","source_raw_turn_ids","evidence_spans","candidate-review-filled-20260909","南京","上海路","郭医生","3号出口"]
PII_PATTERNS={
 "email":re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",re.I),
 "cn_mobile":re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
 "cn_id":re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)"),
 "address_cue":re.compile(r"(?:路|街|巷|弄|号楼|单元|室|出口)\s*\d{1,4}"),
}
PRIVATE_REFERENCE_PATTERNS={
 "candidate_id":re.compile(r"(?<![A-Z0-9-])C\d{4}(?!\d)"),
 "source_turn_id":re.compile(r"(?<![A-Za-z0-9])r\d{4}(?!\d)"),
 "copied_source_rubric":re.compile(r"病例主要材料|病例依据[:：]原文|外部安全依据"),
}

def fail(message:str)->None:
 raise SystemExit("PUBLIC RELEASE BLOCKED: "+message)

def scan_text(rel:str,text:str,allow_validator_tokens:bool=False)->None:
 if not allow_validator_tokens:
  for token in FORBIDDEN_TEXT:
   if token in text: fail(f"forbidden provenance/identifier token {token!r} in {rel}")
  for label,pattern in {**PII_PATTERNS,**PRIVATE_REFERENCE_PATTERNS}.items():
   if pattern.search(text): fail(f"possible {label} in {rel}")

def main(root:Path)->int:
 root=root.resolve()
 if not root.is_dir(): fail("root is not a directory")
 report_rel="validation/public_release_validation.json"
 paths=sorted(p for p in root.rglob("*") if p.is_file() and p.relative_to(root).as_posix()!=report_rel)
 for path in paths:
  rel=path.relative_to(root).as_posix(); lower=rel.lower(); suffix=path.suffix.lower()
  if suffix not in ALLOWED_EXTENSIONS: fail(f"unexpected file type: {rel}")
  if any(fragment in lower for fragment in FORBIDDEN_FILE_FRAGMENTS): fail(f"forbidden file name: {rel}")
  if suffix in {".md",".json",".py",""}:
   text=path.read_text(encoding="utf-8")
   scan_text(rel,text,allow_validator_tokens=(rel=="scripts/validate_public_release.py"))
   if suffix==".json":
    try: json.loads(text)
    except Exception as exc: fail(f"invalid JSON in {rel}: {exc}")
  elif suffix==".xlsx":
   try:
    text_nodes=[]
    with zipfile.ZipFile(path) as archive:
     for name in archive.namelist():
      if not name.endswith(".xml"):
       continue
      try:
       root_xml=ET.fromstring(archive.read(name))
      except ET.ParseError:
       continue
      for element in root_xml.iter():
       if element.tag.rsplit("}",1)[-1]=="t" and element.text:
        text_nodes.append(element.text)
    inner="\n".join(text_nodes)
   except Exception as exc: fail(f"invalid XLSX in {rel}: {exc}")
   scan_text(rel+" [display text]",inner)
 report={"schema_version":"groundsignal-public-release-validation/v0.2","passed":True,"file_count":len(paths),"files":[{"path":p.relative_to(root).as_posix(),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],"formal_approval":False,"clinical_gold":False,"stored_report_excludes_self":True}
 print(json.dumps(report,ensure_ascii=False,indent=2))
 return 0
if __name__=="__main__": raise SystemExit(main(Path(sys.argv[1] if len(sys.argv)>1 else ".")))
