import json
import re

from requests import request

url = "http://0.0.0.0:8080"

print(request("POST", f"{url}/language", data={"text": "Tri smi kinisiri."}).content)

f = open("res/extracted_texts/veidemann/texts.ldjson")

paths = {"R"}
for i, line in enumerate(f):
    d = json.loads(line)
    if "discoveryPath" in d and "contentType" in d:
        if re.match("^R*$", d["discoveryPath"]) and re.match("text", d["contentType"], re.IGNORECASE):
            req = request("POST", f"{url}/language", data=d)
            if req.status_code < 400:
                res = req.json()

                if res["details"][0]["languageCode"] not in {"no", "nn"}:
                    print(i)
                    print(d)
                    print(res)
