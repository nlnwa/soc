import datetime
import random
import re
from collections import namedtuple

alphabet_tuple = namedtuple("AlphabetTuple", ["alphabet", "k1_coefficients", "k2_coefficients"])

alphabets = {
    10: alphabet_tuple(alphabet="123456789",
                       k1_coefficients=(3, 7, 6, 1, 8, 9, 4, 5, 2),
                       k2_coefficients=(5, 4, 3, 2, 7, 6, 5, 4, 3, 2)),
    17: alphabet_tuple(alphabet="159ABCDEGKMPTUWXZ",
                       k1_coefficients=(3, 7, 6, 1, 8, 9, 4, 5, 2),
                       k2_coefficients=(5, 4, 3, 2, 7, 6, 5, 4, 3, 2)),
    19: alphabet_tuple(alphabet="2589ACDEFHJLMNPTUWX",
                       k1_coefficients=(3, 7, 6, 1, 8, 9, 4, 5, 2),
                       k2_coefficients=(5, 4, 3, 2, 7, 6, 5, 4, 3, 2)),
    23: alphabet_tuple(alphabet="2589ACDEFGHIJKLMNPRTUWX",
                       k1_coefficients=(3, 7, 6, 1, 8, 9, 4, 5, 2),
                       k2_coefficients=(5, 4, 3, 2, 7, 6, 5, 4, 3, 2)),
    29: alphabet_tuple(alphabet="3679ABCDEFHIJKLMNOPQRSTUVWXYZ",
                       k1_coefficients=(3, 7, 6, 1, 8, 9, 4, 5, 2),
                       k2_coefficients=(5, 4, 3, 2, 7, 6, 5, 4, 3, 2)),
}


def calculate_control_digits(digits, k1_coeffs, k2_coeffs, q=11):
    calc_k1, calc_k2 = 0, 0
    for dig, c1, c2 in zip(digits, k1_coeffs, k2_coeffs):
        calc_k1 += c1 * dig
        calc_k2 += c2 * dig
    calc_k1 = q - calc_k1 % q
    if calc_k1 == q:
        calc_k1 = 0
    calc_k2 = q - (calc_k2 + k2_coeffs[-1] * calc_k1) % q
    if calc_k2 == q:
        calc_k2 = 0
    return calc_k1, calc_k2


def find_id_number(txt):
    alph = alphabets[10]
    matches = re.finditer(r"(\d\d)(\d\d)(\d\d) ?(\d{5})", txt)
    for match in matches:
        day = int(match[1])
        month = int(match[2])
        year = int(match[3])
        personal = int(match[4])
        individual, control = divmod(personal, 100)

        d1, d2 = divmod(day, 10)
        m1, m2 = divmod(month, 10)
        y1, y2 = divmod(year, 10)
        (i1, i2), i3 = divmod(individual // 10, 10), individual % 10
        k1, k2 = divmod(control, 10)

        digits = (d1, d2, m1, m2, y1, y2, i1, i2, i3, k1, k2)

        calc_k1, calc_k2 = calculate_control_digits(digits, alph.k1_coefficients, alph.k2_coefficients)

        if calc_k1 != k1 or calc_k2 != k2:
            continue

        if individual < 100 and year < 40 \
                or 500 <= individual and (
                year < 40
                or individual < 900 and year < 55):
            year += 2000
        elif individual < 500:
            year += 1900
        elif individual < 800 and 55 <= year:
            year += 1800
        else:
            continue

        try:
            date = datetime.date(year, month, day)
        except ValueError:
            continue
        if date > datetime.date.today():
            continue

        gender = "fm"[individual % 2]
        yield "".join(str(d) for d in digits), date, gender


def gen_id_number(date: datetime.date, gender):
    alph = alphabets[10]
    day, month, year = date.day, date.month, date.year
    century, decade = divmod(year, 100)

    i1_cand = None
    if century == 18 and 55 <= decade:
        i1_cand = (7, 6, 5)
    elif century == 19:
        if decade <= 40:
            i1_cand = (4, 3, 2, 1, 0)
        else:
            i1_cand = (4, 3, 2, 1)
    elif century == 20:
        if decade < 40:
            i1_cand = (9, 8, 7, 6, 5, 0)
        elif decade < 55:
            i1_cand = (8, 7, 6, 5)

    if i1_cand is None:
        raise ValueError("Invalid date")

    i2_cand = (9, 8, 7, 6, 5, 4, 3, 2, 1, 0)
    if gender == "f":
        i3_cand = (8, 6, 4, 2, 0)
    elif gender == "m":
        i3_cand = (9, 7, 5, 3, 1)
    else:
        raise ValueError("Invalid gender")

    d1, d2 = divmod(day, 10)
    m1, m2 = divmod(month, 10)
    y1, y2 = divmod(decade, 10)

    for i1 in i1_cand:
        for i2 in i2_cand:
            for i3 in i3_cand:
                digits = (d1, d2, m1, m2, y1, y2, i1, i2, i3)
                k1, k2 = calculate_control_digits(digits, alph.k1_coefficients, alph.k2_coefficients)

                if k1 > 9 or k2 > 9:
                    continue

                personal_id = f"{d1}{d2}{m1}{m2}{y1}{y2}{i1}{i2}{i3}{k1}{k2}"

                yield personal_id


if __name__ == '__main__':

    m = set(gen_id_number(datetime.date.today(), "m"))
    f = set(gen_id_number(datetime.date.today(), "f"))
    gend = sorted(m | f, reverse=True).__iter__()

    me = "010720"
    conc = "\n".join(me + str(u).zfill(5) for u in range(100000 - 1, -1, -1))
    c = 0
    for idn in find_id_number(conc):
        if idn[1].year == 2020:
            print(idn)
            c += 1
            if idn[0] != next(gend):
                print("Error:", idn)
    if (g := next(gend, None)) is None:
        print("Success!")
    else:
        print(g)
    print(c)

    # print(list(find_id_number("Personnr:26049730852, 27089345676")))
