"""Gera dados.json para a pagina ao vivo no GitHub Pages.

Busca os arquivos por UF do TSE (2o turno, eleicao 6258), calcula a
apuracao crua e a projecao pelo modelo por estado (votos / fracao de
secoes totalizadas, somando as UFs), e escreve o JSON que a pagina le.

Uso: TSE_ELEICAO_2T_ID=6258 python3 gerar_dados.py [saida.json]
Padrao: ~/workspace/eleicoes-2026/github-pages/dados.json
Nunca inventa numero: se uma UF falhar, ela entra em ufs_sem_dados e
os totais somam so as UFs com dados.
"""
import json, urllib.request, datetime, os, sys

ELEICAO_ID = os.environ.get("TSE_ELEICAO_2T_ID", "6258").strip()
BASE = f"https://resultados.tse.jus.br/oficial/ele2026/{ELEICAO_ID}/dados"
ARQ = f"e{int(ELEICAO_ID):06d}"
UFS = ["ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa", "pb",
       "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to"]
NOMES = {"FLAVIO BOLSONARO": "Bolsonaro", "LULA": "Lula"}
NOMES_UF = {"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
            "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
            "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
            "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
            "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
            "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SE": "Sergipe",
            "SP": "São Paulo", "TO": "Tocantins"}

def fetch(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def parse(data):
    out = {}
    for agr in data["carg"][0]["agr"]:
        for par in agr["par"]:
            for cand in par["cand"]:
                out[cand["nmu"]] = int(cand["vap"])
    return out

def main():
    saida = sys.argv[1] if len(sys.argv) > 1 else \
        "/home/hatch/workspace/eleicoes-2026/github-pages/dados.json"
    estados, sem_dados = {}, []
    tf_all = True
    for uf in UFS:
        try:
            d = fetch(f"/{uf}/{uf}-c0001-{ARQ}-u.json")
        except Exception:
            sem_dados.append(uf.upper()); continue
        ts, st = int(d["s"]["ts"]), int(d["s"]["st"])
        if d.get("tf") != "s":
            tf_all = False
        votos = parse(d)
        frac = st / ts if ts else 0
        proj = {n: (v / frac if frac else 0) for n, v in votos.items()}
        estados[uf.upper()] = {"nome": NOMES_UF[uf.upper()], "secoes_totais": ts,
                               "secoes_apuradas": st, "fracao": frac,
                               "votos": votos, "projetado": proj}
    tot_ts = sum(e["secoes_totais"] for e in estados.values())
    tot_st = sum(e["secoes_apuradas"] for e in estados.values())
    frac = tot_st / tot_ts if tot_ts else 0
    votos_tot, proj_tot = {}, {}
    for e in estados.values():
        for n, v in e["votos"].items():
            votos_tot[n] = votos_tot.get(n, 0) + v
        for n, v in e["projetado"].items():
            proj_tot[n] = proj_tot.get(n, 0) + v
    tot_v, tot_p = sum(votos_tot.values()), sum(proj_tot.values())
    def share(d, tot):
        return {NOMES.get(n, n): (100 * v / tot if tot else 0) for n, v in d.items()}
    agora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    out = {
        "atualizado_em": agora.strftime("%H:%M"),
        "atualizado_iso": agora.isoformat(),
        "eleicao": ELEICAO_ID,
        "secoes_pct": 100 * frac,
        "secoes_apuradas": tot_st,
        "secoes_totais": tot_ts,
        "votos_validos_apurados": tot_v,
        "votos_validos_projetados": tot_p,
        "cru_votos": votos_tot,
        "cru_pct": share(votos_tot, tot_v),
        "proj_votos": proj_tot,
        "proj_pct": share(proj_tot, tot_p),
        "definida": bool(tf_all and estados) or frac >= 0.995,
        "ufs_sem_dados": sem_dados,
        "estados": estados,
    }
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    json.dump(out, open(saida, "w"), ensure_ascii=False)
    print(f"dados.json escrito: {100*frac:.1f}% apurado, {tot_v} votos validos, "
          f"projecao {share(proj_tot, tot_p)}")

if __name__ == "__main__":
    main()
