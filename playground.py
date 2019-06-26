import json
import re
import string

import pycld2


def split(txt, min_length=16, max_length=128):
    spl = txt.split("\n")
    for s in spl:
        s = s.strip()
        if len(s) < min_length:
            pass
        elif len(s) <= max_length:
            yield s
        else:
            step = len(s) // (len(s) // max_length + 1) + 1
            assert len(s) % step >= min_length
            for i in range(0, len(s), step):
                yield s[i: i + step]


df = json.load(open("res/twitter/sigridr/result.json"))

print(json.dumps(df[0], indent=4))

for user in df:
    # print(user)
    for stat in user["statuses"]:
        txt = ''.join(x for x in stat["full_text"] if x in string.printable)
        det = pycld2.detect(txt, hintTopLevelDomain="no", hintLanguage="no", bestEffort=True)

        if det[2][0][1] in ["no", "nn"]:
            print("\t", det, re.sub(r"\n|(https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-z]{1,6}\b([-a-zA-Z0-9@:%_\+.~#?&\/\/=]*))|(#\w+)|(@\w+)", "", stat["full_text"]))