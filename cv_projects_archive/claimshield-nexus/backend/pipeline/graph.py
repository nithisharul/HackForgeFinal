"""Network detection on the provider-member bipartite graph.

1. Project to provider-provider edges weighted by shared members, kept only when
   the overlap is far above what the local member pool would give by chance (lift).
2. Leiden community detection on that graph -> candidate rings.
3. Referral cycles (strongly connected components) and shared ownership per ring.
4. BiRank: propagate risk from seed providers through shared members.
"""
from collections import Counter
from itertools import combinations

import networkx as nx
import numpy as np
import pandas as pd
from scipy import sparse


def communities(G):
    try:
        import igraph as ig
        import leidenalg
        nodes = list(G.nodes)
        idx = {n: i for i, n in enumerate(nodes)}
        g = ig.Graph(n=len(nodes), edges=[(idx[a], idx[b]) for a, b in G.edges])
        g.es["weight"] = [G[a][b]["weight"] for a, b in G.edges]
        part = leidenalg.find_partition(g, leidenalg.ModularityVertexPartition, weights="weight", seed=0)
        return [[nodes[i] for i in c] for c in part], "leiden"
    except ImportError:  # fall back so the pipeline still runs without leidenalg
        return [list(c) for c in nx.community.louvain_communities(G, weight="weight", seed=0)], "louvain"


def birank(claims, seeds, alpha=0.85, iters=60):
    provs = sorted(claims.provider_id.unique())
    mems = sorted(claims.member_id.unique())
    pi = {p: i for i, p in enumerate(provs)}
    mi = {m: i for i, m in enumerate(mems)}
    w = claims.groupby(["provider_id", "member_id"]).size().reset_index(name="n")
    W = sparse.csr_matrix((w.n, (w.provider_id.map(pi), w.member_id.map(mi))), shape=(len(provs), len(mems)), dtype=float)
    dp = np.asarray(W.sum(1)).ravel()
    dm = np.asarray(W.sum(0)).ravel()
    S = sparse.diags(1 / np.sqrt(dp)) @ W @ sparse.diags(1 / np.sqrt(dm))
    p0 = np.array([seeds.get(p, 0.0) for p in provs])
    p0 = p0 / p0.sum() if p0.sum() > 0 else p0
    p = p0.copy()
    for _ in range(iters):
        m = S.T @ p
        p = alpha * (S @ m) + (1 - alpha) * p0
    return pd.Series(p / p.max() if p.max() > 0 else p, index=provs)


def run(claims, prov, members, referrals, seeds):
    P = prov.set_index("provider_id")
    nm = claims.groupby("provider_id").member_id.nunique()
    city_n = members.groupby("city").size()

    shared = Counter()
    for ps in claims.groupby("member_id").provider_id.unique():
        for a, b in combinations(sorted(ps), 2):
            shared[(a, b)] += 1
    ref = referrals.groupby(["from_provider_id", "to_provider_id"]).size().to_dict()

    pairs = {k for k, v in shared.items() if v >= 5}
    pairs |= {tuple(sorted(k)) for k, v in ref.items() if v >= 5 and k[0] != k[1]}
    for _, grp in prov.groupby("owner_id"):
        pairs |= set(combinations(sorted(grp.provider_id), 2))
    rows = []
    for a, b in pairs:
        s = shared.get((a, b), 0)
        expected = nm[a] * nm[b] / city_n[P.city[a]]
        rows.append({"a": a, "b": b, "shared": s, "lift": round(s / expected, 2) if expected else 0.0,
                     "ref_ab": ref.get((a, b), 0), "ref_ba": ref.get((b, a), 0),
                     "same_owner": int(P.owner_id[a] == P.owner_id[b])})
    edges = pd.DataFrame(rows)

    G = nx.Graph()
    for r in edges[(edges.shared >= 15) & (edges.lift >= 3)].itertuples():
        G.add_edge(r.a, r.b, weight=r.shared)
    comms, method = communities(G) if G.number_of_edges() else ([], "none")

    D = nx.DiGraph()
    D.add_edges_from(k for k, v in ref.items() if v >= 15)
    in_cycle = set().union(*[c for c in nx.strongly_connected_components(D) if len(c) >= 3] or [set()])

    net = pd.DataFrame({"provider_id": prov.provider_id, "cluster_id": "", "cluster_score": 0.0})
    net["in_referral_cycle"] = net.provider_id.isin(in_cycle).astype(int)
    clusters = {}
    for i, comm in enumerate([c for c in comms if len(c) >= 3], start=1):
        cid = f"N{i:02d}"
        comm = sorted(comm)
        owners = P.owner_id[comm].value_counts()
        owner_share = float(owners.iloc[0] / len(comm))
        cyc = sum(p in in_cycle for p in comm) / len(comm)
        sub = claims[claims.provider_id.isin(comm)]
        seen = sub.groupby("member_id").provider_id.nunique()
        shared_members = set(seen[seen >= 3].index)
        score = 0.5 + 0.25 * (owner_share >= 0.5) + 0.25 * (cyc >= 0.5)
        clusters[cid] = {
            "cluster_id": cid, "providers": comm, "size": len(comm), "method": method,
            "top_owner": owners.index[0], "owner_share": round(owner_share, 2),
            "referral_cycle": bool(cyc >= 0.5), "shared_members": len(shared_members),
            "shared_member_ids": sorted(shared_members),
            "paid_on_shared_members": round(float(sub[sub.member_id.isin(shared_members)].paid_amount.sum()), 2),
            "score": score,
        }
        net.loc[net.provider_id.isin(comm), ["cluster_id", "cluster_score"]] = [cid, score]

    net["birank"] = net.provider_id.map(birank(claims, seeds)).fillna(0).round(4)
    return net, edges, clusters
