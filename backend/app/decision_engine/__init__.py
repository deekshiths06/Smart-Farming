"""Explainable Crop Intelligence decision engine.

The engine is deliberately deterministic and transparent: every input is a
measured, validated value (field profile, latest soil measurement, live weather)
or an admin-managed crop requirement with a named source. It never invents
values, never substitutes averages, and never produces yield, price or profit
claims. When an input is missing it says so (``needs_information``) instead of
guessing.

Public entry points: :func:`app.decision_engine.recommendation.evaluate_field`
(no persistence) and :func:`app.decision_engine.recommendation.generate_recommendations`
(persists one row per crop plus the input snapshot).
"""
