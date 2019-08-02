import csv
import json


# Generates regular expressions for various typically Norwegian text features.

def get_names(file, delimiter=";"):
    # Fetches names from file
    source = open(file)
    rdr = csv.reader(source, delimiter=delimiter)
    names = []
    next(rdr)
    for row in rdr:
        names.append(row[0][0].upper() + row[0][1:].lower())

    return names


# Postal code + city
# https://data.norge.no/data/posten-norge/postnummer-i-norge
source = open("res/Postnummerregister-ansi.txt", encoding="iso 8859-1")
rdr = csv.reader(source, delimiter="\t")
postal = []

for row in rdr:
    postal.append(row[0] + " " + row[1])

# https://www.ssb.no/navn
surnames = get_names("res/etternavn.csv")
boy_names = get_names("res/guttenavn_alle.csv")
girl_names = get_names("res/jentenavn_alle.csv")

# https://en.wikipedia.org/wiki/List_of_country_names_in_various_languages_(J%E2%80%93P)#N
norway_names = "an Iorua|Naraoẏe|নরওয়ে|Na Uy|Nirribhidh|Noorweë|Noorwegen|Norge|Noreg|Noregur|Noreuwei|Norŭwei|노르웨이|" \
               "Norga|Norge|Norja|Norra|Norsko|Nórsko|Noruega|Noruwega|Noruwē|ノルウェー|Norveç|Norvèg·e|Norvège|" \
               "Norvegia|Norvégia|Norvehia|Норвегія|Norvēģija|Norvegija|Norvegio|Norvegiya|Норвегия|Norvegiya" \
               "|נורבגיה|" \
               "in-Norveġja|Norvegjia|Norvegye|נאָרװעגיע|Norveška|Норвешка|Norveška|Norvigía|Νορβηγία|Norway|" \
               "Norway|නෝර්වේ|Norweege|Norwegen|Norwègia|Norwegia|Norwegska|Norwéy|ኖርዌይ|Norwij|Nowe|นอร์เวย์|" \
               "Norwy|Nuówēi|挪威|Nuruwai|நோர்வே".split("|")

# https://translatr.varunmalhotra.xyz/
norway_names += "Noorse|النرويجية|norveçli|нарвежская|норвежки|নরওয়েজিয়ান|norveški|noruec|Norwegian " \
                "nga|norský|norwegian|Norsk|Norwegisch|Νορβηγός|Norwegian|Norwegian|noruego|norra|Norvegiako" \
                "|نروژی|norja|norvégien|Gaeilge|Noruegués|નૉર્વેજીયન|Yaren mutanen " \
                "Norway|नार्वेजियन|Norwegian|norveški|norwegian|norvég|նորվեգական|Norwegia|Norwegian|norwegian" \
                "|norvegese|נורבגי|ノルウェーの|Norwegian|ნორვეგიული|норвегиялық|ន័រវេស|ನಾರ್ವೇಜಿಯನ್|노르웨이의|Norwegian" \
                "|ນອກແວ|Norvegijos|norvēģu|norvejiana|Norwegian|Норвешка|നോർവീജിയൻ|Норвегийн|नॉर्वेजियन|norwegian" \
                "|Norveġiż|နျော|नर्वेजियन|Noors|norsk|Chinorowe|ਨਾਰਵੇਈ|norweski|norueguês|norvegian" \
                "ă|норвежский|නෝර්වීජියානු|nórsky|Norveški|Norwegian|norvegjez|норвешки|Norwegian|Norwegia|Norwegian" \
                "|Norway|நார்வேஜியன்|నార్వేజియన్|Норвегиягӣ|นอร์เวย์|Norwegian|Norveçli|норвезький|ناروے|Norvegiya|Na " \
                "Uy|נאָרוועגיש|Norwegian|挪威|挪威|挪威|Norwegian".split("|")

# https://en.wikipedia.org/wiki/Administrative_divisions_of_Norway#Regions
counties = r"akershus|aust.?agder|buskerud|finnmark|hedmark|hordaland|møre|romsdal|nordland|oppland|oslo|" \
           r"rogaland|sogn|fjordane|telemark|troms|trøndelag|vest.?agder|vestfold|østfold".split("|")

d = {
    "postal": postal,
    "boy_names": boy_names,
    "girl_names": girl_names,
    "surnames": surnames,
    "norway_names": norway_names,
    "counties": counties
}

with open("res/expressions.json", "w") as fp:
    json.dump(d, fp, indent=4)
