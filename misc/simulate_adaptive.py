import math
import time

import scipy.stats as stts

from misc.harvest_adjust import average_adjust_func


def simulate(similarities, adj_func, default_delay=3600, target=0.9):
    hist = []

    class Sim:  # Just a basic class that emulates HtmlResult's similarity method
        def __init__(self, t, b):
            self.t = t
            self.b = b

        def similarity(self, other):
            return (self.b * other.b) ** (abs(self.t - other.t) / (2 * default_delay))

        def __str__(self):
            return f"Sim(b={self.b},t={self.t})"

    t = time.time()
    delay = default_delay
    for s in similarities:
        hist.append((t, Sim(t, s)))
        delay = adj_func(default_delay, target, hist)
        # print(delay)
        t += delay
    return delay / default_delay, (t - time.time()) / default_delay


if __name__ == '__main__':
    n = 32
    adj_f = average_adjust_func
    print("All 1s:", simulate([1] * n, adj_f))
    print("All 0s:", simulate([0] * n, adj_f))
    print("All 1s, 0 at end:", simulate([1 - (i + 1) // n for i in range(n)], adj_f))
    print("All 1s, 01 at end:", simulate([0 if i == n - 2 else 1 for i in range(n)], adj_f))
    print("All 0s, 1 at end:", simulate([(i + 1) // n for i in range(n)], adj_f))
    print("All 1s, 0.7 at end:", simulate([1 - 0.3 * ((i + 1) // n) for i in range(n)], adj_f))
    for v in 0.9, 0.5, 0.1:
        r = simulate([v] * n, adj_f)
        opt = math.log(0.9) / math.log(v)
        print(f"All {v}: {r} (Optimal: {opt})")
    for alp, bet in (90, 10), (95, 5), (50, 50):
        sims = stts.beta.rvs(alp, bet, size=n)
        m = sims.mean()
        opt = math.log(0.9) / math.log(m)
        r = simulate(sims, adj_f)
        print(f"Beta({alp}, {bet}) dist: {r} (Optimal:{opt})")
