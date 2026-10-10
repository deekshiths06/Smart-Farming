"""Prompt 5: Soil Intelligence.

Adds the soil measurement history, soil report metadata, and configurable
agronomic reference ranges, then seeds the reference ranges from published
guidance (ICAR Soil Health Card ratings, USDA-NRCS soil pH classes, FAO salinity
classes, IRRI/Purdue crop guidance).

Revision ID: 0003_soil_intelligence
Revises: 0002_field_intelligence
Create Date: 2026-10-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_soil_intelligence"
down_revision: Union[str, None] = "0002_field_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ICAR = "ICAR - Soil Health Card ratings (Muhr et al. 1959), adopted by the Indian Soil Health Card scheme"
ICAR_URL = "https://soilhealth.dac.gov.in"
USDA_PH = "USDA-NRCS soil pH classes"
USDA_PH_URL = "https://www.nrcs.usda.gov"
FAO_EC = "FAO - saline soil classification (EC, dS/m)"
FAO_EC_URL = "https://www.fao.org/soils-portal"
FAO_MOISTURE = "USDA-NRCS / FAO - representative field-capacity ranges by soil texture (approximate)"
FAO_MOISTURE_URL = None
IRRI = "IRRI Rice Knowledge Bank - optimum soil pH for rice"
IRRI_URL = "http://www.knowledgebank.irri.org"
PURDUE = "Purdue University Extension / IPNI - optimum soil pH for maize"
PURDUE_URL = None

NUMERIC_PARAMS = ("ph", "nitrogen", "phosphorus", "potassium", "ec", "organic_carbon", "moisture")
ALL_PARAMS = NUMERIC_PARAMS + ("texture",)
TEXTURE_CLASSES = (
    "sand",
    "loamy_sand",
    "sandy_loam",
    "loam",
    "silt_loam",
    "silt",
    "sandy_clay_loam",
    "clay_loam",
    "silty_clay_loam",
    "sandy_clay",
    "silty_clay",
    "clay",
    "other",
)


def _ranges() -> list[dict]:
    rows: list[dict] = []

    def add(parameter, context_type, context_value, label, min_v, max_v, unit, outcome, explanation, source, source_url, sequence):
        rows.append(
            {
                "parameter": parameter,
                "context_type": context_type,
                "context_value": context_value,
                "label": label,
                "min_value": min_v,
                "max_value": max_v,
                "unit": unit,
                "outcome": outcome,
                "explanation": explanation,
                "source": source,
                "source_url": source_url,
                "sequence": sequence,
                "is_active": True,
            }
        )

    # pH - USDA-NRCS pH classes (unit, general).
    add("ph", "general", None, "Strongly acidic", None, 5.5, "", "below",
        "pH below 5.5. Nutrient availability and microbial activity degrade; most crops benefit "
        "from liming before planting.", USDA_PH, USDA_PH_URL, 0)
    add("ph", "general", None, "Slightly acidic", 5.5, 6.5, "", "below",
        "Below the neutral range. Many crops still grow, but P and micronutrient availability vary.", USDA_PH, USDA_PH_URL, 1)
    add("ph", "general", None, "Neutral", 6.5, 7.5, "", "within",
        "Optimal for most crops: plant nutrients are most available in this band.", USDA_PH, USDA_PH_URL, 2)
    add("ph", "general", None, "Alkaline", 7.5, 8.5, "", "above",
        "Above neutral. Iron, zinc and phosphorus become less available in alkaline soils.", USDA_PH, USDA_PH_URL, 3)
    add("ph", "general", None, "Strongly alkaline", 8.5, None, "", "above",
        "pH above 8.5 - expect nutrient deficiencies and possible calcareous/calcic soil.", USDA_PH, USDA_PH_URL, 4)

    # EC - FAO salinity classes (dS/m).
    add("ec", "general", None, "Non-saline", None, 2.0, "dS/m", "within",
        "Salts are not a concern for most crops (EC below 2 dS/m).", FAO_EC, FAO_EC_URL, 0)
    add("ec", "general", None, "Slightly saline", 2.0, 4.0, "dS/m", "above",
        "Mild salinity - sensitive crops may be affected; leach if symptoms appear.", FAO_EC, FAO_EC_URL, 1)
    add("ec", "general", None, "Moderately saline", 4.0, 8.0, "dS/m", "above",
        "Salinity likely to restrict growth of many crops; choose salt-tolerant varieties.", FAO_EC, FAO_EC_URL, 2)
    add("ec", "general", None, "Strongly saline", 8.0, 16.0, "dS/m", "above",
        "Severe salinity. Most crops will struggle without reclamation.", FAO_EC, FAO_EC_URL, 3)
    add("ec", "general", None, "Very strongly saline", 16.0, None, "dS/m", "above",
        "Extreme salinity. Only the most tolerant halophytes grow; seek specialist advice.", FAO_EC, FAO_EC_URL, 4)

    # Organic carbon - ICAR single-factor ratings (%).
    add("organic_carbon", "general", None, "Low", None, 0.4, "%", "below",
        "Low organic carbon (below 0.4%). Adding crop residue, manure or green manure will build soil health.", ICAR, ICAR_URL, 0)
    add("organic_carbon", "general", None, "Medium", 0.4, 0.75, "%", "within",
        "Medium organic carbon. Maintain organic inputs to avoid decline.", ICAR, ICAR_URL, 1)
    add("organic_carbon", "general", None, "High", 0.75, None, "%", "above",
        "High organic carbon (above 0.75%). Good soil structure and nutrient cycling.", ICAR, ICAR_URL, 2)

    # N / P / K - ICAR Soil Health Card ratings (kg/ha available nutrient).
    add("nitrogen", "general", None, "Low", None, 280.0, "kg/ha", "below",
        "Available N below 280 kg/ha. Nitrogen is likely the first limiting nutrient; the crop "
        "usually responds to N fertiliser.", ICAR, ICAR_URL, 0)
    add("nitrogen", "general", None, "Medium", 280.0, 560.0, "kg/ha", "within",
        "Available N in the medium band (280-560 kg/ha). Plan split doses to match crop demand.", ICAR, ICAR_URL, 1)
    add("nitrogen", "general", None, "High", 560.0, None, "kg/ha", "above",
        "Available N above 560 kg/ha. Avoid excess N; manage to prevent leaching and lodging.", ICAR, ICAR_URL, 2)

    add("phosphorus", "general", None, "Low", None, 22.0, "kg/ha", "below",
        "Available P below 22 kg/ha. Roots, flowering and grain-fill often benefit from P.", ICAR, ICAR_URL, 0)
    add("phosphorus", "general", None, "Medium", 22.0, 56.0, "kg/ha", "within",
        "Available P in the medium band.", ICAR, ICAR_URL, 1)
    add("phosphorus", "general", None, "High", 56.0, None, "kg/ha", "above",
        "Available P above 56 kg/ha. Enough for most crops; avoid building up more.", ICAR, ICAR_URL, 2)

    add("potassium", "general", None, "Low", None, 110.0, "kg/ha", "below",
        "Available K below 110 kg/ha - common in light-textured soils. K supports water balance "
        "and stalk strength.", ICAR, ICAR_URL, 0)
    add("potassium", "general", None, "Medium", 110.0, 280.0, "kg/ha", "within",
        "Available K in the medium band.", ICAR, ICAR_URL, 1)
    add("potassium", "general", None, "High", 280.0, None, "kg/ha", "above",
        "Available K above 280 kg/ha. Sufficient for most cropping; reintroduce K regularly.", ICAR, ICAR_URL, 2)

    # Regional example: Karnataka applies the national Soil Health Card ratings.
    for label, lo, hi, outcome, seq in (
        ("Low", None, 280.0, "below", 0),
        ("Medium", 280.0, 560.0, "within", 1),
        ("High", 560.0, None, "above", 2),
    ):
        add("nitrogen", "region", "Karnataka", label, lo, hi, "kg/ha", outcome,
            "Available N band as used under the Soil Health Card scheme in Karnataka.", ICAR, ICAR_URL, seq)

    # Moisture - approximate field capacity by USDA texture class (%). Interpret only.
    fc = {
        "sand": (5.0, 10.0),
        "loamy_sand": (10.0, 15.0),
        "sandy_loam": (15.0, 20.0),
        "loam": (20.0, 30.0),
        "silt_loam": (25.0, 35.0),
        "silt": (30.0, 35.0),
        "sandy_clay_loam": (20.0, 30.0),
        "clay_loam": (27.0, 35.0),
        "silty_clay_loam": (30.0, 35.0),
        "sandy_clay": (25.0, 35.0),
        "silty_clay": (35.0, 40.0),
        "clay": (35.0, 45.0),
    }
    for texture, (lo, hi) in fc.items():
        add("moisture", "soil_class", texture, "Approx. field capacity", lo, hi, "%", "within",
            "Approximate field-capacity range for this texture class. Values clearly below tend "
            "toward dry, above toward saturated - interpret alongside the measurement method.",
            FAO_MOISTURE, FAO_MOISTURE_URL, 0)

    # Crop guidance (applied once a crop is chosen for the field in the future).
    add("ph", "crop", "rice", "Optimal for rice", 5.5, 6.5, "", "within",
        "IRRI reports best rice growth in this pH band; many farmers still grow tolerant varieties outside it.", IRRI, IRRI_URL, 0)
    add("ph", "crop", "maize", "Optimal for maize", 5.5, 7.0, "", "within",
        "Maize grows well in this pH band.", PURDUE, PURDUE_URL, 0)

    return rows


def upgrade() -> None:
    reports = op.create_table(
        "soil_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("field_id", sa.Integer(), sa.ForeignKey("fields.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False, unique=True),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=True),
        sa.Column("report_source", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="uploaded"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('uploaded', 'linked')", name="ck_soil_reports_status"),
        sa.CheckConstraint("file_size_bytes >= 0", name="ck_soil_reports_file_size_non_negative"),
    )
    op.create_index("ix_soil_reports_field_id", "soil_reports", ["field_id"])
    op.create_index("ix_soil_reports_user_id", "soil_reports", ["user_id"])

    op.create_table(
        "soil_measurements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "field_id",
            sa.Integer(),
            sa.ForeignKey("fields.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tested_on", sa.Date(), nullable=False),
        sa.Column("test_source", sa.String(length=200), nullable=True),
        sa.Column("source_kind", sa.String(length=30), nullable=False, server_default="farmer_entered"),
        sa.Column(
            "report_id",
            sa.Integer(),
            sa.ForeignKey("soil_reports.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("ph", sa.Double(), nullable=True),
        sa.Column("nitrogen", sa.Double(), nullable=True),
        sa.Column("phosphorus", sa.Double(), nullable=True),
        sa.Column("potassium", sa.Double(), nullable=True),
        sa.Column("ec", sa.Double(), nullable=True),
        sa.Column("organic_carbon", sa.Double(), nullable=True),
        sa.Column("moisture", sa.Double(), nullable=True),
        sa.Column("texture", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("ph IS NULL OR (ph >= 0 AND ph <= 14)", name="ck_soil_measurements_ph_range"),
        sa.CheckConstraint("nitrogen IS NULL OR nitrogen >= 0", name="ck_soil_measurements_nitrogen_non_negative"),
        sa.CheckConstraint("phosphorus IS NULL OR phosphorus >= 0", name="ck_soil_measurements_phosphorus_non_negative"),
        sa.CheckConstraint("potassium IS NULL OR potassium >= 0", name="ck_soil_measurements_potassium_non_negative"),
        sa.CheckConstraint("ec IS NULL OR ec >= 0", name="ck_soil_measurements_ec_non_negative"),
        sa.CheckConstraint("organic_carbon IS NULL OR organic_carbon >= 0", name="ck_soil_measurements_organic_carbon_non_negative"),
        sa.CheckConstraint("moisture IS NULL OR (moisture >= 0 AND moisture <= 100)", name="ck_soil_measurements_moisture_range"),
        sa.CheckConstraint("source_kind IN ('farmer_entered', 'report_confirmed')", name="ck_soil_measurements_source_kind"),
        sa.CheckConstraint(
            "texture IS NULL OR texture IN "
            "(" + ",".join(f"'{t}'" for t in TEXTURE_CLASSES) + ")",
            name="ck_soil_measurements_texture",
        ),
    )
    op.create_index("ix_soil_measurements_field_id", "soil_measurements", ["field_id"])
    op.create_index("ix_soil_measurements_user_id", "soil_measurements", ["user_id"])
    op.create_index("ix_soil_measurements_tested_on", "soil_measurements", ["tested_on"])
    op.create_index("ix_soil_measurements_field_tested", "soil_measurements", ["field_id", "tested_on"])

    ranges_table = op.create_table(
        "soil_reference_ranges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parameter", sa.String(length=30), nullable=False),
        sa.Column("context_type", sa.String(length=20), nullable=False, server_default="general"),
        sa.Column("context_value", sa.String(length=60), nullable=True),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("min_value", sa.Double(), nullable=True),
        sa.Column("max_value", sa.Double(), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=True),
        sa.Column("outcome", sa.String(length=10), nullable=False, server_default="within"),
        sa.Column("explanation", sa.String(length=500), nullable=True),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=300), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "parameter IN " + "(" + ",".join(f"'{p}'" for p in ALL_PARAMS) + ")",
            name="ck_soil_reference_ranges_parameter",
        ),
        sa.CheckConstraint(
            "context_type IN ('general', 'region', 'soil_class', 'crop')",
            name="ck_soil_reference_ranges_context_type",
        ),
        sa.CheckConstraint(
            "outcome IN ('below', 'within', 'above')",
            name="ck_soil_reference_ranges_outcome",
        ),
    )
    op.create_index("ix_soil_reference_ranges_parameter", "soil_reference_ranges", ["parameter"])
    op.create_index("ix_soil_reference_ranges_context_type", "soil_reference_ranges", ["context_type"])

    op.bulk_insert(ranges_table, _ranges())


def downgrade() -> None:
    op.drop_index("ix_soil_reference_ranges_context_type", table_name="soil_reference_ranges")
    op.drop_index("ix_soil_reference_ranges_parameter", table_name="soil_reference_ranges")
    op.drop_table("soil_reference_ranges")
    op.drop_index("ix_soil_measurements_field_tested", table_name="soil_measurements")
    op.drop_index("ix_soil_measurements_tested_on", table_name="soil_measurements")
    op.drop_index("ix_soil_measurements_user_id", table_name="soil_measurements")
    op.drop_index("ix_soil_measurements_field_id", table_name="soil_measurements")
    op.drop_table("soil_measurements")
    op.drop_index("ix_soil_reports_user_id", table_name="soil_reports")
    op.drop_index("ix_soil_reports_field_id", table_name="soil_reports")
    op.drop_table("soil_reports")