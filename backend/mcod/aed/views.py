import os
import tempfile
import uuid
from typing import Dict, Optional

import pandas as pd
from django.contrib import admin
from django.core.cache import cache
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from mcod.aed.constants import COL_ACCESS, COL_AVAILABILITY, COL_STATUS, COL_VERIFIED
from mcod.aed.converter import PROFILES_DIR, convert_dataframe, load_profile, read_any
from mcod.aed.template import build_template_bytes
from mcod.aed.utils import main_df_to_csv_bytes

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".geojson"}
CACHE_SECONDS = 30 * 60
REPORT_ROWS_SHOWN = 300


def _profiles():
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json"))


def _context(request, **extra):
    ctx = {"title": "Konwerter wykazu AED", "profiles": _profiles(), "has_permission": True, **admin.site.each_context(request)}
    ctx.update(extra)
    return ctx


TEMPLATE = "admin/aed/converter.html"
DEFAULT_FIELDS = (
    ("data_zrodla", COL_VERIFIED),
    ("dostepnosc", COL_AVAILABILITY),
    ("dostep", COL_ACCESS),
    ("status", COL_STATUS),
)


def _upload_error(upload) -> Optional[str]:
    """Komunikat o błędzie wgranego pliku albo None, gdy plik można konwertować."""
    if not upload:
        return "Wybierz plik do konwersji."
    if os.path.splitext(upload.name)[1].lower() not in ALLOWED_EXTENSIONS:
        return "Dozwolone formaty: csv, xlsx, xls, json, geojson."
    if upload.size > MAX_UPLOAD_BYTES:
        return "Plik jest za duży (limit 5 MB)."
    return None


def _defaults_from_post(post) -> Dict[str, str]:
    values = {col: (post.get(field) or "").strip() for field, col in DEFAULT_FIELDS}
    return {col: value for col, value in values.items() if value}


def _convert_upload(upload, profile_name: str, defaults: Dict[str, str], north_first: bool):
    """Zapisuje plik tymczasowo, konwertuje i sprząta. Zwraca (df, out, report, mapping, profile)."""
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(upload.name)[1].lower(), delete=False) as tmp:
        for chunk in upload.chunks():
            tmp.write(chunk)
        path = tmp.name
    try:
        df = read_any(path)
        profile = load_profile(profile_name) if profile_name else None
        out, report, mapping = convert_dataframe(df, profile, defaults, "AED", north_first)
    finally:
        os.unlink(path)
    return df, out, report, mapping, profile


def _result_context(request, upload, df, out, report, mapping, profile, defaults):
    key = uuid.uuid4().hex
    cache.set(f"aed-conv-{key}-wynik", main_df_to_csv_bytes(out), CACHE_SECONDS)
    cache.set(f"aed-conv-{key}-raport", pd.DataFrame(report).to_csv(index=False).encode("utf-8"), CACHE_SECONDS)
    counts = pd.Series([r["wynik"] for r in report]).value_counts().to_dict() if report else {}
    mapped = [
        {"cel": target, "zrodlo": ", ".join(m.sources), "metoda": m.method, "pewnosc": int(round(m.confidence * 100))}
        for target, m in mapping.columns.items()
    ]
    return _context(
        request,
        result=True,
        key=key,
        filename=upload.name,
        total=len(df),
        converted=len(out),
        counts=counts,
        mapped=mapped,
        pl1992=mapping.pl1992,
        combined_point=mapping.combined_point,
        missing=mapping.missing_required({**((profile or {}).get("defaults") or {}), **defaults}),
        report=report[:REPORT_ROWS_SHOWN],
        report_truncated=len(report) > REPORT_ROWS_SHOWN,
        preview=out.head(15).fillna("").values.tolist(),
        preview_columns=list(out.columns),
    )


@require_http_methods(["GET", "POST"])
def converter_view(request):
    if request.method == "GET":
        return render(request, TEMPLATE, _context(request))

    upload = request.FILES.get("plik")
    profile_name = request.POST.get("profil") or ""
    error = _upload_error(upload)
    if error is None and profile_name and profile_name not in _profiles():
        error = "Nieznany profil źródła."
    if error:
        return render(request, TEMPLATE, _context(request, error=error))

    defaults = _defaults_from_post(request.POST)
    try:
        df, out, report, mapping, profile = _convert_upload(upload, profile_name, defaults, request.POST.get("osie_pn") == "on")
    except Exception as exc:  # noqa: BLE001  (niepoprawny plik użytkownika)
        return render(request, TEMPLATE, _context(request, error=f"Nie udało się odczytać pliku: {exc}"))
    return render(request, TEMPLATE, _result_context(request, upload, df, out, report, mapping, profile, defaults))


def download_view(request, key, kind):
    if kind not in ("wynik", "raport") or not key.isalnum():
        raise Http404
    data = cache.get(f"aed-conv-{key}-{kind}")
    if data is None:
        raise Http404("Wynik wygasł, uruchom konwersję ponownie.")
    name = "wykaz-aed.csv" if kind == "wynik" else "raport-konwersji.csv"
    response = HttpResponse(data, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{name}"'
    return response


def template_view(request):
    response = HttpResponse(
        build_template_bytes(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="wzorcowy-zakres-danych-AED.xlsx"'
    return response


converter_admin_view = admin.site.admin_view(converter_view)
template_admin_view = admin.site.admin_view(template_view)
download_admin_view = admin.site.admin_view(download_view)
