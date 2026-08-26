"""Canonical report construction and fail-closed validation for TC-FIXTURE-003."""
from __future__ import annotations
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable
from .trove_curata_transform_contract import FALSE_CLAIMS,FIXTURE_ID,PLAN_STATUSES,PREDECESSOR,ROUTES,SCHEMA_VERSION,canonical_json_bytes,content_id,require,sha256_bytes
from .trove_curata_transform_engine import apply_baseline_fragment,assemble_output,evaluate_plan,predecessor_context,residual_audit,simulate_provider_fragment

def _output(source:str,text:str,engine:str)->dict[str,Any]:
    p={"source_sha256":source,"output_sha256":sha256_bytes(text.encode()),"byte_length":len(text.encode()),"engine":engine}
    return {"record_type":"curata_derived_output","output_record_id":content_id("curata-derived-output",p),**p,"source_record_mutated":False,"admission_state":"not_admitted","deletion_state":"not_deleted"}

def _route(case,status,disagreement,residual):
    return "review_required" if case["policy_state"]=="review_required" or status!="accepted" or disagreement or residual else "transformation_verified"

def build_report(manifest,fixture_root,versions,provider_transform:Callable|None=None):
    root=Path(fixture_root); pm_path=root/manifest["predecessor_manifest"]; pm=json.loads(pm_path.read_text()); proot=pm_path.parent
    provider_transform=provider_transform or simulate_provider_fragment
    config={"fixture_id":FIXTURE_ID,"schema_version":SCHEMA_VERSION,"predecessor":PREDECESSOR,"providers":versions,"plan_authority":"gcl_owned_static_manifest","fragment_scoped_provider_execution":True,"gcl_output_assembly":True,"source_records_immutable":True,"external_project_dependency":False,"network_required_for_replay":False}
    cfg=sha256_bytes(canonical_json_bytes(config)); reports=[]; groups={}
    for case in sorted(manifest["cases"],key=lambda x:x["case_id"]):
        ctx=predecessor_context(pm,proot,case["predecessor_case_id"]); plan=evaluate_plan(case,ctx); text=ctx["text"]
        if plan["status"]=="accepted":
            po,pr,gaps=assemble_output(text,plan["resolved_operations"],provider_transform); bo,br,bg=assemble_output(text,plan["resolved_operations"],apply_baseline_fragment); require(gaps==bg,"source-gap drift")
        else: po=bo=text; pr=br=[]; gaps=[text]
        dis=po!=bo; residual=residual_audit(po,ctx["case"]["baseline_rules"]); route=_route(case,plan["status"],dis,residual["observation_count"])
        por=_output(ctx["text_sha256"],po,"presidio_anonymizer_fragment_adapter"); bor=_output(ctx["text_sha256"],bo,"grand_intellect_baseline")
        rp={"plan_id":plan["plan_id"],"source_sha256":ctx["text_sha256"],"canonical_observation_digest":ctx["canonical_observation_digest"],"provider_output_record_id":por["output_record_id"],"baseline_output_record_id":bor["output_record_id"],"residual_audit_id":residual["residual_audit_id"],"configuration_sha256":cfg}
        receipt={"record_type":"curata_transformation_receipt","receipt_id":content_id("curata-transformation-receipt",rp),**rp,"stage":"governed_pii_transformation_and_residual_audit","provider_identity":{"name":"presidio-anonymizer","version":versions["presidio-anonymizer"],"adapter":"gcl_fragment_scoped_v1"},"provider_may_select_spans":False,"provider_may_select_operators":False,"provider_may_authorize_route":False,"source_record_mutated":False,"network_used":False,"provider_disagreement":dis}
        yp={"receipt_id":receipt["receipt_id"],"route":route,"routing_authority":"grandchallenge","plan_status":plan["status"],"policy_state":case["policy_state"]}
        routing={"record_type":"curata_transformation_routing","routing_record_id":content_id("curata-transformation-routing",yp),**yp,"admission_state":"not_admitted","deletion_state":"not_deleted","privacy_state":"not_established","training_eligibility":"not_assessed"}
        absent=all(r["operator"]=="keep" or r["output_fragment"]!=o["matched_text"] for r,o in zip(pr,plan["resolved_operations"]))
        checks={"source_binding_matches":case["source_sha256"]==ctx["text_sha256"] if plan["status"]!="rejected_stale_source" else True,"observation_binding_matches":case["canonical_observation_digest"]==ctx["canonical_observation_digest"] if plan["status"]!="rejected_observation_digest" else True,"plan_status_matches":plan["status"]==case["expected_plan_status"],"route_matches":route==case["expected_route"],"provider_disagreement_matches":dis is case["expect_provider_disagreement"],"residual_expectation_matches":bool(residual["observation_count"]) is case["expect_residual"],"outside_spans_preserved":bool(gaps),"intended_literals_absent":absent,"source_record_immutable":not receipt["source_record_mutated"] and not por["source_record_mutated"],"provider_has_no_authority":not receipt["provider_may_select_spans"] and not receipt["provider_may_select_operators"] and not receipt["provider_may_authorize_route"],"no_release_action":routing["admission_state"]=="not_admitted" and routing["deletion_state"]=="not_deleted"}
        plan_record={"record_type":"curata_transformation_plan","plan_id":plan["plan_id"],"plan_state":case["plan_state"],"status":plan["status"],"binding":plan["binding"],"resolved_operations":deepcopy(plan["resolved_operations"]),"plan_authority":"grandchallenge"}
        cr={"case_id":case["case_id"],"case_class":case["case_class"],"predecessor_case_id":case["predecessor_case_id"],"predecessor_context":{"source_sha256":ctx["text_sha256"],"canonical_observation_digest":ctx["canonical_observation_digest"],"provider_observation_digest":ctx["provider_observation_set"]["observation_digest"],"baseline_observation_digest":ctx["baseline_observation_set"]["observation_digest"]},"plan_record":plan_record,"provider_operation_results":pr,"baseline_operation_results":br,"provider_output":po,"baseline_output":bo,"provider_output_record":por,"baseline_output_record":bor,"residual_audit":residual,"transformation_receipt":receipt,"routing_record":routing,"checks":checks,"passed":all(checks.values())}
        reports.append(cr)
        if case["duplicate_group"]: groups.setdefault(case["duplicate_group"],[]).append((case["case_id"],ctx["text_sha256"],plan["plan_id"],por["output_record_id"],receipt["receipt_id"]))
    dup=[{"duplicate_group":g,"members":sorted(x[0] for x in m),"source_digest_equal":len({x[1] for x in m})==1,"plan_digest_equal":len({x[2] for x in m})==1,"output_digest_equal":len({x[3] for x in m})==1,"receipt_digest_equal":len({x[4] for x in m})==1} for g,m in sorted(groups.items())]
    report={"schema_version":SCHEMA_VERSION,"fixture_id":FIXTURE_ID,"predecessor":PREDECESSOR,"configuration":config,"configuration_sha256":cfg,"case_count":len(reports),"cases":reports,"duplicate_checks":dup,"claims":{k:False for k in sorted(FALSE_CLAIMS)},"passed":all(x["passed"] for x in reports) and all(all(x[k] for k in ("source_digest_equal","plan_digest_equal","output_digest_equal","receipt_digest_equal")) for x in dup)}
    validate_report(report,manifest,root); require(report["passed"],"fixture acceptance checks failed"); return report

def validate_report(report,manifest,fixture_root):
    require(set(report)=={"schema_version","fixture_id","predecessor","configuration","configuration_sha256","case_count","cases","duplicate_checks","claims","passed"},"report field drift")
    require(report["schema_version"]==SCHEMA_VERSION and report["fixture_id"]==FIXTURE_ID and report["predecessor"]==PREDECESSOR,"report identity drift")
    c=report["configuration"]; require(c["plan_authority"]=="gcl_owned_static_manifest" and c["fragment_scoped_provider_execution"] and c["gcl_output_assembly"] and c["source_records_immutable"] and not c["external_project_dependency"] and not c["network_required_for_replay"],"configuration authority drift")
    require(report["configuration_sha256"]==sha256_bytes(canonical_json_bytes(c)),"configuration digest drift"); require(set(report["claims"])==FALSE_CLAIMS and not any(report["claims"].values()),"claim inflation")
    require(report["case_count"]==len(report["cases"])==len(manifest["cases"]),"case count drift")
    root=Path(fixture_root); pm_path=root/manifest["predecessor_manifest"]; pm=json.loads(pm_path.read_text()); proot=pm_path.parent; cases={x["case_id"]:x for x in manifest["cases"]}
    for r in report["cases"]:
        case=cases[r["case_id"]]; ctx=predecessor_context(pm,proot,case["predecessor_case_id"]); plan=evaluate_plan(case,ctx); require(r["case_class"]==case["case_class"] and r["predecessor_case_id"]==case["predecessor_case_id"],"case drift")
        require(r["predecessor_context"]=={"source_sha256":ctx["text_sha256"],"canonical_observation_digest":ctx["canonical_observation_digest"],"provider_observation_digest":ctx["provider_observation_set"]["observation_digest"],"baseline_observation_digest":ctx["baseline_observation_set"]["observation_digest"]},"predecessor evidence drift")
        p=r["plan_record"]; require(p["plan_id"]==content_id("curata-transformation-plan",p["binding"]) and p["status"] in PLAN_STATUSES and p["status"]==plan["status"] and p["binding"]==plan["binding"] and p["resolved_operations"]==plan["resolved_operations"] and p["plan_authority"]=="grandchallenge","plan drift")
        ops=p["resolved_operations"]; text=ctx["text"]; gaps=[]; cur=0
        for o in ops: gaps.append(text[cur:o["start_char"]]); cur=o["end_char"]
        gaps.append(text[cur:])
        for rk,tk,engine in (("provider_output_record","provider_output","presidio_anonymizer_fragment_adapter"),("baseline_output_record","baseline_output","grand_intellect_baseline")):
            rec=r[rk]; txt=r[tk]; payload={"source_sha256":rec["source_sha256"],"output_sha256":rec["output_sha256"],"byte_length":rec["byte_length"],"engine":rec["engine"]}
            require(rec["source_sha256"]==ctx["text_sha256"] and rec["output_sha256"]==sha256_bytes(txt.encode()) and rec["byte_length"]==len(txt.encode()) and rec["engine"]==engine and rec["output_record_id"]==content_id("curata-derived-output",payload) and not rec["source_record_mutated"] and rec["admission_state"]=="not_admitted" and rec["deletion_state"]=="not_deleted","output record drift")
        for key in ("provider_operation_results","baseline_operation_results"):
            results=r[key]; require(len(results)==len(ops),"operation count drift")
            for z,o in zip(results,ops): require(z["observation_id"]==o["observation_id"] and z["entity_type"]==o["entity_type"] and z["start_char"]==o["start_char"] and z["end_char"]==o["end_char"] and z["operator"]==o["operator"] and z["parameters"]==o["parameters"] and z["source_fragment_sha256"]==sha256_bytes(o["matched_text"].encode()) and z["output_fragment_sha256"]==sha256_bytes(z["output_fragment"].encode()),"operation evidence drift")
        rebuild=lambda key:"".join(y for pair in zip(gaps,[x["output_fragment"] for x in r[key]]+[""]) for y in pair)
        require(rebuild("provider_operation_results")==r["provider_output"] and rebuild("baseline_operation_results")==r["baseline_output"],"outside-span drift")
        for z,o in zip(r["baseline_operation_results"],ops): require(z["output_fragment"]==apply_baseline_fragment(o["matched_text"],o["entity_type"],o["operator"],o["parameters"]),"baseline semantic drift")
        residual=residual_audit(r["provider_output"],ctx["case"]["baseline_rules"]); require(r["residual_audit"]==residual,"residual drift")
        receipt=r["transformation_receipt"]; rp={k:receipt[k] for k in ("plan_id","source_sha256","canonical_observation_digest","provider_output_record_id","baseline_output_record_id","residual_audit_id","configuration_sha256")}
        require(receipt["receipt_id"]==content_id("curata-transformation-receipt",rp) and receipt["plan_id"]==p["plan_id"] and receipt["source_sha256"]==ctx["text_sha256"] and receipt["canonical_observation_digest"]==ctx["canonical_observation_digest"] and receipt["provider_output_record_id"]==r["provider_output_record"]["output_record_id"] and receipt["baseline_output_record_id"]==r["baseline_output_record"]["output_record_id"] and receipt["residual_audit_id"]==residual["residual_audit_id"] and receipt["configuration_sha256"]==report["configuration_sha256"] and not receipt["provider_may_select_spans"] and not receipt["provider_may_select_operators"] and not receipt["provider_may_authorize_route"] and not receipt["source_record_mutated"] and not receipt["network_used"] and receipt["provider_disagreement"]==(r["provider_output"]!=r["baseline_output"]),"receipt drift")
        route=r["routing_record"]; yp={k:route[k] for k in ("receipt_id","route","routing_authority","plan_status","policy_state")}
        require(route["routing_record_id"]==content_id("curata-transformation-routing",yp) and route["receipt_id"]==receipt["receipt_id"] and route["route"] in ROUTES and route["route"]==_route(case,p["status"],receipt["provider_disagreement"],residual["observation_count"]) and route["routing_authority"]=="grandchallenge" and route["admission_state"]=="not_admitted" and route["deletion_state"]=="not_deleted" and route["privacy_state"]=="not_established" and route["training_eligibility"]=="not_assessed","routing drift")
        require(r["passed"]==all(r["checks"].values()),"pass inflation")
    require(isinstance(report["passed"],bool),"report pass type drift")
