"""Cronograma mensual de transicion con estacionalidad.

Este modulo no calcula horarios de rutas. Convierte un mes de inicio en un
calendario mensual de proyecto para detectar si fases o hitos criticos caen en
temporada de alta demanda.

No usa datos externos ni dias reales: trabaja con meses discretos y con el
perfil estacional documentado para el caso.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


MONTH_NAMES: dict[int, str] = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

SEASONALITY_PROFILE: dict[int, tuple[float, str]] = {
    1: (0.85, "favorable"),
    2: (0.85, "favorable"),
    3: (0.85, "favorable"),
    4: (1.00, "normal"),
    5: (1.00, "normal"),
    6: (1.00, "normal"),
    7: (1.08, "medio"),
    8: (1.08, "medio"),
    9: (1.08, "medio"),
    10: (1.25, "alto"),
    11: (1.25, "alto"),
    12: (1.25, "alto"),
}

HIGH_SEASON_MONTHS = frozenset({7, 8, 9, 10, 11, 12})
CRITICAL_PEAK_MONTHS = frozenset({10, 11, 12})

DEFAULT_PHASE_SPECS: tuple[tuple[str, int], ...] = (
    ("Preparacion", 4),
    ("Construccion", 6),
    ("Migracion", 4),
    ("Finalizacion", 3),
)

DEFAULT_MILESTONE_SPECS: tuple[tuple[str, int], ...] = (
    ("Acuerdo con sindicatos", 2),
    ("Construccion terminada", 8),
    ("Sistemas funcionando", 10),
    ("Migracion completa", 14),
)


@dataclass(frozen=True)
class TimelinePhase:
    """Fase secuencial del proyecto."""

    name: str
    duration_months: int
    start_project_month: int
    end_project_month: int


@dataclass(frozen=True)
class TimelineMilestone:
    """Hito critico situado en un mes de proyecto y de calendario."""

    name: str
    project_month: int
    calendar_month: int
    multiplier: float
    risk_level: str
    in_high_season: bool

    @property
    def month_name(self) -> str:
        return MONTH_NAMES[self.calendar_month]

    @property
    def in_critical_peak(self) -> bool:
        return self.calendar_month in CRITICAL_PEAK_MONTHS


@dataclass(frozen=True)
class TimelineMonth:
    """Fila mensual del cronograma."""

    project_month: int
    calendar_month: int
    month_name: str
    phase: str
    multiplier: float
    risk_level: str
    in_high_season: bool

    @property
    def in_critical_peak(self) -> bool:
        return self.calendar_month in CRITICAL_PEAK_MONTHS


@dataclass(frozen=True)
class TimelineWarning:
    """Advertencia o nota informativa derivada del cronograma."""

    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class TimelineResult:
    """Resultado completo del cronograma estacional."""

    start_month: int
    total_duration_months: int
    months: tuple[TimelineMonth, ...]
    phases: tuple[TimelinePhase, ...]
    milestones: tuple[TimelineMilestone, ...]
    warnings: tuple[TimelineWarning, ...]
    summary: str
    score: int
    suggested_start_month: int | None = None

    @property
    def start_month_name(self) -> str:
        return MONTH_NAMES[self.start_month]

    @property
    def suggested_start_month_name(self) -> str | None:
        if self.suggested_start_month is None:
            return None
        return MONTH_NAMES[self.suggested_start_month]

    @property
    def high_season_month_count(self) -> int:
        return sum(1 for month in self.months if month.in_high_season)

    @property
    def critical_peak_month_count(self) -> int:
        return sum(1 for month in self.months if month.in_critical_peak)

    @property
    def high_season_milestone_count(self) -> int:
        return sum(1 for milestone in self.milestones if milestone.in_high_season)

    @property
    def high_severity_warning_count(self) -> int:
        return sum(1 for warning in self.warnings if warning.severity == "alta")


def build_timeline(
    start_month: int = 1,
    phase_specs: Sequence[tuple[str, int]] = DEFAULT_PHASE_SPECS,
    milestone_specs: Sequence[tuple[str, int]] = DEFAULT_MILESTONE_SPECS,
) -> TimelineResult:
    """Construye el cronograma mensual para un mes de inicio.

    Args:
        start_month: mes calendario de inicio, de 1 a 12.
        phase_specs: pares ``(nombre, duracion_meses)`` secuenciales.
        milestone_specs: pares ``(nombre, mes_proyecto)``.
    """

    _validate_start_month(start_month)
    phases = _build_phases(phase_specs)
    total_duration = sum(phase.duration_months for phase in phases)
    _validate_milestone_specs(milestone_specs, total_duration)

    months = _build_months(start_month, phases)
    milestones = _build_milestones(start_month, milestone_specs)
    warnings = _build_warnings(months, milestones)
    score = _score_calendar(months, phases, milestones)
    suggested = _suggest_start_month(start_month, phase_specs, milestone_specs, score)
    summary = _build_summary(start_month, months, milestones, warnings, suggested)

    return TimelineResult(
        start_month=int(start_month),
        total_duration_months=total_duration,
        months=months,
        phases=phases,
        milestones=milestones,
        warnings=warnings,
        summary=summary,
        score=score,
        suggested_start_month=suggested,
    )


def _validate_start_month(start_month: int) -> None:
    if not isinstance(start_month, int):
        raise ValueError("start_month debe ser un entero entre 1 y 12")
    if not 1 <= start_month <= 12:
        raise ValueError("start_month debe estar entre 1 y 12")


def _build_phases(phase_specs: Sequence[tuple[str, int]]) -> tuple[TimelinePhase, ...]:
    if not phase_specs:
        raise ValueError("Debe existir al menos una fase")

    phases: list[TimelinePhase] = []
    current_month = 1
    for name, duration in phase_specs:
        if not str(name).strip():
            raise ValueError("Las fases deben tener nombre")
        if not isinstance(duration, int) or duration <= 0:
            raise ValueError("Todas las duraciones de fase deben ser enteros positivos")

        end_month = current_month + int(duration) - 1
        phases.append(
            TimelinePhase(
                name=str(name),
                duration_months=int(duration),
                start_project_month=current_month,
                end_project_month=end_month,
            )
        )
        current_month = end_month + 1

    return tuple(phases)


def _validate_milestone_specs(
    milestone_specs: Sequence[tuple[str, int]],
    total_duration: int,
) -> None:
    for name, project_month in milestone_specs:
        if not str(name).strip():
            raise ValueError("Los hitos deben tener nombre")
        if not isinstance(project_month, int):
            raise ValueError("Los meses de hito deben ser enteros")
        if not 1 <= project_month <= total_duration:
            raise ValueError("Todos los hitos deben estar dentro de la duracion total")


def _calendar_month(start_month: int, project_month: int) -> int:
    return ((int(start_month) - 1 + int(project_month) - 1) % 12) + 1


def _seasonality(calendar_month: int) -> tuple[float, str, bool]:
    multiplier, risk_level = SEASONALITY_PROFILE[calendar_month]
    return multiplier, risk_level, calendar_month in HIGH_SEASON_MONTHS


def _phase_for_project_month(project_month: int, phases: Sequence[TimelinePhase]) -> str:
    for phase in phases:
        if phase.start_project_month <= project_month <= phase.end_project_month:
            return phase.name
    raise ValueError("project_month fuera de las fases definidas")


def _build_months(
    start_month: int,
    phases: Sequence[TimelinePhase],
) -> tuple[TimelineMonth, ...]:
    total_duration = sum(phase.duration_months for phase in phases)
    rows: list[TimelineMonth] = []
    for project_month in range(1, total_duration + 1):
        calendar_month = _calendar_month(start_month, project_month)
        multiplier, risk_level, in_high_season = _seasonality(calendar_month)
        rows.append(
            TimelineMonth(
                project_month=project_month,
                calendar_month=calendar_month,
                month_name=MONTH_NAMES[calendar_month],
                phase=_phase_for_project_month(project_month, phases),
                multiplier=multiplier,
                risk_level=risk_level,
                in_high_season=in_high_season,
            )
        )
    return tuple(rows)


def _build_milestones(
    start_month: int,
    milestone_specs: Sequence[tuple[str, int]],
) -> tuple[TimelineMilestone, ...]:
    milestones: list[TimelineMilestone] = []
    for name, project_month in milestone_specs:
        calendar_month = _calendar_month(start_month, project_month)
        multiplier, risk_level, in_high_season = _seasonality(calendar_month)
        milestones.append(
            TimelineMilestone(
                name=str(name),
                project_month=int(project_month),
                calendar_month=calendar_month,
                multiplier=multiplier,
                risk_level=risk_level,
                in_high_season=in_high_season,
            )
        )
    return tuple(milestones)


def _months_for_phase(
    months: Sequence[TimelineMonth],
    phase: TimelinePhase,
) -> tuple[TimelineMonth, ...]:
    return tuple(
        month
        for month in months
        if phase.start_project_month <= month.project_month <= phase.end_project_month
    )


def _phase_touches_peak(months: Sequence[TimelineMonth], phase_name: str) -> bool:
    return any(
        month.phase == phase_name and month.in_critical_peak
        for month in months
    )


def _build_warnings(
    months: Sequence[TimelineMonth],
    milestones: Sequence[TimelineMilestone],
) -> tuple[TimelineWarning, ...]:
    warnings: list[TimelineWarning] = []

    if _phase_touches_peak(months, "Migracion"):
        warnings.append(
            TimelineWarning(
                code="MIGRATION_PEAK",
                severity="alta",
                message=(
                    "La fase de migracion toca octubre-diciembre, periodo que el "
                    "enunciado recomienda evitar para cambios criticos."
                ),
            )
        )

    systems_peak = any(
        "sistemas" in milestone.name.lower() and milestone.in_critical_peak
        for milestone in milestones
    )
    if systems_peak:
        warnings.append(
            TimelineWarning(
                code="SYSTEMS_PEAK",
                severity="alta",
                message=(
                    "El hito de sistemas cae en octubre-diciembre; conviene "
                    "protegerlo con respaldo y margen operativo."
                ),
            )
        )

    if _phase_touches_peak(months, "Finalizacion"):
        warnings.append(
            TimelineWarning(
                code="FINALIZATION_PEAK",
                severity="media",
                message=(
                    "La finalizacion o cierre de DQA4 coincide con el pico "
                    "octubre-diciembre."
                ),
            )
        )

    for milestone in milestones:
        if milestone.in_high_season:
            severity = "alta" if milestone.in_critical_peak else "media"
            warnings.append(
                TimelineWarning(
                    code="MILESTONE_HIGH_SEASON",
                    severity=severity,
                    message=(
                        f"El hito '{milestone.name}' cae en {milestone.month_name}, "
                        f"con riesgo estacional {milestone.risk_level}."
                    ),
                )
            )

    christmas_phase_names = {"Migracion", "Finalizacion"}
    christmas_exposed = any(
        month.phase in christmas_phase_names and month.in_critical_peak
        for month in months
    )
    if christmas_exposed:
        warnings.append(
            TimelineWarning(
                code="CHRISTMAS_EXPOSED",
                severity="media",
                message=(
                    "El periodo octubre-diciembre queda expuesto en fases de "
                    "transicion operativa."
                ),
            )
        )
    else:
        warnings.append(
            TimelineWarning(
                code="CHRISTMAS_PROTECTED",
                severity="info",
                message=(
                    "Las fases de migracion y finalizacion evitan el pico "
                    "octubre-diciembre."
                ),
            )
        )
    return tuple(warnings)


def _score_calendar(
    months: Sequence[TimelineMonth],
    phases: Sequence[TimelinePhase],
    milestones: Sequence[TimelineMilestone],
) -> int:
    score = 0
    score += sum(2 for month in months if month.in_high_season)
    score += sum(3 for month in months if month.in_critical_peak)
    score += sum(5 for milestone in milestones if milestone.in_high_season)
    score += sum(4 for milestone in milestones if milestone.in_critical_peak)

    for phase in phases:
        phase_months = _months_for_phase(months, phase)
        if phase.name == "Migracion" and any(month.in_critical_peak for month in phase_months):
            score += 12
        if phase.name == "Finalizacion" and any(month.in_critical_peak for month in phase_months):
            score += 8

    if any("sistemas" in milestone.name.lower() and milestone.in_critical_peak for milestone in milestones):
        score += 10

    return score


def _suggest_start_month(
    current_start_month: int,
    phase_specs: Sequence[tuple[str, int]],
    milestone_specs: Sequence[tuple[str, int]],
    current_score: int,
) -> int | None:
    candidates: list[tuple[int, int, int]] = []
    phases = _build_phases(phase_specs)
    total_duration = sum(phase.duration_months for phase in phases)
    _validate_milestone_specs(milestone_specs, total_duration)

    for candidate in range(1, 13):
        months = _build_months(candidate, phases)
        milestones = _build_milestones(candidate, milestone_specs)
        score = _score_calendar(months, phases, milestones)
        jan_mar_priority = 0 if candidate in {1, 2, 3} else 1
        candidates.append((score, jan_mar_priority, candidate))

    best_score, _, best_month = min(candidates)
    if best_month == current_start_month or best_score >= current_score:
        return None
    return best_month


def _build_summary(
    start_month: int,
    months: Sequence[TimelineMonth],
    milestones: Sequence[TimelineMilestone],
    warnings: Sequence[TimelineWarning],
    suggested_start_month: int | None,
) -> str:
    high_months = sum(1 for month in months if month.in_high_season)
    peak_months = sum(1 for month in months if month.in_critical_peak)
    high_milestones = sum(1 for milestone in milestones if milestone.in_high_season)
    high_warnings = sum(1 for warning in warnings if warning.severity == "alta")

    if high_warnings:
        stance = (
            f"Inicio en {MONTH_NAMES[start_month]}: cronograma delicado, con "
            f"{high_warnings} alerta(s) alta(s)."
        )
    elif high_milestones or peak_months:
        stance = (
            f"Inicio en {MONTH_NAMES[start_month]}: cronograma aceptable con "
            "riesgos estacionales a vigilar."
        )
    else:
        stance = (
            f"Inicio en {MONTH_NAMES[start_month]}: cronograma favorable frente "
            "a la estacionalidad."
        )

    details = (
        f"Atraviesa {high_months} mes(es) de temporada alta, "
        f"{peak_months} de ellos en octubre-diciembre, y coloca "
        f"{high_milestones} hito(s) critico(s) en temporada alta."
    )
    if suggested_start_month is not None:
        alternative = (
            f"Como alternativa simple, probar inicio en "
            f"{MONTH_NAMES[suggested_start_month]} reduce el score estacional."
        )
    else:
        alternative = "No aparece un mes alternativo claramente mejor con este score simple."

    disclaimer = (
        "El calendario no decide por si solo la viabilidad; debe cruzarse con "
        "economia, operacion, personas y riesgos."
    )
    return " ".join([stance, details, alternative, disclaimer])
