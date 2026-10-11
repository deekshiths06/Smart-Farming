"""Central ANNADATA crop catalogue.

This is the single reference list of crops a farmer can pick when telling the
app *what they photographed*, so the disease selector is never limited to the
handful of crops the image model happens to know.

Relationship to the rest of the project
---------------------------------------
The Crop Recommendations knowledge base (``app.data.crop_knowledge``) is a
purpose-specific dataset: every crop there carries documented agronomic
requirements so it can be scored against a field. That list is deliberately
narrow (29 crops across cereals, millets, pulses, oilseeds, fibre and
vegetables).

The catalogue here is a **strict superset** built on top of it:

- the recommendation crops are imported and re-used verbatim (same ``key`` slug
  and ``display_name``), so the two can never drift apart;
- additional India-relevant crops are appended for the categories the
  recommendation base does not cover (fruits, spices, plantation/cash crops,
  forage, and more cereals/millets/pulses/oilseeds).

Being in this catalogue does **not** mean the disease model can analyse the
crop. Model coverage is a separate, explicitly documented fact (see
``app.services.plant_disease_model``); the catalogue API reports it per crop as
``model_supported``. The two lists are intentionally different sizes.
"""

from __future__ import annotations

from typing import Final

from app.data.crop_knowledge import CROPS as _RECOMMENDATION_CROPS

# Category set for the catalogue. A superset of the recommendation categories
# (cereal, millet, pulse, oilseed, fibre, vegetable).
CATEGORY_LABELS: Final[dict[str, str]] = {
    "cereal": "Cereals",
    "millet": "Millets",
    "pulse": "Pulses",
    "oilseed": "Oilseeds",
    "fibre": "Fibre crops",
    "vegetable": "Vegetables",
    "fruit": "Fruits",
    "spice": "Spices & condiments",
    "plantation": "Plantation & cash crops",
    "forage": "Forage & fodder",
    "other": "Other crops",
}

CATEGORY_ORDER: Final[tuple[str, ...]] = (
    "cereal",
    "millet",
    "pulse",
    "oilseed",
    "vegetable",
    "fruit",
    "spice",
    "plantation",
    "fibre",
    "forage",
    "other",
)


def _entry(
    key: str,
    display_name: str,
    category: str,
    synonyms: tuple[str, ...] | list[str] = (),
) -> dict:
    """One catalogue row with cleaned, de-duplicated search synonyms."""
    seen: list[str] = []
    for term in synonyms:
        term = (term or "").strip()
        if not term:
            continue
        if term.lower() == display_name.lower():
            continue
        if term.lower() in {t.lower() for t in seen}:
            continue
        seen.append(term)
    return {
        "key": key,
        "display_name": display_name,
        "category": category,
        "synonyms": seen,
    }


# Common names and regional synonyms for the recommendation crops, so the
# selector finds them by what a farmer actually calls them.
_RECOMMENDATION_SYNONYMS: Final[dict[str, list[str]]] = {
    "rice": ["paddy", "dhan", "nellu", "akki"],
    "maize": ["corn", "makka", "makai", "bhutta", "mokkajonna"],
    "wheat": ["gehun", "godhi", "gahu"],
    "sorghum": ["jowar", "jonna", "cholam", "dhura"],
    "pearl_millet": ["bajra", "bajri", "kambu", "sajjalu"],
    "finger_millet": ["ragi", "mandua", "nachni", "kelvaragu"],
    "groundnut": ["peanut", "moongphali", "shenga", "verkadalai", "palli"],
    "chickpea": ["chana", "kabuli chana", "bengal gram", "senagalu", "kadala"],
    "pigeonpea": ["tur", "arhar", "toor dal", "kandi", "thuvaram"],
    "green_gram": ["moong", "mung", "pesalu", "pachai payaru", "hesaru"],
    "cotton": ["kapas", "rui", "paruthi", "pratti"],
    "tomato": ["tamatar", "thakkali", "ramya"],
    "barley": ["jau", "barli"],
    "barnyard_millet": ["sanwa", "sama", "kuthiraivali", "odalu"],
    "kodo_millet": ["kodra", "arikelu", "varagu"],
    "foxtail_millet": ["navane", "kakun", "thenai", "korralu"],
    "black_gram": ["urad", "urad dal", "minapa", "ulundhu"],
    "lentil": ["masoor", "masur", "masoor dal", "mysore dal"],
    "cowpea": ["lobia", "chawli", "alsande", "karamani", "bobbarlu"],
    "mustard": ["sarson", "rai", "sarso", "kadugu", "aava"],
    "soybean": ["soya", "soya bean", "bhatmas", "soya bean"],
    "sunflower": ["surajmukhi", "sooryakanthi", "poddu tirugudu"],
    "sesame": ["til", "gingelly", "nuvvulu", "ellu"],
    "jute": ["pat", "joot", "chanal"],
    "potato": ["aloo", "aalugadda", "urulaikizhangu", "batata"],
    "onion": ["pyaz", "kanda", "vengayam", "eerulli", "ulli"],
    "chilli": ["mirch", "mirchi", "menasinakai", "milagai", "koora mirapa"],
    "brinjal": ["eggplant", "aubergine", "baingan", "vankaya", "kathirikkai"],
    "okra": ["bhindi", "lady finger", "bendakaya", "vendakkai"],
}


# Additional crops beyond the recommendation knowledge base.
_EXTRA_CROPS: Final[tuple[dict, ...]] = (
    # --- Fruits -------------------------------------------------------------
    _entry("apple", "Apple", "fruit", ["seb"]),
    _entry("banana", "Banana", "fruit", ["kela", "vazhai", "bale", "kadali"]),
    _entry("mango", "Mango", "fruit", ["aam", "aamra", "maav", "mamidi"]),
    _entry("guava", "Guava", "fruit", ["amrood", "peru", "jamakaya"]),
    _entry("pomegranate", "Pomegranate", "fruit", ["anar", "dalimb", "danimma", "mathalam"]),
    _entry("papaya", "Papaya", "fruit", ["papita", "pappali", "bommi"]),
    _entry("lemon", "Lemon", "fruit", ["nimbu", "elumichai", "nimmakaya"]),
    _entry("orange", "Orange", "fruit", ["santra", "narangi", "kamala", "nagpur orange"]),
    _entry("grape", "Grape", "fruit", ["angoor", "draksha", "drakshai", "draksa"]),
    _entry("cherry", "Cherry", "fruit", ["sour cherry", "cherry fruit"]),
    _entry("peach", "Peach", "fruit", ["aadu", "aru", "peach fruit"]),
    _entry("plum", "Plum", "fruit", ["aloo bukhara", "alubukhara"]),
    _entry("pear", "Pear", "fruit", ["nashpati", "berikkai"]),
    _entry("strawberry", "Strawberry", "fruit", ["strawberries"]),
    _entry("blueberry", "Blueberry", "fruit", ["blueberries"]),
    _entry("raspberry", "Raspberry", "fruit", ["raspberries"]),
    _entry("blackberry", "Blackberry", "fruit", ["blackberries"]),
    _entry("watermelon", "Watermelon", "fruit", ["tarbooz", "mathan", "kalangadi"]),
    _entry("muskmelon", "Muskmelon", "fruit", ["kharbooja", "kekkarikkai", "kharbuja"]),
    _entry("pineapple", "Pineapple", "fruit", ["ananas", "annasi", "anasa"]),
    _entry("sapota", "Sapota", "fruit", ["chikoo", "sapayya", "sapota fruit"]),
    _entry("custard_apple", "Custard apple", "fruit", ["sitaphal", "sharifa", "seethaphal"]),
    _entry("litchi", "Litchi", "fruit", ["lychee", "lichi"]),
    _entry("amla", "Indian gooseberry (amla)", "fruit", ["amla", "nellikai", "usirikaya"]),
    _entry("jamun", "Jamun", "fruit", ["java plum", "naaval", "neredu"]),
    _entry("ber", "Ber", "fruit", ["indian jujube", "bor", "regu"]),
    _entry("fig", "Fig", "fruit", ["anjeer", "aththi", "fig fruit"]),
    _entry("jackfruit", "Jackfruit", "fruit", ["kathal", "palapazham", "panasa"]),
    _entry("avocado", "Avocado", "fruit", ["butter fruit", "avocado pear"]),
    _entry("dragon_fruit", "Dragon fruit", "fruit", ["pitaya"]),
    _entry("kiwi", "Kiwi", "fruit", ["kiwi fruit", "chinese gooseberry"]),
    # --- Vegetables ---------------------------------------------------------
    _entry("cabbage", "Cabbage", "vegetable", ["patta gobi", "muttaikose", "kosu"]),
    _entry("cauliflower", "Cauliflower", "vegetable", ["phool gobi", "poo", "hookosu"]),
    _entry("carrot", "Carrot", "vegetable", ["gajar", "carrot root"]),
    _entry("radish", "Radish", "vegetable", ["mooli", "mullangi", "moolangi"]),
    _entry("beetroot", "Beetroot", "vegetable", ["chukandar", "beet"]),
    _entry("spinach", "Spinach", "vegetable", ["palak", "keerai", "palakura"]),
    _entry("cucumber", "Cucumber", "vegetable", ["kheera", "vellarikkai", "dosa kaya"]),
    _entry("pumpkin", "Pumpkin", "vegetable", ["kaddu", "parangikai", "gummadi kaya"]),
    _entry("bitter_gourd", "Bitter gourd", "vegetable", ["karela", "pavakkai", "kakarakaya"]),
    _entry("bottle_gourd", "Bottle gourd", "vegetable", ["lauki", "surakkai", "sorakaya", "ghiya"]),
    _entry("ridge_gourd", "Ridge gourd", "vegetable", ["turai", "peerkangai", "beerakaya"]),
    _entry("snake_gourd", "Snake gourd", "vegetable", ["chichinda", "pudalangai", "potlakaya"]),
    _entry("ivy_gourd", "Ivy gourd", "vegetable", ["kundru", "kovakkai", "dondakaya", "tindora"]),
    _entry("drumstick", "Drumstick (moringa)", "vegetable", ["moringa", "sahjan", "murungai", "munaga"]),
    _entry("pepper_bell", "Bell pepper (capsicum)", "vegetable", ["capsicum", "shimla mirch", "sweet pepper"]),
    _entry("squash", "Squash", "vegetable", ["butternut", "pumpkin squash"]),
    _entry("sweet_potato", "Sweet potato", "vegetable", ["shakarkandi", "genasu", "sakkaraivalli"]),
    _entry("taro", "Taro (arbi)", "vegetable", ["arbi", "colocasia", "seppankizhangu", "chamagadda"]),
    _entry("elephant_foot_yam", "Elephant foot yam", "vegetable", ["jimikand", "suran", "kanda"]),
    _entry("tapioca", "Tapioca (cassava)", "vegetable", ["cassava", "maravalli", "karrapendalam"]),
    _entry("turnip", "Turnip", "vegetable", ["shalgam", "turnip root"]),
    _entry("lettuce", "Lettuce", "vegetable", ["salad leaf"]),
    _entry("broccoli", "Broccoli", "vegetable", ["broccoli"]),
    _entry("french_bean", "French bean", "vegetable", ["green bean", "haricot", "beans"]),
    _entry("cluster_bean", "Cluster bean (guar)", "vegetable", ["guar", "gawar", "goruchikkudu"]),
    # --- Cereals ------------------------------------------------------------
    _entry("oats", "Oats", "cereal", ["jai", "javi"]),
    _entry("rye", "Rye", "cereal", ["rye grain"]),
    _entry("buckwheat", "Buckwheat", "cereal", ["kuttu", "kothu"]),
    _entry("amaranth", "Amaranth (grain)", "cereal", ["rajgira", "chaulai", "thotakura"]),
    _entry("quinoa", "Quinoa", "cereal", ["quinoa grain"]),
    # --- Millets ------------------------------------------------------------
    _entry("proso_millet", "Proso millet (common millet)", "millet", ["chena", "variga", "baragu"]),
    _entry("little_millet", "Little millet", "millet", ["samai", "kutki", "chama"]),
    _entry("browntop_millet", "Browntop millet", "millet", ["korale", "andu korralu"]),
    # --- Pulses -------------------------------------------------------------
    _entry("green_pea", "Green pea", "pulse", ["matar", "peas", "batani", "pattani"]),
    _entry("horse_gram", "Horse gram", "pulse", ["kulthi", "kollu", "hurali", "ulavalu"]),
    _entry("moth_bean", "Moth bean", "pulse", ["moth", "matki", "madua"]),
    _entry("rajma", "Rajma (kidney bean)", "pulse", ["kidney bean", "rajmah"]),
    _entry("lathyrus", "Lathyrus (khesari)", "pulse", ["khesari", "teora"]),
    # --- Oilseeds -----------------------------------------------------------
    _entry("castor", "Castor", "oilseed", ["arandi", "amudham"]),
    _entry("linseed", "Linseed (flax)", "oilseed", ["alsi", "flax", "agasi"]),
    _entry("niger", "Niger", "oilseed", ["ramtil", "sorguja", "gurellu"]),
    _entry("safflower", "Safflower", "oilseed", ["kusum", "kardi"]),
    # --- Fibre crops --------------------------------------------------------
    _entry("hemp", "Hemp", "fibre", ["bhang"]),
    _entry("mesta", "Mesta (kenaf)", "fibre", ["kenaf", "ambadi"]),
    _entry("sunhemp", "Sunhemp", "fibre", ["sanai", "sun hemp"]),
    _entry("ramie", "Ramie", "fibre", ["rhea"]),
    _entry("sisal", "Sisal", "fibre", ["sisal hemp"]),
    # --- Spices & condiments ------------------------------------------------
    _entry("turmeric", "Turmeric", "spice", ["haldi", "manjal", "pasupu"]),
    _entry("ginger", "Ginger", "spice", ["adrak", "inji", "allam", "shunti"]),
    _entry("garlic", "Garlic", "spice", ["lehsun", "poondu", "vellulli", "lasan"]),
    _entry("black_pepper", "Black pepper", "spice", ["kali mirch", "miriyalu", "kurumulaku"]),
    _entry("cumin", "Cumin", "spice", ["jeera", "jeeraka", "seeragam"]),
    _entry("coriander", "Coriander", "spice", ["dhania", "kothamalli", "dhaniyalu"]),
    _entry("fenugreek", "Fenugreek", "spice", ["methi", "vendhayam", "menthikura"]),
    _entry("cardamom", "Cardamom", "spice", ["elaichi", "elakkai", "yelakki"]),
    _entry("clove", "Clove", "spice", ["laung", "kirambu", "lavangam"]),
    _entry("cinnamon", "Cinnamon", "spice", ["dalchini", "lavangapattai"]),
    _entry("nutmeg", "Nutmeg", "spice", ["jaiphal", "jathikai"]),
    _entry("fennel", "Fennel", "spice", ["saunf", "perunjeeragam", "sompu"]),
    _entry("ajwain", "Ajwain (carom)", "spice", ["carom seeds", "omam", "vaamu"]),
    _entry("star_anise", "Star anise", "spice", ["chakra phool"]),
    # --- Plantation & cash crops -------------------------------------------
    _entry("tea", "Tea", "plantation", ["chai", "theyilai", "tea leaf"]),
    _entry("coffee", "Coffee", "plantation", ["kaapi", "kofi"]),
    _entry("rubber", "Rubber", "plantation", ["rahbar"]),
    _entry("coconut", "Coconut", "plantation", ["nariyal", "thengai", "kobbari", "narikel"]),
    _entry("arecanut", "Arecanut", "plantation", ["supari", "adike", "betel nut", "pakku"]),
    _entry("cashew", "Cashew", "plantation", ["kaju", "mundiri", "jeedipappu"]),
    _entry("cocoa", "Cocoa", "plantation", ["kakao"]),
    _entry("oil_palm", "Oil palm", "plantation", ["palm oil"]),
    _entry("betel_vine", "Betel vine", "plantation", ["paan", "betel leaf", "vetrilai", "tambulam"]),
    # --- Forage & fodder ----------------------------------------------------
    _entry("berseem", "Berseem", "forage", ["barseem", "egyptian clover"]),
    _entry("lucerne", "Lucerne (alfalfa)", "forage", ["alfalfa", "rajka"]),
    _entry("napier_grass", "Napier grass", "forage", ["elephant grass", "napier fodder"]),
    _entry("guinea_grass", "Guinea grass", "forage", ["guinea fodder"]),
    # --- Other --------------------------------------------------------------
    _entry("sugarcane", "Sugarcane", "other", ["ganna", "karumbu", "cherukugaddi"]),
    _entry("date_palm", "Date palm", "other", ["khajur", "dates", "perichchankai"]),
)


def _build_catalogue() -> list[dict]:
    by_key: dict[str, dict] = {}
    # 1. The recommendation knowledge base, reused verbatim (same key + name).
    for crop in _RECOMMENDATION_CROPS:
        by_key[crop["name"]] = _entry(
            crop["name"],
            crop["display_name"],
            crop["category"],
            _RECOMMENDATION_SYNONYMS.get(crop["name"], []),
        )
    # 2. Additional region-relevant crops.
    for crop in _EXTRA_CROPS:
        by_key.setdefault(crop["key"], crop)

    order = {category: index for index, category in enumerate(CATEGORY_ORDER)}
    return sorted(
        by_key.values(),
        key=lambda crop: (order.get(crop["category"], len(order)), crop["display_name"].lower()),
    )


CROP_CATALOGUE: Final[list[dict]] = _build_catalogue()

CROP_CATALOGUE_BY_KEY: Final[dict[str, dict]] = {
    crop["key"]: crop for crop in CROP_CATALOGUE
}

__all__ = [
    "CATEGORY_LABELS",
    "CATEGORY_ORDER",
    "CROP_CATALOGUE",
    "CROP_CATALOGUE_BY_KEY",
]
