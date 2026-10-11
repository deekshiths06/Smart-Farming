"""Crop catalogue API tests.

The catalogue (every crop a farmer can pick) is deliberately larger than the
disease model's coverage. These tests lock in that separation, the search
behaviour (case, partial, regional synonyms), pagination and filtering.
"""

from app.data import crop_catalogue as data
from app.services import crop_catalogue as svc
from app.services import plant_disease_model as model
from tests.conftest import auth_headers, fresh_email, register_user


def register(client):
    email = fresh_email("catalogue")
    register_user(client, email=email)
    return email, auth_headers(client, email)


def get(client, headers, **params):
    return client.get("/api/catalogue/crops", headers=headers, params=params)


def keys(payload):
    return [item["key"] for item in payload["items"]]


# --- Authentication ---------------------------------------------------------


def test_catalogue_requires_auth(client):
    assert client.get("/api/catalogue/crops").status_code == 401


# --- Whole-catalogue shape --------------------------------------------------


def test_full_catalogue_is_returned(client):
    _, headers = register(client)
    r = get(client, headers, limit=500)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["catalogue_size"] == data.CROP_CATALOGUE.__len__()
    assert body["total"] == body["catalogue_size"]
    assert len(body["items"]) == body["catalogue_size"]
    # A broad catalogue, not the model's handful of crops.
    assert body["catalogue_size"] >= 100


def test_catalogue_covers_many_categories(client):
    _, headers = register(client)
    body = get(client, headers, limit=500).json()
    category_keys = {c["key"] for c in body["categories"]}
    # Cereals through fruits, spices and plantation crops.
    assert {
        "cereal",
        "millet",
        "pulse",
        "oilseed",
        "vegetable",
        "fruit",
        "spice",
        "plantation",
        "fibre",
    } <= category_keys
    # Category counts add up to the whole catalogue.
    assert sum(c["count"] for c in body["categories"]) == body["catalogue_size"]


# --- Catalogue vs model coverage --------------------------------------------


def test_catalogue_is_not_truncated_to_model_coverage(client):
    _, headers = register(client)
    body = get(client, headers, limit=500).json()
    supported = model.supported_crop_keys()

    # The catalogue is much larger than the model's coverage.
    assert body["catalogue_size"] > body["model_supported_count"]
    assert body["model_supported_count"] == len(supported)

    items = {item["key"]: item for item in body["items"]}
    # A crop in the catalogue but NOT in the model must still be selectable...
    assert "rice" in items
    assert items["rice"]["model_supported"] is False
    # ...and a crop the model knows is flagged as supported.
    assert "tomato" in items
    assert items["tomato"]["model_supported"] is True


def test_every_model_crop_is_in_the_catalogue(client):
    _, headers = register(client)
    body = get(client, headers, limit=500).json()
    items = {item["key"]: item for item in body["items"]}
    for key in model.supported_crop_keys():
        assert key in items, f"{key} is supported by the model but missing from the catalogue"
        assert items[key]["model_supported"] is True
    # The service's own view of supported keys matches the model service exactly.
    assert svc.model_supported_keys() == set(model.supported_crop_keys())


# --- Search -----------------------------------------------------------------


def test_search_is_case_insensitive(client):
    _, headers = register(client)
    assert keys(get(client, headers, q="ToMaTo").json()) == ["tomato"]


def test_search_matches_partial_names(client):
    _, headers = register(client)
    assert "tomato" in keys(get(client, headers, q="tom").json())
    assert "potato" in keys(get(client, headers, q="pota").json())


def test_search_matches_common_and_regional_synonyms(client):
    _, headers = register(client)
    cases = {
        "paddy": "rice",
        "haldi": "turmeric",
        "kela": "banana",
        "angoor": "grape",
        "kollu": "horse_gram",
        "shimla mirch": "pepper_bell",
        "jowar": "sorghum",
        "bhindi": "okra",
    }
    for query, expected in cases.items():
        assert expected in keys(get(client, headers, q=query).json()), query


def test_search_with_no_matches_is_empty(client):
    _, headers = register(client)
    body = get(client, headers, q="zzzzzznotacrop").json()
    assert body["items"] == []
    assert body["total"] == 0
    # The category list still comes back so the UI can render filters.
    assert body["categories"]


def test_search_result_is_flagged_for_model_support(client):
    _, headers = register(client)
    items = {item["key"]: item for item in get(client, headers, q="m").json()["items"]}
    assert items["maize"]["model_supported"] is True
    assert items["mango"]["model_supported"] is False


# --- Filtering & pagination -------------------------------------------------


def test_category_filter(client):
    _, headers = register(client)
    body = get(client, headers, category="fruit", limit=500).json()
    assert body["total"] >= 20
    assert all(item["category"] == "fruit" for item in body["items"])


def test_pagination_slices_without_overlap(client):
    _, headers = register(client)
    first = get(client, headers, limit=10, offset=0).json()
    second = get(client, headers, limit=10, offset=10).json()
    assert first["total"] == second["total"] == data.CROP_CATALOGUE.__len__()
    assert len(first["items"]) == 10 and len(second["items"]) == 10
    assert set(keys(first)).isdisjoint(set(keys(second)))


def test_search_is_ranked_by_relevance(client):
    _, headers = register(client)
    # An exact/prefix display-name match should come before a synonym-only match.
    body = get(client, headers, q="rice").json()
    assert body["items"][0]["key"] == "rice"
