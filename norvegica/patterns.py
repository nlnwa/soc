import json
import re

expressions = json.load(open("res/expressions.json"))

ensure_start = r"((?<=\W)|(?<=^))"  # Split up because lookbehind requires fixed width
ensure_end = r"(?=\W|$)"

# Patterns
pattern_names = re.compile(f"{ensure_start}"
                           f"(({expressions['boy_names']}|{expressions['girl_names']})"
                           f" ({expressions['surnames']})){ensure_end}")
pattern_postal = re.compile(expressions["postal"], re.IGNORECASE)
pattern_phone = re.compile(expressions["phone"])  # eg. "+47 51 99 00 00"
pattern_norway = re.compile(f"{ensure_start}({expressions['norway_names']}){ensure_end}", re.IGNORECASE)
pattern_counties = re.compile(f"{ensure_start}({expressions['counties']}){ensure_end}", re.IGNORECASE)
pattern_kroner = re.compile(f"{expressions['kroner']}{ensure_end}", re.IGNORECASE)
pattern_email = re.compile(expressions["email"])  # https://emailregex.com/

pattern_kr_dom = re.compile("se|dk|is|fo|gl", re.IGNORECASE)  # Domains of countries that use kr
pattern_kr_lan = re.compile("sv|da|is|fo|kl", re.IGNORECASE)  # Language codes of countries that use kr
pattern_no_html_lang = re.compile("^(no(?!ne)|nb|nn|nno|nob|nor)|bokmaal|nynorsk|NO$",
                                  re.IGNORECASE)  # Norwegian HTML lang names

# All country code top level domains
pattern_cctld = re.compile(expressions["cctld"])

