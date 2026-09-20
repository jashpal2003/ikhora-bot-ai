"""Decision Calibration & Brier Score evaluation (P1, §11.3)."""

from typing import Any
from pydantic import BaseModel


class CalibrationMetrics(BaseModel):
    """Brier score and calibration evaluation for a decision provider."""

    sample_size: int
    brier_score: float  # Mean squared error: 0.0 is perfect calibration, 1.0 is worst
    expected_calibration_error: float
    reliability_bins: list[dict[str, Any]]


def calculate_brier_score(predictions: list[float], actuals: list[int]) -> float:
    """Compute Brier score: MSE between predicted probabilities and binary outcomes.
    
    Brier = (1 / N) * sum((p_i - y_i)^2)
    """
    if not predictions or len(predictions) != len(actuals):
        return 0.0
    total_sq_error = sum((p - y) ** 2 for p, y in zip(predictions, actuals, strict=False))
    return float(total_sq_error / len(predictions))


def evaluate_decision_calibration(
    predictions: list[float],
    actuals: list[int],
    num_bins: int = 5,
) -> CalibrationMetrics:
    """Bin predictions and compute calibration metrics and reliability curve."""
    if not predictions or len(predictions) != len(actuals):
        return CalibrationMetrics(
            sample_size=0,
            brier_score=0.0,
            expected_calibration_error=0.0,
            reliability_bins=[],
        )

    brier = calculate_brier_score(predictions, actuals)
    bin_size = 1.0 / num_bins
    bins_data: list[dict[str, Any]] = []
    total_samples = len(predictions)
    ece = 0.0

    for b in range(num_bins):
        low = b * bin_size
        high = (b + 1) * bin_size
        bin_preds: list[float] = []
        bin_actuals: list[int] = []

        for p, y in zip(predictions, actuals, strict=False):
            if (b == num_bins - 1 and low <= p <= high) or (low <= p < high):
                bin_preds.append(p)
                bin_actuals.append(y)

        bin_count = len(bin_preds)
        if bin_count > 0:
            avg_pred = sum(bin_preds) / bin_count
            avg_actual = sum(bin_actuals) / bin_count
            abs_diff = abs(avg_pred - avg_actual)
            ece += (bin_count / total_samples) * abs_diff
            bins_data.append({
                "bin": f"[{low:.1f}, {high:.1f}]",
                "count": bin_count,
                "avg_predicted": round(avg_pred, 3),
                "actual_positive_rate": round(avg_actual, 3),
            })
        else:
            bins_data.append({
                "bin": f"[{low:.1f}, {high:.1f}]",
                "count": 0,
                "avg_predicted": round((low + high) / 2, 3),
                "actual_positive_rate": 0.0,
            })

    return CalibrationMetrics(
        sample_size=total_samples,
        brier_score=round(brier, 4),
        expected_calibration_error=round(ece, 4),
        reliability_bins=bins_data,
    )
