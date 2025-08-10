# -*- coding: utf-8 -*-
# soubor: bus_ticket_core/models/__init__.py

# ===================================================================
# DŮLEŽITÉ: Pořadí importů je klíčové!
# Modely musí být načteny dříve, než jsou použity v jiných modelech.
# ===================================================================

# 1. Nejdříve načteme modely, na které se ostatní odkazují.
from . import way_point
from . import price_models
from . import seat_models

# 2. Poté načteme hlavní modely, které používají ty předchozí.
from . import route_models
from . import trip_models

# 3. Nakonec načteme modely, které dědí z ostatních.
from . import inherited_models