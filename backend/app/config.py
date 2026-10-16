import os

SECRET_KEY = "super_secret_basketball_jwt_key_engineering_thesis"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

DB_CONFIG = {
    "user": "basket_user",
    "password": "basket_password123",
    "database": "basketball_db",
    "host": "localhost",
    "port": 5432
}

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

SURFACE_MAP = {
    "asfalt": "asphalt",
    "asphalt": "asphalt",
    "tartan": "tartan",
    "beton": "concrete",
    "concrete": "concrete",
    "parkiet": "indoor_parquet",
    "indoor_parquet": "indoor_parquet"
}

BACKBOARD_MAP = {
    "stal/krata": "steel_grid",
    "stalowa": "steel_grid",
    "steel_grid": "steel_grid",
    "szklo akrylowe": "acrylic_glass",
    "akryl": "acrylic_glass",
    "acrylic_glass": "acrylic_glass",
    "drewno": "wood_plywood",
    "sklejka": "wood_plywood",
    "wood_plywood": "wood_plywood",
    "wlokno szklane": "fiberglass",
    "fiberglass": "fiberglass"
}

RIM_MAP = {
    "standard_rigid": "standard_rigid",
    "sztywna": "standard_rigid",
    "uchylna": "flex_spring",
    "flex_spring": "flex_spring",
    "podwojna": "double_rim",
    "double_rim": "double_rim"
}

NET_MAP = {
    "lancuchowa": "chain",
    "łańcuchowa": "chain",
    "chain": "chain",
    "sznurkowa": "nylon",
    "nylon": "nylon",
    "brak": "none",
    "none": "none"
}