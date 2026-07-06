from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from app.comparison.comparator import compare_calculations
from app.domain.schemas import CalculationSource, ComparisonResult, DraftRequest, DraftResult
from app.drafting.service import build_ai_draft, build_template_draft
from app.ingestion.archive import expand_zip_payload, is_zip
from app.ingestion.extractor import extract_calculation
from app.ingestion.pdf import parse_pdf_bytes
from app.ingestion.segmentation import resolve_segment_sources, split_process_document
from app.ingestion.spreadsheets import parse_spreadsheet_bytes
from app.planning.docx import markdown_to_docx_bytes
from app.planning.engine import build_planning_case
from app.planning.extractor import analyze_document
from app.planning.schemas import InsuredProfile, PlanningCase
from app.security import require_access_token
from app.storage.memory import planning_repository, repository

router = APIRouter(prefix="/api", dependencies=[Depends(require_access_token)])


@router.post("/cases/analyze", response_model=ComparisonResult)
async def analyze_case(
    office_files: list[UploadFile] = File(default=[]),
    inss_files: list[UploadFile] = File(default=[]),
    court_files: list[UploadFile] = File(default=[]),
    auto_files: list[UploadFile] = File(default=[]),
) -> ComparisonResult:
    calculations = []
    for upload, source in [
        *[(file, CalculationSource.OFFICE) for file in office_files],
        *[(file, CalculationSource.INSS) for file in inss_files],
        *[(file, CalculationSource.COURT_ACCOUNTING) for file in court_files],
        *[(file, None) for file in auto_files],
    ]:
        payload = await upload.read()
        expanded = expand_zip_payload(payload) if is_zip(upload.filename or "", payload) else [(upload.filename or "upload", payload)]
        for file_name, file_payload in expanded:
            parsed = parse_payload(file_name, file_payload)
            if parsed is None:
                continue
            segments = split_process_document(parsed)
            for segment, segment_source in resolve_segment_sources(segments, source):
                calculations.append(extract_calculation(segment, segment_source))

    if not calculations:
        raise HTTPException(status_code=400, detail="Nenhum PDF, XLSX ou CSV valido foi enviado.")

    comparison = compare_calculations(calculations)
    repository.add(comparison)
    return comparison


@router.post("/planning/analyze", response_model=PlanningCase)
async def analyze_planning_case(
    profile_json: str | None = Form(default=None),
    case_files: list[UploadFile] = File(default=[]),
) -> PlanningCase:
    profile = parse_profile(profile_json)
    documents = []
    for upload in case_files:
        payload = await upload.read()
        expanded = (
            expand_zip_payload(payload)
            if is_zip(upload.filename or "", payload)
            else [(upload.filename or "upload", payload)]
        )
        for file_name, file_payload in expanded:
            parsed = parse_payload(file_name, file_payload)
            if parsed is not None:
                documents.append(analyze_document(parsed))

    planning_case = build_planning_case(profile, documents)
    planning_repository.add(planning_case)
    return planning_case


@router.get("/planning/cases", response_model=list[PlanningCase])
def list_planning_cases() -> list[PlanningCase]:
    return planning_repository.list()


@router.get("/planning/cases/{case_id}", response_model=PlanningCase)
def get_planning_case(case_id: str) -> PlanningCase:
    planning_case = planning_repository.get(case_id)
    if not planning_case:
        raise HTTPException(status_code=404, detail="Planejamento nao encontrado.")
    return planning_case


@router.get("/planning/cases/{case_id}/report.docx")
def download_planning_docx(case_id: str) -> Response:
    planning_case = planning_repository.get(case_id)
    if not planning_case:
        raise HTTPException(status_code=404, detail="Planejamento nao encontrado.")
    payload = markdown_to_docx_bytes(planning_case.report_markdown)
    safe_id = case_id[:8]
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="planejamento-previdenciario-{safe_id}.docx"'},
    )


@router.get("/cases", response_model=list[ComparisonResult])
def list_cases() -> list[ComparisonResult]:
    return repository.list()


@router.get("/cases/{case_id}", response_model=ComparisonResult)
def get_case(case_id: str) -> ComparisonResult:
    comparison = repository.get(case_id)
    if not comparison:
        raise HTTPException(status_code=404, detail="Caso nao encontrado.")
    return comparison


@router.post("/drafts", response_model=DraftResult)
async def create_draft(request: DraftRequest) -> DraftResult:
    if request.use_ai:
        return await build_ai_draft(request.comparison, request.target)
    return build_template_draft(request.comparison, request.target)


def parse_payload(file_name: str, payload: bytes):
    lower = file_name.lower()
    if lower.endswith(".pdf"):
        return parse_pdf_bytes(file_name, payload)
    if lower.endswith(".xlsx") or lower.endswith(".xls") or lower.endswith(".csv"):
        return parse_spreadsheet_bytes(file_name, payload)
    return None


def parse_profile(profile_json: str | None) -> InsuredProfile:
    if not profile_json:
        return InsuredProfile()
    try:
        data = json.loads(profile_json)
        return InsuredProfile.model_validate(data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Perfil do segurado invalido: {exc}") from exc
