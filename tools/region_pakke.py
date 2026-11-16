"""Gjennomgangspakke for en region (T1, Theodor 09.11.2026): én markdown-fil med oversikt, én tabell per spot
(id og navn, posisjon og hvor den kommer fra, facing, svellvindu, offshore-vind, BarentsWatch-punkt med avstand,
dybde og retning, eksponering, tidevannssted, vern/forbud, sikkerhet A/B/C og hva som er usikkert), spotene som
holdes tilbake, og kallbudsjettet med regionen. Tegner også ett oversiktsbilde for regionen.

Leser spots.json (gjelder foran alt annet når spoten ligger der), data/kandidater/bygget/<id>.json (spotfabrikken),
kandidater.json, posisjoner.json, vern.json og status_overstyring.json. Skriver bare pakka og bildet - endrer aldri
spots.json eller de byggede forslagene. Hemmelige kandidater er aldri med. Manglende verdier vises som «–», aldri 0.

Ligger det en fil <ut uten .md>.notater.md ved siden av, limes den inn under sammendraget (håndskrevet: hva som er
nytt, hva som skal til for spotene som holdes tilbake, spørsmål til gjennomgangen).

  python tools/region_pakke.py "Lofoten,Vesterålen" data/kandidater/bygget/lofoten-vesteralen.md [--uten-bilde]
Kystdata til bildet fra tools/kystdata.py (privat/geodata/, sett NORDSURF_PRIVAT hvis privat/ ligger et annet sted)."""
import datetime as dt
import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import kallregnskap  # noqa: E402

KD = ROOT / "data" / "kandidater"
BYGGET = KD / "bygget"
PRIVAT = Path(os.environ.get("NORDSURF_PRIVAT") or ROOT / "privat")
VERN_RAA = PRIVAT / "kandidater" / "bevis" / "vern"
HEMMELIGE = PRIVAT / "kandidater" / "hemmelige.json"
FARGER = {"publisert": "#22A36B", "holdt tilbake": "#BF8A00", "bygget forslag": "#0B7483", "parkert": "#4A4A4A",
          "venter på lokalkunnskap": "#7A5BA8", "ikke bygget": "#B8402A"}


def les(p, default=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def vern_oppslag(kid, pos):
    """Verneområdene innen 2 km av pos med avstand derfra, fra Naturbase-oppslaget kandidat_triage.py lagret rundt
    posisjonsforslaget (privat/kandidater/bevis/vern/). None når det ikke finnes noe oppslag for akkurat denne posisjonen."""
    f = VERN_RAA / f"naturbase_{kid}_forslag_{pos['lat']:.5f}_{pos['lon']:.5f}.json"
    if not f.exists():
        return None
    from pyproj import Transformer
    from shapely.geometry import Point, shape
    x, y = Transformer.from_crs(4326, 25833, always_xy=True).transform(pos["lon"], pos["lat"])
    ut = []
    for ft in les(f).get("features", []):
        if ft.get("geometry"):
            a = ft["properties"]
            ut.append({"naturvernId": a.get("naturvernId"), "navn": a.get("offisieltNavn") or a.get("navn"),
                       "forskrift": a.get("verneforskrift"), "avstand_m": round(shape(ft["geometry"]).distance(Point(x, y)))})
    return sorted(ut, key=lambda h: h["avstand_m"])


def dist_m(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def retning(a, b):
    """Kompassretning (grader) fra a til b."""
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return math.degrees(math.atan2(y, x)) % 360


def fmt_w(w):
    if not w:
        return "–"
    return " + ".join(f"{a}–{b}°" for a, b in (w if isinstance(w[0], list) else [w]))


def bredde(w):
    if not w:
        return None
    return sum((b - a) % 360 for a, b in (w if isinstance(w[0], list) else [w]))


def vinkel(a, b):
    return abs((a - b + 180) % 360 - 180)


def utenfor_vindu(f, w):
    """Grader facing ligger utenfor nærmeste kant av vinduet (0 = innenfor)."""
    if f is None or not w:
        return 0
    deler = w if isinstance(w[0], list) else [w]
    if any((f - a) % 360 <= (b - a) % 360 for a, b in deler):
        return 0
    return min(min(vinkel(f, a), vinkel(f, b)) for a, b in deler)


def midt(w):
    a, b = w if not isinstance(w[0], list) else max(w, key=lambda x: (x[1] - x[0]) % 360)
    return (a + ((b - a) % 360) / 2) % 360


def ll(p, n=6):
    return f"{round(p['lat'], n)}, {round(p['lon'], n)}" if p else "–"


def celle(t):
    return str(t).replace("|", "/").replace("\n", " ")


class Region:
    def __init__(self, regioner):
        self.regioner = regioner
        self.cfg = les(ROOT / "spots.json")
        self.spots = {s["id"]: s for s in self.cfg["spots"]}
        alle = les(KD / "kandidater.json")["kandidater"]
        hemmelig = {x for k in alle if k["status"] == "hemmelig" for x in (k["id"], k.get("nordsurf_id")) if x}
        # de hemmelige ligger utenfor git (privat/kandidater/hemmelige.json) - finnes fila, holdes id-ene deres også ute
        hemmelig |= {x for k in les(HEMMELIGE, {"kandidater": []})["kandidater"] for x in (k.get("id"), k.get("nordsurf_id")) if x}
        self.kand_for = {k["nordsurf_id"]: k["id"] for k in alle if k.get("nordsurf_id") and k["status"] != "hemmelig"}
        self.kand = {k["id"]: k for k in alle
                     if k.get("region") in regioner and k["status"] != "hemmelig"}
        self.pos = les(KD / "posisjoner.json", {"kandidater": {}})["kandidater"]
        self.vern = les(KD / "vern.json", {"kandidater": {}})["kandidater"]
        self.forskrifter = les(KD / "vern_forskrifter.json", {"forskrifter": {}})["forskrifter"]
        self.parkert = les(KD / "status_overstyring.json", {"kandidater": {}})["kandidater"]
        self.baseline = les(ROOT / "data" / "exposure_baseline.json", {})
        self.bygget = {}
        for f in BYGGET.glob("*.json"):
            if not f.stem.startswith("validering"):
                self.bygget[f.stem] = les(f)
        # spots i regionen som ikke står i kandidatlista under samme id (f.eks. unstad mot unstad-beach)
        self.ids = sorted(set(self.kand) | {i for i, s in self.spots.items() if s.get("region") in regioner and i not in hemmelig})

    def navn(self, i):
        return (self.spots.get(i) or self.kand.get(i) or {}).get("name", i)

    def region(self, i):
        return (self.spots.get(i) or self.kand.get(i) or {}).get("region", "–")

    def spot(self, i):
        """Oppføringen som gjelder: spots.json hvis spoten ligger der, ellers fabrikkens forslag."""
        return self.spots.get(i) or (self.bygget.get(i) or {}).get("spot")

    def status(self, i):
        s = self.spots.get(i)
        if s:
            return "publisert" if s.get("enabled") else "holdt tilbake"
        k = self.kand.get(i, {})
        if k.get("status") == "i_nordsurf":
            return None   # samme spot under en annen id i spots.json
        if i in self.parkert or k.get("status") == "parkert":
            return "parkert"
        if (self.pos.get(i) or {}).get("vurdering") == "venter_lokalkunnskap":
            return "venter på lokalkunnskap"
        return "bygget forslag" if i in self.bygget else "ikke bygget"

    def sikkerhet(self, i):
        p = self.pos.get(i) or {}
        fra = (self.bygget.get(i) or {}).get("bygget_fra") or {}
        if fra.get("sikkerhet"):
            return fra["sikkerhet"]
        if p.get("sikkerhet") in ("A", "B", "C"):
            return p["sikkerhet"]
        f = [x.get("sikkerhet") for x in p.get("forslag", []) if x.get("sikkerhet")]
        if f and self.status(i) != "publisert":
            return f"{f[-1]} (forslag, ikke godkjent)"
        return "– (lå i appen før kandidatlista)" if i not in self.kand else "ikke sjekket"

    def posisjonskilde(self, i):
        p, k, s = self.pos.get(i) or {}, self.kand.get(i) or {}, self.spot(i)
        fra = (self.bygget.get(i) or {}).get("bygget_fra") or {}
        if not p and not fra:
            return "spots.json (satt før kandidatlista)" if i in self.spots else "–"
        f = next((x for x in p.get("forslag", []) if s and abs(x["lat"] - s["spot"]["lat"]) < 1e-6
                  and abs(x["lon"] - s["spot"]["lon"]) < 1e-6), None)
        t = []
        if p.get("vurdering") == "godkjent":
            t.append(f"{p.get('metode', 'godkjent')}, {p.get('satt_av')}, {p.get('dato')}")
        elif fra:
            t.append(f"forslag {fra.get('kilde')} (ikke godkjent ennå)")
        else:
            t.append(f"{p.get('metode', '–')} ({p.get('satt_av', '–')})")
        pin = k.get("pin_liste")
        if pin and s:
            t.append(f"{dist_m(pin, s['spot']):.0f} m fra listepinnen")
        b = (f or {}).get("begrunnelse") or (p.get("begrunnelse") if p.get("vurdering") == "godkjent" else None)
        if b:
            t.append(b)
        return ". ".join(t)

    def forslag_tekst(self, i):
        """Siste posisjonsforslag for en spot som ikke er bygget (posisjonen som vises er listepinnen)."""
        p = self.pos.get(i) or {}
        f = (p.get("forslag") or [None])[-1]
        if not f:
            return "–"
        flyttet = f"flyttet {dist_m(p['spot'], f):.0f} m fra listepinnen" if p.get("spot") else ""
        return (f"{ll(f)} ({f.get('satt_av', '–')}, sikkerhet {f.get('sikkerhet', '–')}, ikke godkjent; {flyttet}). "
                f"{f.get('begrunnelse') or ''}").strip()

    def bw(self, i):
        """(tekst, punkt) for BarentsWatch-punktet: koordinat, avstand og retning fra spoten, dybde."""
        s = self.spot(i)
        p = s.get("barentswatch_point") if s else None
        if not p:
            return ("ikke funnet (se «Usikkert»)" if i in self.parkert else "**mangler**"), None
        snitt = [r for b in self.bygget.values() for r in b.get("snitt", [])]   # punktet kan være lånt fra nabospoten
        row = next((r for r in snitt if abs(r["lat"] - p["lat"]) < 1e-6 and abs(r["lon"] - p["lon"]) < 1e-6), None)
        dyp = f"{row['dybde_m']} m dyp" if row and row.get("dybde_m") is not None else "dybde ukjent"
        t = f"{ll(p)} ({dist_m(s['spot'], p):.0f} m ut i retning {retning(s['spot'], p):.0f}°, {dyp})"
        return ("foreløpig: " if "FORELØPIG" in (s.get("_barentswatch") or "") else "") + t, p

    def eksponering(self, i):
        s = self.spot(i)
        t = []
        if s.get("exposure_override") is not None:
            t.append(f"exposure_override {s['exposure_override']}")
        w, f = s.get("swell_window"), s.get("facing")
        if w:
            t.append(f"vindu {bredde(w)}° bredt" + (f", facing {vinkel(f, midt(w)):.0f}° fra midten" if f is not None else ""))
        else:
            t.append("ingen fri linje til åpent hav")
        t.append("geometrisk grunnlinje finnes (data/exposure_baseline.json)" if i in self.baseline
                 else "ingen geometrisk grunnlinje ennå - henteren bruker vindu og skyggekurve som reserve")
        return "; ".join(t)

    def vern_tekst(self, i):
        """Vern målt fra spotens egen posisjon når Naturbase-oppslaget rundt den finnes (ellers fra listepinnen, og det står da)."""
        t = []
        for r in (self.spots.get(i) or {}).get("restriksjoner") or []:
            t.append(f"**restriksjon i appen:** {json.dumps(r, ensure_ascii=False)}")
        kid = i if i in self.kand else self.kand_for.get(i)
        if kid is None:
            return "<br>".join(t) or "ikke sjekket (står ikke i kandidatlista)"
        s = self.spot(i)
        pos = s["spot"] if s else ((self.pos.get(kid) or {}).get("forslag") or [None])[-1]
        opp = vern_oppslag(kid, pos) if pos else None
        fra = "listepinnen" if opp is None else ("spoten" if s else "forslaget")
        kjent = {v.get("naturvernId"): v for v in self.vern.get(kid) or []}
        for h in (self.vern.get(kid) or []) if opp is None else opp:
            v = kjent.get(h["naturvernId"])
            if v is None:   # området ligger innen 2 km av spoten, men ikke av listepinnen
                m = re.search(r"forskrift/(\d{4}-\d{2}-\d{2}-\d+)", h.get("forskrift") or "")
                fs = self.forskrifter.get(m.group(1)) if m else None
                rs = [x for x in (fs or {}).get("restriksjoner", []) if not x.get("verneomrade") or x["verneomrade"] == h["navn"]]
                v = {"restriksjoner": rs, "lest": fs is not None, "merknad": (fs or {}).get("merknad")}
            r = "; ".join(f"{x.get('type')} ({x.get('gjelder')}, {x.get('paragraf')})" for x in v.get("restriksjoner") or [])
            sted = f"{fra} ligger inne i området" if h["avstand_m"] == 0 else f"{h['avstand_m']} m fra {fra}"
            if opp is not None and v.get("avstand_m") is not None and v["avstand_m"] != h["avstand_m"]:
                sted += f" (listepinnen: {v['avstand_m']} m)"
            t.append(f"{h['navn']}, {sted}: "
                     + (r or v.get("merknad") or ("forskriften ikke lest" if not v.get("lest") else "ingen ferdselsforbud funnet")))
        m = (self.kand.get(kid) or {}).get("vern_merknad")
        if m:
            t.append(("Merknad fra kandidatlista (skrevet om listepinnen): " if opp is not None else "") + m)
        return "<br>".join(t) or f"ingen verneområder innen 2 km av {fra}"

    def usikkert(self, i):
        s, b, p = self.spot(i) or {}, self.bygget.get(i) or {}, self.pos.get(i) or {}
        t = list(b.get("flagg") or [])
        bs = b.get("spot") or {}
        if i in self.spots and bs:
            avvik = [k for k in ("facing", "swell_window", "offshore_wind", "barentswatch_point") if bs.get(k) != s.get(k)]
            if avvik:
                t.append("minikartet er tegnet fra fabrikkens bygg; spots.json er rettet etterpå for " + ", ".join(avvik) + " (tabellen viser spots.json)")
        ute = utenfor_vindu(s.get("facing"), s.get("swell_window"))
        if ute >= 1:
            t.append(f"facing {s['facing']}° ligger {ute:.0f}° utenfor eget svellvindu ({fmt_w(s['swell_window'])})")
        if s.get("_holdt_tilbake"):
            t.append(s["_holdt_tilbake"])
        bp = s.get("barentswatch_point")
        if bp and s.get("facing") is not None:
            skjev = vinkel(retning(s["spot"], bp), s["facing"])
            if skjev > 20:
                t.append(f"BarentsWatch-punktet ligger i retning {retning(s['spot'], bp):.0f}°, {skjev:.0f}° fra facing {s['facing']}° "
                         "(snittet og de grå prikkene på minikartet følger retningen snittet ble tatt i)")
            if dist_m(s["spot"], bp) > 1500:
                t.append(f"BarentsWatch-punktet ligger {dist_m(s['spot'], bp):.0f} m ut, utenfor fabrikkens 1,5 km: lavere sikkerhet")
        if "FORELØPIG" in (s.get("_barentswatch") or ""):
            t.append("BarentsWatch-punktet er foreløpig (bare dybde) - snittet i Actions er ikke kjørt")
        if any(x in (s.get("_offshore_vind") or "") for x in ("ubekreftet", "ukalibrert")):
            t.append(f"offshore-vind: {s['_offshore_vind']}")
        if s and s.get("ideal_height") is None:
            t.append("ideal_height/max_height mangler (ikke beachbreak) - må settes")
        elif "ukalibrert" in (s.get("_ideal_height") or ""):
            t.append(f"ideal_height {s.get('ideal_height')} / max_height {s.get('max_height')}: {s['_ideal_height']}")
        for k, v in (s.get("_rettet") or {}).items():
            if k not in ("ideal_height/max_height",):
                t.append(f"{k} rettet: {v}")
        if i in self.parkert:
            t.append(self.parkert[i]["begrunnelse"])
        if p.get("vurdering") == "venter_lokalkunnskap" and p.get("begrunnelse"):
            t.append(p["begrunnelse"])
        return t

    def tidevann(self, i):
        tz = ((self.bygget.get(i) or {}).get("spot") or {}).get("tidevann") or {}
        if not tz.get("name"):
            return "slås opp av henteren (Kartverket)" if i in self.spots else "–"
        d = tz.get("delay")
        return f"{tz['name']}" + (f" ({d} min)" if d not in (None, "0") else "") + (f", faktor {tz['factor']}" if tz.get("factor") else "")


def oversiktsbilde(R, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shapely
    import kystdata
    pts = [(i, R.spot(i)["spot"], R.status(i)) for i in R.ids if R.status(i) and R.spot(i)]
    pts += [(i, R.pos[i]["spot"], R.status(i)) for i in R.ids if R.status(i) and not R.spot(i) and (R.pos.get(i) or {}).get("spot")]
    if not pts:
        return False
    la = [p["lat"] for _, p, _ in pts]
    lo = [p["lon"] for _, p, _ in pts]
    la0, la1 = min(la) - 0.12, max(la) + 0.12
    k = math.cos(math.radians((la0 + la1) / 2))
    half = max((max(lo) - min(lo)) / 2 + 0.3, (la1 - la0) / 2 / k * 1.0)
    lo0, lo1 = (min(lo) + max(lo)) / 2 - half, (min(lo) + max(lo)) / 2 + half
    land = shapely.clip_by_rect(kystdata.land("osm"), lo0, la0, lo1, la1).simplify(0.0008)
    fig, ax = plt.subplots(figsize=(11, 11 * (la1 - la0) / ((lo1 - lo0) * k)), dpi=110)
    ax.set_facecolor("#B7D3DF")
    for g in getattr(land, "geoms", [land]):
        if g.geom_type == "Polygon":
            ax.fill(*g.exterior.xy, color="#F2EDE2", ec="#8F8268", lw=0.4)
    ax.set_xlim(lo0, lo1)
    ax.set_ylim(la0, la1)
    ax.set_aspect(1 / k)
    sett = set()
    lag = list(FARGER)[::-1]   # publisert og holdt tilbake tegnes øverst (g-frame lå skjult under g-force, 131 m unna)
    for i, p, st in sorted(pts, key=lambda x: -x[1]["lat"]):
        ax.plot(p["lon"], p["lat"], "o", ms=7, color=FARGER[st], mec="white", label=None if st in sett else st,
                zorder=3 + lag.index(st) / 10)
        sett.add(st)
    # etikettene: første ledige plass rundt punktet (spotene ligger tett i Unstad- og Flakstad-bukta), med strek inn
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    opptatt = [ax.transData.transform((p["lon"], p["lat"])) for _, p, _ in pts]
    bokser = []
    plasser = [(dx * r, dy * r) for r in (9, 22, 38, 56, 76) for dx, dy in
               ((1, 0.5), (1, -0.6), (-1, 0.5), (-1, -0.6), (0.2, 1.2), (0.2, -1.3), (1.4, 0), (-1.4, 0))]
    for i, p, st in sorted(pts, key=lambda x: -x[1]["lat"]):
        valgt = None
        for dx, dy in plasser:
            a = ax.annotate(i, (p["lon"], p["lat"]), xytext=(dx, dy), textcoords="offset points", fontsize=7, zorder=4,
                            ha="left" if dx >= 0 else "right", va="center",
                            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8),
                            arrowprops=dict(arrowstyle="-", lw=0.5, color="#555555") if abs(dx) + abs(dy) > 16 else None)
            bb = a.get_window_extent(rend).expanded(1.04, 1.25)
            fri = (not any(bb.overlaps(b) for b in bokser)
                   and not any(bb.x0 <= x <= bb.x1 and bb.y0 <= y <= bb.y1 for x, y in opptatt))
            if fri or (dx, dy) == plasser[-1]:
                valgt = bb
                break
            a.remove()
        bokser.append(valgt)
    ax.tick_params(labelsize=6)
    ax.set_title(f"{', '.join(sorted(R.regioner))}: {len(pts)} spots, {dt.date.today().isoformat()}", fontsize=9)
    ax.legend(loc="lower right", fontsize=7)
    ax.text(0.01, 0.01, "© OpenStreetMap-bidragsytere", transform=ax.transAxes, fontsize=6)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return True


def kallbudsjett(R):
    aktive = [s for s in R.cfg["spots"] if s.get("enabled")]
    ekstra = [R.spot(i) for i in R.ids if R.status(i) in ("holdt tilbake", "bygget forslag") and (R.spot(i) or {}).get("offshore")]
    rows = [("i dag (publiserte)", kallregnskap.regnskap(aktive)),
            (f"med alle {len(ekstra)} ventende i regionen slått på", kallregnskap.regnskap(aktive + ekstra))]
    L = ["| | Spots | Open-Meteo vektet per kjøring | per døgn (grense 10 000) | verste time (5 000) | verste minutt (600) | BarentsWatch per kjøring / døgn | met.no per kjøring | Kartverket per kjøring |",
         "|---|---|---|---|---|---|---|---|---|"]
    for navn, r in rows:
        d, u = kallregnskap.per_day(r), kallregnskap.utnyttelse(r)
        L.append(f"| {navn} | {r['spots']} | {r['Open-Meteo']['vektet']:.0f} | {d['døgn']:.0f} ({u['døgn']:.0%}) | {d['time']:.0f} ({u['time']:.0%}) | "
                 f"{d['minutt']:.0f} ({u['minutt']:.0%}) | {r['BarentsWatch']} / {r['BarentsWatch'] * kallregnskap.RUNS_PER_DAY} | {r['met.no']} | {r['Kartverket']} |")
    return L


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    R = Region(set(args[0].split(",")))
    out = Path(args[1])
    ids = [i for i in R.ids if R.status(i)]
    n = {st: sum(1 for i in ids if R.status(i) == st) for st in FARGER}
    bilde = out.with_name(out.stem + "-oversikt.png")
    har_bilde = bilde.exists() if "--uten-bilde" in sys.argv else oversiktsbilde(R, bilde)
    L = [f"# Gjennomgangspakke: {', '.join(sorted(R.regioner))} ({len(ids)} spots)", "",
         f"Laget {dt.date.today().isoformat()} av tools/region_pakke.py fra spots.json (gjelder der spoten ligger inne) og fabrikkens forslag "
         "(data/kandidater/bygget/<id>.json). " + ", ".join(f"{v} {k}" for k, v in n.items() if v) + ".", "",
         "Vindu: fri linje 150 km over GSHHS f (300 m kysttoleranse). Facing: strandnormal ±150 m langs kysten. Offshore-vind: motsatt av "
         "facing ±45° når ikke annet står. BarentsWatch-punkt: snittregelen 15.10 (første punkt utover med minst 8 m dyp og flat Hs). "
         "Tidevann: Kartverkets referansested for posisjonen. Vern: Naturbase innen 2 km, målt fra spotens posisjon der oppslaget finnes "
         "(ellers fra listepinnen, og da står det), forskriften lest på Lovdata. "
         "Sikkerhet: A = navn, strandtype, synlig bølge/formasjon og retning stemmer; B = to av fire; C = resten (bygges ikke)."]
    if har_bilde:
        L += ["", f"![Oversikt]({bilde.name})"]
    notat = out.with_name(out.stem + ".notater.md")
    if notat.exists():
        L += ["", notat.read_text(encoding="utf-8").strip()]
    L += ["", "## Oversikt", "",
          "| id | Navn | Region | Status | Sikkerhet | facing | Vindu | Offshore-vind | BarentsWatch-punkt |", "|---|---|---|---|---|---|---|---|---|"]
    for i in ids:
        s = R.spot(i) or {}
        L.append(f"| {i} | {R.navn(i)} | {R.region(i)} | {R.status(i)} | {R.sikkerhet(i)} | {str(s.get('facing')) + '°' if s.get('facing') is not None else '–'} | "
                 f"{fmt_w(s.get('swell_window'))} | {fmt_w(s.get('offshore_wind'))} | {celle(R.bw(i)[0]) if s else '–'} |")
    tilbake = [i for i in ids if R.status(i) in ("holdt tilbake", "parkert", "venter på lokalkunnskap", "ikke bygget")]
    if tilbake:
        L += ["", "## Holdes tilbake, parkert eller ikke bygget", "", "| id | Status | Hvorfor |", "|---|---|---|"]
        for i in tilbake:
            hvorfor = ((R.spots.get(i) or {}).get("_holdt_tilbake") or (R.parkert.get(i) or {}).get("begrunnelse")
                       or (R.pos.get(i) or {}).get("begrunnelse") or "posisjonen er ikke kontrollert (listepinne)")
            L.append(f"| {i} | {R.status(i)} | {celle(hvorfor)} |")
    L += ["", "## Kallbudsjett", ""] + kallbudsjett(R)
    L += ["", "Open-Meteo: vekt 1,14 per punkt (16 dager), to bølgemodeller per havpunkt og ett vindpunkt per spot, 8 kjøringer per døgn; "
          "verste minutt regner alle kall i en kjøring i samme minutt. Testen fetcher/test_kallregnskap.py holder hver grense under 50 %.",
          "", "## Spotene"]
    for i in ids:
        s = R.spot(i)
        L += ["", f"### {R.navn(i)} (`{i}`) - {R.status(i)}", ""]
        if not s:
            p = R.pos.get(i) or {}
            L += ["| | |", "|---|---|", f"| Posisjon | {ll(p.get('spot'))} - listepinnen (ikke kontrollert) |",
                  f"| Forslag | {celle(R.forslag_tekst(i))} |",
                  f"| Sikkerhet | {R.sikkerhet(i)} |", f"| Vern/forbud | {celle(R.vern_tekst(i))} |",
                  f"| Usikkert | {celle('<br>'.join(R.usikkert(i)) or '–')} |"]
            continue
        hav = s.get("offshore")
        L += ["| | |", "|---|---|",
              f"| Posisjon | {ll(s['spot'])} - {celle(R.posisjonskilde(i))} |",
              f"| Facing | {str(s['facing']) + '°' if s.get('facing') is not None else '–'} |",
              f"| Svellvindu | {fmt_w(s.get('swell_window'))} |",
              f"| Offshore-vind | {fmt_w(s.get('offshore_wind'))} |",
              f"| Havpunkt | {ll(hav, 4)}" + (f" ({dist_m(s['spot'], hav) / 1000:.0f} km ut i retning {retning(s['spot'], hav):.0f}°)" if hav else "") + " |",
              f"| BarentsWatch-punkt | {celle(R.bw(i)[0])}" + (f"<br>{celle(s['_barentswatch'])}" if s.get("_barentswatch") else "") + " |",
              f"| Eksponering | {R.eksponering(i)} |",
              f"| Tidevannssted | {R.tidevann(i)} |",
              f"| Høyder | ideal {s.get('ideal_height') or '–'}, maks {s.get('max_height') or '–'} |",
              f"| Vern/forbud | {celle(R.vern_tekst(i))} |",
              f"| Sikkerhet | {R.sikkerhet(i)} |",
              f"| Usikkert | {celle('<br>'.join(R.usikkert(i)) or '–')} |"]
        if (BYGGET / f"{i}.png").exists():
            L += ["", f"![{i}]({i}.png)"]
    L += ["", "Kyst © OpenStreetMap-bidragsytere og GSHHS; dybde EMODnet Bathymetry; tidevann © Kartverket; bølger BarentsWatch; vern Naturbase (Miljødirektoratet)."]
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Skrev {out} ({len(ids)} spots)" + (f" og {bilde.name}" if har_bilde else ""))


if __name__ == "__main__":
    main()
