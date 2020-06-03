import csv
import json
import re


# Generates regular expressions for various typically Norwegian text features.
def get_names(file, delimiter=";"):
    # Fetches names from file
    source = open(file)
    rdr = csv.reader(source, delimiter=delimiter)
    names = set()
    next(rdr)
    for row in rdr:
        for name in row:
            name = re.sub(r"\W|\d", "", name)
            if name:
                names.add(name[0].upper() + name[1:].lower())

    return "|".join(names)


# Postal code + city
# https://data.norge.no/data/posten-norge/postnummer-i-norge
source = open("res/Postnummerregister-ansi.txt", encoding="iso 8859-1")
rdr = csv.reader(source, delimiter="\t")
postal = []

for row in rdr:
    postal.append(row[0] + " " + row[1])

postal = "|".join(postal)

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
               "Norway|නෝර්වේ|Norweege|Norwegen|Norwègia|Norwegia|Norwegska|Norwéy|ኖርዌይ|Norwij|นอร์เวย์|" \
               "Norwy|Nuówēi|挪威|Nuruwai|நோர்வே"

# https://translatr.varunmalhotra.xyz/
norway_names += "Noorse|النرويجية|Norveç|Нарвежская|норвежки|নরওয়েজিয়ান|Norveški|Noruec|Norwegian|Norština|Norwyeg" \
                "|Norsk|norwegisch|Νορβηγός|Norwegian|Norwegian|noruego|Norra keeles|Norvegiako|نروژی|Norjan " \
                "kieli|norvégien|Ioruais|Noruegués|નોર્વેજીયન|Yaren mutanen " \
                "Norway|नार्वेजियन|Norwegian|norveški|Nòvejyen|norvég|Նորվեգերեն|Norwegia|Ndi " \
                "Norwegian|Norsku|norvegese|נורווגית|ノルウェー語|Norwegia|ნორვეგიული|Норвегиялық|ន័រវេស។|ನಾರ್ವೇಜಿಯನ್|노르웨이 " \
                "인|Norwegian|ນໍເວ|Norvegų|Norvēģi|norvejiana|Rakihi|Норвешки|നോർവീജിയൻ|Норвеги хэл|नॉर्वेजियन|Bahasa " \
                "Norway|Norveġiż|နျော|नर्वेजियन|Noors|Norwegian|Chinorway|ਨਾਰਵੇਜੀਅਨ|norweski|norueguês|norvegian" \
                "|норвежский язык|නෝර්වීජියානු|nórsky|Norveščina|Noorwiijiga|norvegjez|Норвешки|Se-Norway|Norwegia" \
                "|norrman|Kinorwe|நார்வேஜியன்|నార్వేజియన్|Норвегӣ|นอร์เวย์|Norwegian|Norveççe" \
                "|Норвезька|نارویجین|Norvegcha|Na Uy|נאָרוועגיש|Nowejiani|挪威|挪威|挪威|IsiNorway"

# https://en.wikipedia.org/wiki/Administrative_divisions_of_Norway#Regions
counties = r"akershus|aust.?agder|buskerud|finnmark|hedmark|hordaland|møre|romsdal|nordland|oppland|oslo|" \
           r"rogaland|sogn|fjordane|telemark|troms|trøndelag|vest.?agder|vestfold|østfold"

phone = r"([^\d]|^)((\(?(\+|00)?47\)?)(\W?\d){8})([^\d]|$)"
kroner = r"(\d+ ?(kr(oner)?|NOK))"

email = r"(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[" \
        r"\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(" \
        r"?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[" \
        r"0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[" \
        r"a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[" \
        r"\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"

cctld = "ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bl|bm|bn" \
        "|bo|br|bq|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cw|cx|cy|cz" \
        "|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl" \
        "|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp" \
        "|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mf|mg|mh|mk" \
        "|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe" \
        "|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm" \
        "|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk" \
        "|um|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zr|zw"

d = {
    "postal": postal,
    "boy_names": boy_names,
    "girl_names": girl_names,
    "surnames": surnames,
    "norway_names": norway_names,
    "counties": counties,
    "phone": phone,
    "kroner": kroner,
    "email": email,
    "cctld": cctld
}

with open("res/expressions.json", "w") as fp:
    json.dump(d, fp, indent=4)
